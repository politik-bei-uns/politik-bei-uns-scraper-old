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


class Body(Base):
  """
  A body class
  """
  def __init__(self, identifier=None, rgs=None, name=None, modified=None):
    self.identifier = identifier
    self.numericId = numericId
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    
    self.system = system
    self.contactEmail = contactEmail
    self.contactName = contactName
    self.rgs = rgs
    self.equivalentBody = equivalentBody
    self.name = name
    self.nameLong = nameLong
    self.website = website
    self.license = license
    self.licenseValidSinceDay = licenseValidSinceDay
    #organization
    #meeting
    #paper
    #member
    self.classification = classification
    super(Body, self).__init__()
