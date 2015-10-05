# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Marian Steinbach, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from base import Base
import filters


class Meeting(Base):
  """
  A meeting class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
               name=None, shortName=None, start=None, end=None, room=None, streetAdress=None, postalCode=None, locality=None, type=None, location=None,
               organization=None, chairPerson=None, scribe=None, participant=None, invited=None, attendant=None,
               invitation=None, resultsProtocol=None, verbatimProtocol=None, auxiliaryFile=None, agendaItem=None, nameShort=None):
    self.originalId = originalId
    self.body = body
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    self.keyword = keyword
    
    self.name = name
    self.x_start = start
    self.x_end = end
    self.room = room
    self.streetAddress = streetAdress
    self.postalCode = postalCode
    self.locality = locality
    self.type = type # non-oparl
    self.location = location # ref
    self.organization = organization # list of organization
    self.chairPerson = chairPerson
    self.participant = participant # ref list depreciated(?)
    self.invitation = invitation #list of file
    self.scribe = scribe
    self.invited = invited #list
    self.attendant = attendant #list
    
    self.resultsProtocol = resultsProtocol #file
    self.verbatimProtocol = verbatimProtocol #file
    self.auxiliaryFile = auxiliaryFile #list of file
    self.agendaItem = agendaItem #list of agendaitem
    
    super(Meeting, self).__init__()

  @property
  def start(self):
    """Fancy getter for the x_date_start property"""
    return self.x_start

  @start.setter
  def start(self, value):
    """
    Fancy setter for the x_start property, which
    applies a string-to-datetime filter if ecessary
    """
    if type(value) == str:
      self.x_start = filters.datestring_to_datetime(value)
    else:
      self.x_start = value

  @property
  def end(self):
    """Fancy getter for the x_end property"""
    return self.x_end

  @start.setter
  def end(self, value):
    """
    Fancy setter for the x_end property, which
    applies a string-to-datetime filter if ecessary
    """
    if type(value) == str:
      self.x_end = filters.datestring_to_datetime(value)
    else:
      self.x_end = value
