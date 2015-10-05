# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from base import Base
import filters


class LegislativeTerm(Base):
  """
  A legislativeterm class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
               name=None, startDate=None, endDate=None):
    self.body = body
    self.originalId = originalId
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
