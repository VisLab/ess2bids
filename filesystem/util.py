"""
This module contains several functions that act as wrappers for reading several filetypes that are used
in BIDS studies.

It also contains a 'file_extensions' list, which contains all legal file extensions
"""

import json
import os.path
from typing import *

common_extensions = ['.json', '.tsv', '', '.md']

file_extensions = ['.set', '.nii']

def read_tsv(tsv_file, primary_index = 0):
    """
    Reads in a .tsv file, and maps it to a dictionary or a list.

    * If primary_index is None, this function returns a list of dictionaries, each key-value pair being a column/value pair for each row
    * If primary_index is an int, this function returns a dictionary instead, where the column specified in the index is used as a key for each row

    :param tsv_file: the source filepath of a given .tsv file
    :param primary_index: index of column used as a key for each row, if not None
    :return:
        If primary_index is None:
            Returns a list of dictionaries, each dictionary having the key for the column label, and the value for that given row/column

        If primary_index is not None:
            Returns a dictionary of dictionaries. Each parent dictionary has a key pertaining to each value of the column specified as "primary_index",
            each sub dictionary having a key for every OTHER column label, with each value for that given row/column

    """
    try:
        file = open(tsv_file, "r")
        header_fields = file.readline().strip().split("\t")
        if primary_index is not None:
            d = dict()
        else:
            d = list()

        while True:
            line = file.readline()

            if line is None or len(line) == 0:
                break

            line = line.strip().split('\t')

            if primary_index is not None:
                d[line[primary_index]] = dict()
            else:
                d.append(dict())

            for i in range(0, len(line)):
                if primary_index is not None and i == primary_index:
                    continue
                elif primary_index is not None:
                    d[line[primary_index]][header_fields[i]] = line[i]
                else:
                    d[-1][header_fields[i]] = line[i]

        file.close()
        return d

    except IOError:
        if os.path.exists(tsv_file):
            print("Unable to read %s" % tsv_file)
        return None

def read_json(json_file):
    """
    Serves as a wrapper for json.load, which returns None if a filepath doesn't exist

    :raises:
        JSONDecodeError: If .json file is corrupted

    :param json_file:
    :return: The result from json.load(), if json_file points to an existing JSON file
    """

    try:
        file = open(json_file, "r")
        dictionary = json.load(file)
        file.close()

        return dictionary
    except IOError:
        if os.path.exists(json_file):
            print("Unable to read %s" % json_file)
        return None


def write(entity, output_path, changes = None, append=False):
    """
    Serves as a wrapper for file.write()

    * If changes are provided, and the output_path isn't featured in the changes list, the function is idempotent.

    :param entity: Str-like object that is written
    :param output_path: Destination for file being written
    :param changes: The list of files to be changed, if specified
    :param append: If True, the file is appended instead of overwritten
    :return:
    """
    if not is_changed(output_path, changes) or entity is None: return
    if append:
        file = open(output_path, "a")
    else:
        file = open(output_path, "w")
    file.write(entity)
    file.close()


def write_json(entity: Dict, output_path, changes = None):
    """
    Serves as a wrapper for json.dump()

    * If changes are provided, and the output_path isn't featured in the changes list, the function is idempotent.

    :param entity: A dictionary that is JSON serializable
    :param output_path: Destination for file being written
    :param changes: The list of files to be changed, if specified
    :return:
    """
    if not is_changed(output_path, changes) or not bool(entity): return
    file = open(output_path, "w")
    json.dump(entity, file, indent=2)
    file.close()


def write_tsv(entity_tree, output_path, primary_key = None, changes = None, default="n/a"):
    """
    Takes a dictionary/list of dictionaries, and then writes it to a .tsv file

    * Also takes objects that have 'fields' in their namespace that point to a dictionary.
    * If changes are provided, and the output_path isn't featured in the changes list, the function is idempotent.
    * If primary_key isn't provided, and entity_tree is a dictionary, then the keys for entity_tree aren't written to the .tsv
    * If primary_key is provided, each key in the root entity_tree will be written under the column specified as the value for 'primary_key'
    * If a sub dictionary doesn't contain a field that another sub dictionary does, the prior dictionary will create a field with the specified default value

    :raises:
        TypeError: if entity_tree doesn't match the above description

    :param entity_tree: Dictionary/list of dictionaries
    :param output_path: Destination for file being written
    :param primary_key: Header name for the keys in the parent dictionary
    :param changes: The list of files to be changed, if specified
    :return:
    """

    if not is_changed(output_path, changes) or not bool(entity_tree): return
    header = []

    for key in entity_tree:
        fields = dict()
        if isinstance(entity_tree, dict):
            if hasattr(entity_tree[key], 'fields'):
                fields = entity_tree[key].fields
            elif isinstance(entity_tree[key], dict):
                fields = entity_tree[key]
            header += [i for i in list(fields.keys()) if i not in header]
        elif isinstance(entity_tree, list):
            header += [i for i in key if i not in header]
        else:
            raise TypeError(
                "This method requires a list of dictionary, dictionary of dictionaries, or objects that have a dict() attribute called 'fields'")

    if header is None:
        return

    file = open(output_path, "w")
    file.write((primary_key + "\t" if primary_key else "") + "\t".join(header))

    for key in entity_tree:
        fields = dict()
        if isinstance(entity_tree, dict):
            if hasattr(entity_tree[key], 'fields'):
                fields = entity_tree[key].fields
            elif isinstance(entity_tree[key], dict):
                fields = entity_tree[key]
            file.write("\n" + (key + "\t" if primary_key else "") + "\t".join([str(fields[k]) if k in fields else default for k in header]))
        else:
            file.write("\n" + "\t".join(
                [str(key[k]) if k in key else default for k in header]))

    file.close()


def is_changed(output_path, changes):
    if changes is None or output_path in changes or not os.path.exists(output_path):
        return True
    else:
        return False


def printv(string, verbose=True):
    if verbose:
        print(string)