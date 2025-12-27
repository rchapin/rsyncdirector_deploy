# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2019, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

from __future__ import annotations
import os
import string
from argparse import Namespace, ArgumentDefaultsHelpFormatter
from fabric import Connection
from io import StringIO
from logging import Logger
from pathlib import Path
from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.consts import (
    REMOTE_CONFIG_DIR,
    REMOTE_LOG_DIR,
)
from rsyncdirector_deploy.deploy.utils import Utils
from rsyncdirector_deploy.deploy.linux import LinuxDistro
from typing import Tuple


class Configs(ArgParser):

    parser = None

    def __init__(self):
        super(Configs, self.__init__())

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

    @staticmethod
    def install(args: Namespace, logger: Logger):
        logger.info("Configs.install")
        conn = Utils.get_connection(args.installation_host, args.installation_user)

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
        for dir in [REMOTE_LOG_DIR, REMOTE_CONFIG_DIR, rsyncdirector_config["pid_file_dir"]]:
            conn.run(f"mkdir -p {dir}")
            conn.run(f"chown {args.remote_rsyncdirector_run_user}: {dir}")
            conn.run(f"chmod 775 {dir}")

        config_file_name = Path(args.local_rsyncdirector_config_file_path).name
        remote_config_path = os.path.join(os.sep, "etc", "rsyncdirector", config_file_name)

        # Load, hydrate, and deploy configuration files. Each env file name has a
        # 'service_instance_identifier' added to it.  This enables us to run multiple instances of
        # the rsyncdirector, each with different configs via the same systemd unit file.
        local_env_tmpl_path = configs_dir / "etc" / "rsyncdirector" / "rsyncdirector.env.tmpl"
        local_env_tmpl_str = Utils.load_file(local_env_tmpl_path)
        local_env_tmpl = string.Template(local_env_tmpl_str)
        local_env_hydrated = local_env_tmpl.substitute({"config_path": remote_config_path})
        remote_env_path = os.path.join(
            os.sep, REMOTE_CONFIG_DIR, f"rsyncdirector-{args.service_instance_identifier}.env"
        )

        local_run_sh_tmpl_path = configs_dir / "etc" / "rsyncdirector" / "rsyncdirector.sh.tmpl"
        local_run_sh_tmpl_str = Utils.load_file(local_run_sh_tmpl_path)
        local_run_sh_tmpl = string.Template(local_run_sh_tmpl_str)
        local_run_sh_hydrated = local_run_sh_tmpl.substitute(
            {"virt_env_parent_dir": args.remote_virt_env_dir}
        )
        remote_run_sh_path = os.path.join(os.sep, "etc", "rsyncdirector", "rsyncdirector.sh")

        conn.put(args.local_rsyncdirector_config_file_path, remote_config_path)
        conn.put(StringIO(local_env_hydrated), remote_env_path)
        conn.put(StringIO(local_run_sh_hydrated), remote_run_sh_path)
        conn.run(f"chown -R {args.remote_rsyncdirector_run_user}: {REMOTE_CONFIG_DIR}")
        conn.run(f"chmod 774 {remote_run_sh_path}")

        local_unit_file_tmpl_path = configs_dir / "etc" / "systemd" / "system" / "rsyncdirector@.service.tmpl"
        local_unit_file_tmpl_str = Utils.load_file(local_unit_file_tmpl_path)
        local_unit_file_tmpl = string.Template(local_unit_file_tmpl_str)
        local_unit_file_hydrated = local_unit_file_tmpl.substitute(
            {
                "user": args.remote_rsyncdirector_run_user,
                "group": args.remote_rsyncdirector_run_user,
            }
        )
        remote_unit_file_path = os.path.join(
            os.path.sep, "etc", "systemd", "system", "rsyncdirector@.service"
        )
        conn.put(StringIO(local_unit_file_hydrated), remote_unit_file_path)
        conn.run("systemctl daemon-reload")

        conn.close()
