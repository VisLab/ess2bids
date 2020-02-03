"""
This module contains functions used to export a BIDSProject object to the physical filesystem.
"""

from json import JSONDecodeError

import os
import shutil
import os.path
import re

from datetime import datetime

from filesystem import util
from structure.project import *
from structure.subject import *
from structure.task import *

bids_ignore = """field_replacements.json
archived
VALIDATOR_OUTPUT.txt
REPORT.txt"""


# TODO: each sidecar is written with _eeg in the name. make this more agnostic? as well as coordsystem and electrodes
# TODO: what if there's no session level?
def export_project(bids_project: BIDSProject, output_path, changes=None, renamed=None, stub=False, verbose=False, additional_report= ""):
    """
    Exports a BIDSProject to the given file path.

    * Any existing sidecar, field_replacements.json, or renamed files are cut/paste to an 'archived' directory, located at the top-level of the exported BIDS study
    * Each file that is archived has a labeled ISO 8601 datetime in the filename used to show when that file was last modified.
    * If changes is provided as a list, only the filepaths specified in changes are overwritten. Changes shouldn't be provided if the output directory is "fresh"
    * If renamed is provided as a dictionary, each key resembles the old filename, and its corresponding value resmebles the new filename

    :raises OSError

    :param bids_project: An imported BIDS study
    :param output_path: The destination for the top level of the BIDS study
    :param changes: List of files that should be modified, if not None
    :param renamed: dictionary of old_filename/new_filename key/value pairs, if not None
    :param stub: If set to True, large scans and ignored files will not be copied over.
    :param verbose: If set to True, informational logs are sent to standard out
    :param report: Additional information that should be included with the generation REPORT that's generated with each export.
    :return: None
    """

    util.printv("Preprocessing Dataset...", verbose)
    bids_project.preprocess()

    if bool(renamed):
        util.printv("Renaming requested files...", verbose)
        for old_name, new_name in renamed.items():
            if os.path.exists(old_name):
                try:
                    os.rename(old_name, new_name)
                except OSError:
                    print("[WARNING] Unable to rename %s to %s" % (old_name, new_name))

    util.printv("Generating top level files...", verbose)
    if not os.path.isdir(output_path):
        os.makedirs(output_path)

    if changes is None:
        report = " --> BIDS study generated with Ess-Bids on %s\n\n" % str(datetime.utcnow())
        util.write(report + additional_report, "%s/REPORT.txt" % output_path, changes)
    else:
        util.write(additional_report, "%s/REPORT.txt" % output_path, changes=None, append=True)

    d = util.read_json('%s/dataset_description.json' % output_path)
    if d and bids_project.dataset_description != d:
        _send_to_archive(output_path, 'dataset_description.json')

    util.write_json(bids_project.dataset_description, '%s/dataset_description.json' % output_path, changes=changes)
    util.write(bids_project.readme, '%s/README' % output_path, changes=changes)
    util.write(bids_project.changes, '%s/CHANGES' % output_path, changes=changes)

    for task_label, task in bids_project.tasks.items():
        try:
            d = util.read_json('%s/task-%s_eeg.json' % (output_path, task_label))
            if d and task.get_fields() != d:
                _send_to_archive(output_path, "task-%s_eeg.json" % task_label)
        except JSONDecodeError:
            print("[WARNING] Existing '%s/task-%s_eeg.json' has a JSON encoding error. Archiving..." % (output_path, task_label))
            _send_to_archive(output_path, "task-%s_eeg.json" % task_label)
        util.write_json(task.get_fields(), "%s/task-%s_eeg.json" % (output_path, task_label))
        if task.event_codes:
            util.write_json({'event_code': {'Description': 'Maps Event Code IDS to their respective HED tags',
                                            'EventCodes': task.event_codes}},
                            "%s/task-%s_events.json" % (output_path, task_label), changes=changes)

    _scrub_renamed_tasks(bids_project.tasks.keys(), output_path, '')

    try:
        d = util.read_json('%s/field_replacements.json' % output_path)
        if d and bids_project.field_replacements != d:
            _send_to_archive(output_path, 'field_replacements.json')
    except JSONDecodeError:
        print("[WARNING] Existing '%s/field_replacements.json' has a JSON encoding error. Archiving..." % output_path)
        _send_to_archive(output_path, "field_replacements.json")
        changes.remove('%s/field_replacements.json' % output_path)
    util.write_json(bids_project.field_replacements, '%s/field_replacements.json' % (output_path), changes=changes)

    local_ignore = bids_ignore
    for ignored_file in bids_project.ignored_files:
        local_ignore += "\n" + os.path.basename(ignored_file)
        copyargs = (ignored_file, os.path.join(output_path, os.path.basename(ignored_file)))
        if not stub and not util.is_changed(os.path.join(output_path, os.path.basename(ignored_file)), changes):
            if os.path.isdir(ignored_file):
                shutil.copytree(*copyargs)
            else:
                shutil.copy(*copyargs)

    util.write(bids_ignore, "%s/.bidsignore" % output_path, changes=changes)

    util.write_tsv({"sub-" + k: v for k, v in bids_project.subjects.items()}, "%s/participants.tsv" % output_path, primary_key="participant_id" ,changes=changes)
    util.write_json(bids_project.field_definitions, "%s/participants.json" % output_path, changes=changes)

    for subject_label, subject in bids_project.subjects.items():
        util.printv("Generating files for Subject %s:" % subject_label, verbose)
        dir_context = "%s/sub-%s/sub-%s" % (output_path, subject_label, subject_label)
        if not os.path.isdir('%s/sub-%s' % (output_path, subject_label)): os.mkdir('%s/sub-%s' % (output_path, subject_label))
        util.write_tsv({ "ses-" + k: v for k,v in subject.sessions.items()}, "%s_sessions.tsv" % dir_context, primary_key="session_id", changes=changes)
        util.write_json(subject.field_definitions, "%s_sessions.json" % dir_context,  changes=changes)
        for task_label, task in bids_project.tasks.items():
            try:
                d = util.read_json('%s_task-%s_eeg.json' % (dir_context, task_label))
                if d and task.get_fields(subject_label=subject_label) != d:
                    _send_to_archive(output_path, "%s_task-%s_eeg.json" % (dir_context[len(output_path) + 1:], task_label))
            except JSONDecodeError:
                print("[WARNING] Existing '%s_task-%s_eeg.json' has a JSON encoding error. Archiving..." % (dir_context, task_label))
                _send_to_archive(output_path, "%s_task-%s_eeg.json" % (dir_context[len(output_path) + 1:], task_label))
            util.write_json(task.get_fields(subject_label=subject_label), "%s_task-%s_eeg.json" % (dir_context, task_label))
        _scrub_renamed_tasks(bids_project.tasks.keys(), output_path, 'sub-%s/' % subject_label)
        for session_label, session in subject.sessions.items():
            if len(subject.sessions) != 1 or session_label != session_agnostic_token:
                util.printv("...for session %s" % session_label, verbose)
                dir_context = "%s/sub-%s/ses-%s/sub-%s_ses-%s" % (output_path, subject_label, session_label, subject_label, session_label)
            if not os.path.isdir(dir_context[:dir_context.rfind('/')]): os.mkdir(dir_context[:dir_context.rfind('/')])
            segmented_dir_context = (dir_context[:dir_context.rfind('/')], dir_context[dir_context.rfind('/') + 1:])
            util.write_tsv(session.scans, '%s_scans.tsv' % dir_context, primary_key='filename', changes=changes)
            util.write_json(session.field_definitions, "%s_scans.json" % dir_context, changes=changes)
            _scrub_renamed_tasks(bids_project.tasks.keys(), output_path, dir_context[len(output_path) + 1:dir_context.rfind('/')])
            for task_label, task in bids_project.tasks.items():
                try:
                    d = util.read_json('%s_task-%s_eeg.json' % (dir_context, task_label))
                    if d and task.get_fields(subject_label=subject_label, session_label=session_label) != d:
                        _send_to_archive(output_path,
                                        "%s_task-%s_eeg.json" % (dir_context[len(output_path) + 1:], task_label))
                except JSONDecodeError:
                    print("[WARNING] Existing '%s_task-%s_eeg.json' has a JSON encoding error. Archiving..." % (
                    dir_context, task_label))
                    _send_to_archive(output_path, "%s_task-%s_eeg.json" % (dir_context[len(output_path) + 1:], task_label))
                util.write_json(task.get_fields(subject_label=subject_label, session_label= session_label),
                                "%s_task-%s_eeg.json" % (dir_context, task_label))

            if not os.path.isdir("%s/eeg" % segmented_dir_context[0]): os.mkdir('%s/eeg' % segmented_dir_context[0])
            util.write_json(session.coordsystem, "%s/eeg/%s_coordsystem.json" % segmented_dir_context, changes=changes)
            util.write_tsv(session.electrodes, "%s/eeg/%s_electrodes.tsv" % segmented_dir_context, primary_key='name', changes=changes)
            run_count = 0

            for scan_label, scan in session.scans.items():
                run_count += 1
                if scan.run == 0 and len(session.scans) > 1:
                    scan.run = run_count
                dir_context = "%s/eeg/%s" % segmented_dir_context
                task_run_context = "%s_task-%s" % (dir_context, scan.task) + ("_run-%1d" % (scan.run) if scan.run != 0 else "")
                util.write_tsv(scan.channels, "%s_channels.tsv" % task_run_context, primary_key='name', changes=changes)
                util.write_tsv(scan.events, "%s_events.tsv" % task_run_context, changes=changes)
                if not os.path.exists("%s_eeg.set" % task_run_context) and not stub:
                    util.printv("Copying scan %s" % scan_label, verbose)
                    shutil.copy(scan.path, "%s_eeg.set" % task_run_context)
                _scrub_renamed_tasks(bids_project.tasks.keys(), output_path,
                                    dir_context[len(output_path) + 1:dir_context.rfind('/')])

                for task_label, task in bids_project.tasks.items():
                    try:
                        d = util.read_json('%s_eeg.json' % task_run_context)
                        if d and task.get_fields(subject_label=subject_label, session_label=session_label, scan_name=scan_label) != d:
                            _send_to_archive(output_path,
                                            "%s_eeg.json" % (task_run_context[len(output_path) + 1:]))
                    except JSONDecodeError:
                        print("[WARNING] Existing '%s_eeg.json' has a JSON encoding error. Archiving..." % task_run_context)
                        _send_to_archive(output_path,
                                         "%s_eeg.json" % task_run_context[len(output_path) + 1:])
                    util.write_json(task.get_fields(subject_label=subject_label, session_label=session_label, scan_name=scan_label),
                                    "%s_eeg.json" % task_run_context)
    util.printv("...done!", verbose)


def _send_to_archive(bids_path, sub_path):
    """
    Cut and pastes a given file to the 'archived/' directory at the top-level of the BIDS study

    :param bids_path: Root path of the BIDS study
    :param sub_path: Relative path from the BIDS study to the file being archived
    :return:
    """
    if not os.path.exists(os.path.join(bids_path, sub_path)):
        return
    filename_base = os.path.basename(sub_path)
    segmented_filename = (filename_base[:filename_base.rfind('.')], filename_base[filename_base.rfind('.') + 1:])

    last_modified = datetime.utcfromtimestamp(os.path.getmtime(os.path.join(bids_path, sub_path))).strftime("%Y-%m-%d_%H-%M-%S")

    if not os.path.exists('%s/archived' % bids_path):
        os.makedirs('%s/archived' % bids_path)

    shutil.move(os.path.join(bids_path, sub_path), "%s/archived/%s(%s).%s" % (bids_path, segmented_filename[0], str(last_modified), segmented_filename[1]))


def _scrub_renamed_tasks(task_list, bids_path, sub_path):

    """
    Sends all sidecars (or files that refer to a specific task) not associated with the given BIDSProject to 'archived/'

    * Typically called when re-exporting a "fresh" project, and there exist sidecars associated with a renamed task

    :param task_list: List of tasks from a BIDSProject
    :param bids_path: Root path of the BIDS study
    :param sub_path: Relative path from the BIDS study to the file being archived
    :return:
    """
    for file in [f for f in os.listdir(os.path.join(bids_path, sub_path)) if 'task-' in f and f.split('.')[-1] not in util.file_extensions]:
        if re.match(r".*task-([A-Za-z0-9]+)", file).group(1) not in task_list:
            _send_to_archive(bids_path, os.path.join(sub_path, file))