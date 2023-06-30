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
from typing import Optional, Union

from smlmp_exceptions import *
from smlmp_sanitized_config import *

import subprocess
import email
import email.policy
import smtplib

policy = email.policy.SMTP.clone(refold_source="none")


def sendmail(
    message: email.message.EmailMessage,
    specified_recipients_only: bool = False,
    extra_recipients: list[str] = [],
) -> None:
    bounce_address = LOGNAME + RECIPIENT_DELIMITER + "bounces@" + DOMAIN
    conn = smtplib.SMTP()
    conn.connect(SMTPHOST, SMTPPORT)
    if specified_recipients_only:
        recipients = extra_recipients
    else:
        recipients = extra_recipients + extract_recipient_addresses(message)
    conn.send_message(message, from_addr=bounce_address, to_addrs=recipients)


def tell_postmaster(message: email.message.EmailMessage) -> None:
    sendmail(message, specified_recipients_only=True, extra_recipients=[POSTMASTER])
    return


def extract_recipient_addresses(message: email.message.EmailMessage) -> list[str]:
    to_addresses = [
        address.username + "@" + address.domain for address in message["To"].addresses
    ] if message["To"] else []
    cc_addresses = [
        address.username + "@" + address.domain for address in message["CC"].addresses
    ] if message["To"] else []
    return to_addresses + cc_addresses


def report_error(e: SMLMPException) -> None:
    new_message = email.message.EmailMessage(policy=policy)
    new_message["Subject"] = e.report_subject
    new_message["From"] = LOGNAME + "@" + DOMAIN
    new_message["To"] = POSTMASTER
    new_message.set_content("\n".join(e.args))
    tell_postmaster(new_message)


def parse_local_address(address: str) -> tuple[str, Optional[str], str]:
    if RECIPIENT_DELIMITER in address:
        list_name, remaining = address.split(RECIPIENT_DELIMITER, 1)
        extension, domain = remaining.rsplit("@", 1)
    else:
        list_name, domain = address.rsplit("@", 1)
        extension = None
    return list_name, extension, domain

