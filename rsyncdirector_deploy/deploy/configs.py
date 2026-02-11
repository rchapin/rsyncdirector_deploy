# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

from __future__ import annotations

import os
import string
import sys
from argparse import ArgumentDefaultsHelpFormatter, Namespace
from io import StringIO
from logging import Logger
from pathlib import Path
from typing import Dict

from fabric import Connection

from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.consts import REMOTE_CONFIG_DIR, REMOTE_LOG_DIR
from rsyncdirector_deploy.deploy.linux import LinuxDistro
from rsyncdirector_deploy.deploy.utils import Utils


class Configs(ArgParser):

    parser = None

    def __init__(self):
        super().__init__()

    @staticmethod
    def add_args(subparsers, parents=[]):
        Configs.parser = subparsers.add_parser(
            "configs",
            help=(
                "Deploy the configurations and required directories and systemd configurations "
                "to run the application"
            ),
            parents=parents,
            formatter_class=ArgumentDefaultsHelpFormatter,
        )

        Configs.parser.set_defaults(func=Configs.install)
        Configs.parser.add_argument(
            "--service-instance-identifier",
            "-i",
            type=str,
            required=True,
            help=(
                "Deployment configurations allow for multiple instances of the rsyncdirector to be "
                "running on an individual host at the same time.  This is achieved through the use of "
                "a systemd service template.  This configuration defines the systemd serivce instance "
                "for this deployment."
            ),
        )
        Configs.parser.add_argument(
            "--local-rsyncdirector-config-file-path",
            "-c",
            type=str,
            required=True,
            help="Path on the local host to the rsyncdirector config file to be deployed to the installation host",
        )

        Configs.parser.add_argument(
            "--clear-existing-configs",
            "-k",
            action="store_true",
            help="Will clear any existing configs in the /etc/rsyncdirector dir on the installation host",
        )

    @staticmethod
    def install(args: Namespace, logger: Logger):
        logger.info("Configs.install")
        conn = Utils.get_connection(args.installation_host, args.installation_user)

        if args.clear_existing_configs:
            Configs.clear_existing_configs(conn, logger, args.installation_host)

        # Ensure that logrotate is installed.
        distro = LinuxDistro.get_linux_distro(conn)
        LinuxDistro.install_packages(conn, distro, ["logrotate", "sudo"])
        logger.info("logrotate installed/verified")

        # Figure out the path to this file so that we can load the require config template files.
        current_file_path = Path(__file__).resolve()
        module_dir = current_file_path.parent.parent
        configs_dir = module_dir / "configs"

        # Confirm that python is already installed
        result = conn.run(f"stat {args.remote_python_path}", warn=True, hide=True)
        if not result.ok:
            raise Exception(f"python is not installed; expected_path={args.remote_python_path}")

        LinuxDistro.create_run_user(conn, args.remote_rsyncdirector_run_user)
        rsyncdirector_config = Utils.load_yaml_file(args.local_rsyncdirector_config_file_path)

        remote_dirs = [REMOTE_LOG_DIR, REMOTE_CONFIG_DIR]
        # Only create another remote dire if there is a pid file dir defined in the config.
        if "pid_file_dir" in rsyncdirector_config:
            remote_dirs.append(rsyncdirector_config["pid_file_dir"])
        for dir in remote_dirs:
            conn.run(f"mkdir -p {dir}")
            conn.run(f"chown {args.remote_rsyncdirector_run_user}: {dir}")
            conn.run(f"chmod 755 {dir}")

        files = []

        config_file_name = Path(args.local_rsyncdirector_config_file_path).name
        remote_config_path = os.path.join(os.sep, REMOTE_CONFIG_DIR, config_file_name)
        files.append(
            {
                "data": Utils.load_file(args.local_rsyncdirector_config_file_path),
                "remote_path": os.path.join(os.sep, REMOTE_CONFIG_DIR, config_file_name),
                "user_group": f"{args.remote_rsyncdirector_run_user}:",
                "perms": "644",
            }
        )

        # Load, hydrate, and deploy configuration files. Some files have a
        # 'service_instance_identifier' added to it.  This enables us to run multiple instances of
        # the rsyncdirector, each with different configs via the same systemd unit file.
        env_tmpl_path = configs_dir / "etc" / "rsyncdirector" / "rsyncdirector.env.tmpl"
        env_hydrated = Configs.load_and_hydrate_tmpl(
            env_tmpl_path, {"config_path": remote_config_path}
        )
        files.append(
            {
                "data": env_hydrated,
                "remote_path": os.path.join(
                    os.sep,
                    REMOTE_CONFIG_DIR,
                    f"rsyncdirector-{args.service_instance_identifier}.env",
                ),
                "user_group": f"{args.remote_rsyncdirector_run_user}:",
                "perms": "644",
            }
        )

        logrotate_tmpl_path = configs_dir / "etc" / "logrotate.d" / "rsyncdirector.tmpl"
        logrotate_hydrated = Configs.load_and_hydrate_tmpl(
            logrotate_tmpl_path, {"id": args.service_instance_identifier}
        )
        files.append(
            {
                "data": logrotate_hydrated,
                "remote_path": os.path.join(
                    os.sep,
                    "etc",
                    "logrotate.d",
                    f"rsyncdirector-{args.service_instance_identifier}",
                ),
                "user_group": "root:",
                "perms": "644",
            }
        )

        run_sh_tmpl_path = configs_dir / "etc" / "rsyncdirector" / "rsyncdirector.sh.tmpl"
        run_sh_hydrated = Configs.load_and_hydrate_tmpl(
            run_sh_tmpl_path,
            {"virt_env_parent_dir": args.remote_virt_env_dir},
        )
        files.append(
            {
                "data": run_sh_hydrated,
                "remote_path": os.path.join(os.sep, REMOTE_CONFIG_DIR, "rsyncdirector.sh"),
                "user_group": f"{args.remote_rsyncdirector_run_user}:",
                "perms": "744",
            }
        )

        unit_file_tmpl_path = (
            configs_dir / "etc" / "systemd" / "system" / "rsyncdirector@.service.tmpl"
        )
        unit_file_hydrated = Configs.load_and_hydrate_tmpl(
            unit_file_tmpl_path,
            {
                "user": args.remote_rsyncdirector_run_user,
                "group": args.remote_rsyncdirector_run_user,
            },
        )
        files.append(
            {
                "data": unit_file_hydrated,
                "remote_path": os.path.join(
                    os.path.sep, "etc", "systemd", "system", "rsyncdirector@.service"
                ),
                "user_group": "root:",
                "perms": "644",
            }
        )

        for file in files:
            remote_path = file["remote_path"]
            conn.put(StringIO(file["data"]), remote_path)
            conn.run(f"chown {file["user_group"]} {remote_path}")
            conn.run(f"chmod {file["perms"]} {remote_path}")
        conn.run("systemctl daemon-reload")
        conn.run("systemctl restart logrotate")
        conn.close()

        print(
            f"\nrsyncdirector config installation on host [{args.installation_host}] is complete\n"
            f"run 'systemctl start rsyncdirector@{args.service_instance_identifier}.service' to start\n"
            f"and 'systemctl enble rsyncdirector@{args.service_instance_identifier}.service' to ensure it will start on boot",
            flush=True,
        )

    @staticmethod
    def load_and_hydrate_tmpl(tmpl_file_path: Path, data: Dict) -> str:
        tmpl_str = Utils.load_file(tmpl_file_path)
        tmpl = string.Template(tmpl_str)
        return tmpl.substitute(data)

    @staticmethod
    def clear_existing_configs(conn: Connection, logger: Logger, host: str) -> None:
        # DO NOT remove any .pid files if they are in this dir.
        result = conn.run(f"ls -1 {REMOTE_CONFIG_DIR}/* | grep -v '.pid'", warn=True, hide=True)
        if result is None:
            raise Exception(f"unable to get listing of [{REMOTE_CONFIG_DIR}] on installation host")

        stdout = (result.stdout or "").strip()
        # If the command exited non-zero but produced no output, treat this as "no non-pid files"
        # and proceed without raising, since there is nothing to delete.
        if not result.ok and stdout == "":
            logger.info(
                f"No non-pid config files found in [{REMOTE_CONFIG_DIR}] on installation host; "
                "skipping deletion of existing configs."
            )
            return

        if not result.ok:
            raise Exception(f"unable to get listing of [{REMOTE_CONFIG_DIR}] on installation host")
        print("deleting existing config files:")
        for line in result.stdout.splitlines():
            print(line)

        confirmation = (
            input(
                f"Running install configs with --clear-existing-configs flag. "
                f"This will clean all existing config files from the [{REMOTE_CONFIG_DIR}] "
                f"directory on host [{host}], you could suffer data loss. "
                "Do you want to continue? (yes/no): "
            )
            .lower()
            .strip()
        )
        if confirmation == "yes":
            result = conn.run(f"rm -rf {REMOTE_CONFIG_DIR}/*")
            if not result.ok:
                raise Exception("deleting existing config files; " f"path={REMOTE_CONFIG_DIR}")
        else:
            logger.info(
                "Exiting installation. Not deleting existing config files from "
                f"remote dir [{REMOTE_CONFIG_DIR}]."
            )
            sys.exit(0)
