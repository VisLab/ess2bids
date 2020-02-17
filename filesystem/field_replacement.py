import os

from copy import deepcopy
from filesystem import load, export
from datetime import datetime

from structure.project import *
from structure.subject import *
from structure.task import *


def replace_fields(bids_path, stub=False):
    """
    Scans 'field_replacements.json' for changes that need to be made to different fields,
    and re-exports the project.

    :param bids_path: Path of the BIDS project that needs to have fields replaced
    :param stub: Should be set to True if the file is missing large Scan files
    :return: None
    """
    try:
        project = load.import_project(bids_path, stub=stub)
    except IOError as e:
        raise IOError("Failed to import BIDS study", *e.args)

    field_replacements = project.field_replacements

    change_list = set()
    renamed = dict()
    fail_list = list()
    warning_list = list()

    if 'channels' in field_replacements:
        for channel_label, changes in field_replacements['channels'].items():
            for change in changes:
                updated = {k: v for (k, v) in change.items() if k != 'where'}
                skip = False
                # for update in updated:
                #     if '\t' in updated[update]:
                #         fail_list.append("Malformed field replacement entry in %s" % channel_label)
                #         skip = True
                # if skip:
                #     continue
                if 'type' in updated and updated['type'] not in channel_types:
                    warning_list.append("Channel type is invalid per BIDS EEG specification for channel label %s" % channel_label)

                for entities in _where(project, change.get('where')):
                    if 'scan' in entities:
                        project.subjects[entities['subject']].sessions[entities['session']].scans[entities['scan']].channels[channel_label].update(updated)
                        change_list.add(
                            "%s/sub-%s/" % (bids_path, entities['subject']) + "%s" % ("ses-%s/" % entities['session'] if (
                                        'session' in entities and entities['session'] != session_agnostic_token) else "") +
                                                                                                   entities['scan'][:entities['scan'].rfind('_')] + "_channels.tsv")
                    elif 'session' in entities:
                        for scan_label, scan in project.subjects[entities['subject']].sessions[entities['session']].scans.items():
                            scan.channels[channel_label].update(updated)
                            change_list.add(
                                "%s/sub-%s/" % (bids_path, entities['subject']) + "%s" % ("ses-%s/" % entities['session'] if (
                                        'session' in entities and entities['session'] != session_agnostic_token) else "") +
                                                                                                   scan_label[:scan_label.rfind('_')] + "_channels.tsv")
                    elif 'subject' in entities:
                        for session_label, session in project.subjects[entities['subject']].sessions.items():
                            for scan_label, scan in session.scans.items():
                                scan.channels[channel_label].update(updated)
                                change_list.add(
                                    "%s/sub-%s/" % (bids_path, entities['subject']) + "%s" % ("ses-%s/" % session_label if session_label != session_agnostic_token else "") +
                                                                                                       scan_label[:scan_label.rfind('_')] + "_channels.tsv")
    if 'tasks' in field_replacements:
        old_field_replacement_tasks = deepcopy(field_replacements['tasks'])
        for task_label, changes in old_field_replacement_tasks.items():
            for change in changes:
                if 'rename' in change:
                    if isinstance(change['rename'], str) and change['rename'].isalnum():
                        project.tasks[change['rename']] = project.tasks[task_label]
                        del project.tasks[task_label]

                        field_replacements['tasks'][task_label].remove(change)
                        field_replacements['tasks'][change['rename']] = field_replacements['tasks'][task_label]
                        del field_replacements['tasks'][task_label]
                        change_list.add("%s/field_replacements.json" % bids_path)

                        old_name = task_label
                        task_label = change['rename']

                        for root, dirs, files in os.walk(bids_path):
                            if root.split(os.path.sep)[-1] != "archived":
                                for file in files:
                                    if old_name in file:
                                        renamed[os.path.join(root, file)] = os.path.join(root, file[:file.rfind(old_name)] + task_label + file[file.rfind(old_name) + len(old_name):])

                        for subject_label, subject in project.subjects.items():
                            for session_label, session in subject.sessions.items():
                                for scan_label, scan in deepcopy(session.scans).items():
                                    if scan.task == old_name:
                                        new_key = scan_label[:scan_label.rfind('task-') + 5] + task_label + scan_label[scan_label.rfind("task-") + 5 + len(old_name):]
                                        session.scans[scan_label].task = task_label
                                        session.scans[new_key] = session.scans[scan_label]
                                        del session.scans[scan_label]

                                        ses = "ses-%s" % session_label if session_label != session_agnostic_token else ""

                                        change_list.add("%s/sub-%s/" % (bids_path, subject_label) + ses + "/" if ses else "" + "sub-%s_" % subject_label +
                                                                                                                          ses + "_" if ses else "" + "scans.tsv" )
                    else:
                        fail_list.append("Task label %s needs to be alphanumeric" % change['rename'])

        for task_label, changes in field_replacements['tasks'].items():
            if task_label not in project.tasks:
                fail_list.append("Task label %s isn't in the project structure" % task_label)
                continue
            for change in changes:
                if 'where' not in change:
                    updated = {k: v for (k, v) in change.items() if k != 'rename'}
                    for field, field_value in updated.items():
                        project.tasks[task_label].add_field(field, field_value)
                        change_list.add("%s/task-%s_eeg.json" % (bids_path, task_label))
                else:
                    if not isinstance(change['where'], dict):
                        fail_list.append("Malformed field replacement entry in %s" % task_label)
                    for entities in _where(project, change['where']):
                        updated = {k: v for (k, v) in change.items() if not (k == 'where' or k == 'rename')}
                        for field, field_value in updated.items():
                            project.tasks[task_label].add_field(field, field_value, entities.get('subject'), entities.get('session'), entities.get('scan'))
                            # assume that all files that are less specific are changed, makes consolidating fields easier
                            change_path = bids_path + "/"
                            change_name = "task-%s_eeg.json" % task_label
                            change_list.add(change_path + change_name)

                            if 'subject' in entities:
                                change_path += "sub-%s/" % entities['subject']
                                change_name = "sub-%s_" % entities['subject'] + change_name
                                change_list.add(change_path + change_name)
                            if 'session' in entities and entities['session'] != session_agnostic_token:
                                change_path += "ses-%s/" % entities['session']
                                change_name = "ses-%s_" % entities['session'] + change_name
                                change_list.add(change_path + change_name)
                            if 'scan' in entities:
                                change_path += entities['scan'].split("/") + "/"
                                run_count = project.subjects[entities['subject']].sessions[entities['session']].scans[entities['scan']].run
                                if run_count != 0:
                                    change_name = change_name[:change_name.rfind('_')] + "_run-%d" % run_count + change_name[change_name.rfind('_'):]
                                change_list.add(change_path + change_name)

    report = "\n --> Finalizer ran on %s" % str(datetime.utcnow())
    if len(fail_list) > 0:
        print("Errors have occurred in field replacements. See 'REPORT.txt' for details")
        report += "\n\n ==== REPLACEMENT FAILURES ==== \n(check values for tab characters)\n\n"
        for fail in fail_list:
            report += fail + "\n"

    if len(warning_list) > 0:
        print("Warnings were generated with field replacements. See 'REPORT.txt' for details")
        report += "\n\n ==== REPLACEMENT WARNINGS ==== \n\n"
        for warning in warning_list:
            report += warning + "\n"

    print(report)

    try:
        export.export_project(project, bids_path, changes=change_list, renamed=renamed, stub=stub, additional_report=report)
    except IOError as e:
        raise IOError("Failed to export BIDS study", *e.args)


def _where(project: BIDSProject, kwargs):
    """
    Internal function used to decide which subject, session, and/or scans correspond with a given set of key/value pairs

    * Each entry in **kwargs correspond to a given key/value pair in 'participants.tsv' and '_sessions.tsv'

    :param project: BIDSProject used to probe key-value pairs
    :param kwargs: Dictionary where key-value pair that can be associated with a given subject, session, or scan
    :return:
    """
    primary_keys = ('participant_id', 'session_id', 'filename')
    entries = list()
    for subject_label, subject in project.subjects.items():
        for session_label, session in subject.sessions.items():
            if not kwargs or (kwargs == {k: v for (k,v) in kwargs.items() if (session.fields.get(k) == v or (k == 'session_id' and v == 'ses-' + session_label)) or (subject.fields.get(k) == v or (k == 'participant_id' and v == 'sub-' + subject_label))}):
                entries.append({'subject': subject_label, 'session':session_label})

    return entries
