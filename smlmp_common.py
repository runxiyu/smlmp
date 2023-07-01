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

from config import *

if not HTTP_ROOT.endswith("/"):
    HTTP_ROOT += "/"

import subprocess
import email
import email.policy
import smtplib
import re

policy = email.policy.SMTP.clone(refold_source="none")

class SMLMPException(Exception):
    report_subject = "SMLMP Exception"


class SMLMPCriticalError(SMLMPException):
    report_subject = "SMLMP Critical Error"


class SMLMPInvalidConfiguration(SMLMPCriticalError):
    report_subject = "SMLMP Invalid Configuration"


class SMLMPRecipientError(SMLMPException):
    report_subject = "SMLMP Recipient Error"


class SendmailError(SMLMPRecipientError):
    report_subject = "SMLMP Sendmail Error"


class SMLMPSenderError(SMLMPException):
    report_subject = "SMLMP Sender Error"

class SMLMPParseError(SMLMPSenderError):
    report_subject = "SMLMP Parse Error"


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
    ] if message["CC"] else []
    return to_addresses + cc_addresses


def report_error(e: SMLMPException) -> None:
    new_message = email.message.EmailMessage(policy=policy)
    new_message["Subject"] = e.report_subject
    new_message["From"] = LOGNAME + "@" + DOMAIN
    new_message["To"] = POSTMASTER
    new_message.set_content("\n".join(e.args))
    tell_postmaster(new_message)


def parse_local_address(address: str) -> tuple[str, str, str]:
    if RECIPIENT_DELIMITER in address:
        list_name, remaining = address.split(RECIPIENT_DELIMITER, 1)
        extension, domain = remaining.rsplit("@", 1)
    else:
        list_name, domain = address.rsplit("@", 1)
        extension = ""
    return list_name, extension, domain

def parse_dkim_header(dkim_header: str) -> tuple[set[str], dict[str, str]]:
    # Adapted from dkimpy, modified from original software
    #
    # This function, parse_dkim_header, is also covered under the following
    # copyright and license. THIS LICENSE DOES NOT APPLY TO THE ENTIRE PROGRAM.
    #
    # Copyright (C) 2023        Andrew Yu <https://www.andrewyu.org/>
    # Copyright (C) 2019        Scott Kitterman <scott@kitterman.com>
    # Copyright (C) 2017        Gene Shuman <gene@valimail.com>
    # Copyright (C) 2011, 2012  Stuart D. Gathman
    #
    # This software is provided 'as-is', without any express or implied
    # warranty.  In no event will the author be held liable for any damages
    # arising from the use of this software.
    #
    # Permission is granted to anyone to use this software for any purpose,
    # including commercial applications, and to alter it and redistribute it
    # freely, subject to the following restrictions:
    #
    # 1. The origin of this software must not be misrepresented; you must not
    #    claim that you wrote the original software. If you use this software
    #    in a product, an acknowledgment in the product documentation would be
    #    appreciated but is not required.
    # 2. Altered source versions must be plainly marked as such, and must not be
    #    misrepresented as being the original software.
    # 3. This notice may not be removed or altered from any source distribution.
    tags = {}
    tag_specs = dkim_header.strip().split(';')
    # Trailing semicolons are valid.
    if not tag_specs[-1]:
        tag_specs.pop()
    for tag_spec in tag_specs:
        try:
            key, value = [x.strip() for x in tag_spec.split('=', 1)]
        except ValueError:
            raise SMLMPParseError("invalid tag spec", tag_spec)
        if re.match(r'^[a-zA-Z](\w)*', key) is None:
            raise SMLMPParseError("invalid tag spec", tag_spec)
        if key in tags:
            raise SMLMPParseError("duplicate tag", key)
        tags[key] = value
    dkim_include_headers = set([x.lower() for x in re.split(r"\s*:\s*", tags['h'])])
    return dkim_include_headers, tags
