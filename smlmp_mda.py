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

from config import *
from smlmp_common import *

import sys
import os
import email
import subprocess
import json

def deliver() -> None:
    with open("db.json", "r") as db_file:
        db = json.load(db_file)

    raw_message: bytes = sys.stdin.buffer.read()
    parsed_message = email.message_from_bytes(raw_message)
    print(type(parsed_message))

    # If any of these tests fail we have a configuration error.
    assert os.environ['MAIL_CONFIG'] == '/etc/postfix'
    assert os.environ['LOGNAME'] == LOGNAME
    assert os.environ['DOMAIN'] == DOMAIN

    receiving_address = os.environ['ORIGINAL_RECIPIENT']
    list_name, extension, _ = parse_local_address(receiving_address)

    # If the email is directly sent to the mailing list management user, it's unsolicited mail, so let's just throw it to the postmaster.
    if list_name == LOGNAME:
        sendmail(raw_message, force_recipients=[POSTMASTER])
        return

    if list_name not in db:
        raise SMLMPInvalidConfiguration("I was asked to handle email for %s but I wasn't configured to do so. You have a broken Postfix or SMLMP configuration." % list_name)

    # Sanitize message
    parsed_message['Return-Path'] = LOGNAME + RECIPIENT_DELIMITER + 'bounces@' + DOMAIN # TODO: Does this even work? Apparently not, use postfix mapping.
    sendmail(parsed_message, force_recipients=db[list_name][members])


if __name__ == '__main__':
    try:
        deliver()
    except SMLMPException as e:
        report_error(e)
