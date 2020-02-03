"""
This module defines the BIDSProject class, as well as several BIDS domain specific definitions
"""

from structure.subject import BIDSSubject
from structure.task import BIDSTask
from typing import Dict

__all__ = ['channel_types', 'BIDSProject']

BIDS_version = "1.2.1"

channel_types = {'AUDIO', 'EEG','EOG', 'ECG', 'EMG', 'EYEGAZE', 'GSR', 'HEOG', 'MISC', 'PUPIL',
                 'REF', 'RESP', 'SYSCLOCK', 'TEMP', 'TRIG', 'VEOG'}

class BIDSProject:
    """
    This class contains top-level information about a given BIDS study, as well as converter specific information,
    such as ignored files and field_replacements.
    """
    def __init__(self, project_name):
        self.project_name = project_name
        self.subjects: Dict[str, BIDSSubject] = dict()
        self.tasks: Dict[str, BIDSTask] = dict()
        self.dataset_description = dict()
        self.field_definitions = dict()
        self.original_path = ""
        self.readme = ""
        self.changes = ""
        self.event_codes = dict()
        self.field_replacements = {'channels': dict(), 'tasks': dict()}
        self.ignored_files = list()

    def init_dataset_description(self, name, license, authors=list(), acknowledgements="n/a", how_to_acknowledge="n/a",
                                 funding=list(), references_and_links=list(), datasetDOI="n/a"):
        self.dataset_description["Name"] = name
        self.dataset_description["BIDSVersion"] = BIDS_version
        self.dataset_description["License"] = license
        self.dataset_description["Authors"] = authors
        self.dataset_description["Acknowledgments"] = acknowledgements
        self.dataset_description["HowToAcknowledge"] = how_to_acknowledge
        self.dataset_description["Funding"] = funding
        self.dataset_description["ReferencesAndLinks"] = references_and_links
        self.dataset_description["DatasetDOI"] = datasetDOI

    def preprocess(self):
        """
        This method performs miscellaneous clean up on a given BIDSProject, typically used before export.

        :return:
        """
        for subject_name, subject in self.subjects.items():
            for session_name, session in subject.sessions.items():
                for filename, scan in session.scans.items():
                    self.tasks[scan.task].add_field("EEGChannelCount", len(
                        list(filter(lambda x: scan.channels[x]['type'] == 'EEG', scan.channels.keys()))), subject_label=subject_name, session_label=session_name, scan_name=filename)
                    self.tasks[scan.task].add_field("EOGChannelCount", len(
                        list(filter(lambda x: scan.channels[x]['type'] == 'EOG', scan.channels.keys()))), subject_label=subject_name, session_label=session_name, scan_name=filename)
                    self.tasks[scan.task].add_field("ECGChannelCount", len(
                        list(filter(lambda x: scan.channels[x]['type'] == 'ECG', scan.channels.keys()))), subject_label=subject_name, session_label=session_name, scan_name=filename)
                    self.tasks[scan.task].add_field("EMGChannelCount", len(
                        list(filter(lambda x: scan.channels[x]['type'] == 'EMG', scan.channels.keys()))), subject_label=subject_name, session_label=session_name, scan_name=filename)
                    self.tasks[scan.task].add_field("MiscChannelCount", len(
                        list(filter(lambda x: scan.channels[x]['type'] == 'MISC', scan.channels.keys()))), subject_label=subject_name, session_label=session_name, scan_name=filename)

        for event_code in self.event_codes:
            for task_name, task in self.tasks.items():
                task.event_codes[event_code] = self.event_codes[event_code]

        for task_name, task in self.tasks.items():
            task.add_field('SoftwareFilters', "n/a")
            task.preprocess_fields()

    def generate_warnings(self):
        """
        Generates a series of warnings that might indicate issues with the conversion and/or BIDS compliance

        :return: a list of strings used to indicate warnings
        """
        warnings_list = list()

        for subject_name, subject in self.subjects.items():
            for session_name, session in subject.sessions.items():
                if session.electrodes and not session.coordsystem:
                    warnings_list.append("Warning: session %s specifies electrodes, but no coordinate system" % session_name)
                for filename, scan in session.scans.items():
                    if list(session.electrodes.keys()) != list(filter(lambda x: scan.channels[x]['type'] == 'EEG', scan.channels.keys())):
                        warnings_list.append("Warning: session %s has mismatched electrodes with %s" % (session_name, filename))

        if len(self.event_codes) > 1 and len(self.tasks) > 1:
            warnings_list.append("Warning: some eventCodes fail to specify a taskLabel")

        return warnings_list