# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import os
import sys
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter
from fabric import Connection
from logging import Logger
from pathlib import Path
from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.deploy.utils import Utils
from typing import Tuple


class Ssh(ArgParser):

    parser = None

    def __init__(self):
        super(Ssh, self.__init__())

    @staticmethod
    def add_args(subparsers, parents=[]):
        parent_args = parents.copy()

        # Add args common to all Ssh sub parsers
        hosts_arg = ArgumentParser(add_help=False)
        hosts_arg.add_argument(
            "--hosts",
            "-g",
            type=str,
            nargs="+",
            help="A space-separated list of hosts",
        )
        parent_args.append(hosts_arg)

        Ssh.parser = subparsers.add_parser(
            "ssh",
            help="Setup SSH configurations for rsyncdirector users",
            formatter_class=ArgumentDefaultsHelpFormatter,
        )

        # Create subparsers for different ssh operations.
        ssh_subparsers = Ssh.parser.add_subparsers(
            dest="ssh_configs", help="Choose ssh configuration operation", required=True
        )

        add_known_host_keys = ssh_subparsers.add_parser(
            "add-known-host-keys",
            help="Add ssh keys from remote hosts to the rsyncdirector user's ssh known_hosts file",
            parents=parent_args,
            formatter_class=ArgumentDefaultsHelpFormatter,
        )
        add_known_host_keys.add_argument(
            "--type",
            "-t",
            type=str,
            nargs="+",
            required=True,
            help=(
                "Specify the type of the key to fetch from the scanned host.  'all', will "
                "retreive all keys from the host: example rsa, ed25519, etc."
            ),
        )
        add_known_host_keys.add_argument(
            "--port",
            "-r",
            type=str,
            required=False,
            default="22",
            help="Specify an alternate SSH port",
        )
        add_known_host_keys.set_defaults(func=Ssh.add_known_host_keys)

    @staticmethod
    def help(_args: Namespace, _logger: Logger) -> None:
        print("run with -h for details on how to use ssh commands")

    @staticmethod
    def add_known_host_keys(args: Namespace, logger: Logger) -> None:
        logger.info("Ssh.add_known_host_keys")
        conn = Utils.get_connection(args.installation_host, args.installation_user)
        user = args.remote_rsyncdirector_run_user
        host = args.installation_host

        def add_key(conn: Connection, host: str, port: str, type: str) -> None:
            opts = [f"-p {port}"]
            if type != "all":
                opts.append(f"-t {type}")
            opts = " ".join(opts)
            cmd = f"ssh-keyscan {opts} -H {host}"
            result = conn.sudo(cmd, user=user, warn=True, hide=False)
            if not result.ok:
                raise Exception(f"executing ssh-keyscan; cmd={cmd}, result={result}")

            keys = result.stdout
            if keys == "":
                raise Exception(f"empty key return from ssh-keyscan; cmd={cmd}, result={result}")
            keys = keys.split("\n")
            home = Ssh.get_home(conn, host, user)
            known_hosts_path = os.path.join(os.path.sep, home, ".ssh", "known_hosts")
            for key in keys:
                conn.sudo(f'echo "{key}" >> {known_hosts_path}', user=user)

        confirmation = (
            input(
                f"Adding host keys for {user}@{host} fory hosts={args.hosts}\n"
                "This operation will REMOVE ALL existing keys for the provided hosts before adding new keys\n"
                "Do you want to continue? (yes/no): "
            )
            .lower()
            .strip()
        )
        if confirmation != "yes":
            logger.info(f"Exiting without adding known host keys; {user}@{host} hosts={args.hosts}")
            sys.exit(0)

        for host in args.hosts:
            conn.sudo(f"ssh-keygen -R {host}", user=user)
            if len(args.type) == 1 and args.type[0] == "all":
                add_key(conn, host, args.port, "all")
                continue
            for t in args.type:
                add_key(conn, host, args.port, t)

    @staticmethod
    def get_home(conn: Connection, host: str, user: str) -> str:
        result = conn.run(f"getent passwd {user}", warn=True, hide=True)
        if not result.ok:
            raise Exception(f"getent passwd {user}; result={result}")
        stdout = result.stdout.strip()
        stdout_tokens = stdout.split(":")
        if len(stdout_tokens) < 6:
            raise Exception(
                f"invalid value returned attmpting to parse result of getent; stdout={stdout}, stdout_tokens={stdout_tokens}"
            )
        return stdout_tokens[5]
