# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

import sys
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter
from logging import Logger
from rsyncdirector_deploy.argparser import ArgParser
from rsyncdirector_deploy.deploy.configs import Configs
from rsyncdirector_deploy.deploy.install import Install
from rsyncdirector_deploy.deploy.ssh import Ssh
from rsyncdirector_deploy.consts import REMOTE_RSYNC_DIRECTOR_RUN_USER, REMOTE_VIRT_ENV_DIR


class RsyncDirector(ArgParser):

    parser = None

    def __init__(self):
        super(RsyncDirector, self.__init__())

    @staticmethod
    def add_args(subparsers, parents=[]):
        parent_args = parents.copy()

        # Add args common to all RsyncDirector sub parsers
        remote_rsyncdirector_run_user_arg = ArgumentParser(add_help=False)
        remote_rsyncdirector_run_user_arg.add_argument(
            "--remote-rsyncdirector-run-user",
            "-u",
            type=str,
            default=REMOTE_RSYNC_DIRECTOR_RUN_USER,
            help="User under which we want to run the service on the host on which we are installing rsyncdirector",
        )
        parent_args.append(remote_rsyncdirector_run_user_arg)

        remote_python_path = ArgumentParser(add_help=False)
        remote_python_path.add_argument(
            "--remote-python-path",
            "-p",
            type=str,
            required=True,
            help="Path on the remote host to the Python binary with which we will create the virtual environment",
        )
        parent_args.append(remote_python_path)

        remote_virt_env_parent_path = ArgumentParser(add_help=False)
        remote_virt_env_parent_path.add_argument(
            "--remote-virt-env-dir",
            "-e",
            type=str,
            default=REMOTE_VIRT_ENV_DIR,
            help="The directory on the remote host in which the virtual environment will be created",
        )
        parent_args.append(remote_virt_env_parent_path)

        # RsyncDirector doesn't have any actual run targets so we DO NOT add any parents arguments.
        RsyncDirector.parser = subparsers.add_parser(
            "rsyncdirector",
            help="Install rsyncdirector application and configurations",
            formatter_class=ArgumentDefaultsHelpFormatter,
        )

        # When calling just the rsyncdirector target in the argparse tree, just display the help for
        # this branch in the tree.
        RsyncDirector.parser.set_defaults(func=RsyncDirector.help)

        subparser = RsyncDirector.parser.add_subparsers()
        Configs.add_args(subparser, parent_args)
        Install.add_args(subparser, parent_args)

        ssh_parent_args = parents.copy()
        ssh_parent_args.append(remote_rsyncdirector_run_user_arg)
        Ssh.add_args(subparser, ssh_parent_args)

    @staticmethod
    def help(_args: Namespace, _logger: Logger) -> None:
        print(
            "Deploy the RsyncDirector configs and application.  When deploying for the first"
            "time run 'configs' first, then 'install'.  After which, you can run either to "
            "update either the configs or the version of the RsyncDirector."
        )
        print()
        RsyncDirector.parser.print_help(sys.stderr)
