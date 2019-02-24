#! /usr/bin/python
import argparse

from syncPreAlpha import sync
from zeroDollarReport import report as zReport


def _getArgs():
    """Get arguments from command line."""

    parser = argparse.ArgumentParser(
        description=
        "This is a collection of scripts to make interacting with NewSpring applications easier"
    )
    parser.add_argument(
        "--zero",
        help="Runs the Zero Dollar Transaction Report",
        action="store_true")
    parser.add_argument(
        "--sync", help="Syncs Rock pre-alpha", action="store_true")
    args = parser.parse_args()
    return args


if __name__ == "__main__":

    # get command line arguments
    args = _getArgs()

    # $0 transaction report
    if args.zero: zReport()

    # Sync pre alpha
    if args.sync: sync()
