# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Marian Steinbach
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import datetime

import parse
from pytz import timezone


def remove_whitespace(string):
    return string.replace(' ', '')


def datestring_to_datetime(inp):
    """ Convert a date/time string do proper start (and optionally end) datetime
    """
    berlin = timezone('Europe/Berlin')
    if isinstance(inp, (str, unicode)):
        string = inp.strip()
        fmt = ('{day:d}.{month:d}.{year:d} '
               '{hour:d}:{minute:d}-{hourend:d}:{minuteend:d}')
        p = parse.parse(fmt, string)
        if p is not None:
            out = datetime.datetime(p['year'], p['month'], p['day'], p['hour'],
                                    p['minute'], tzinfo=berlin)
            return out
        else:
            fmt = '{day:d}.{month:d}.{year:d} {hour:d}:{minute:d}'
            p = parse.parse(fmt, string)
            if p is not None:
                out = datetime.datetime(p['year'], p['month'], p['day'],
                                        p['hour'], p['minute'], tzinfo=berlin)
                return out
            else:
                fmt = '{day:d}.{month:d}.{year:d}'
                p = parse.parse(fmt, string)
                if p is not None:
                    out = datetime.datetime(p['year'], p['month'], p['day'],
                                            0, 0, tzinfo=berlin)
                    return out
                else:
                    return None
    return inp
