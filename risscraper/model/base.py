# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Marian Steinbach, Ernesto Ruge
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


class Base(object):
    """
    A base object
    """

    def __init__(self):
        self._filters = []
        #{
        #    'fieldname': 'identifier',
        #    'filter': lambda x: filters.remove_whitespace(x)
        #}]
        self._required_fields = []
        self._enforced_types = {}
        self._defaults = {
            'modified': datetime.datetime.utcnow(),
            'created': datetime.datetime.utcnow(),
        }
        self.apply_defaults()
        #self.apply_filters()

    def dict(self):
        self.apply_filters()
        out = {}
        for key in dir(self):
            if key.startswith('_'):
                continue
            val = getattr(self, key)
            if callable(val):
                continue
            if val is None:
                continue
            outkey = key
            if outkey.startswith('x_'):
                outkey = outkey[2:]
            out[outkey] = val
        return out

    def apply_defaults(self):
        for key in self._defaults.keys():
            if key in dir(self):
                if getattr(self, key) is None:
                    setattr(self, key, self._defaults[key])
            else:
                setattr(self, key, self._defaults[key])

    def apply_filters(self):
        for key in dir(self):
            if key.startswith('_'):
                continue
            value = getattr(self, key)
            if callable(value):
                continue
            if value is None:
                continue
            for flt in self._filters:
                if key == flt['fieldname']:
                    value = flt['filter'](value)
                    setattr(self, key, value)
