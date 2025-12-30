# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import getpass
import os
from argparse import Namespace, ArgumentDefaultsHelpFormatter
from contextlib import contextmanager
from fabric import Connection
from logging import Logger
from pathlib import Path
from typing import List
from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.deploy.utils import Utils
from rsyncdirector_deploy.deploy.linux import LinuxDistro

REMOTE_VIRT_ENV_PARENT_DIR = "/usr/local"


class Install(ArgParser):

    parser = None

    def __init__(self):
        super(Install, self.__init__())

    @staticmethod
    def add_args(subparsers, parents=[]):
        # When creating a parser in which we want to add other sub_parers, only add the parents to
        # the new sub_parsers.
        Install.parser = subparsers.add_parser(
            "install",
            help="Install the rsyncdirector application",
            formatter_class=ArgumentDefaultsHelpFormatter,
        )

        # Create subparsers for different install methods.
        install_subparsers = Install.parser.add_subparsers(
            dest="install_method", help="Choose installation method", required=True
        )

        # Package index installation subcommand.
        package_index = install_subparsers.add_parser(
            "package-index",
            help="Install from a package index",
            parents=parents,  # Pass through parent parsers
            formatter_class=ArgumentDefaultsHelpFormatter,
        )
        package_index.add_argument(
            "--package-index-url",
            "-i",
            type=str,
            required=False,
            default=None,
            help="URL of the package index.  If none is provided install from Official PyPi Package Index",
        )
        package_index.add_argument(
            "--trusted-host",
            "-t",
            type=str,
            required=False,
            default=None,
            help="Specify the host name of the package index if you want to skip TLS verification",
        )
        package_index.add_argument(
            "--version",
            "-v",
            type=str,
            default="latest",
            help="Specify a specific version to install, omitting this option will deploy the latest version",
        )
        package_index.add_argument(
            "--package-index-credentials",
            "-c",
            action="store_true",
            help="Prompt for a package index username and password if required",
        )

        package_index.set_defaults(func=Install.install)

        # Wheel file installation subcommand
        wheel_parser = install_subparsers.add_parser(
            "wheel",
            help="Install from local wheel file",
            parents=parents,  # Pass through parent parsers
            formatter_class=ArgumentDefaultsHelpFormatter,
        )
        wheel_parser.add_argument(
            "--local-whl-file-path",
            "-w",
            type=str,
            required=True,
            help="Path to the rsyncdirector .whl file to be installed",
        )
        wheel_parser.set_defaults(func=Install.install)

    @staticmethod
    def create_virtualenv(
        conn: Connection, logger: Logger, python_path: str, path: str, user: str
    ) -> None:
        Utils.delete_dir(conn, logger, path, "removing and recreating virtual environment")
        # result = conn.run(f"{python_path} -mvenv {path}", warn=True)
        result = conn.run(f"mkdir -p {path}", warn=True, hide=True)
        if not result.ok:
            raise Exception(f"creating virtual env directory; path={path}, result={result}")
        result = conn.run(f"chown {user}: {path}")
        if not result.ok:
            raise Exception(
                f"chowning virtual env directory; path={path}, user={user}, result={result}"
            )
        result = conn.sudo(f"{python_path} -mvenv {path}", warn=True, user=user)
        if not result.ok:
            raise Exception(
                f"creating virtual env; python_path={python_path}, path={path}, result={result}"
            )

    @staticmethod
    def install(args: Namespace, logger: Logger) -> None:
        logger.info("Install.install")
        conn = Utils.get_connection(args.installation_host, args.installation_user)

        # Ensure that the required user and groups exist
        LinuxDistro.create_run_user(conn, args.remote_rsyncdirector_run_user)
        Install.create_virtualenv(
            conn,
            logger,
            args.remote_python_path,
            args.remote_virt_env_dir,
            args.remote_rsyncdirector_run_user,
        )

        # Just call the virt env pip command directly to avoid having to source the virtl env
        # activate script.
        venv_pip = f"{args.remote_virt_env_dir}/bin/pip"

        match args.install_method:
            case "package-index":
                Install.install_from_package_index(args, logger, conn, venv_pip)
            case "wheel":
                Install.install_from_wheel(args, logger, conn, venv_pip)
            case _:
                raise Exception(f"invalid install method; install_method={args.install_method}")

        conn.close()

    @staticmethod
    def install_from_package_index(
        args: Namespace,
        logger: Logger,
        conn: Connection,
        venv_pip: str,
    ) -> None:
        # We will use the following URL if we do not have to add uid and passwd.
        url = args.package_index_url

        # Check to see if we need to prompt for username and password
        username = ""
        password = ""
        if args.package_index_credentials:
            username = input("Enter package index username: ").strip()
            password = getpass.getpass("Enter package index password: ").strip()

            # Add the username and password to the URL
            url_protocol_and_path_tokens = args.package_index_url.split("//")
            if len(url_protocol_and_path_tokens) != 2:
                raise Exception(f"malformed --package-index-url: {args.package_index_url}")
            protocol = url_protocol_and_path_tokens[0]
            path = url_protocol_and_path_tokens[1]
            url = (
                f"{protocol}//$INDEX_UID:$INDEX_PASSWD@{path}"
                if username and password
                else f"{protocol}//{path}"
            )

        pkg = f"rsyncdirector=={args.version}" if args.version != "latest" else "rsyncdirector"
        pip_opts = []
        if url:
            pip_opts = [f"--index-url {url}"]
        if args.trusted_host:
            pip_opts.append(f"--trusted-host {args.trusted_host}")
        pip_opts = " ".join(pip_opts)
        pip_cmd = f"{venv_pip} install {pkg} {pip_opts}"
        conn.sudo(
            pip_cmd,
            user=args.remote_rsyncdirector_run_user,
            env={"INDEX_UID": username, "INDEX_PASSWD": password},
        )

    @staticmethod
    def install_from_wheel(
        args: Namespace, logger: Logger, conn: Connection, venv_pip: str
    ) -> None:
        local_whl_file_name = Path(args.local_whl_file_path).name
        remote_whl_file_path = os.path.join(os.path.sep, "var", "tmp", local_whl_file_name)
        conn.put(args.local_whl_file_path, remote_whl_file_path)
        conn.sudo(
            f"{venv_pip} install {remote_whl_file_path}", user=args.remote_rsyncdirector_run_user
        )
        conn.run(f"rm {remote_whl_file_path}")
