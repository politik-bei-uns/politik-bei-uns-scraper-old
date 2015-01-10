# encoding: utf-8

"""
Copyright (c) 2012 Marian Steinbach

Hiermit wird unentgeltlich jeder Person, die eine Kopie der Software und
der zugehörigen Dokumentationen (die "Software") erhält, die Erlaubnis
erteilt, sie uneingeschränkt zu benutzen, inklusive und ohne Ausnahme, dem
Recht, sie zu verwenden, kopieren, ändern, fusionieren, verlegen
verbreiten, unterlizenzieren und/oder zu verkaufen, und Personen, die diese
Software erhalten, diese Rechte zu geben, unter den folgenden Bedingungen:

Der obige Urheberrechtsvermerk und dieser Erlaubnisvermerk sind in allen
Kopien oder Teilkopien der Software beizulegen.

Die Software wird ohne jede ausdrückliche oder implizierte Garantie
bereitgestellt, einschließlich der Garantie zur Benutzung für den
vorgesehenen oder einen bestimmten Zweck sowie jeglicher Rechtsverletzung,
jedoch nicht darauf beschränkt. In keinem Fall sind die Autoren oder
Copyrightinhaber für jeglichen Schaden oder sonstige Ansprüche haftbar zu
machen, ob infolge der Erfüllung eines Vertrages, eines Delikts oder anders
im Zusammenhang mit der Software oder sonstiger Verwendung der Software
entstanden.
"""

import datetime
import filters
import sys


class Base(object):
  """
  A base object
  """

  def __init__(self):
    self._filters = []
    #{
    #  'fieldname': 'identifier',
    #  'filter': lambda x: filters.remove_whitespace(x)
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
