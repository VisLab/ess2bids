import os
import shutil

"""
This module is designed to fix some encoding issues regarding 'study_description.xml' and use of the XML tagging library.
"""

def replacer_make(study_dir):
    with open(os.path.join(study_dir, 'study_description.xml'), 'r', encoding='utf8') as desc:
        new_lines = list()
        for line in desc:
            line = line.replace('×', 'x').replace('—', '-').replace('"', '"')  # .replace('Ω', u"\u03A9")
            new_lines.append(line)

        if not os.path.exists(os.path.join(study_dir, 'DELETEME')):
            os.makedirs(os.path.join(study_dir, 'DELETEME'))

    with open(os.path.join(study_dir, 'DELETEME', 'study_description.xml'), 'w') as temp:
        for line in new_lines:
            temp.write(line)


def replacer_delete(study_dir):
    shutil.rmtree(os.path.join(study_dir, 'DELETEME'), ignore_errors=True)
