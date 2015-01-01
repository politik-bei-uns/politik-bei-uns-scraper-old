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
import hashlib


class File(Base):
  """
  An file class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
               name=None, fileName=None, paper=None, mimeType=None, date=None, sha1Checksum=None,
               size=None, text=None, accessUrl=None, downloadUrl=None, masterDocument=None, meeting=None,
               masterFile=None, derivativeFile=None, fileRole=None, content=None, originalDownloadPossible = True):
    self.body = body
    self.originalId = originalId
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    self.keyword = keyword
    
    self.name = name
    self.fileName = fileName
    self.paper = paper #list generated(?)
    self.mimeType = mimeType
    self.date = date
    self.sha1Checksum = sha1Checksum
    self.size = size
    self.text = text
    self.accessUrl = accessUrl
    self.downloadUrl = downloadUrl
    self.meeting = meeting #list generated
    self.masterFile = masterFile
    self.derivativeFile = derivativeFile #list generated
    self.fileRole = fileRole
    
    # Non OParl
    self.x_content = content
    self.originalDownloadPossible = originalDownloadPossible
    
    super(File, self).__init__()

  @property
  def content(self):
    return self.x_content

  @content.setter
  def content(self, value):
    self.x_content = value
    if value is None:
      self.size = None
      self.sha1Checksum = None
    else:
      self.size = len(value)
      self.sha1Checksum = hashlib.sha1(value).hexdigest()
