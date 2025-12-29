# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import argparse
import logging
import os
import sys

# from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.deploy.python import Python
from rsyncdirector_deploy.deploy.rsyncdirector import RsyncDirector

logging.basicConfig(
    format="%(asctime)s,%(levelname)s,%(module)s,[%(threadName)s],%(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)


def parse_args():
    top_parser = argparse.ArgumentParser()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--installation-host",
        "-o",
        type=str,
        required=True,
        help="Hostname of machine onto which rsyncdirector is to be installed",
    )
    common.add_argument(
        "--installation-user",
        "-s",
        type=str,
        default="root",
        help=(
            "User with which we will install components on the remote host.  If you override this, "
            "that user may not have the permissions to execute all required actions"
        ),
    )

    subparsers = top_parser.add_subparsers()
    RsyncDirector.add_args(subparsers, [common])
    Python.add_args(subparsers, [common])

    # If the user has not provided any arguments at all, print the help.
    if len(sys.argv) == 1:
        top_parser.print_help(sys.stderr)
        sys.exit(1)

    return top_parser.parse_args(), top_parser


def main():
    args, parser = parse_args()
    logger = logging.getLogger(__name__)
    # If the user has selected a branch in the tree for which there is no defined function print the
    # help.
    if "func" not in args:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args.func(args, logger)


###########################################################
# MAIN
###########################################################

if __name__ == "__main__":
    main()
