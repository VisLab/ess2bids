from lxml import etree


def extract_description(xmlpath):
    doc_root = etree.parse(xmlpath, etree.XMLParser(encoding='utf-8')).getroot()
    description = dict()

    description['head'] = _xml2head(doc_root)
    description['sessions'] = _xml2sessions(doc_root.find('sessions').findall('session'))
    description['tasks'] = _xml2tasks(doc_root.find('tasks').findall('task'))
    description['rec_parameter_sets'] = _xml2recordingparametersets(
        doc_root.find('recordingParameterSets').findall('recordingParameterSet'))
    description['event_codes'] = _xml2eventcodes(doc_root.find('eventCodes').findall('eventCode'))

    _scrub_na(description)
    return description


def _xml2head(head):
    header_dict = dict()

    # extract each attribute
    header_dict['Title'] = head.findtext('title')
    header_dict['Description'] = head.findtext('description')
    header_dict['Funding Organization'] = head.find('project').find('funding').findtext('organization')
    header_dict['UUID'] = head.findtext('uuid')
    header_dict['Root URI'] = head.findtext('rootURI')

    # following code accounts for possible missing tags in license
    license_tag = head.find('summary').find('license')
    license_type = license_tag.findtext('type')
    text = license_tag.findtext('text')
    link = license_tag.findtext('link')
    header_dict['Study License'] = f"{license_type or ''} {text or ''} {link or ''}".strip()

    return header_dict


def _xml2sessions(sessions):
    # turn the Element object into a dict of sessions
    sessions_dict = dict()
    for session in sessions:
        key = session.findtext('number')
        if key not in sessions_dict:
            sessions_dict[key] = list()
        current_session = dict()

        current_session['Task Label'] = session.findtext('taskLabel')
        current_session['Lab ID'] = session.findtext('labId')
        current_session['Subjects'] = _subjects_from_session_xml(session.findall('subject'))

        current_session['Notes'] = ''
        current_session['Data Recordings'] = \
            _data_recordings_from_session_xml(session.find('dataRecordings').findall('dataRecording'))

        sessions_dict[key].append(current_session)

    return sessions_dict


def _subjects_from_session_xml(subjects):
    subjects_dict = dict()
    for subject in subjects:
        key = subject.findtext('labId')
        current_subject = subjects_dict[key] = dict()

        current_subject['In Session Number'] = subject.findtext('inSessionNumber')
        current_subject['Group'] = subject.findtext('group')
        current_subject['Gender'] = subject.findtext('gender')
        current_subject['Year of Birth'] = subject.findtext('YOB')
        current_subject['Age'] = subject.findtext('age')
        current_subject['Hand'] = subject.findtext('hand')
        current_subject['Vision'] = subject.findtext('vision')
        current_subject['Hearing'] = subject.findtext('hearing')
        current_subject['Height'] = subject.findtext('height')
        current_subject['Weight'] = subject.findtext('weight')
        current_subject['Channel Locations'] = subject.findtext('channelLocations')

        medication = subject.find('medication')
        caffeine = medication.findtext('caffeine')
        alcohol = medication.findtext('alcohol')

        current_subject['Medication'] = {'Caffeine': caffeine, 'Alcohol': alcohol}

    return subjects_dict


def _data_recordings_from_session_xml(data_recordings):
    data_recordings_dict = dict()
    for data_recording in data_recordings:
        key = data_recording.findtext('dataRecordingUuid')
        current_data_recording = data_recordings_dict[key] = dict()

        current_data_recording['Filename'] = data_recording.findtext('filename')
        current_data_recording['Data Recording UUID'] = data_recording.findtext('dataRecordingUuid')
        current_data_recording['Start Date Time'] = data_recording.findtext('startDateTime')
        current_data_recording['Recording Parameter Set Label'] = data_recording.findtext('recordingParameterSetLabel')
        current_data_recording['Event Instance File'] = data_recording.findtext('eventInstanceFile')
        current_data_recording['Original Filename and Path'] = data_recording.findtext('originalFileNameAndPath')

    return data_recordings_dict


def _xml2tasks(tasks):
    tasks_dict = dict()
    for task in tasks:
        key = task.findtext('taskLabel')
        current_task = tasks_dict[key] = dict()

        current_task['Description'] = task.findtext('description')
        current_task['Tag'] = task.findtext('tag')

    return tasks_dict


def _xml2recordingparametersets(rec_parameter_sets):
    rps_dict = dict()
    for rps in rec_parameter_sets:
        key = rps.findtext('recordingParameterSetLabel')
        current_rps = rps_dict[key] = dict()

        modalities = rps.find('channelType').findall('modality')

        for modality in modalities:
            key = modality.findtext('type')
            current_mod = current_rps[key] = dict()

            current_mod['Sampling Rate'] = modality.findtext('samplingRate')
            current_mod['Name'] = modality.findtext('name')
            current_mod['Description'] = modality.findtext('description')
            current_mod['Start Channel'] = modality.findtext('startChannel')
            current_mod['End Channel'] = modality.findtext('endChannel')
            current_mod['Subject In-Session Number'] = modality.findtext('subjectInSessionNumber')
            current_mod['Reference Location'] = modality.findtext('referenceLocation')
            current_mod['Reference Label'] = modality.findtext('referenceLabel')
            current_mod['Channel Location Type'] = modality.findtext('channelLocationType')

            current_mod['Channel Labels'] = list(map(str.strip, modality.findtext('channelLabel').split(',')))
            current_mod['Non-Scalp Channel Labels'] = \
                list(map(str.strip, modality.findtext('nonScalpChannelLabel').split(',')))

    return rps_dict


def _xml2eventcodes(event_codes):
    event_codes_list = list()  # iterated as list instead of dict to avoid indexing by both task label and event code
    for event_code in event_codes:
        current_event_code = dict()
        event_codes_list.append(current_event_code)

        current_event_code['Code'] = event_code.findtext('code')
        current_event_code['Task Label'] = event_code.findtext('taskLabel') or ''

        try:
            current_event_code['No. instances'] = int(event_code.findtext('numberOfInstances'))
        except AttributeError:
            current_event_code['No. instances'] = 0

        condition = event_code.find('condition')
        current_event_code['HED Tag'] = condition.findtext('tag')
        current_event_code['Label'] = condition.findtext('label')
        current_event_code['Description'] = condition.findtext('description')

    return event_codes_list


def _scrub_na(d):
    incorrect_nas = ("NA", 'NaN', '', None)

    if isinstance(d, dict):
        for key, value in d.items():
            try:
                iter(value)
                if not isinstance(value, str):
                    _scrub_na(value)
                else:
                    d[key] = value if value not in incorrect_nas else 'n/a'
            except TypeError:
                pass  # isn't str or dictionary, should be idempotent
    elif isinstance(d, list) or isinstance(d, set) or isinstance(d, tuple):
        for item in d:
            _scrub_na(item)
