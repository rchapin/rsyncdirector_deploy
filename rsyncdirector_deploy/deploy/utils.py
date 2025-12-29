# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import sys
import yaml
from fabric import Connection
from logging import Logger
from pathlib import Path
from typing import Dict


class Utils(object):

    @staticmethod
    def get_connection(host: str, user: str) -> Connection:
        return Connection(
            host=host,
            user=user,
        )

    @staticmethod
    def load_yaml_file(path: str) -> Dict:
        with open(path, "r") as fh:
            return yaml.load(fh, Loader=yaml.FullLoader)

    def load_file(path: Path) -> str:
        with open(path, "r") as fh:
            return fh.read()

    def delete_dir(conn: Connection, logger: Logger, path: str, existing_dir_msg: str) -> None:
        # The directory may not exist.
        result = conn.run(f'test -d "{path}"', warn=True, hide=True)
        if result.ok:
            confirmation = (
                input(
                    f"Deleting [{path}]; reason: {existing_dir_msg}. "
                    "This directory will be rm -rf'd. If this is the wrong directory "
                    "you could suffer data loss.  Do you want to continue? (yes/no): "
                )
                .lower()
                .strip()
            )
            if confirmation == "yes":
                result = conn.run(f"rm -rf {path}")
                if not result.ok:
                    raise Exception(
                        "deleting remote target directory before installing; " f"path={path}"
                    )
            else:
                logger.info(
                    f"Exiting installation. Not deleting remote dir [{path}]. "
                    "Either delete the existing dir or re-run the "
                    "installation providing an alternate target directory."
                )
                sys.exit(0)
        else:
            logger.info(f"no existing directory to delete; path={path}")
