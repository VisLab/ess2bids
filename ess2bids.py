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
from ess.generator import *
from ess.replacer import replacer_delete, replacer_make
import matlab.engine
import sys
import os
import json


def load_config():
    try:
        config_json = open('config.json')
        config = json.load(config_json)
        config_json.close()
        required = ['EEGLAB installation path', 'BIDSVersion']
        if not all(k in config for k in required):
            print("Missing fields in 'config.json':")
            print([k for k in required if k not in config])
            sys.exit(1)
    except EnvironmentError as e:
        print("Unable to open 'config.json'")
        raise e
    return config


def main():
    config = load_config()

    parser = argparse.ArgumentParser()

    parser.add_argument('input', type=str)
    parser.add_argument('output', type=str)
    parser.add_argument('-s', '--stub', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    try:
        try:
            bids_file = generate_bids_project(os.path.abspath(args.input), config['EEGLAB installation path'], verbose=args.verbose)
        except LXMLDecodeError:
            print(f'There was an error with {args.input}. Attempting to fix encoding errors...')
            replacer_make(args.input)
            bids_file = generate_bids_project(os.path.abspath(args.input), config['EEGLAB installation path'], verbose=args.verbose)
        finally:
            replacer_delete(args.input)
    except LXMLDecodeError:
        print("Unable to decode 'study_description.xml', exiting...")
        sys.exit(1)
    except OSError as e:
        print(e)
        sys.exit(1)
    except matlab.engine.MatlabExecutionError:
        print("Failed to call 'eeglab()'. Check 'config.json' to make sure your EEGLAB installation path is correct.")
        sys.exit(1)
    except matlab.engine.EngineError:
        print("Unable to start Matlab engine. Did you install 'matlabengineforpython'?")
        sys.exit(1)

    bids_file.dataset_description['BIDSVersion'] = config['BIDSVersion']
    try:
        report = generate_report(bids_file)
        export_project(bids_file, args.output, stub=args.stub, verbose=args.verbose, additional_report=report)
    except OSError as e:
        print(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
