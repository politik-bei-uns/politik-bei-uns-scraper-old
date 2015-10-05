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
import hashlib


class File(Base):
  """
  An file class
  """
  def __init__(self, originalId=None, body=None, originalUrl=None, created=None, modified=None, keyword=None,
               name=None, fileName=None, paper=None, mimeType=None, date=None, sha1Checksum=None,
               size=None, text=None, accessUrl=None, downloadUrl=None, masterDocument=None, meeting=None,
               masterFile=None, derivativeFile=None, license=None, fileRole=None, content=None, originalDownloadPossible = True):
    self.body = body
    self.originalId = originalId
    self.originalUrl = originalUrl
    self.created = created
    self.modified = modified
    self.keyword = keyword
    
    self.fileName = fileName
    self.name = name
    self.mimeType = mimeType
    self.date = date
    self.size = size
    self.sha1Checksum = sha1Checksum
    self.text = text
    self.accessUrl = accessUrl
    self.downloadUrl = downloadUrl
    self.paper = paper #list generated(?)
    self.meeting = meeting #list generated
    self.masterFile = masterFile
    self.derivativeFile = derivativeFile #list generated
    self.license = license
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
