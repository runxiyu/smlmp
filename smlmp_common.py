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
from smlmp_smtpdirect import *
from config import *

import subprocess
import email

policy = email.policy.SMTP # or the utf-8 variant? TODO
sendmail = smtp_sendmail

def tell_postmaster(message: email.message.EmailMessage) -> None:
    sendmail(message, specified_recipients_only=True, extra_recipients=[POSTMASTER])
    return

def extract_recipient_addresses(message: email.message.EmailMessage) -> list[str]:
    to_addresses = [address.username + '@' + address.domain for address in message['To'].addresses]
    cc_addresses = [address.username + '@' + address.domain for address in message['CC'].addresses]
    return to_addresses + cc_addresses


def report_error(e: SMLMPException) -> None:
    new_message = email.message.EmailMessage(policy=policy)
    new_message['Subject'] = e.report_subject
    new_message['From'] = LOGNAME + '@' + DOMAIN
    new_message['To'] = POSTMASTER
    new_message.set_content('\n'.join(e.args))
    tell_postmaster(new_message)

def parse_local_address(address: str) -> tuple[str, Optional[str], str]:
    if RECIPIENT_DELIMITER in address:
        list_name, remaining = address.split(RECIPIENT_DELIMITER, 1)
        extension, domain = remaining.rsplit('@', 1)
    else:
        list_name, domain = address.rsplit('@', 1)
        extension = None
    return list_name, extension, domain
