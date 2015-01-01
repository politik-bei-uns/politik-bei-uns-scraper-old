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

from base import Base
import filters


class LegislativeTerm(Base):
  """
  A legislativeterm class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
               name=None, startDate=None, endDate=None):
    self.originalId = originalId
    self.body = body
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    self.keyword = keyword
    
    self.name = name
    self.x_startDate = start
    self.x_endDate = end
    
    super(LegislativeTerm, self).__init__()

  @property
  def startDate(self):
    """Fancy getter for the x_date_start property"""
    return self.x_startDate

  @start.setter
  def startDate(self, value):
    """
    Fancy setter for the x_start property, which
    applies a string-to-datetime filter if ecessary
    """
    if type(value) == str:
      self.x_startDate = filters.datestring_to_datetime(value)
    else:
      self.x_startDate = value

  @property
  def endDate(self):
    """Fancy getter for the x_end property"""
    return self.x_endDate

  @start.setter
  def endDate(self, value):
    """
    Fancy setter for the x_end property, which
    applies a string-to-datetime filter if ecessary
    """
    if type(value) == str:
      self.x_endDate = filters.datestring_to_datetime(value)
    else:
      self.x_endDate = value
