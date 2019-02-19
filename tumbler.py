#! /usr/bin/python
from zeroDollarReport import report as zReport
import argparse


def _getArgs():
    """Get arguments from command line."""

    parser = argparse.ArgumentParser(
        description="This is a collection of scripts to make interacting with NewSpring applications easier.")
    parser.add_argument("-z", "--zero", help="Runs the Zero Dollar Transaction Report")
    args = parser.parse_args()
    return args

if __name__ == "__main__": 

    # get command line arguments
    args = _getArgs()

    # $0 transaction report
    if args.z: zReport()
