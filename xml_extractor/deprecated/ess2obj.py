from lxml import etree
from xml_extractor.deprecated.ClassDef import *

parser = etree.XMLParser(encoding='utf-8')

def xml2sessionlist(xmlpath):  # opens xml at path and returns a list of session objects
    # parse xml for sessions etree
    etree_sessions = etree.parse(xmlpath, parser).getroot().find('sessions').findall('session')

    # turn the Element object into a list of sessions
    sessions = list()
    for session in etree_sessions:
        number = session.find('number').text
        tasklabel = session.find('taskLabel').text
        sessionlabid = session.find('labId').text

        etreesubjects = session.findall('subject')  # get Element objects to parse

        subjects = list()
        for subject in etreesubjects:
            subjectlabid = subject.find('labId').text
            insessionnumber = subject.find('inSessionNumber').text
            group = subject.find('group').text
            gender = subject.find('gender').text
            yob = subject.find('YOB').text
            age = subject.find('age').text
            hand = subject.find('hand').text
            vision = subject.find('vision').text
            hearing = subject.find('hearing').text
            height = subject.find('height').text
            weight = subject.find('weight').text
            medication = subject.find('medication')
            channellocations = subject.find('channelLocations').text

            caffeine = medication.find('caffeine').text
            alcohol = medication.find('alcohol').text
            medication = Medication(caffeine, alcohol)

            subjects.append(Subject(subjectlabid, insessionnumber, group, gender, yob, age, hand, vision, hearing,
                                    height, weight, medication, channellocations))
        notes = ''

        datarecordings = list()
        for datarecord in session.find('dataRecordings').findall('dataRecording'):
            filename = datarecord.find('filename').text
            datarecordinguuid = datarecord.find('dataRecordingUuid').text
            startdatetime = datarecord.find('startDateTime').text
            recordingparametersetlabel = datarecord.find('recordingParameterSetLabel').text
            eventinstancefile = datarecord.find('eventInstanceFile').text
            originalfilenameandpath = datarecord.find('originalFileNameAndPath').text

            datarecordings.append(DataRecording(filename, datarecordinguuid, startdatetime, recordingparametersetlabel,
                                                eventinstancefile, originalfilenameandpath))

        sessions.append(Session(number, tasklabel, sessionlabid, subjects, notes, datarecordings))
    return sessions


def xml2tasklist(xmlpath):
    # parse xml for tasks etree
    etree_tasks = etree.parse(xmlpath, parser).getroot().find('tasks').findall('task')

    # make list
    tasks = list()
    for task in etree_tasks:
        tasks.append(Task(task.find('taskLabel').text, task.find('tag').text, task.find('description').text))
    return tasks


def xml2eventcodelist(xmlpath):
    # parse xml for eventcodes etree
    etree_eventcodes = etree.parse(xmlpath, parser).getroot().find('eventCodes').findall('eventCode')

    eventcodes = list()
    for eventcode in etree_eventcodes:
        code = eventcode.find('code').text
        tasklabel = eventcode.find('taskLabel')
        if tasklabel is not None:
            tasklabel = tasklabel.text
        else:
            tasklabel = ''
        try:
            numinstances = int(eventcode.find('numberOfInstances').text)
        except AttributeError:
            numinstances = 1
        hedtag = eventcode.find('condition').find('tag').text
        label = eventcode.find('condition').find('label').text
        description = eventcode.find('condition').find('description').text

        eventcodes.append(EventCode(code, tasklabel, numinstances, hedtag, label, description))
    return eventcodes


def xml2recparamsetlist(xmlpath):
    # parse xml for recparamsets etree
    etree_recparamsets = etree.parse(xmlpath, parser).getroot().find('recordingParameterSets').findall('recordingParameterSet')

    recparamsets = list()
    for recparamset in etree_recparamsets:
        recordingparametersetlabel = recparamset.find('recordingParameterSetLabel').text
        etree_channeltypes = recparamset.find('channelType').findall('modality')

        channeltypes = list()
        for modality in etree_channeltypes:
            mtype = modality.find('type').text
            samplingrate = modality.find('samplingRate').text
            name = modality.find('name').text
            description = modality.find('description').text
            startchannel = modality.find('startChannel').text
            endchannel = modality.find('endChannel').text
            subjectinsessionnumber = modality.find('subjectInSessionNumber').text
            referencelocation = modality.find('referenceLocation').text
            referencelabel = modality.find('referenceLabel').text
            channellocationtype = modality.find('channelLocationType').text

            channellabels = list(map(str.strip, modality.find('channelLabel').text.split(',')))
            nonscalpchannellabels = list(map(str.strip, modality.find('nonScalpChannelLabel').text.split(',')))

            channeltypes.append(
                Modality(mtype, samplingrate, name, description, startchannel, endchannel, subjectinsessionnumber,
                         referencelocation, referencelabel, channellocationtype, channellabels, nonscalpchannellabels))

        recparamsets.append(RecordingParameterSet(recordingparametersetlabel, channeltypes))
    return recparamsets


def xml2head(xmlpath):
    """
    extract: title, description(notshort), project.funding.org, uuid, rooturi, summary.licence(concatenate the 3 things)
    """
    headtree = etree.parse(xmlpath, parser).getroot()

    # extract each attribute
    title = headtree.find('title').text
    description = headtree.find('description').text
    fundingorganization = headtree.find('project').find('funding').find('organization').text
    uuid = headtree.find('uuid').text
    rooturi = headtree.find('rootURI').text

    # following code accounts for possible missing tags in license
    ltype = headtree.find('summary').find('license').find('type')
    text = headtree.find('summary').find('license').find('text')
    link = headtree.find('summary').find('license').find('link')
    none_check = lambda x: '' if x is None else x
    studylicense = f'{none_check(ltype.text)} {none_check(text.text)} {none_check(link.text)}'.strip()
    return Head(title, description, fundingorganization, uuid, rooturi, studylicense)


def clean_obj(obj):
    for attr, value in obj.__dict__.items():
        if value is None:
            return
        elif isinstance(value, str):
            # do all the string cleanups
            if value == 'NA': obj.__dict__[attr] = 'n/a'
        elif isinstance(value, list):
            clean_list(value)  # recursive call
        else:  # obj
            clean_obj(value)


def clean_list(obj_list):
    for obj in obj_list:
        clean_obj(obj)
    return obj_list
