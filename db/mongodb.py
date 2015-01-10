# encoding: utf-8

"""
Copyright (c) 2012 Marian Steinbach, Ernesto Ruge

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

from pymongo import MongoClient
from pymongo import ASCENDING
from pymongo import DESCENDING
from bson.dbref import DBRef
import gridfs
import sys
from hashlib import md5
import logging
import re
import translitcodec
import pytz
import datetime
from bson.objectid import ObjectId
from copy import deepcopy
from uuid import uuid4
import types


class MongoDatabase(object):
  """
  Database handler for a MongoDB backend
  """

  def __init__(self, base_config):
    client = MongoClient(base_config.DB_HOST, base_config.DB_PORT)
    self.db = client[base_config.DB_NAME]
    self.base_config = base_config
    self.fs = gridfs.GridFS(self.db)
    self.slugify_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

  def setup(self, config):
    """
    Initialize database, if not yet done. Shouln't destroy anything.
    """
    # body
    self.config = config
    self.db.body.ensure_index([('rgs', ASCENDING)], unique=True)
    self.body_uid = config['city']['_id']
    
    """
    self.db.committee.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.person.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.organisation.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # meeting = session
    self.db.meeting.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.meeting.ensure_index([('numeric_id', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.meeting.ensure_index([('slug', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # agendaitem
    self.db.agendaitem.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.agendaitem.ensure_index([('numeric_id', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.agendaitem.ensure_index([('slug', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # paper = submission
    self.db.paper.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.paper.ensure_index([('numeric_id', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.paper.ensure_index([('slug', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # document = attachment
    self.db.document.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.document.ensure_index([('slug', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # committee
    self.db.committee.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    # we don't have ids there, so its not unique
    self.db.committee.ensure_index([('numeric_id', ASCENDING), ('body', ASCENDING)], unique=False)
    self.db.committee.ensure_index([('slug', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # person
    self.db.person.ensure_index([('identifier', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.person.ensure_index([('numeric_id', ASCENDING), ('body', ASCENDING)], unique=True)
    self.db.person.ensure_index([('slug', ASCENDING), ('body', ASCENDING)], unique=True)
    
    # location 
    #self.db.document.ensure_index([('identifier', ASCENDING), ('rs', ASCENDING)], unique=True)
    
    #self.db.sessions.ensure_index([('numeric_id', ASCENDING), ('rs', ASCENDING)], unique=True)
    #self.db.sessions.ensure_index([('url', ASCENDING), ('rs', ASCENDING)], unique=True)
    #self.db.submissions.ensure_index([('numeric_id', ASCENDING), ('rs', ASCENDING)], unique=True)
    #self.db.submissions.ensure_index([('url', ASCENDING), ('rs', ASCENDING)], unique=True)
    #self.db.submissions.ensure_index([('identifier', ASCENDING), ('rs', ASCENDING)], unique=True)
    #self.db.attachments.ensure_index([('identifier', ASCENDING), ('rs', ASCENDING)], unique=True)
    self.db.fs.files.ensure_index(
      [
        ('body', ASCENDING),
        ('filename', ASCENDING),
        ('uploadDate', DESCENDING),
      ],
      unique=True)
    """
  def erase(self):
    """
    Delete all data from database.
    """
    self.db.queue.remove({})
    self.db.agendaitem.remove({})
    self.db.consultation.remove({})
    self.db.file.remove({})
    self.db.legislativeterm.remove({})
    self.db.location.remove({})
    self.db.meeting.remove({})
    self.db.membership.remove({})
    self.db.organization.remove({})
    self.db.paper.remove({})
    self.db.person.remove({})
    self.db.fs.files.remove({})
    self.db.fs.chunks.remove({})

  def get_config(self, body_uid):
    """
    Returns Config JSON
    """
    config = self.db.config.find_one()
    if '_id' in config:
      del config['_id']
    local_config = self.db.body.find_one({'_id': ObjectId(body_uid)})
    if 'config' in local_config:
      config = self.merge_dict(config, local_config['config'])
      del local_config['config']
    config['city'] = local_config
    return config

  def dict_merge(self, a, b):
    if not isinstance(b, dict):
      return b
    result = deepcopy(a)
    for k, v in b.iteritems():
      if k in result and isinstance(result[k], dict):
        result[k] = self.dict_merge(result[k], v)
      else:
        result[k] = deepcopy(v)
    return result

  def save_result_string(self, result_string):
    random_uid = uuid4()
    self.db.body.config.scraper.result_strings.insert({'from': result_string, 'to': random_uid})
    return random_uid

  def get_object(self, collection, key, value):
    """
    Return a document
    """
    result = self.db[collection].find_one({key: value,'body': DBRef('body', id=self.body_uid)})
    return result

  def get_object_id(self, collection, key, value):
    """
    Return the ObjectID of a document in the given collection identified
    by the given key:value pair
    """
    result = self.get_object(collection, key, value)
    if result is not None:
      if '_id' in result:
        return result['_id']

  def meeting_exists(self, id):
    if self.get_object_id('meeting', 'externalId', id) is not None:
      return True
    return False

  def agendaitem_exists(self, id):
    if self.get_object_id('agendaitem', 'externalId', id) is not None:
      return True
    return False
  
  def document_exists(self, id):
    if self.get_object_id('document', 'externalId', id) is not None:
      return True
    return False

  def paper_exists(self, id):
    if self.get_object_id('paper', 'externalId', id) is not None:
      return True
    return False
  
  def dereference_object(self, data_dict, attribute, datatype=False):
    if attribute in data_dict:
      # replace object datasets with DBRef dicts
      if datatype:
        save_funct = getattr(self, 'save_' + datatype)
      else:
        save_funct = getattr(self, 'save_' + attribute)
        datatype = attribute
      if isinstance(data_dict[attribute], list):
        for n in range(len(data_dict[attribute])):
          oid = save_funct(data_dict[attribute][n])
          data_dict[attribute][n] = DBRef(collection=datatype, id=oid)
      else:
        oid = save_funct(data_dict[attribute])
        data_dict[attribute] = DBRef(collection=datatype, id=oid)
    return data_dict
  
  
  def save_object(self, data_dict, data_stored, object_type):
    # new object
    if data_stored is None:
      # insert new document
      datatable = getattr(self.db, object_type)
      oid = datatable.insert(data_dict)
      logging.info("%s %s inserted as new", object_type, oid)
      return oid
    # update object
    else:
      berlin = pytz.timezone('Europe/Berlin')
      # compare old and new dict and then send update
      logging.info("%s %s updated with _id %s", object_type, data_dict['originalId'], data_stored['_id'])
      set_attributes = {}
      for key in data_dict.keys():
        if key in ['modified', 'created']:
          continue
        if key not in data_stored:
          logging.debug("Key '%s' will be added to %s", key, object_type)
          set_attributes[key] = data_dict[key]
        else:
          # add utc info to datetime objects
          if isinstance(data_stored[key], datetime.datetime):
            data_stored[key] = pytz.utc.localize(data_stored[key])
          if data_stored[key] != data_dict[key]:
            logging.debug("Key '%s' in %s has changed", key, object_type)
            set_attributes[key] = data_dict[key]
      if set_attributes != {}:
        set_attributes['modified'] = data_dict['modified']
        datatable = getattr(self.db, object_type)
        datatable.update({'_id': data_stored['_id']}, {'$set': set_attributes})
      return data_stored['_id']
  
  def ensure_index(self, ):
    pass

  def create_slug(self, data_dict, object_type):
    current_slug = self.slugify(data_dict['originalId'])
    slug_counter = 0
    while (True):
      dataset = self.get_object(object_type, 'slug', current_slug)
      if dataset:
        if data_dict['originalId'] != dataset['originalId']:
          slug_counter += 1
          current_slug = self.slugify(data_dict['originalId']) + '-' + str(slug_counter)
        else:
          return current_slug
      else:
        return current_slug

  def save_person(self, person):
    person_stored = self.get_object('person', 'originalId', person.originalId)
    
    person_dict = person.dict()
    
    # setting body
    person_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    # ensure that there is an originalId
    if 'originalId' not in person_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", person_dict.originalUrl)
    
    # dereference objects
    person_dict = self.dereference_object(person_dict, 'membership')
    
    # save data
    return self.save_object(person_dict, person_stored, 'person')

  def save_membership(self, membership):
    membership_stored = self.get_object('membership', 'originalId', membership.originalId)
    
    membership_dict = membership.dict()
    
    # setting body
    membership_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    # ensure that there is an originalId
    if 'originalId' not in membership_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", membership_dict.originalUrl)
    
    # dereference objects
    membership_dict = self.dereference_object(membership_dict, 'organization')
    
    # save data
    return self.save_object(membership_dict, membership_stored, 'membership')

  def save_organization(self, organization):
    organization_stored = self.get_object('organization', 'originalId', organization.originalId)
    organization_dict = organization.dict()
    
    # setting body
    organization_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    # ensure that there is an originalId
    if 'originalId' not in organization_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", organization_dict.originalUrl)
    
    # create slug
    organization_dict['slug'] = self.create_slug(organization_dict, 'committee')
    
    # save data
    return self.save_object(organization_dict, organization_stored, 'organization')
  
  def save_meeting(self, meeting):
    """
    Write meeting object to database. This means dereferencing all associated objects as DBrefs
    """
    meeting_stored = self.get_object('meeting', 'originalId', meeting.originalId)
    meeting_dict = meeting.dict()

    # setting body
    meeting_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    # ensure that there is an originalId
    if 'originalId' not in meeting_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", meeting_dict.originalUrl)
    
    # dereference items
    meeting_dict = self.dereference_object(meeting_dict, 'organization')
    meeting_dict = self.dereference_object(meeting_dict, 'agendaItem')
    meeting_dict = self.dereference_object(meeting_dict, 'invitation', 'file')
    meeting_dict = self.dereference_object(meeting_dict, 'resultsProtocol', 'file')
    meeting_dict = self.dereference_object(meeting_dict, 'verbatimProtocol', 'file')
    meeting_dict = self.dereference_object(meeting_dict, 'auxiliaryFile', 'file')
    
    # save data
    return self.save_object(meeting_dict, meeting_stored, 'meeting')

  
  def save_agendaItem(self, agendaitem):
    """
    Write agendaitem object to database. This means dereferencing all associated objects as DBrefs
    """
    agendaitem_stored = self.get_object('agendaitem', 'originalId', agendaitem.originalId)
    agendaitem_dict = agendaitem.dict()

    # setting body
    agendaitem_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    if 'originalId' not in agendaitem_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", agendaitem_dict.originalUrl)
    
    # dereference items
    agendaitem_dict = self.dereference_object(agendaitem_dict, 'consultation')

    return self.save_object(agendaitem_dict, agendaitem_stored, 'agendaitem')
  
  def save_consultation(self, consultation):
    """
    Write consultation object to database. This means dereferencing all associated objects as DBrefs
    """
    consultation_stored = self.get_object('consultation', 'originalId', consultation.originalId)
    consultation_dict = consultation.dict()

    # setting body
    consultation_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    
    if 'originalId' not in consultation_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", consultation_dict.originalUrl)
    
    # dereference items
    consultation_dict = self.dereference_object(consultation_dict, 'paper')

    return self.save_object(consultation_dict, consultation_stored, 'consultation')

  def save_paper(self, paper):
    """Write paper to DB and return ObjectID"""
    paper_stored = self.get_object('paper', 'originalId', paper.originalId)
    paper_dict = paper.dict()

    paper_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    if 'originalId' not in paper_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", paper_dict.originalUrl)
    
    # dereference items
    paper_dict = self.dereference_object(paper_dict, 'relatedPaper', 'paper')
    paper_dict = self.dereference_object(paper_dict, 'mainFile', 'file')
    paper_dict = self.dereference_object(paper_dict, 'auxiliaryFile', 'file')
    paper_dict = self.dereference_object(paper_dict, 'originator', 'organization')
    paper_dict = self.dereference_object(paper_dict, 'underDirectionOf', 'organization')
    paper_dict = self.dereference_object(paper_dict, 'superordinatedPaper', 'paper')
    paper_dict = self.dereference_object(paper_dict, 'subordinatedPaper', 'paper')
    
    return self.save_object(paper_dict, paper_stored, 'paper')
  
  
  def save_file(self, file):
    """
    Write file to DB and return ObjectID.
    - If the file already exists, the existing file
      is updated in the database.
    - If the file.content has changed, a new GridFS file version
      is added.
    - If file is depublished, no new file is stored.
    """
    file_stored = self.get_object('file', 'originalId', file.originalId)
    file_dict = file.dict()
    
    file_dict['body'] = DBRef(collection='body',id=self.body_uid)
    
    if 'originalId' not in file_dict:
      logging.critical("Fatal error: no originalId avaiable at url %s", paper_dict.originalUrl)

    file_dict = self.dereference_object(file_dict, 'masterFile', 'file')
    
    
    file_changed = False
    if file_stored is not None:
      # file exists in database and must be compared field by field
      logging.info("file %s is already in db with _id=%s", file.originalId, str(file_stored['_id']))
      # check if file is referenced
      file_data_stored = None
      if 'file' in file_stored:
        # assuming DBRef in file.file
        assert type(file_stored['file']) == DBRef
        file_data_stored = self.db.fs.files.find_one({'_id': file_stored['file'].id})
      if file_data_stored is not None and file.content:
        # compare stored and submitted file
        if file_data_stored['length'] != len(file.content):
          file_changed = True
        elif file_data_stored['md5'] != md5(file.content).hexdigest():
          file_changed = True
      if file_data_stored is None and file.content:
        file_changed = True
    # Create new file version (if necessary)
    if ((file_changed and 'depublication' not in file_stored) or (file_stored is None)) and file.content:
      file_oid = self.fs.put(file.content,
        filename=file.filename,
        body=DBRef('body', self.body_uid))
      logging.info("New file version stored with _id=%s", str(file_oid))
      file_dict['file'] = DBRef(collection='fs.files', id=file_oid)

    # erase file content (since stored elsewhere above)
    if 'content' in file_dict:
      del file_dict['content']
    
    oid = None
    if file_stored is None:
      # insert new
      oid = self.db.file.insert(file_dict)
      logging.info("File %s inserted with _id %s", file.originalId, str(oid))
    else:
      # Only do partial update
      oid = file_stored['_id']
      set_attributes = {}
      for key in file_dict.keys():
        if key in ['modified', 'created']:
          continue
        if key not in file_stored:
          set_attributes[key] = file_dict[key]
        else:
          # add utc info to datetime objects
          if isinstance(file_stored[key], datetime.datetime):
            file_stored[key] = pytz.utc.localize(file_stored[key])
          if file_stored[key] != file_dict[key]:
            logging.debug("Key '%s' will be updated", key)
            set_attributes[key] = file_dict[key]
      if 'file' not in file_dict and 'file' in file_stored:
          set_attributes['file'] = file_stored['file']
      if file_changed or set_attributes != {}:
        set_attributes['modified'] = file_dict['modified']

        self.db.file.update({'_id': oid}, {'$set': set_attributes})
    return oid

  def slugify(self, identifier):
    identifier = unicode(identifier)
    identifier = identifier.replace('/', '-')
    identifier = identifier.replace(' ', '-')
    result = []
    for word in self.slugify_re.split(identifier.lower()):
      word = word.encode('translit/long')
      if word:
        result.append(word)
    return unicode('-'.join(result))
  
  def queue_status(self):
    """
    Prints out information on the queue
    """
    aggregate = self.db.queue.aggregate([
      {
        "$group": {
          "_id": {
            "rs": "$rs",
            "status": "$status",
            "qname": "$qname"
          },
          "count": {"$sum": 1}
        }
      },
      {
        "$sort": {"_id.rs": 1}
      }])
    rs = None
    for entry in aggregate['result']:
      logging.info("Queue %s, status %s: %d jobs", entry['_id']['qname'], entry['_id']['status'], entry['count'])

  def merge_dict(self, x, y):
    merged = dict(x,**y)
    xkeys = x.keys()
    for key in xkeys:
      if type(x[key]) is types.DictType and y.has_key(key):
        merged[key] = self.merge_dict(x[key],y[key])
    return merged
