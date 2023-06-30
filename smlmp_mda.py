#!/usr/bin/env python3
#
# smlmp_mda.py: smlmp mail delivery agent
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

from smlmp_sanitized_config import *
from smlmp_common import *

import sys
import os
import email
import email.parser
import email.policy
import subprocess
import json

def deliver() -> None:
    with open(PATH_TO_DBJSON, "r") as db_file:
        db = json.load(db_file)

    raw_message: bytes = sys.stdin.buffer.read()
    msg = email.message_from_bytes(raw_message, policy=policy)
    assert type(msg) is email.message.EmailMessage

    # If any of these tests fail we have a configuration error.
    assert os.environ['MAIL_CONFIG'] == '/etc/postfix'
    assert os.environ['LOGNAME'] == LOGNAME
    assert os.environ['DOMAIN'] == DOMAIN

    receiving_address = os.environ['ORIGINAL_RECIPIENT']
    list_name, extension, receiving_address_domain = parse_local_address(receiving_address)

    if receiving_address_domain != DOMAIN:
        raise SMLMPInvalidConfiguration("ORIGINAL_RECIPIENT's domain %s is not the DOMAIN %s configured in config.py." % (receiving_address_domain, DOMAIN))
    del receiving_address_domain

    # If the email is directly sent to the mailing list management user, it's unsolicited mail, so let's just throw it to the postmaster.
    if list_name == LOGNAME:
        sendmail(msg, specified_recipients_only=True, extra_recipients=[POSTMASTER])
        return

    if list_name not in db:
        raise SMLMPInvalidConfiguration("I was asked to handle email for %s but I wasn't configured to do so. You have a broken Postfix or SMLMP configuration." % list_name)

    # Sanitize message TODO
    msg["List-Post"] = "<" + list_name @ DOMAIN + ">"
    msg["List-Help"] = "<" + HTTP_ROOT + ">"

    sendmail(msg, specified_recipients_only=True, extra_recipients=db[list_name]["members"])


if __name__ == '__main__':
    try:
        deliver()
    except SMLMPException as e:
        report_error(e)
