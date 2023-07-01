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
from typing import Union, Any

from smlmp_common import *

import sys
import os
import email
import subprocess
import json
import dkim


def deliver() -> None:
    with open(PATH_TO_DBJSON, "r") as db_file:
        db = json.load(db_file)

    raw_message: bytes = sys.stdin.buffer.read()
    msg = email.message_from_bytes(raw_message, policy=policy)
    assert type(msg) is email.message.EmailMessage

    # If any of these tests fail we have a configuration error
    assert os.environ["LOGNAME"] == LOGNAME
    assert os.environ["DOMAIN"] == DOMAIN

    try:
        receiving_address = os.environ["ORIGINAL_RECIPIENT"]
        list_name, extension, receiving_address_domain = parse_local_address(
            receiving_address
        )

        if receiving_address_domain != DOMAIN:
            raise SMLMPInvalidConfiguration(
                "ORIGINAL_RECIPIENT's domain %s is not the DOMAIN %s configured in config.py."
                % (receiving_address_domain, DOMAIN)
            )
        del receiving_address_domain

        # If the email is directly sent to the mailing list management user, it's unsolicited, so let's just throw it to the postmaster.
        if list_name == LOGNAME:
            sendmail(msg, specified_recipients_only=True, extra_recipients=[POSTMASTER])
            return


        if list_name not in db:
            raise SMLMPInvalidConfiguration(
                "I was asked to handle email for %s but I wasn't configured to do so. You have a broken Postfix or SMLMP configuration."
                % list_name
            )

        if receiving_address not in extract_recipient_addresses(msg):
            raise SMLMPSenderError(
                "BCCing or otherwise sending emails to the mailing list services without the list's address being in To or CC headers is unsupported."
            )


        handle_mail_addressed_to_list(
            msg,
            list_name=list_name,
            list_config=db[list_name],
            extension=extension,
            DOMAIN=DOMAIN,
            LOGNAME=LOGNAME,
            receiving_address=receiving_address,
        )

    except SMLMPSenderError as e:
        return_path = msg["Return-Path"][1:-1]
        newmsg = email.message.EmailMessage(policy=policy)
        newmsg["To"] = return_path
        newmsg["Subject"] = e.report_subject
        newmsg.set_content("\n".join(e.args))
        sendmail(newmsg)

    except SMLMPException as e:
        report_error(e)


def handle_mail_addressed_to_list(
        msg: email.message.EmailMessage, list_name: str, list_config: dict[str, Any], extension: str, DOMAIN: str, LOGNAME: str, receiving_address: str
) -> None:
    if extension:
        # TODO Implement action addresses based on extensions
        raise SMLMPException(
            "Oops, extensions in list addresses aren't implemented yet!"
        )

    # The absence of an extension means that the incoming mail is posted to the main list address. We then check and deliver the message.
    if len(msg["From"].addresses) != 1:
        raise SMLMPSenderError("You must use one and only one address in the From header.")
    from_address = msg["From"].addresses[0].username + "@" + msg["From"].addresses[0].domain
    if list_config["allowed_senders"] == "members":
        if from_address not in list_config["members"]:
            raise SMLMPSenderError("Only list members may post to this list.")
    elif list_config["allowed_senders"] == "moderators":
        if from_address not in list_config["moderators"]:
            raise SMLMPSenderError("Only list moderators may post to this list.")
    else:
        if list_config["allowed_senders"] != "anyone":
            raise SMLMPInvalidConfiguration("allowed_senders must be one of 'anyone', 'moderators' and 'members'.")

    if not msg["DKIM-Signature"]:
        raise SMLMPSenderError("Your email does not have a DKIM Signature.")
    elif not dkim.verify(msg.as_bytes()):
        raise SMLMPSenderError("Your email does not pass DKIM.")

    dkim_include_headers, dkim_tags = parse_dkim_header(msg["DKIM-Signature"])

    # TODO Sanitize message

    # TODO Track headers that we are modifying; if we are attempting to modify DKIM h=
    force_munge_headers = {"list-post", "list-help", "list-subscribe", "list-unsubscribe", "list-archive", "list-owner", "list-id", "sender", "list-unsubscribe-post"} # must be lowercase
    if dkim_include_headers.intersection(force_munge_headers):
        raise SMLMPSenderError("Please do not include any of %s in your DKIM h= tag. This makes it impossible for the mailing list program to add list-related headers properly." % str(force_munge_headers))

    if list_config["announcements-only"]:
        msg["List-Post"] = "NO"
    else:
        msg["List-Post"] = "<" + list_name + "@" + DOMAIN + ">"

    msg["List-Help"] = "<" + HTTP_ROOT + list_name + ">"
    msg["List-Subscribe"] = (
        "<" + list_name + RECIPIENT_DELIMITER + "subscribe@" + DOMAIN + ">"
    )
    msg["List-Unsubscribe"] = (
        "<" + list_name + RECIPIENT_DELIMITER + "unsubscribe@" + DOMAIN + ">"
    )
    msg["List-Archive"] = "<" + HTTP_ROOT + list_name + "/archive" + ">"
    msg["List-Owner"] = "<" + list_config["owner"] + ">"
    msg["List-ID"] = list_config["shortname"] + " <" + list_name + ".lists." + DOMAIN + ">"
    msg["Sender"] = list_name + RECIPIENT_DELIMITER + "bounces@" + DOMAIN  # Or LOGNAME?
    del msg[
        "List-Unsubscribe-Post"
    ]  # We do not follow RFC8058, but we still need to sanitize these headers.

    sendmail(
        msg, specified_recipients_only=True, extra_recipients=list_config["members"]
    )


if __name__ == "__main__":
    deliver()
else:
    raise Exception(
        "You shouldn't use smlmp_mda.py as a library. Run it directly by putting it in an alias list for piping."
    )
