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


class Paper(Base):
  """
  A paper class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
               name=None, nameShort=None, reference=None, publishedDate=None, paperType=None, relatedPaper=None,
               mainFile=None, auxiliaryFile=None, location=None, originator=None, consultation=None, underDirectionOf=None,
               superordinatedPaper=None, subordinatedPaper=None):
    self.body = body
    self.originalId = originalId
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    self.keyword = keyword
    
    self.name = name
    self.nameShort = nameShort
    self.reference = reference
    self.x_publishedDate = publishedDate
    self.paperType = paperType
    self.relatedPaper = relatedPaper #list of paper
    self.mainFile = mainFile
    self.auxiliaryFile = auxiliaryFile #list of file
    self.location = location #list
    self.originator = originator #list of person or organization
    self.consultation = consultation #list of consultation
    self.underDirectionOf = underDirectionOf #list of organization
    
    # Non OParl
    self.superordinatedPaper = superordinatedPaper
    self.subordinatedPaper = subordinatedPaper
    
    super(Paper, self).__init__()

  @property
  def publishedDate(self):
    """Fancy getter for the date property"""
    return self.x_publishedDate

  @publishedDate.setter
  def publishedDate(self, value):
    """
    Fancy setter for the x_date property, which
    applies a string-to-datetime filter if necessary
    """
    if type(value) == str:
      self.x_publishedDate = filters.datestring_to_datetime(value)
    else:
      self.x_publishedDate = value

