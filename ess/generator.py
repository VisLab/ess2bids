"""
This module contains functions that map an ESS file structure into a BIDSProject object

This module also places recommendations in 'field_replacements.json' file attributes that need
to be changed in order for the output BIDS study to be considered BIDS compliant
"""

__all__ = ["generate_bids_project", "generate_report", "LXMLDecodeError"]

import datetime
import io
import re
import os.path

from ess.definitions import *
from structure.project import BIDSProject, channel_types
from structure.task import BIDSTask
from structure.subject import BIDSSession, BIDSScan, BIDSSubject
from xml_extractor.ess2obj import extract_description
from utilities.matlab_instance import get_matlab_instance

DISPLAY_VALS = None
DISPLAY_MATLAB_OUTPUT = None


def generate_bids_project(input_directory, verbose=False) -> BIDSProject:
    """
    Converts an ESS structure into a BIDSProject

    :param input_directory: Source filepath for a given ESS study
    :param verbose: If set to True, additional logging is provided to standard output
    :return: BIDSProject object mapped from ESS file structure
    """

    global DISPLAY_MATLAB_OUTPUT, DISPLAY_VALS

    DISPLAY_MATLAB_OUTPUT = verbose
    DISPLAY_VALS = verbose

    try:
        full_xml = extract_description(os.path.join(input_directory, "study_description.xml"))
    except IOError:
        try:
            input_directory = os.path.join(input_directory, "Level1/")
            full_xml = extract_description(os.path.join(input_directory, "study_description.xml"))
        except (IOError, OSError):
            raise IOError("ESS project directory doesn't contain 'study_description.xml'")
        except Exception as e:
            raise LXMLDecodeError(input_directory, e)
    except Exception as e:
        raise LXMLDecodeError(input_directory, e)

    header = full_xml['head']

    bids_file = BIDSProject(os.path.basename(input_directory))
    bids_file.init_dataset_description(header['Title'], header['Study License'],
                                       funding=[header['Funding Organization']])
    bids_file.original_path = input_directory
    bids_file.readme = f"Description: {header['Description']}\nLegacy UUID: {header['UUID']}\n"
    bids_file.changes = "1.0.0 - %s\n - Initial Release" % datetime.date.today()

    print("Reading project %s..." % input_directory)
    _generate_bids_sessions(bids_file, full_xml, input_directory)
    _generate_bids_tasks(bids_file, full_xml)

    for event_code in full_xml['event_codes']:
        if event_code['No. instances'] == 0:
            pass
        elif event_code['Task Label'] and bids_file.tasks[underscore_to_camelcase(event_code['Task Label'])]:
            bids_file.tasks[underscore_to_camelcase(event_code['Task Label'])].event_codes[event_code['Code']] = \
            event_code['HED Tag']
        else:
            bids_file.event_codes[event_code['Code']] = event_code['HED Tag']

    print('Finalizing product...')

    bids_file.ignored_files.append(os.path.join(input_directory, "additional_documentation"))
    return bids_file


def generate_report(bids_file: BIDSProject) -> str:
    """
    Function used to indicate information/warnings regarding the conversion from ESS

    Prints disclaimers about all conversions, as well as project specific issues that may affect compliance

    :param bids_file:
    :return: A large string containing part of the report from the conversion.
    """
    warnings_list = []
    report = disclaimer

    for subject_name, subject in bids_file.subjects.items():
        for session_name, session in subject.sessions.items():
            if session.electrodes and not session.coordsystem:
                warnings_list.append(
                    "Warning: session %s specifies electrodes, but no coordinate system" % session_name)
            for filename, scan in session.scans.items():
                if list(session.electrodes.keys()) != list(
                        filter(lambda x: scan.channels[x]['type'] == 'EEG', scan.channels.keys())):
                    warnings_list.append(
                        "Warning: session %s has mismatched electrodes with %s" % (session_name, filename))

    if len(bids_file.event_codes) > 1 and len(bids_file.tasks) > 1:
        warnings_list.append("Warning: some eventCodes fail to specify a taskLabel")

    if len(warnings_list) > 0:
        report += "\n\n === WARNINGS === \n\n"
        for warning in warnings_list:
            report += warning + "\n"

    return report


def _generate_bids_sessions(bids_file, xml, input_directory):
    """
    Internal function used to pick apart each session of a given ESS study, and map it to BIDS

    :param bids_file: BIDSProject, which fields are changed in place
    :param xml: Dictionary representation of 'study_description.xml'
    :param input_directory: Source filepath for a given ESS study
    :return:
    """

    subject_num = 0
    subject_dict = dict()
    RPS_electrodes = dict()
    session_numbers = dict()

    matlab_out = io.StringIO()
    matlab_err = io.StringIO()

    for session_key, session_parent in xml['sessions'].items():
        for session in session_parent: # multiple sessions may be indexed on the same number, therefore each number is its own list of sessions
            task_name = underscore_to_camelcase(str(session['Task Label']))
            if task_name not in bids_file.tasks:
                bids_file.tasks[task_name] = BIDSTask()
                bids_file.tasks[task_name].add_field("TaskName", task_name)

            for subject_key, subject in session['Subjects'].items():

                if subject_key not in subject_dict.keys():
                    subject_num += 1
                    subject_id = "%02d" % subject_num

                    if DISPLAY_VALS:
                        print("Adding Subject %s to Structure..." % subject_id, flush=True)

                    subject_dict[subject_key] = subject_id
                    bids_file.subjects[subject_id] = BIDSSubject()

                    for field in subject.keys():
                        if field.lower().replace(" ", "_") in participant_level_tags.keys() and subject[field] != "n/a":
                            bids_file.subjects[subject_id].fields[field.lower().replace(" ", "_")] = subject[field]
                            bids_file.field_definitions[field.lower().replace(" ", "_")] = participant_level_tags[
                                field.lower().replace(" ", "_")]

                    bids_file.subjects[subject_id].fields['legacy_labID'] = subject_key
                    bids_file.field_definitions['legacy_labID'] = participant_level_tags['legacy_labID']

                subject_id = subject_dict[subject_key]

                if session_key not in session_numbers:
                    session_id = "%02d" % (len(bids_file.subjects[subject_id].sessions) + 1)
                    session_numbers[session_key] = session_id

                    if DISPLAY_VALS:
                        print("Adding information from Session %s" % session_id, flush=True)

                    lowest_time = ""
                    for run_key in session['Data Recordings'].keys():
                        run = session['Data Recordings'][run_key]
                        if lowest_time == "" or run['Start Date Time'] < lowest_time:
                            lowest_time = run['Start Date Time']

                    bids_file.subjects[subject_id].sessions[session_id] = BIDSSession()
                    bids_file.subjects[subject_id].sessions[session_id].fields['acq_time'] = lowest_time
                    bids_file.subjects[subject_id].sessions[session_id].field_definitions['ESS_dataRecordingUuid'] = \
                    scan_level_tags['ESS_dataRecordingUuid']
                    bids_file.subjects[subject_id].sessions[session_id].field_definitions['ESS_inSessionRecordingNum'] = scan_level_tags['ESS_inSessionRecordingNum']
                    bids_file.subjects[subject_id].sessions[session_id].fields['ESS_subjectLabID'] = subject_key
                    bids_file.subjects[subject_id].field_definitions['ESS_subjectLabID'] = session_level_tags['ESS_subjectLabID']

                    # if session.get('Number') and session['Number'] != "n/a":
                    bids_file.subjects[subject_id].sessions[session_id].fields['ESS_sessionNum'] = session_key
                    bids_file.subjects[subject_id].field_definitions['ESS_sessionNum'] = session_level_tags['ESS_sessionNum']

                    if session.get('Lab ID') and session['Lab ID'] != "n/a":
                        bids_file.subjects[subject_id].sessions[session_id].fields['ESS_sessionID'] = session['Lab ID']
                        bids_file.subjects[subject_id].field_definitions['ESS_sessionID'] = session_level_tags[
                            'ESS_sessionID']

                    if session.get('In Session Number') and session['In Session Number'] != 'n/a':
                        bids_file.subjects[subject_id].sessions[session_id].fields['ESS_inSessionRecordingNum'] = session['In Session Number']
                        bids_file.subjects[subject_id].field_definitions['ESS_inSessionRecordingNum'] = session_level_tags['ESS_inSessionRecordingNum']

                    if subject.get('Medication'):
                        if subject['Medication'].get('Caffeine') and subject['Medication'].get('Caffeine') != 'n/a':
                            bids_file.subjects[subject_id].sessions[session_id].fields['caffeine'] = subject['Medication']['Caffeine']
                            bids_file.subjects[subject_id].field_definitions['caffeine'] = session_level_tags['caffeine']

                        if subject['Medication'].get('Alcohol') and subject['Medication']['Alcohol'] != 'n/a':
                            bids_file.subjects[subject_id].sessions[session_id].fields['alcohol'] = subject['Medication']['Alcohol']
                            bids_file.subjects[subject_id].field_definitions['alcohol'] = session_level_tags['alcohol']

                    for field in subject.keys():
                        if session_level_tags.get(field) and subject[field] and subject[field] != "n/a" and subject[field] != "":
                            bids_file.subjects[subject_id].sessions[session_id].fields[field.lower().replace(" ", "_")] = \
                                subject[field]
                            bids_file.subjects[subject_id].field_definitions[field.lower().replace(" ", "_")] = \
                                session_level_tags[field.lower().replace(" ", "_")]
                else:
                    session_id = session_numbers[session_key]

                rec_parameter_sets = xml['rec_parameter_sets']

                for run_key, run in session['Data Recordings'].items():
                    current_ses_dir = os.path.join(input_directory, "session", session_key)

                    run_count = len([i for i in bids_file.subjects[subject_id].sessions[session_id].scans.keys() if task_name in i]) + 1
                    current_label = "eeg/sub-%s_ses-%s_task-%s_run-%1d_eeg.set" % (subject_id, session_id, task_name, run_count)

                    bids_file.subjects[subject_id].sessions[session_id].scans[current_label] = BIDSScan(os.path.join(current_ses_dir, run['Filename']), task_name)
                    bids_file.subjects[subject_id].sessions[session_id].scans[current_label].run = run_count
                    bids_file.subjects[subject_id].sessions[session_id].scans[current_label].fields['ESS_dataRecordingUuid'] = run['Data Recording UUID']
                    bids_file.subjects[subject_id].sessions[session_id].scans[current_label].fields['ESS_inSessionRecordingNum'] = run['Filename'][run['Filename'].rfind('_') + 1:run['Filename'].rfind('.')]

                    try:
                        f = open(os.path.join(current_ses_dir, run['Event Instance File']), "r")

                        for line in f.readlines():
                            tokens = line.strip('\n').split('\t')
                            tags = None

                            if tokens[0] in bids_file.event_codes:
                                tags = tokens[2].replace(bids_file.event_codes[tokens[0]], '')
                            else:
                                for tl, task in bids_file.tasks.items():
                                    if tl == tokens[0]:
                                        tags = tokens[2].replace(task.event_codes, '')
                                        break

                            bids_file.subjects[subject_id].sessions[session_id].scans[current_label].events.append(
                                {'onset': tokens[1], 'duration': 'n/a', 'event_code': tokens[0]})

                            if tags:
                                bids_file.subjects[subject_id].sessions[session_id].scans[
                                    current_label].events[-1]['HED'] = tags

                        f.close()
                    except OSError as e:
                        print("Event instance file %s unavailable." % run['Event Instance File'])
                        raise e

                    if not bids_file.subjects[subject_id].sessions[session_id].electrodes:
                        if run['Recording Parameter Set Label'] not in RPS_electrodes.keys():
                            print("Extracting electrode set from %s..." % run['Recording Parameter Set Label'])

                            rps_entry = get_matlab_instance().ExtractChannels(run['Filename'], current_ses_dir, nargout=5,
                                                                      stdout=matlab_out, stderr=matlab_err)
                            if DISPLAY_MATLAB_OUTPUT:
                                print(matlab_out.getvalue())
                                print(matlab_err.getvalue())

                            new_rps_entry = list()
                            for i in range(6):
                                new_rps_entry.append(list())

                            for i in range(len(rps_entry[1])):
                                if not (rps_entry[1][i] and rps_entry[1][i] != "EEG"):
                                    for j in range(0, len(rps_entry)):
                                        new_rps_entry[j].append(rps_entry[j][i])
                                elif rps_entry[1][i] == 'EKG':
                                    rps_entry[1][i] = 'ECG'

                            RPS_electrodes[run['Recording Parameter Set Label']] = new_rps_entry

                        rps_entry = RPS_electrodes[run['Recording Parameter Set Label']]
                        bids_file.subjects[subject_id].sessions[session_id].coordsystem = {
                            'EEGCoordinateSystem': 'RAS',
                            'EEGCoordinateUnits': 'mm'
                        }

                        bids_file.subjects[subject_id].sessions[session_id].fields['legacy_recordingParameterSet'] = run[
                            'Recording Parameter Set Label']
                        bids_file.subjects[subject_id].field_definitions['legacy_recordingParameterSet'] = \
                        session_level_tags['legacy_recordingParameterSet']

                        for i in range(0, len(rps_entry[0])):
                            bids_file.subjects[subject_id].sessions[session_id].electrodes[rps_entry[0][i]] = {'x': rps_entry[2][i], 'y': rps_entry[3][i], 'z': rps_entry[4][i]}

                    for ps_label, ps in [ (psl, ps) for psl, ps in rec_parameter_sets.items() if psl == run['Recording Parameter Set Label']]:
                        for modality, mode in ps.items():
                            modality = modality.upper()
                            if modality not in channel_types and modality != 'EKG':
                                modality = 'MISC'
                            if modality == 'EEG':
                                bids_file.tasks[task_name].add_field("SamplingFrequency", float(mode['Sampling Rate']),
                                                                     subject_label=subject_id, session_label=session_id,
                                                                     scan_name=current_label)
                                bids_file.tasks[task_name].add_field("CapManufacturer", mode['Name'] or "n/a",
                                                                     subject_label=subject_id,
                                                                     session_label=session_id,
                                                                     scan_name=current_label)
                                bids_file.tasks[task_name].add_field("EEGPlacementScheme", mode['Channel Location Type'] or "n/a",
                                                                     subject_label=subject_id, session_label=session_id,
                                                                     scan_name=current_label)
                                bids_file.tasks[task_name].add_field("EEGReference", mode['Reference Label'] or "n/a",
                                                                     subject_label=subject_id, session_label=session_id,
                                                                     scan_name=current_label)
                            if modality == 'EKG':
                                modality = 'ECG'

                            for channel in mode['Channel Labels']:
                                if channel in mode['Non-Scalp Channel Labels']:
                                    if channel not in bids_file.field_replacements['channels']:
                                        bids_file.field_replacements['channels'][channel] = list()

                                    has_entry = any(filter(lambda x: x['where']['legacy_recordingParameterSet'] == run['Recording Parameter Set Label'], bids_file.field_replacements['channels'][channel]))

                                    if not has_entry:
                                        bids_file.field_replacements['channels'][channel].append(
                                            {'where': {
                                                'legacy_recordingParameterSet': run['Recording Parameter Set Label']
                                            }, 'type': None}
                                        )
                                    modality = 'null'

                                channels_dict = bids_file.subjects[subject_id].sessions[session_id].scans[
                                    current_label].channels
                                channels_dict[channel] = dict()
                                channels_dict[channel]['type'] = modality
                                channels_dict[channel]['units'] = u'µV'
                                channels_dict[channel]['sampling_frequency'] = mode['Sampling Rate']
                                # stubbed, since all channels have the same reference, so this only goes in the sidecar...channels_dict[channel]['reference'] = mode['Reference Label']


def _generate_bids_tasks(bids_file, xml):
    """
    Internal function use to pick apart task references in 'study_description.xml'

    :param bids_file: BIDSProject, which fields are changed in place
    :param xml: Extracted XML document for study_description
    :return:
    """

    for task_label, task in xml['tasks'].items():
        new_task_name = underscore_to_camelcase(task_label)
        if new_task_name not in bids_file.tasks:
            bids_file.tasks[new_task_name] = BIDSTask()

        bids_file.tasks[new_task_name].add_field('TaskDescription', task['Description'])

        bids_file.field_replacements['tasks'][new_task_name] = list()
        for rps_label in xml['rec_parameter_sets']:
            bids_file.field_replacements['tasks'][new_task_name].append(
                {'where': {
                    'legacy_recordingParameterSet': rps_label
                }, 'PowerLineFrequency': None}
            )



def underscore_to_camelcase(string):
    """
    Rudimentary converter used to make labels BIDS compliant

    :param string: String to be converted
    :return: String that is now alphanumeric
    """
    new_string = ""
    needs_capitalize = False
    for c in string:
        if c == '_' or c == '-' or c == ' ':
            needs_capitalize = True
        elif needs_capitalize:
            new_string += c.upper()
            needs_capitalize = False
        else:
            new_string += c
    new_string = re.sub(r'\W+', '', new_string)
    return new_string

class LXMLDecodeError(Exception):
    """
    Exception that is thrown if there was a decoding error with 'study_description.xml'
    """
    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            super().__init__(self, "An error occurred in decoding 'study_description.xml' in %s" % args[0], args[1:],
                             kwargs)
        else:
            super().__init__(self, "An error occurred in decoding 'study_description.xml'", args, kwargs)
