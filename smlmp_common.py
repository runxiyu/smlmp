# smlmp_common.py: common functions used in smlmp
# Copyright (C) 2023  Andrew Yu <https://www.andrewyu.org/>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import annotations
from typing import Optional

from smlmp_exceptions import *
from config import *

import subprocess
import email


def sendmail(message: bytes, force_recipients: list[str] = [], extra_recipients: list[str] = []) -> None:
    if force_recipients:
        p = subprocess.Popen([SENDMAIL_CMD, '-oi'] + force_recipients + extra_recipients, stdin=subprocess.PIPE)
    else:
        p = subprocess.Popen([SENDMAIL_CMD, '-t', '-oi'] + extra_recipients, stdin=subprocess.PIPE)
    stdout, stderr = p.communicate(input=message)
    if p.returncode != 0:
        raise SendmailError(stderr)
    else:
        return

def parse_local_address(address: str) -> tuple[str, Optional[str], str]:
    if RECIPIENT_DELIMITER in address:
        list_name, remaining = address.split(RECIPIENT_DELIMITER, 1)
        extension, domain = remaining.rsplit('@', 1)
    else:
        list_name, domain = address.rsplit('@', 1)
        extension = None
    return list_name, extension, domain
