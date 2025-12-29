# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import os
import requests
import tempfile
import argparse
from argparse import Namespace
from contextlib import chdir
from invoke import run
from logging import Logger
from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.deploy.utils import Utils

REMOTE_PARENT_DIR_DEFAULT = "/usr/local"


class Python(ArgParser):

    parser = None

    def __init__(self):
        super(Python, self.__init__())

    @staticmethod
    def add_args(subparsers, parents=[]):
        Python.parser = subparsers.add_parser(
            "python",
            help="Compile Python on the remote host",
            parents=parents,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        Python.parser.add_argument(
            "--source-tarball-url",
            "-u",
            type=str,
            required=True,
            help="Specify the URL for the compatible Python source tarball to be downloaded, unpacked and compiled. See https://www.python.org/downloads/",
        )
        Python.parser.add_argument(
            "--source-tarball-md5sum",
            "-m",
            type=str,
            required=True,
            help="Specify the MD5 Sum for the Python source tarball to be downloaded",
        )
        Python.parser.add_argument(
            "--remote-parent-dir",
            "-r",
            type=str,
            default=REMOTE_PARENT_DIR_DEFAULT,
            help="The parent directory into which the Python directory will be installed",
        )
        Python.parser.set_defaults(func=Python.install)

    @staticmethod
    def install(args: Namespace, logger: Logger) -> None:
        logger.info("installing Python; args={args}")
        conn = Utils.get_connection(args.installation_host, args.installation_user)

        with tempfile.TemporaryDirectory() as temp_dir:
            filename = os.path.basename(args.source_tarball_url)
            if not filename:
                raise Exception("could not glean file name from URL")

            source_dir = filename.replace(".tgz", "")
            version = source_dir.replace("Python-", "")
            file_path = os.path.join(os.sep, temp_dir, filename)

            response = requests.get(args.source_tarball_url, stream=True)
            response.raise_for_status()
            with open(file_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=8192):
                    fh.write(chunk)

            logger.info(f"Python tarball downloaded, file_path={file_path}")
            with chdir(temp_dir):
                result = run(f"md5sum {file_path}")
                if result.return_code != 0:
                    raise Exception(
                        f"getting checksum for python tarball; file_path={file_path}, result={result}"
                    )
                md5sum = result.stdout.split()[0]
                if args.source_tarball_md5sum != md5sum:
                    raise Exception(
                        f"md5sums did not match; expected={args.source_tarball_md5sum}, actual={md5sum}"
                    )

                remote_tarball_dir = os.path.join(os.sep, "var", "tmp", "python-src")
                conn.run(f"mkdir -p {remote_tarball_dir}")
                remote_tarball_path = os.path.join(os.sep, remote_tarball_dir, filename)
                remote_source_path = os.path.join(os.sep, remote_tarball_dir, source_dir)
                conn.put(file_path, remote_tarball_path)

                # Delete any existing python installation if it exists.
                remote_target_dir = os.path.join(
                    os.sep, args.remote_parent_dir, f"python-{version}"
                )

                Utils.delete_dir(
                    conn, logger, remote_target_dir, "removing and rebuilding python installation"
                )
                # result = conn.run(f'test -d "{remote_target_dir}"', warn=True, hide=True)
                # if result.ok:
                # else:
                #     logger.info(
                #         "no existing python installation continuing to compile and "
                #         f"install; remote_target_dir={remote_target_dir}"
                #     )

                with conn.cd(remote_tarball_dir):
                    conn.run(f"tar -xzvf {filename}")
                with conn.cd(remote_source_path):
                    conn.run(
                        f"./configure --prefix={remote_target_dir} --exec-prefix={remote_target_dir}"
                    )
                    conn.run("make && make install")

        conn.close()
