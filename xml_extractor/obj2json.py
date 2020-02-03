import json

# next 4 functions to turn obj lists to dicts

incorrect_NAs = ("NA", 'NaN', None)

def sessionlist2dict(sessionlist):
    ret = dict()
    for session in sessionlist:
        if session.number not in ret:
            ret[session.number] = list()
        ret[session.number].append(scrub_na(session.todict()))
    return ret


def tasklist2dict(tasklist):
    ret = dict()
    for task in tasklist:
        ret[task.tasklabel] = scrub_na(task.todict())
    return ret


def eventcodelist2dict(eventlist):
    ret = dict()
    for event in eventlist:
        ret[event.code+event.tasklabel] = scrub_na(event.todict())
    return ret


def RPSlist2dict(RPSlist):
    ret = dict()
    for recparamset in RPSlist:
        ret[recparamset.recordingparametersetlabel] = scrub_na(recparamset.todict())
    return ret

def scrub_na(d):
    return {k:(v if v not in incorrect_NAs else "n/a") for k,v in d.items()}

def dict2json(sessionsdict, filepath):
    string = json.dumps(sessionsdict)
    with open(filepath, "w") as file:
        file.write(string)
