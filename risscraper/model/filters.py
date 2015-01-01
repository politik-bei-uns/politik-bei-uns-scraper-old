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

import parse
import datetime
from pytz import timezone


def remove_whitespace(string):
  return string.replace(' ', '')


def datestring_to_datetime(inp):
  """
  Convert a date/time string do proper start (and optionally end) datetime
  """
  berlin = timezone('Europe/Berlin')
  if type(inp) in [str, unicode]:
    string = inp.strip()
    format = '{day:d}.{month:d}.{year:d} {hour:d}:{minute:d}-{hourend:d}:{minuteend:d}'
    p = parse.parse(format, string)
    if p is not None:
      out = datetime.datetime(p['year'], p['month'], p['day'], p['hour'], p['minute'], tzinfo=berlin)
      return out
    else:
      format = '{day:d}.{month:d}.{year:d} {hour:d}:{minute:d}'
      p = parse.parse(format, string)
      if p is not None:
        out = datetime.datetime(p['year'], p['month'], p['day'], p['hour'], p['minute'], tzinfo=berlin)
        return out
      else:
        format = '{day:d}.{month:d}.{year:d}'
        p = parse.parse(format, string)
        if p is not None:
          out = datetime.datetime(p['year'], p['month'], p['day'], 0, 0, tzinfo=berlin)
          return out
        else:
          return None
  return inp