import os.path
import re
import sys
from json import JSONDecodeError

from filesystem import util
from structure.project import *
from structure.subject import *
from structure.task import *

def import_project(path, stub=False) -> BIDSProject:
    """
    Imports a BIDSProject from a given file path.

    :param path: Points to the top level of a given BIDS study
    :param stub: Should be set to True if the BIDS study doesn't contain any large scan files or ignored files

    :return: The resulting BIDSProject
    """
    bids_project = BIDSProject(os.path.basename(path))

    try:
        bids_project.dataset_description = util.read_json(os.path.join(path, 'dataset_description.json'))
    except JSONDecodeError:
        print("[ERROR] Unable to load 'dataset_description.json', due to a JSON error")
        sys.exit(1)

    for subject_name, subject in util.read_tsv(os.path.join(path, "participants.tsv")).items():
        bids_project.subjects[subject_name[4:]] = BIDSSubject()
        bids_project.subjects[subject_name[4:]].fields = subject

    if os.path.exists(os.path.join(path, "field_replacements.json")):
        try:
            bids_project.field_replacements = util.read_json(os.path.join(path, "field_replacements.json"))
        except JSONDecodeError:
            print("[WARNING] Unable to load 'field_replacements.json', due to a JSON error")

    if os.path.exists(os.path.join(path, "participants.json")):
        try:
            bids_project.field_definitions = util.read_json(os.path.join(path, "participants.json"))
        except JSONDecodeError:
            print("[ERROR] Unable to load 'participants.json', due to a JSON error")
            sys.exit(1)

    for task in [file for file in os.listdir(path) if re.match(r"task-.*?\.json", file)]:
        task_name = task[5:task.rfind("_")]

        if task_name not in bids_project.tasks:
            bids_project.tasks[task_name] = BIDSTask()

        try:
            task_dict = util.read_json(os.path.join(path, task))
            if '_events' in task:
                field = task_dict.get('event_code')
                if field:
                    bids_project.tasks[task_name].event_codes = field['EventCodes']
            else:
                bids_project.tasks[task_name].fields.update({"root" + task_specificity_token + k: v for k, v in task_dict.items()})
        except JSONDecodeError:
            print("[ERROR] Unable to load '%s', due to a JSON error" % task)
            sys.exit(1)

    for subject in [dir for dir in os.listdir(path) if re.match(r"sub-[a-zA-Z0-9]+", dir) and os.path.isdir(os.path.join(path, dir))]:
        subject_label = subject[4:]
        session_list = [dir for dir in os.listdir(os.path.join(path, subject)) if re.match(r"ses-[a-zA-Z0-9]+", dir) and os.path.isdir(os.path.join(path, subject, dir))]

        if os.path.exists(os.path.join(path, subject, "%s_sessions.tsv" % subject)):
            for session_name, session in util.read_tsv(os.path.join(path, subject, "%s_sessions.tsv" % subject)).items():
                bids_project.subjects[subject_label].sessions[session_name[4:]] = BIDSSession()
                bids_project.subjects[subject_label].sessions[session_name[4:]].fields = session
        elif session_list:
            for session in session_list:
                bids_project.subjects[subject_label].sessions[session[4:]] = BIDSSession()
        else:
            bids_project.subjects[subject_label].sessions[session_agnostic_token] = BIDSSession()

        if os.path.exists(os.path.join(path, subject, "%s_sessions.json" % subject)):
            try:
                bids_project.subjects[subject_label].field_definitions.update(util.read_json(os.path.join(path, subject, "%s_sessions.json" % subject)))
            except JSONDecodeError:
                print("[ERROR] Unable to load '%s', due to a JSON error" % os.path.join(subject, "%s_sessions.json" % subject))
                sys.exit(1)

        for sidecar in [file for file in os.listdir(os.path.join(path, subject)) if re.match(r"%s_task-[a-zA-Z0-9]+_.*?\.json" % subject, file)]:
            try:
                task_name = re.match(r"%s_task-([a-zA-Z0-9]+)_.*?\.json" % subject, sidecar).group(1)
                bids_project.tasks[task_name].fields.update({subject_label + task_specificity_token + k: v for (k,v) in util.read_json(os.path.join(path, subject, sidecar)).items()})
            except JSONDecodeError:
                print("[ERROR] Unable to load '%s', due to a JSON error" % os.path.join(subject, sidecar))
                sys.exit(1)

        for sub_ses in [os.path.join(subject, dir) for dir in session_list] or (subject,):
            if len(os.path.split(sub_ses)) == 2:
                session = bids_project.subjects[subject_label].sessions[os.path.split(sub_ses)[1][4:]]
                for sidecar in [file for file in os.listdir(os.path.join(path, sub_ses)) if
                                re.match(r"%s_task-[a-zA-Z0-9]+_.*?\.json" % '_'.join(os.path.split(sub_ses)), file)]:
                    try:
                        task_name = re.match(r"task-([a-zA-Z0-9]+)_", sidecar).group(1)
                        bids_project.tasks[task_name].fields.update(
                            {os.path.split(sub_ses)[0] + task_specificity_token + os.path.split(sub_ses)[1] + task_specificity_token + k: v for (k, v) in util.read_json(os.path.join(path, sub_ses, sidecar)).items()})
                    except JSONDecodeError:
                        print("[ERROR] Unable to load '%s', due to a JSON error" % os.path.join(sub_ses, sidecar))
                        sys.exit(1)
            else:
                session = bids_project.subjects[subject].sessions[session_agnostic_token]

            for recording_type in [dir for dir in os.listdir(os.path.join(path, sub_ses)) if os.path.isdir(os.path.join(path, sub_ses,dir))]:
                for scan_file in os.listdir(os.path.join(path, sub_ses, recording_type)):
                    if scan_file[scan_file.rfind('.'):] in util.file_extensions:
                        session.scans["%s/%s" % (recording_type, scan_file)] = BIDSScan(os.path.join(path, sub_ses, recording_type, scan_file), re.search(r"task-([a-zA-Z0-9]+)_", scan_file).group(1))
                        if "_run-" in scan_file:
                            session.scans["%s/%s" % (recording_type, scan_file)].run = int(scan_file[scan_file.find("_run-") + 5:scan_file.rfind("_")])
                    elif '_coordsystem.json' in scan_file:
                        try:
                            session.coordsystem = util.read_json(os.path.join(path, sub_ses, recording_type, scan_file))
                        except JSONDecodeError:
                            print("[ERROR] Unable to load '%s', due to a JSON error" % os.path.join(sub_ses, recording_type, scan_file))
                            sys.exit(1)

                    elif '_electrodes.tsv' in scan_file:
                        electrodes = util.read_tsv(os.path.join(path, sub_ses, recording_type, scan_file))
                        electrodes = {k:float(v) for k,v in electrodes.items() if k == 'x' or k == 'y' or k == 'z'}
                        session.electrodes = electrodes
                    elif re.match("%s_task-[A-Za-z0-9]+_.*?%s.json" % ('_'.join(os.path.split(sub_ses)), recording_type), scan_file):
                        try:
                            task_name = re.match(r"%s_task-([a-zA-Z0-9]+)_.*?\.json" % '_'.join(os.path.split(sub_ses)), scan_file).group(1)
                            bids_project.tasks[task_name].fields.update(
                                {task_specificity_token.join(sub_ses.split('/') + [recording_type + '/' + scan_file, k]): v for (k, v) in
                                 util.read_json(os.path.join(path, subject, sidecar)).items()})
                        except JSONDecodeError:
                            print(
                                "[ERROR] Unable to load '%s', due to a JSON error" % os.path.join(subject, sidecar))
                            sys.exit(1)

            scans_tsv_path = [file for file in os.listdir(os.path.join(path, sub_ses)) if '_scans' in file]
            for file in scans_tsv_path:
                if '.tsv' in file:
                    for scan_name, scan in util.read_tsv(os.path.join(path, sub_ses, file)).items():
                        session.scans[scan_name] = BIDSScan(os.path.join(path, sub_ses, scan_name), re.search(r"task-([a-zA-Z0-9]+)_", scan_name).group(1))
                        if "_run-" in scan_name:
                            session.scans[scan_name].run = int(scan_name[scan_name.find("_run-") + 5:scan_name.rfind("_")])
                        session.scans[scan_name].fields = scan
                elif '.json' in file:
                    try:
                        session.field_definitions = util.read_json(os.path.join(path, sub_ses, file))
                    except JSONDecodeError:
                        print("[ERROR] Unable to load '%s', due to a JSON error" % os.path.join(sub_ses, file))
                        sys.exit(1)

            if len(session.scans.items()) == 0:
                raise IOError("No reference to scans found")

            for scan_name, scan in session.scans.items():
                scan.channels = util.read_tsv(os.path.join(path, sub_ses, scan_name[:scan_name.rfind('_')] + "_channels.tsv"))
                scan.events = util.read_tsv(os.path.join(path, sub_ses, scan_name[:scan_name.rfind('_')] + "_events.tsv"), primary_index=None)

    if os.path.exists(os.path.join(path, "README")):
        readme_md = open(os.path.join(path, "README"), "r")
        bids_project.readme = readme_md.read()
        readme_md.close()

    if os.path.exists(os.path.join(path, "CHANGES")):
        changes_md = open(os.path.join(path, "CHANGES"), "r")
        bids_project.changes = changes_md.read()
        changes_md.close()

    return bids_project