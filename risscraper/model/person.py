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


class Person(Base):
  """
  A person class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
      name=None, familyName=None, givenName=None, title=None, formOfAddress=None, gender=None,
      email=None, phone=None, streetAddress=None, postalCode=None, locality=None, status=None, membership=None,
      fax=None, mobile=None, website=None):
    self.originalId = originalId
    self.body = body
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    self.keyword = keyword
    
    self.name = name
    self.familyName = familyName
    self.givenName = givenName
    self.title = title #list
    self.formOfAddress = formOfAddress
    self.gender = gender
    self.email = email
    self.phone = phone
    self.streetAddress = streetAddress
    self.postalCode = postalCode
    self.locality = locality
    self.status = status
    self.membership = membership #list
    
    # non OParl
    self.fax = fax
    self.mobile = mobile
    self.website = website
    super(Person, self).__init__()
