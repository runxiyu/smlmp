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

try:
    from .common import *
except ImportError:
    from common import *

import sys
import os
import email
import subprocess
import json
import dkim
import fcntl
import configparser

def deliver() -> None:
    config = get_config()
    db = read_db()

    raw_message: bytes = sys.stdin.buffer.read()
    msg = email.message_from_bytes(raw_message, policy=policy)
    assert type(msg) is email.message.EmailMessage

    # If any of these tests fail we have a configuration error
    assert os.environ["LOCAL"] == config["general"]["localname"]
    assert os.environ["DOMAIN"] == config["general"]["domain"]

    try:
        return_path = os.environ["SENDER"]
        receiving_address = os.environ["ORIGINAL_RECIPIENT"]
        list_name, extension, receiving_address_domain = parse_local_address(receiving_address)

        if receiving_address_domain != config["general"]["domain"]:
            raise SMLMPInvalidConfiguration(
                "ORIGINAL_RECIPIENT's domain %s is not the domain %s configured."
                % (receiving_address_domain, config["general"]["domain"])
            )
        del receiving_address_domain

        # If the email is directly sent to the mailing list management user, it's unsolicited, so let's just throw it to the administrator.
        if list_name == config["general"]["localname"]:
            sendmail(msg, specified_recipients_only=True, extra_recipients=[config["general"]["administrator"]])
            return

        if len(msg["From"].addresses) != 1:
            raise SMLMPSenderError("Only one From addres is supported.")
        from_address = (msg["From"].addresses[0].username + "@" + msg["From"].addresses[0].domain).lower()

        if not msg["DKIM-Signature"]:
            raise SMLMPSenderError("Your email does not have a DKIM Signature.")
        elif not dkim.verify(msg.as_bytes()):
            # TODO: verify DMARC instead of DKIM
            raise SMLMPSenderError("Your email does not pass DKIM.")

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
            db=db,
            extension=extension,
            config=config,
            from_address=from_address,
        )



    except SMLMPSenderError as e:
        # Bounce to the user that their message failed, providing a reason.
        newmsg = email.message.EmailMessage(policy=policy)
        newmsg["To"] = return_path
        newmsg["Subject"] = "Undelivered Mail Returned to Sender"
        newmsg["From"] = config["general"]["localname"] + config["general"]["recipient_delimiter"] + "bounces@" + config["general"]["domain"]
        newmsg.set_content("Your email to this mailing list was rejected with this error message:\n\n" + "\n".join(e.args))
        newmsg.add_attachment(raw_message, maintype="message", subtype="rfc822", filename="original.eml")
        sendmail(newmsg)

    # except SMLMPException as e:
    except Exception as e:
        # Tell the administrator that a weird exception has occured.
        report_error(e)

        # Also bounce to the user that their message failed.
        newmsg = email.message.EmailMessage(policy=policy)
        newmsg["To"] = return_path
        newmsg["Subject"] = "Undelivered Mail Returned to Sender"
        newmsg["From"] = config["general"]["localname"] + config["general"]["recipient_delimiter"] + "bounces@" + config["general"]["domain"]
        newmsg.set_content("""This is the mailing list system, SMLMP, at host %s.

Your email to this mailing list program failed to deliver due to an
internal exception. Most likely, you did nothing wrong, and the server
is misconfigured, or perhaps the mailing list software is buggy. The
exception has been reported to the server's administrator, who should be
able to see and fix the problem.

The administrator of this server is %s.

The mailing list software used is SMLMP, with its upstream hosted at
https://git.andrewyu.org/andrew/smlmp.git/.
""" % (config["general"]["domain"], config["general"]["administrator"]))
        newmsg.add_attachment(raw_message, maintype="message", subtype="rfc822", filename="original.eml")
        # Consider using multipart delivery reports
        sendmail(newmsg)

def handle_mail_addressed_to_list(
    msg: email.message.EmailMessage,
    list_name: str,
    db: dict[str, Any],
    extension: str,
    config: configparser.ConfigParser,
    from_address: str
) -> None:
    if extension:
        with open(config["general"]["database"], "r+") as db_file:
            fcntl.flock(db_file, fcntl.LOCK_EX)
            # Reload the database so we won't overwrite other processes' changes that might have occured between our first read of the database and right here.
            db = json.load(db_file)
            # TODO: Don't use SenderError, make a new exception that replies with the correct formatting, i.e. From the command address, rather than the bounces address; also don't say "Undelivered mail returned to sender"; also send it to the MIME From, not the Envelope From; also set In-Reply-To to Message-ID
            try:
                if extension == "subscribe":
                    if from_address in db[list_name]["members"]:
                        raise SMLMPSenderError("You are already subscribed to the list, there's no need to subscribe.")
                    if not db[list_name]["self-subscribe-allowed"]:
                        raise SMLMPSenderError("You cannot subscribe yourself to this list. Perhaps contact the owner %s." % db[list_name]["owner"])
                    db[list_name]["members"].append(from_address)
                elif extension == "unsubscribe":
                    if from_address not in db[list_name]["members"]:
                        raise SMLMPSenderError("You are not subscribed to the list, you can't unsubscribe.")
                    while from_address in db[list_name]["members"]:
                        db[list_name]["members"].remove(from_address)
                else:
                    raise SMLMPSenderError("%s is not a valid subaddressing extension." % extension)
                json.dump(db, db_file, check_circular=True, indent=0)
            finally:
                db_file.flush()
                fcntl.flock(db_file, fcntl.LOCK_UN)
                db_file.close()
        # TODO: Reply with success/failure
        return

    # The absence of an extension means that the incoming mail is posted to the main list address. We then check and deliver the message.

    if db[list_name]["allowed_senders"] == "members":
        if from_address not in db[list_name]["members"]:
            raise SMLMPSenderError("Only list members may post to this list.")
    elif db[list_name]["allowed_senders"] == "moderators":
        if from_address not in db[list_name]["moderators"]:
            raise SMLMPSenderError("Only list moderators may post to this list.")
    else:
        if db[list_name]["allowed_senders"] != "anyone":
            raise SMLMPInvalidConfiguration("allowed_senders must be one of 'anyone', 'moderators' and 'members'.")

    dkim_include_headers, dkim_tags = parse_dkim_header(msg["DKIM-Signature"])

    # TODO Sanitize message

    # TODO Track headers that we are modifying; if we are attempting to modify DKIM h=
    force_munge_headers = {
        "list-post",
        "list-help",
        "list-subscribe",
        "list-unsubscribe",
        "list-archive",
        "list-owner",
        "list-id",
        "sender",
        "list-unsubscribe-post",
    }  # must be lowercase
    if dkim_include_headers.intersection(force_munge_headers):
        raise SMLMPSenderError(
            "Please do not include any of %s in your DKIM h= tag. This makes it impossible for the mailing list program to add list-related headers properly."
            % str(force_munge_headers)
        )

    if db[list_name]["announcements-only"]:
        msg["List-Post"] = "NO"
    else:
        msg["List-Post"] = "<" + list_name + "@" + config["general"]["domain"] + ">"

    msg["List-Help"] = "<" + config["general"]["web_root"] + list_name + ">"
    msg["List-Subscribe"] = (
        "<" + list_name + config["general"]["recipient_delimiter"] + "subscribe@" + config["general"]["domain"] + ">"
    )
    msg["List-Unsubscribe"] = (
        "<" + list_name + config["general"]["recipient_delimiter"] + "unsubscribe@" + config["general"]["domain"] + ">"
    )
    if db[list_name]["archive"]:
        msg["List-Archive"] = "<" + config["general"]["web_root"] + list_name + "/archive" + ">"
    else:
        del msg["List-Archive"]
    msg["List-Owner"] = "<" + db[list_name]["owner"] + ">"
    msg["List-ID"] = db[list_name]["shortname"] + " <" + list_name + ".lists." + config["general"]["domain"] + ">"
    msg["Sender"] = (
        config["general"]["localname"] + config["general"]["recipient_delimiter"] + "bounces@" + config["general"]["domain"]
    )  # Or config["general"]["localname"]?
    del msg["List-Unsubscribe-Post"]  # We do not follow RFC8058, but we still need to sanitize these headers.

    sendmail(msg, specified_recipients_only=True, extra_recipients=db[list_name]["members"])
    if db[list_name]["archive"]:
        sendmail(msg, specified_recipients_only=True, extra_recipients=[config["delivery agent"]["archiver_address"]])


if __name__ == "__main__":
    deliver()
else:
    raise Exception(
        "You shouldn't use smlmp_mda.py as a library. Run it directly by putting it in an alias list for piping from your MTA."
    )
