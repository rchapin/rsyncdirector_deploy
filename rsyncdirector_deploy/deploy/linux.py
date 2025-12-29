# This software is released under the Revised BSD License.
# See LICENSE for details
#
# Copyright (c) 2025, Ryan Chapin, https//:www.ryanchapin.com
# All rights reserved.

from __future__ import annotations
from enum import Enum
from fabric import Connection
from typing import Tuple


class LinuxDistro(Enum):
    # The string value is the "NAME" entry in the contents of the /etc/os-release file.
    ALMALINUX = "AlmaLinux"
    ALPINE = "Alpine"
    DEBIAN = "Debian GNU/Linux"
    FEDORA = "Fedora Linux"
    UBUNTU = "Ubuntu"
    REDHAT = "Red Hat Enterprise Linux"
    CENTOS = "CentOS Linux"
    CENTOS_STREAM = "CentOS Stream"
    UNKNOWN = "unknown"

    @staticmethod
    def create_group(conn: Connection, group: str) -> Tuple[bool, int]:
        def get_group_id(group: str) -> Tuple[bool, int]:
            result = conn.run(f"getent group {group}", warn=True, hide=True)
            if result.ok:
                # We only need the group name and gid fields
                group_name, _, group_id, _ = result.stdout.split(":", 3)
                # The group provided and the one found has to match
                if group == group_name:
                    return True, int(group_id)
                return False, 0
            return False, 0

        # Does a group already exist for this user?
        success, existing_id = get_group_id(group)
        if success is True and existing_id > 0:
            return True, existing_id

        result = conn.run(f"addgroup {group}")
        if result.ok:
            # Get the group id
            success, group_id = get_group_id(group)
            if success is True and group_id > 0:
                return True, group_id

        return False, 0

    @staticmethod
    def create_run_user(conn: Connection, user_name: str) -> None:
        if user_name == "root":
            return

        def does_user_exist(user_name: str) -> bool:
            result = conn.run(f"getent passwd {user_name}", warn=True, hide=True)
            return result.ok

        success, group_id = LinuxDistro.create_group(conn, user_name)
        if success and group_id > 0:
            if does_user_exist(user_name):
                return

            result = conn.run(
                f"useradd --gid {user_name} -m -s /usr/sbin/nologin {user_name}",
                warn=True,
                hide=True,
            )
            if result.ok:
                return

        raise Exception(f"unable to create user; user_name={user_name}")

    @staticmethod
    def get_enum_value_from_string(value_string: str) -> LinuxDistro:
        try:
            return LinuxDistro(value_string)
        except ValueError:
            return LinuxDistro.UNKNOWN

    @staticmethod
    def get_linux_distro(conn: Connection) -> LinuxDistro:
        result = conn.run("cat /etc/os-release")
        if not result.ok:
            return LinuxDistro.UNKNOWN

        retval = LinuxDistro.UNKNOWN
        stdout = result.stdout.strip()
        lines = stdout.splitlines()
        for line in lines:
            tokens = line.split("=")
            if len(tokens) > 1:
                if tokens[0] == "NAME":
                    name = tokens[1].replace('"', "")
                    retval = LinuxDistro.get_enum_value_from_string(name)
                    break
        return retval

    @staticmethod
    def install_packages(conn: Connection, distro: LinuxDistro, packages: str) -> None:
        cmd = None
        match distro:
            case LinuxDistro.ALPINE:
                cmd = f"apk add {packages}"
            case LinuxDistro.DEBIAN | LinuxDistro.UBUNTU:
                cmd = f"apt-get update && apt-get install -y {packages}"
            case (
                LinuxDistro.ALMALINUX | LinuxDistro.CENTOS | LinuxDistro.FEDORA | LinuxDistro.REDHAT
            ):
                cmd = f"dnf install -y {packages}"
            case _:
                raise Exception(f"unknown distro; distro={distro}")

        result = conn.run(cmd)
