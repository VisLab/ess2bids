"""
Main script for converting an ESS study to a BIDS study

Usage: python ess2bids.py [-sv] <input> <output>

Options:
    -s, --stub: Skip the process of copying over large scan files, as well as files ignored by BIDS
    -v, --verbose: Provide additional logging into standard output

Positional Arguments:
    input: Source of the root of a given ESS study
    output: Destination for the root of a given BIDS study
"""

import argparse

from filesystem.export import export_project
from filesystem import util
from ess.generator import *
from ess.deprecated.generator import generate_bids_project as old_generate_bids_project
from ess.replacer import replacer_delete, replacer_make
from utilities.matlab_instance import *
import matlab.engine
import copy
import sys
import os
import json

default_bids_validator_config = {
    "ignore": (),
    "warn": (),
    "error": (),
    "ignoredFiles": ["/field_replacements.json", "/archived/**", "/VALIDATOR_OUTPUT.txt", "/REPORT.txt"]
}


def load_config():
    try:
        config_json = open('config.json')
        config = json.load(config_json)
        config_json.close()
        required = ['eeglab_path', 'BIDSVersion']
        if not all(config.get(k) for k in required):
            print("Missing fields in 'config.json':")
            print([k for k in required if not config.get(k)])
            sys.exit(1)
        if not config.get('bids-validator-config'):
            config['bids-validator-config'] = default_bids_validator_config
        else:
            config['bids-validator-config'] = {k: (config['bids-validator-config'].get(k) or v)
                                               for k, v in default_bids_validator_config.items()}
    except EnvironmentError as e:
        print("Unable to open 'config.json'")
        raise e
    return config


def write_validator_config(bvc, ignored_files, output_path, config_name=".bids-validator-config.json"):
    output_config = copy.deepcopy(bvc)
    for file in ignored_files:
        ignore_filename = "/" + os.path.basename(file)
        if os.path.isdir(file):
            ignore_filename += "/**"
        output_config['ignoredFiles'].append(ignore_filename)
    util.write_json(output_config, os.path.join(output_path, config_name))


def main():
    config = load_config()

    parser = argparse.ArgumentParser()

    parser.add_argument('input', type=str, help="input directory for top-level ESS study")
    parser.add_argument('output', type=str, help="output path for BIDS study")
    parser.add_argument('-s', '--stub', action='store_true',
                        help="if set, doesn't copy over large files, and only generates metadata")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="if set, generates additional logs for metadata extraction and generation")
    parser.add_argument('-l', '--legacy', action='store_true',
                        help="if set, uses deprecated ESS converter")
    parser.add_argument('-b', '--batch', action='store_true',
                        help="if set, converts all studies within directory set by 'input', \
                        and outputs them as subdirectories in 'output'")

    args = parser.parse_args()

    if args.batch:
        studies = [os.path.join(args.input, study) for study in os.listdir(args.input)]
    else:
        studies = (args.input,)

    try:
        create_matlab_instance(config['eeglab_path'])
    except matlab.engine.MatlabExecutionError:
        print("Failed to call 'eeglab()'. Check 'config.json' to make sure your EEGLAB installation path is correct.")
        sys.exit(1)
    except matlab.engine.EngineError:
        print("Unable to start Matlab engine. Did you install 'matlabengineforpython'?")
        sys.exit(1)

    for study in studies:
        try:
            try:
                if args.legacy:
                    bids_file = old_generate_bids_project(os.path.abspath(study), args.verbose)
                else:
                    bids_file = generate_bids_project(os.path.abspath(study), args.verbose)
            except LXMLDecodeError:
                print(f'There was an error with {study}. Attempting to fix encoding errors...')
                replacer_make(study)
                if args.legacy:
                    bids_file = old_generate_bids_project(os.path.abspath(study), args.verbose)
                else:
                    bids_file = generate_bids_project(os.path.abspath(study), args.verbose)
            finally:
                replacer_delete(study)
        except LXMLDecodeError:
            print("Unable to decode 'study_description.xml', exiting...")
            sys.exit(1)
        except OSError as e:
            print(e)
            sys.exit(1)

        bids_file.dataset_description['BIDSVersion'] = config['BIDSVersion']
        if study == studies[-1]:
            teardown_matlab_instance()
        try:
            report = generate_report(bids_file)
            if args.batch:
                output = os.path.join(args.output, os.path.basename(study))
            else:
                output = args.output
            export_project(bids_file, output, stub=args.stub, verbose=args.verbose, additional_report=report)
            write_validator_config(config['bids-validator-config'], bids_file.ignored_files, output)
        except OSError as e:
            print(e)
            sys.exit(1)


if __name__ == '__main__':
    main()
