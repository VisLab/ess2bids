import json
from abc import abstractmethod, ABC

from xml_extractor.deprecated.obj2json import scrub_na


class ESS2BIDS(ABC):
    @abstractmethod
    def todict(self):
        pass

    def getjsonstring(self):
        return json.dumps(self.todict())

    def writejson(self, filepath):
        with open(filepath, "w") as file:
            file.write(self.getjsonstring())

    def printjson(self):
        print(json.dumps(self.todict(), indent=2))


class Session(ESS2BIDS):
    def __init__(self, number, tasklabel, labid, subjects, notes, datarecordings):
        self.number = number
        self.tasklabel = tasklabel
        self.labid = labid
        self.subjects = subjects  # list of Subject
        self.notes = notes  # might be obj or list?
        self.datarecordings = datarecordings  # list of DataRecording objects

    def todict(self):
        subjects = self.subjects

        # make dictionary for subjects
        subjsdict = dict()
        for subject in subjects:
            subjsdict[subject.labid] = subject.todict()

        # make dictionary for datarecordings
        datarecdict = dict()
        for recording in self.datarecordings:
            datarecdict[recording.datarecordinguuid] = recording.todict()

        # make and return dictionary for session using subject and datarecordings dictionaries
        return scrub_na({
            'Number': self.number,
            'Task Label': self.tasklabel,
            'Lab ID': self.labid,
            'Subjects': subjsdict,
            'Notes': self.notes,
            'Data Recordings': datarecdict
        })


class Subject(ESS2BIDS):
    def __init__(self, labid, insessionnumber, group, gender, yob, age, hand, vision, hearing,
                 height, weight, medication, channellocations):
        self.labid = labid  # different from session's labid
        self.insessionnumber = insessionnumber  # correspond to recordingparametersetlLabel in datarecordings
        self.group = group
        self.gender = gender
        self.yob = yob
        self.age = age
        self.hand = hand
        self.vision = vision
        self.hearing = hearing
        self.height = height
        self.weight = weight
        self.medication = medication  # list? obj?
        self.channellocations = channellocations

    def todict(self):
        return scrub_na({
            "Lab ID": self.labid,
            "In Session Number": self.insessionnumber,
            "Group": self.group,
            "Gender": self.gender,
            "Year of Birth": self.yob,
            "Age": self.age,
            "Hand": self.hand,
            "Vision": self.vision,
            "Hearing": self.hearing,
            "Height": self.height,
            "Weight": self.weight,
            "Medication": self.medication.todict(),
            "Channel Locations": self.channellocations
        })


class Medication(ESS2BIDS):
    def __init__(self, caffeine, alcohol):
        self.caffeine = caffeine
        self.alcohol = alcohol

    def todict(self):
        return scrub_na({
            "Caffeine": self.caffeine,
            "Alcohol": self.alcohol
        })


class DataRecording(ESS2BIDS):
    def __init__(self, filename, datarecordinguuid, startdatetime, recordingparametersetlabel,
                 eventinstancefile, originalfilenameandpath):
        self.filename = filename
        self.datarecordinguuid = datarecordinguuid
        self.startdatetime = startdatetime
        self.recordingparametersetlabel = recordingparametersetlabel
        self.eventinstancefile = eventinstancefile
        self.originalfilenameandpath = originalfilenameandpath

    def todict(self):
        return scrub_na({
            "Filename": self.filename,
            "Data Recording UUID": self.datarecordinguuid,
            "Start Date Time": self.startdatetime,
            "Recording Parameter Set Label": self.recordingparametersetlabel,
            "Event Instance File": self.eventinstancefile,
            "Original Filename and Path": self.originalfilenameandpath
        })


class Task(ESS2BIDS):
    def __init__(self, tasklabel, tag, description):
        self.tasklabel = tasklabel
        self.tag = tag
        self.description = description

    def todict(self):
        return scrub_na({
            "Task Label": self.tasklabel,
            "Description": self.description,
            "Tag": self.tag
        })


class Head(ESS2BIDS):
    def __init__(self, title, description, fundingorganization, uuid, rooturi, studylicense):
        self.title = title
        self.description = description
        self.fundingorganization = fundingorganization
        self.uuid = uuid
        self.rooturi = rooturi
        self.studylicense = studylicense

    def todict(self):
        return scrub_na({
            'Title': self.title,
            'Description': self.description,
            'Funding Organization': self.fundingorganization,
            'UUID': self.uuid,
            'Root URI': self.rooturi,
            'Study License': self.studylicense
            })


class RecordingParameterSet(ESS2BIDS):
    def __init__(self, recordingparametersetlabel, channeltypes):
        self.recordingparametersetlabel = recordingparametersetlabel
        self.channeltypes = channeltypes

    def modalitylist2dict(self):
        ret = dict()
        for modality in self.channeltypes:
            ret[modality.mtype] = scrub_na(modality.todict())
        return ret


    def todict(self):
        return scrub_na({
            "Recording Parameter Set Label": self.recordingparametersetlabel,
            "Channel Types": self.modalitylist2dict()
        })


class Modality(ESS2BIDS):
    def __init__(self, mtype, samplingrate, name, description, startchannel, endchannel, subjectinsessionnumber,
                 referencelocation, referencelabel, channellocationtype, channellabels, nonscalpchannellabels):
        self.mtype = mtype
        self.samplingrate = samplingrate
        self.name = name
        self.description = description
        self.startchannel = startchannel
        self.endchannel = endchannel
        self.subjectinsessionnumber = subjectinsessionnumber
        self.referencelocation = referencelocation
        self.referencelabel = referencelabel
        self.channellocationtype = channellocationtype
        self.channellabels = channellabels
        self.nonscalpchannellabels = nonscalpchannellabels

    def todict(self):
        return scrub_na({
            "Type": self.mtype,
            "Sampling Rate": self.samplingrate,
            "Name": self.name,
            "Description": self.description,
            "Start Channel": self.startchannel,
            "End Channel": self.endchannel,
            "Subject In-Session Number": self.subjectinsessionnumber,
            "Reference Location": self.referencelocation,
            "Reference Label": self.referencelabel,
            "Channel Location Type": self.channellocationtype,
            "Channel Labels": self.channellabels,
            "Non-Scalp Channel Labels": self.nonscalpchannellabels
        })


class EventCode(ESS2BIDS):
    def __init__(self, code, tasklabel, numinstances, hedtag, label, description):
        self.code = code
        self.tasklabel = tasklabel
        self.numinstances = numinstances
        self.hedtag = hedtag
        self.label = label
        self.description = description

    def todict(self):
        return scrub_na({
            "Code": self.code,
            "Task Label": self.tasklabel,
            "No. instances": self.numinstances,
            "HED Tag": self.hedtag,
            "Label": self.label,
            "Description": self.description
        })
