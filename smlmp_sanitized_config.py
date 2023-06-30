# smlmp_smtpdirect.py: Wraps config.py to confirm stuff.
# Copyright (C) 2023  Andrew Yu <https://www.andrewyu.org/>
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

from config import *

# HTTP_ROOT should end with a slash
if not HTTP_ROOT.endswith("/"):
    HTTP_ROOT += "/"
