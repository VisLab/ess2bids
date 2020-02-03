"""
Main script used to replace fields throughout the BIDS study, and validate the study for BIDS compliance

Usage: python finalize.py [-svp] <bids_path>

Options:
    -s, --stub: Skip the process of copying over large scan files, as well as files ignored by BIDS
    -v, --verbose: Provide additional logging into standard output
    -p, --skip_validation: Only replace fields, skip the validation step

Positional Arguments:
    bids_path: Path to the root of a given BIDS study

"""

import os
import sys
import argparse
import subprocess

from filesystem import field_replacement


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bids_path', type=str)
    parser.add_argument('-s', '--stub', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-p', '--skip_validation', action='store_true')

    args = parser.parse_args()

    if not os.path.isdir(args.bids_path):
        print("Invalid directory specified")
        sys.exit(1)
    try:
        field_replacement.replace_fields(args.bids_path, stub=args.stub)
    except IOError as e:
        print(e)
        sys.exit(1)

    if not args.skip_validation and _bids_validator_installed():
        bids_validator_process = subprocess.run("bids-validator %s" % args.bids_path, shell=True, capture_output=True)

        f = open(os.path.join(args.bids_path, "VALIDATOR_OUTPUT.txt"), "w")
        f.write(bids_validator_process.stdout.decode("utf-8"))
        print(f'{args.bids_path} has been analyzed for validity.')
        f.close()

def _bids_validator_installed():
    npm_process = subprocess.run('npm list -g', shell=True, capture_output=True)
    if npm_process.returncode == 0 and 'bids-validator' in npm_process.stdout.decode("utf-8"):
        return True
    else:
        print("Warning: 'bids-validator' isn't installed on your machine. This dataset cannot be tested for validity")
        return False

if __name__ == '__main__':
    main()