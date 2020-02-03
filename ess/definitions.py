"""
This module contains several domain specific definitions used in ESS, which are mapped to more generalized
definitions in BIDS
"""

participant_level_tags = {
    'group': {'Description': 'type of subject group the subject belongs to (e.g. autistic, normal, control...)'},
    'year_of_birth': {'Description': 'subject’s year of birth only'},
    'legacy_labID': {'Description': 'labID used to reference the subject in ESS'}}

session_level_tags = {'age': {'Description': 'subject’s age (in years) at the time of recording.'},
                      'height': {'Units': 'cm'},
                      'weight': {'Units': 'kg'},
                      'gender': {'Description': 'subject’s gender (M, F, or Other)',
                                 'Levels': {'M': 'Male', 'F': 'Female', 'Other': 'not specified'}},
                      'hand': {'Description': 'subject’s dominantly used hand',
                               'Levels': {'R': 'right', 'L': 'left', 'A': 'ambidexterous'}},
                      'alcohol': {
                          'Description': 'whether the subject has consumed alcohol within 12 hours before the recording',
                          'Levels': {'Yes': 'Has consumed caffeine within last 12 hours',
                                     'No': 'Has not consumed caffeine within last 12 hours'}},
                      'caffeine': {'Description': 'hours since last caffeine intake, if less than 12 hours',
                                   'Units': 'hours'},
                      'ESS_sessionNum': {'Description': 'Number of the ESS session in which this recording is found'},
                      'ESS_sessionID': {'Description': 'labID used to reference the session in original lab notes'},
                      'ESS_subjectLabID': {'Description': 'labID used to reference the subject in this study as provided in original lab notes'},
                      'ESS_inSessionRecordingNum' : {'Description': '''Each study may have multiple subjects. These subjects may or may not have
  labIds but they are numbered for the sole purpose of distinction, arbitrarily and in the
  context of the session. For example session 1 will have subjects with inSession
  numbers 1 and 2 , while session 2 may also have subjects with InSession numbers 1
  and 2 but they may refer to two other subjects. This numbering is only to allow
  association between files and subjects in potential absence of subject labIds.
'''},
                      'legacy_recordingParameterSet': {
                          'Description': 'ID used to reference the recordingParameterSet in ESS'}}

scan_level_tags = {
    'ESS_dataRecordingUuid': {'Description': 'Unique universal ID used to reference the specific recording in ESS'},
    'ESS_inSessionRecordingNum' : {'Description': 'Number of the recording associated with a particular subject in an ESS session'}
}

disclaimer = """ === DISCLAIMERS ===

By default, all ESS to BIDS conversions cannot automatically specify the PowerLine frequency field, 
as well as the types for channels for each nonScalpChannelLabel in the ESS study. Ensure to replace 
them in 'field_replacements.json', as they are required in order for the study to be BIDS compliant. 
It's also recommended to include descriptions when specifying types to each of those nonScalpChannelLabels. 

It's highly recommended to include fields for 'License', 'Authors', 'Acknowledgements', 'HowToAcknowledge', 
'ReferencesAndLinks', and 'DatasetDOI'.

"""