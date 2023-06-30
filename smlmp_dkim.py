# smlmp_dkim.py: DKIM-related functionality
# Adapted from dkimpy, modified from original software
#
# Copyright (C) 2023  Andrew Yu <https://www.andrewyu.org/>
# Copyright (C) 2019  Scott Kitterman <scott@kitterman.com>
# Copyright (C) 2017  Gene Shuman <gene@valimail.com>
# Copyright (C) 2011, 2012 Stuart D. Gathman
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
#

from __future__ import annotations
from typing import Optional, Union

from smlmp_exceptions import *

import email
import re
import email.policy

policy = email.policy.SMTP.clone(refold_source="none")

def parse_dkim_header(dkim_header: str) -> tuple[set[str], dict[str, str]]:
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
