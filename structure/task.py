"""
This module defines the BIDSTask class, as well as some BIDS domain specific definitions
"""
# These are modality agnostic fields that are generated in every task
valid_fields = ['TaskName', 'InstitutionName', 'InstitutionAddress', 'Manufacturer', 'ManufacturersModelName',
                'SoftwareVersions', 'TaskDescription', 'Instructions', 'CogAtlasID', 'DeviceSerialNumber']

# These are EEG specific fields
modalities = {'eeg': ['EEGReference', 'SamplingFrequency', 'PowerLineFrequency', 'SoftwareFilters', 'CapManufacturer',
                      'CapManufacturersModelName', 'EEGChannelCount', 'ECGChannelCount', 'EMGChannelCount',
                      'EOGChannelCount', 'MiscChannelCount', 'TriggerChannelCount', 'RecordingDuration',
                      'RecordingType', 'EpochLength', 'HeadCircumference', 'EEGPlacementScheme', 'EEGGround',
                      'HardwareFilters', 'SubjectArtefactDescription']}

__all__ = ['task_specificity_token', 'BIDSTask']

task_specificity_token = '$'


def _field_order(x):
    token = x.split(task_specificity_token)[-1]
    try:
        o = valid_fields.index(token)
        return o
    except ValueError:
        lower = len(valid_fields)
        for modality in modalities.values():
            try:
                o = modality.index(token)
                return lower + o
            except ValueError:
                lower += len(modality)
    return lower + 1


class BIDSTask:
    """
    Class that represents a given BIDSTask

    * Each field is either project, subject, session, or scan specific
    * The specificity of a given field is specified in the key of the field
    * Each key is tokenized using the above-defined token, where the last token is the actual field name

    Attributes:
        fields: key/value pairs for each sidecar entry
        event_codes: EEG specific entries in "_events.json"
    """

    def __init__(self):
        self.fields = dict()
        self.event_codes = dict()

    def add_field(self, key, value, subject_label=None, session_label=None, scan_name=None):
        """
        Adds a field to a given Task

        * If none of the keyword arguments are specified,
        * If session_label is specified, subject_label should be specified as well
        * If scan_name is specified, session_label and subject_label should be specified as well

        :param key: name of the field
        :param value: value of the field
        :param subject_label: the field's given subject_label, if specified
        :param session_label: the field's given session_label, if specified
        :param scan_name: the fields's given scan_name, if specified
        :return:
        """
        if subject_label:
            if session_label:
                if scan_name:
                    self.fields[subject_label + task_specificity_token + session_label + task_specificity_token +
                                scan_name + task_specificity_token + key] = value
                else:
                    self.fields[subject_label + task_specificity_token + session_label +
                                task_specificity_token + key] = value
            else:
                self.fields[subject_label + task_specificity_token + key] = value
        else:
            self.fields["root" + task_specificity_token + key] = value

    def field(self, key, subject_label=None, session_label=None, scan_name=None):
        """
        Fetches a field from the given task

        * If none of the keyword arguments are specified, fetch the project-specific value
        * If session_label is specified, subject_label should be specified as well
        * If scan_name is specified, session_label and subject_label should be specified as well

        :param key: name of the field
        :param subject_label: the field's given subject_label, if specified
        :param session_label: the field's given session_label, if specified
        :param scan_name: the fields's given scan_name, if specified
        :return:
        """
        if subject_label:
            if session_label:
                if scan_name:
                    return self.fields[subject_label + task_specificity_token + session_label +
                                       task_specificity_token + scan_name + task_specificity_token + key]
                else:
                    return self.fields[subject_label + task_specificity_token + session_label +
                                       task_specificity_token + key]
            else:
                return self.fields[subject_label + task_specificity_token + key]
        else:
            return self.fields["root" + task_specificity_token + key]

    def get_fields(self, subject_label=None, session_label=None, scan_name=None):
        """
        Fetches all fields for a given specificity.

        :param subject_label: subject for which fields to fetch
        :param session_label: session for which fields to fetch
        :param scan_name: scan for which fields to fetch
        :return:
        """
        if subject_label:
            if session_label:
                if scan_name:
                    return {key[key.rfind(task_specificity_token) + 1:]: value for (key, value) in self.fields.items()
                            if task_specificity_token.join((subject_label, session_label, scan_name)) in key}
                else:
                    return {key[key.rfind(task_specificity_token) + 1:]: value for (key, value) in self.fields.items()
                            if task_specificity_token.join((subject_label, session_label)) in key and
                            key.count(task_specificity_token) == 2}
            else:
                return {key[key.rfind(task_specificity_token) + 1:]: value for (key, value) in self.fields.items()
                        if subject_label == key.split(task_specificity_token)[0] and
                        key.count(task_specificity_token) == 1}
        else:
            return {key[5:]: value for (key, value) in self.fields.items() if "root" + task_specificity_token in key}

    def preprocess_fields(self):
        """
        Performs clean up on every field in a given task

        * If all scan-specific fields are the same, make it a session-specific field
        * If all session-specific fields are the same, make it a subject-specific field
        * If all subject-specific fields are the same, make it a project-specific field

        :return:
        """

        for subject_label in sorted({k.split(task_specificity_token)[0] for k in self.fields}, reverse=True):
            for session_label in sorted({k.split(task_specificity_token)[1]
                                         for k in self.fields if subject_label == k.split(task_specificity_token)[0]},
                                        reverse=True):
                for field in sorted({k.split(task_specificity_token)[-1]
                                     for k in self.fields
                                     if [subject_label, session_label] == k.split(task_specificity_token)[0:2]
                                     and k.count(task_specificity_token) == 3}, reverse=True):
                    scan_fields = {k: v for (k, v) in self.fields.items() if [subject_label, session_label]
                                   == k.split(task_specificity_token)[0:2] and field in k}
                    if len(set(scan_fields.values())) == 1:
                        self.fields[subject_label + task_specificity_token + session_label +
                                    task_specificity_token + field] = list(scan_fields.values())[0]
                        for scan in scan_fields:
                            del self.fields[scan]
            for field in sorted({k.split(task_specificity_token)[-1]
                                 for k in self.fields
                                 if subject_label == k.split(task_specificity_token)[0]
                                 and k.count(task_specificity_token) == 2}, reverse=True):
                session_fields = {k: v for (k, v) in self.fields.items()
                                  if subject_label == k.split(task_specificity_token)[0] and
                                  k.count(task_specificity_token) == 2 and field in k}
                if len(set(session_fields.values())) == 1:
                    self.fields[subject_label + task_specificity_token + field] = list(session_fields.values())[0]
                    for session in session_fields:
                        del self.fields[session]
        for field in sorted({k.split(task_specificity_token)[-1]
                             for k in self.fields
                             if k.count(task_specificity_token) == 1 and "root" != k.split(task_specificity_token)[0]}):
            subject_fields = {k: v for (k, v) in self.fields.items()
                              if field in k and "root" != k.split(task_specificity_token)[0]}
            if len(set(subject_fields.values())) == 1:
                self.fields["root" + task_specificity_token + field] = list(subject_fields.values())[0]
                for subject in subject_fields:
                    del self.fields[subject]

        self.fields = {k: self.fields[k] for k in sorted(self.fields, key=_field_order)}

    def fill_na(self, modality=None):
        """
        If a task doesn't specify the above-defined fields, stub values are generated in place.

        :param modality: If specified, also stubs modality-specific task fields
        :return:
        """
        fully_consolidated = [k.split(task_specificity_token)[-1]
                              for k in self.fields.keys() if k.split(task_specificity_token)[-1] not in self.fields]
        remaining_fields = [k for k in valid_fields if k not in fully_consolidated]
        if modality and modality in modalities:
            remaining_fields += [k for k in modalities[modality] if k not in fully_consolidated]

        for field in remaining_fields:
            self.fields[field] = "n/a"
