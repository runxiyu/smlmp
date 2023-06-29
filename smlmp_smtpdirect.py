# smlmp_smtpdirect.py: deliver emails with local SMTP server
# Copyright (C) 2023  Andrew Yu <https://www.andrewyu.org/>
# Copyright (C) 1998-2018  Free Software Foundation, Inc.
#
# This library is based on GNU Mailman 2's SMTPDirect handler.
# Some code from there is used here.
# Note that while this file is licensed GPLv3, the rest of the
# program is licensed AGPLv3.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import annotations
from config import *
from smlmp_exceptions import *
from smlmp_common import *

import smtplib

import email



def smtp_sendmail(message: email.message.EmailMessage, specified_recipients_only:bool=False, extra_recipients: list[str] = []) -> None:
    bounce_address = LOGNAME + RECIPIENT_DELIMITER + 'bounces@' + DOMAIN
    conn = smtplib.SMTP()
    conn.connect(SMTPHOST, SMTPPORT)
    if specified_recipients_only:
        recipients = extra_recipients
    else:
        recipients = extra_recipients + extract_recipient_addresses(message)
    conn.send_message(message, from_addr=bounce_address, to_addrs=recipients)
