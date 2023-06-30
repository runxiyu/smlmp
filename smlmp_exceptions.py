# smlmp_exception.py: exception classes used in smlmp
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
