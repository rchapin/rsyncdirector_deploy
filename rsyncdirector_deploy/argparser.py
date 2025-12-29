# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import argparse
from abc import ABC, abstractmethod


class ArgParser(ABC):

    @staticmethod
    @abstractmethod
    def add_args(subparsers, parents=[]) -> None:
        pass
