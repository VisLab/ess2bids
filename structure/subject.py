"""
This module specifies several classes for different BIDS entities
"""

from typing import Dict

session_agnostic_token = '.'


class BIDSSubject:
    """
    This class defines a Subject entity in BIDS

    If there's no session specificity, sessions has a length of one, with a key specified above

    Attributes:
        sessions: Aggregate of BIDSSessions, each key being the session label (not including 'ses-')
        fields: entries in 'participants.tsv' for the given subject
        field_definitions: entries in '_sessions.json' for every session under the subject
    """
    def __init__(self):
        self.sessions: Dict[str, BIDSSession] = dict()
        self.fields = dict() # entries in 'participants.tsv'
        self.field_definitions = dict() # entries in '_sessions.json'


class BIDSSession:
    """
    This class defines a Session entity in BIDS

    Attributes:
        scans: Aggregate of BIDSScans, each key being the relative filepath from the session
        fields: entries in '_sessions.tsv' for the given session
        field_definitions: entries in '_scans.json' for every scan under the session
        electrodes: entries in '_electrodes.tsv' for a given session
        coordsystem: entries in '_coordsystem.json' for a given session
    """
    def __init__(self):
        self.scans: Dict[str, BIDSScan] = dict()
        self.fields = dict()
        self.field_definitions = dict()
        self.electrodes = dict()
        self.coordsystem = dict()


class BIDSScan:
    """
    This class defines as Scan object, which loosely maps to a run in BIDS

    Attributes:
        task: task label (not including task-) for the associated task
        path: original path of the scan file
        run: indexed run of the scan. if 0, then assume there's only one scan
        fields: entries in '_scans.tsv'
        events: entries in '_events.tsv'
        channels: entries in '_channels.tsv'
    """
    def __init__(self, path, task):
        self.task = task
        self.path = path
        self.run = 0
        self.fields = dict()
        self.events = list()
        self.channels = dict()
