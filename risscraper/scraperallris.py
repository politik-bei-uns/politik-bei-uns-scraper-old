# encoding: utf-8

"""
Copyright (c) 2012 Marian Steinbach, Ernesto Ruge, Christian Scholz

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

import mechanize
import urllib2
import parse
import datetime
import time
import queue
import sys
from lxml import etree, html
from lxml.cssselect import CSSSelector
from StringIO import StringIO
import hashlib
import magic
import os
import logging
import requests
import pytz
import re
from pytz import timezone


from model.agendaitem import AgendaItem
from model.body import Body
from model.committee import Committee
from model.document import Document
from model.meeting import Meeting
from model.paper import Paper
from model.person import Person

class ScraperAllRis(object):
  
  body_re = re.compile("<?xml .*<body[ ]*>(.*)</body>") # find everything inside a body of a subdocument
  TIME_MARKER = datetime.datetime(1903,1,1) # marker for no date being found
  
  #adoption_css = CSSSelector("#rismain table.risdeco tbody tr td table.tk1 tbody tr td table.tk1 tbody tr td table tbody tr.zl12 td.text3")
  #adoption_css = CSSSelector("table.risdeco tr td table.tk1 tr td.ko1 table.tk1 tr td table tr.zl12 td.text3")
  adoption_css = CSSSelector("tr.zl12:nth-child(3) > td:nth-child(5)") # selects the td which holds status information such as "beschlossen"
  top_css = CSSSelector("tr.zl12:nth-child(3) > td:nth-child(7) > form:nth-child(1) > input:nth-child(1)") # selects the td which holds the link to the TOP with transcript
  table_css = CSSSelector(".ko1 > table:nth-child(1)") # table with info block
  attachment_1_css = CSSSelector('input[name=DOLFDNR]')
  attachments_css = CSSSelector('table.risdeco table.tk1 table.tk1 table.tk1')
  #main_css = CSSSelector("#rismain table.risdeco")


  def __init__(self, config, db, options):
    # configuration
    self.config = config
    # command line options and defaults
    self.options = options
    # database object
    self.db = db
    # mechanize user agent
    self.user_agent = mechanize.Browser()
    self.user_agent.set_handle_robots(False)
    self.user_agent.addheaders = [('User-agent', config.USER_AGENT_NAME)]
    # Queues
    if self.options.workfromqueue:
      self.person_queue = queue.Queue('ALLRIS_PERSON', config, db)
      self.meeting_queue = queue.Queue('ALLRIS_MEETING', config, db)
      self.paper_queue = queue.Queue('ALLRIS_PAPER', config, db)
    # system info (PHP/ASP)
    self.template_system = None
    self.urls = None
    self.xpath = None
    
    self.user_agent = mechanize.Browser()
    self.user_agent.set_handle_robots(False)
    self.user_agent.addheaders = [('User-agent', config.USER_AGENT_NAME)]

  def work_from_queue(self):
    """
    Empty queues if they have values. Queues are emptied in the
    following order:
    1. Person
    2. Meeting
    3. Paper
    """
    while self.person_queue.has_next():
      job = self.person_queue.get()
      self.get_person(person_id=job['key'])
      self.get_person_committee(person_id=job['key'])
      self.person_queue.resolve_job(job)
    while self.meeting_queue.has_next():
      job = self.meeting_queue.get()
      self.get_meeting(meeting_id=job['key'])
      self.meeting_queue.resolve_job(job)
    while self.paper_queue.has_next():
      job = self.paper_queue.get()
      self.get_paper(paper_id=job['key'])
      self.paper_queue.resolve_job(job)
    # when everything is done, we remove DONE jobs
    self.meeting_queue.garbage_collect()
    self.paper_queue.garbage_collect()

  def guess_system(self):
    """
    Tries to find out which AllRis version we are working with
    and adapts configuration
    TODO: XML Guess
    """
    self.template_system = 'xml'
    logging.info("Nothing to guess until now.")

  def find_person(self):
    find_person_url = self.config.BASE_URL + 'kp041.asp?template=xyz&selfaction=ws&showAll=true&PALFDNRM=1&kpdatfil=&filtdatum=filter&kpname=&kpsonst=&kpampa=99999999&kpfr=99999999&kpamfr=99999999&kpau=99999999&kpamau=99999999&searchForm=true&search=Suchen'
    
    """parse an XML file and return the tree"""
    parser = etree.XMLParser(recover=True)
    r = self.get_url(find_person_url)
    if not r:
      return
    xml = r.text.encode('ascii','xmlcharrefreplace') 
    tree = etree.fromstring(xml, parser=parser)
  
    # element 0 is the special block
    # element 1 is the list of persons
    for node in tree[1].iterchildren():
      elem = {}
      for e in node.iterchildren():
        elem[e.tag] = e.text
      
      # now retrieve person details such as committee memberships etc.
      # we also get the age (but only that, no date of birth)
      person = Person(numeric_id=int(elem['kplfdnr']), identifier=elem['kplfdnr'])
      if elem['link_kp']:
        person.original_url = elem['link_kp']
      # personal information
      
      if elem['adtit']:
        person.title = elem['adtit']
      if elem['antext1'] == 'Frau':
        person.sex = 1
      elif elem['antext1'] == 'Herr':
        person.sex = 2
      if elem['advname']:
        person.firstname = elem['advname']
      if elem['adname']:
        person.lastname = elem['adname']
      
      # address
      if elem['adstr']:
        person.address = elem['adstr']
      if elem['adhnr']:
        person.house_number = elem['adhnr']
      if elem['adplz']:
        person.postalcode = elem['adplz']
      if elem['adtel']:
        person.phone = elem['adtel']
      
      # contact
      if elem['adtel']:
        person.phone = elem['adtel']
      if elem['adtel2']:
        person.mobile = elem['adtel2']
      if elem['adfax']:
        person.fax = elem['adfax']
      if elem['adfax']:
        person.fax = elem['adfax']
      if elem['ademail']:
        person.email = elem['ademail']
      if elem['adwww1']:
        person.website = elem['adwww1']
      
      person_party = elem['kppartei']
      if person_party:
        if person_party in self.config.PARTY_ALIAS:
          person_party = self.config.PARTY_ALIAS[person_party]
        person.committee = [{'committee': Committee(identifier=person_party, title=person_party, type='party')}]
      
      if elem['link_kp'] is not None:
        if hasattr(self, 'person_queue'):
          self.person_queue.add(person.numeric_id)
      else:
        logging.info("Person %s %s has no link", person.firstname, person.lastname)
      oid = self.db.save_person(person)
        
  
  def find_meeting(self, start_date=None, end_date=None):
    """
    Find meetings within a given time frame and add them to the meeting queue.
    """
    meeting_url = "%ssi010.asp?selfaction=ws&template=xyz&kaldatvon=%s&kaldatbis=%s" % (self.config.BASE_URL, start_date.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y"))
    logging.info("Getting meeting overview from %s", meeting_url)
    
    
    parser = etree.XMLParser(recover=True)
    
    r = self.get_url(meeting_url)
    if not r:
      return
    
    xml = r.text.encode('ascii','xmlcharrefreplace') 
    root = etree.fromstring(xml, parser=parser)

    for item in root[1].iterchildren():
      raw_meeting = {}
      for e in item.iterchildren():
        raw_meeting[e.tag] = e.text
      meeting = Meeting(numeric_id=int(raw_meeting['silfdnr']), identifier=int(raw_meeting['silfdnr']))
      meeting.date_start = self.parse_date(raw_meeting['sisbvcs'])
      meeting.date_end = self.parse_date(raw_meeting['sisevcs'])
      meeting.identifier = raw_meeting['siname']
      meeting.original_url = "%sto010.asp?SILFDNR=%s&options=4" % (self.config.BASE_URL, raw_meeting['silfdnr'])
      meeting.title = raw_meeting['sitext']
      meeting.committee_name = raw_meeting['grname']
      meeting.description = raw_meeting['sitext']
      oid = self.db.save_meeting(meeting)
      self.meeting_queue.add(meeting.numeric_id)
      

  def get_committee(self, committee_id=None, committee_url=None):
    pass
  
  def get_person(self, person_id=None, person_url=None):
    # we dont need this(?)
    pass
  
  def get_person_committee(self, person_id=None, committee_url=None):
    url = "%skp020.asp?KPLFDNR=%s&history=true" % (self.config.BASE_URL, person_id)
    response = self.get_url(url)
    if not url:
      return
    tree = html.fromstring(response.text)
      
    committees = []
    person = Person(numeric_id=person_id)
    # maps name of type to form name and membership type
    type_map = {
      u'Rat der Stadt' : {'mtype' : 'parliament', 'field' : 'PALFDNR'},
      u'Fraktion' : {'mtype' : 'organisation', 'field' : 'FRLFDNR'},
      u'Ausschüsse' : {'mtype' : 'committee', 'field' : 'AULFDNR'},
      'Stadtbezirk': {'mtype' : 'parliament', 'field' : 'PALFDNR'},
      'BVV': {'mtype' : 'parliament', 'field' : 'PALFDNR'}
    }

    # obtain the table with the membership list via a simple state machine
    mtype = "parliament"
    field = 'PALFDNR'
    old_group_id = None         # for checking if it changes
    old_group_name = None       # for checking if it changes
    group_id = None             # might break otherwise
    table = tree.xpath('//*[@id="rismain_raw"]/table[2]')[0]
    for line in table.findall("tr"):
      if line[0].tag == "th":
        what = line[0].text.strip()
        if what not in type_map:
          logging.error("Unknown committee type %s at person detail page %s", what, person_id)
          continue
        mtype = type_map[what]['mtype']
        field = type_map[what]['field']
      else:
        if "Keine Information" in line.text_content():
          # skip because no content is available
          continue
        
        membership = {}
        
        # first get the name of group
        group_name = line[1].text_content()
        committee = Committee(identifier=group_name)
        committee.type = mtype

        # now the first col might be a form with more useful information which will carry through until we find another one
        # with it. we still check the name though
        form = line[0].find("form")
        if form is not None:
          group_id = int(form.find("input[@name='%s']" % field).get("value"))
          committee.numeric_id = group_id
          old_group_id = group_id # remember it for next loop
          old_group_name = group_name # remember it for next loop
          
        else:
          # we did not find a form. We assume that the old group still applies but we nevertheless check if the groupname is still the same
          if old_group_name != group_name:
            logging.debug("Group name differs but we didn't get a form with new group id: group name=%s, old group name=%s, group_id=%s at url %s", group_name, old_group_name, old_group_id, url)
        
        # TODO: create a list of functions so we can index them somehow
        function = line[2].text_content()
        raw_date = line[3].text_content()
        
        # parse the date information
        if "seit" in raw_date:
          dparts = raw_date.split()
          membership['end'] = dparts[-1]
        elif "Keine" in raw_date:
          # no date information available
          start_date = end_date = None
        else:
          dparts = raw_date.split()
          membership['start'] = dparts[0]
          membership['end'] = dparts[-1]
        
        membership['committee'] = committee
        committees.append(membership)
        
    person.committee = committees
    oid = self.db.save_person(person)
  
  def get_person_committee_presence(self, person_id=None, person_url=None):
    # URL is like si019.asp?SILFDNR=5672
    # TODO
    pass
  

  def get_meeting(self, meeting_url=None, meeting_id=None):
    """
    Load meeting details (e.g. agendaitems) for the given detail page URL or numeric ID
    """
    meeting_url = "%sto010.asp?selfaction=ws&template=xyz&SILFDNR=%s" % (self.config.BASE_URL, meeting_id)
    
    logging.info("Getting meeting %d from %s", meeting_id, meeting_url)
    
    r = self.get_url(meeting_url)
    if not r:
      return
    # If r.history has an item we have a problem
    if len(r.history):
      if r.history[0].status_code == 302:
        logging.info("Meeting %d from %s seems to be private", meeting_id, meeting_id)
      else:
        logging.error("Strange redirect %d from %s with status code %s", meeting_id, meeting_url, r.history[0].status_code)
      return
    xml = r.text.encode('ascii','xmlcharrefreplace') 
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml, parser=parser)
    
    meeting = Meeting(numeric_id=meeting_id)

    # special area
    special = {}
    for item in root[0].iterchildren():
      special[item.tag] = item.text
    # Woher kriegen wir das Datum? Nur über die Übersicht?
    #if 'sisb' in special:
    #if 'sise' in special:
    if 'saname' in special:
      if special['saname'] in self.config.MEETING_TYPE:
        meeting.type = self.config.MEETING_TYPE[special['saname']]
      else:
        logging.warn("String '%s' not found in MEETING_TYPE", special['saname'])
    # head area
    head = {}
    for item in root[0].iterchildren():
      head[item.tag] = item.text
    if 'raname' in head:
      meeting.room = head['raname']
    if 'raort' in head:
      meeting.address = head['raort']
    agendaitems = []
    
    for item in root[2].iterchildren():
      elem = {}
      for e in item.iterchildren():
        elem[e.tag] = e.text

      section = [elem['tofnum'], elem['tofunum'], elem['tofuunum']]
      section = [x for x in section if x!="0"]
      elem['section'] = ".".join(section)
      agendaitem = Agendaitem()
      
      #agendaitem = elem['topnr']
      agendaitem.numeric_id = int(elem['tolfdnr'])
      if elem['toostLang'] == u'öffentlich':
        agendaitem.public = True
      else:
        agendaitem.public = False
      agendaitem.title = elem['totext1']
      # get agenda detail page
      # TODO: Own Queue
      time.sleep(self.config.WAIT_TIME)
      agendaitem_url = '%sto020.asp?selfaction=ws&template=xyz&TOLFDNR=%s' % (self.config.BASE_URL, agendaitem.numeric_id)
      logging.info("Getting agendaitem %d from %s", agendaitem.numeric_id, agendaitem_url)
      
      agendaitem_r = self.get_url(agendaitem_url)
      if not agendaitem_r:
        return
      
      if len(agendaitem_r.history):
        logging.info("Agenda item %d from %s seems to be private", meeting_id, meeting_url)
      else:
        agendaitem_xml = agendaitem_r.text.encode('ascii','xmlcharrefreplace') 
        agendaitem_parser = etree.XMLParser(recover=True)
        agendaitem_root = etree.fromstring(agendaitem_xml, parser=parser)
        add_agenda_item = {}
        for add_item in agendaitem_root[0].iterchildren():
          if add_item.tag == "rtfWP" and len(add_item) > 0:
            try:
              agendaitem.resolution_text = etree.tostring(add_item[0][1][0])
            except:
              logging.warn("Unable to parse resolution text at %s", agendaitem_url)
          else:
            add_agenda_item[add_item.tag] = add_item.text
        if 'voname' in add_agenda_item:
          # create paper with identifier
          agendaitem.paper = [Paper(numeric_id = int(elem['volfdnr']), title=add_agenda_item['voname'])]
          if add_agenda_item['vobetr'] != agendaitem.title:
            logging.warn("different values for title: %s and %s", agendaitem.title, add_agenda_item['vobetr'])
          if hasattr(self, 'paper_queue'):
            self.paper_queue.add(int(elem['volfdnr']))
        elif int(elem['volfdnr']) is not 0:
          # create paper without identifier
          agendaitem.paper = [Paper(numeric_id = int(elem['volfdnr']))]
          if hasattr(self, 'paper_queue'):
            self.paper_queue.add(int(elem['volfdnr']))
        if "nowDate" not in add_agenda_item:
          # something is broken with this so we don't store it
          logging.warn("Skipping broken agenda at ", agendaitem_url)
        else:
          # dereference result
          if add_agenda_item['totyp'] in self.config.RESULT_STRINGS:
            agendaitem.result = self.config.RESULT_STRINGS[add_agenda_item['totyp']]
          else:
            logging.warn("String '%s' not found in configured RESULT_STRINGS", add_agenda_item['totyp'])
        agendaitems.append(agendaitem)
    meeting.agendaitem = agendaitems
    
    oid = self.db.save_meeting(meeting)
    logging.info("Meeting %d stored with _id %s", meeting_id, oid)
    

  def get_paper(self, paper_url=None, paper_id=None):
    """
    Load paper details for the paper given by detail page URL
    or numeric ID
    """
    paper_url = '%svo020.asp?VOLFDNR=%s' % (self.config.BASE_URL, paper_id)
    logging.info("Getting paper %d from %s", paper_id, paper_url)

    # stupid re-try concept because AllRis sometimes misses start < at tags at first request
    try_counter = 0
    while True:
      try:
        response = self.get_url(paper_url)
        if not response:
          return
        if "noauth" in response.url:
          logging.warn("Paper %s in %s seems to private" % (paper_id, paper_url))
          return
        text = self.preprocess_text(response.text)
        doc = html.fromstring(text)
        data = {}
        
        # Beratungsfolge-Table checken
        table = self.table_css(doc)[0] # lets hope we always have this table
        self.consultation_list_start = False
        last_headline = ''
        for line in table:
          if line.tag == 'tr':
            headline = line[0].text
          elif line.tag == 'td':
            headline = line.text
          else:
            logging.error("ERROR: Serious error in data table. Unable to parse.")
          if headline:
            headline = headline.split(":")[0].lower()
            if headline[-1]==":":
              headline = headline[:-1]
            if headline == "betreff":
              value = line[1].text_content().strip()
              value = value.split("-->")[1]         # there is some html comment with a script tag in front of the text which we remove
              data[headline] = " ".join(value.split())  # remove all multiple spaces from the string
            elif headline in ['verfasser', u'federführend', 'drucksache-art']:
              data[headline] = line[1].text.strip()
            elif headline in ['status']:
              data[headline] = line[1].text.strip()
              # related papers
              if len(line) > 2:
                if len(line[3]):
                  # gets identifier. is there something else at this position? (will break)
                  data['paper'] = [{'paper': Paper(numeric_id=line[3][0][0][1][0].get('href').split('=')[1].split('&')[0] , identifier=line[3][0][0][1][0].text)}]
                  
            elif headline == "beratungsfolge":
              # the actual list will be in the next row inside a table, so we only set a marker
              data = self.parse_consultation_list_headline(line, data) # for parser which have the consultation list here
            elif self.consultation_list_start:
              data = self.parse_consultation_list(line, data) # for parser which have the consultation list in the next tr
              self.consultation_list_start = False # set the marker to False again as we have read it
          last_headline = headline
          # we simply ignore the rest (there might not be much more actually)
        # the actual text comes after the table in a div but it's not valid XML or HTML this using regex
        data['docs'] = self.body_re.findall(response.text)
        first_date = False
        for single_consultation in data['consultation']:
          if first_date:
            if single_consultation['date'] < first_date:
              first_date = single_consultation['date']
          else:
            first_date = single_consultation['date']
        
        paper = Paper(numeric_id = paper_id)
        paper.original_url = paper_url
        paper.title = data['betreff']
        paper.description = data['docs']
        paper.type = data['drucksache-art']
        if first_date:
          paper.date = first_date.strftime("%Y-%m-%d")
        if 'identifier' in data:
          paper.identifier = data['identifier']
        
        paper.document = []
        # get the attachments step 1 (Drucksache)
        document_1 = self.attachment_1_css(doc)
        if len(document_1):
          if document_1[0].value:
            href = '%sdo027.asp' % self.config.BASE_URL
            identifier = document_1[0].value
            title = 'Drucksache'
            document = Document(
              identifier=identifier,
              numeric_id=int(identifier),
              title=title)
            document = self.get_document_file(document, href, True)
            paper.document.append({'document': document, 'relation': 'misc'})
        # get the attachments step 2 (additional attachments)
        documents = self.attachments_css(doc)
        if len(documents) > 0:
          if len(documents[0]) > 1:
            if documents[0][1][0].text.strip() == "Anlagen:":
              for tr in documents[0][2:]:
                link = tr[0][0]
                href = "%s%s" % (self.config.BASE_URL, link.attrib["href"])
                title = link.text
                identifier = str(int(link.attrib["href"].split('/')[4]))
                document = Document(
                  identifier=identifier,
                  numeric_id=int(identifier),
                  title=title)
                document = self.get_document_file(document, href)
                paper.document.append({'document': document, 'relation': 'misc'})
        oid = self.db.save_paper(paper)
        return
      except (KeyError, IndexError):
        if try_counter < 3:
          logging.info("Try again: Getting paper %d from %s", paper_id, paper_url)
          try_counter += 1
        else:
          logging.error("Failed getting paper %d from %s", paper_id, paper_url)
          return
    
  def get_document_file(self, document, document_url, post=False):
    """
    Loads the document file from the server and stores it into
    the document object given as a parameter. The form
    parameter is the mechanize Form to be submitted for downloading
    the document.

    The document parameter has to be an object of type
    model.document.Document.
    """
    time.sleep(self.config.WAIT_TIME)
    logging.info("Getting document '%s'", document.identifier)
    
    document_backup = document
    logging.info("Getting document %s from %s", document.identifier, document_url)

    if post:
      document_file = self.get_url(document_url, post_data={'DOLFDNR': '55434', 'options': '64'})
    else:
      document_file = self.get_url(document_url)
      if not document_file:
        logging.error("Error downloading file %", document_url)
        return document
    document.content = document_file.content
    # catch strange magic exception
    try:
      document.mimetype = magic.from_buffer(document.content, mime=True)
    except magic.MagicException:
      logging.warn("Warning: unknown magic error at document %s from %s", document.identifier, document_url)
      return document_backup
    document.filename = self.make_document_filename(document.identifier, document.mimetype)
    return document

  def make_document_path(self, identifier):
    """
    Creates a reconstructable foder hierarchy for documents
    """
    sha1 = hashlib.sha1(identifier).hexdigest()
    firstfolder = sha1[0:1]   # erstes Zeichen von der Checksumme
    secondfolder = sha1[1:2]  # zweites Zeichen von der Checksumme
    ret = (self.config.ATTACHMENT_FOLDER + os.sep + str(firstfolder) + os.sep +
      str(secondfolder))
    return ret

  def make_document_filename(self, identifier, mimetype):
    ext = 'dat'
    if mimetype in self.config.FILE_EXTENSIONS:
      ext = self.config.FILE_EXTENSIONS[mimetype]
    if ext == 'dat':
      logging.warn("No entry in config.FILE_EXTENSIONS for '%s'", mimetype)
      sys.stderr.write("WARNING: No entry in config.FILE_EXTENSIONS for '%s'\n" % mimetype)
    # Verhindere Dateinamen > 255 Zeichen
    identifier = identifier[:192]
    return identifier + '.' + ext

  def save_document_file(self, content, identifier, mimetype):
    """
    Creates a reconstructable folder hierarchy for documents
    """
    folder = self.make_document_path(identifier)
    if not os.path.exists(folder):
      os.makedirs(folder)
    path = folder + os.sep + self.make_document_filename(self, identifier, mimetype)
    with open(path, 'wb') as f:
      f.write(content)
      f.close()
      return path

  def list_in_string(self, stringlist, string):
    """
    Tests if one of the strings in stringlist in contained in string.
    """
    for lstring in stringlist:
      if lstring in string:
        return True
    return False

  def get_url(self, url, post_data=None):
    retry_counter = 0
    while retry_counter < 4:
      retry = False
      try:
        if post_data is not None:
          response = requests.post(url, post_data)
        else:  
          response = requests.get(url)
        return response
      except requests.exceptions.ConnectionError:
        retry_counter = retry_counter + 1
        retry = True
        logging.info("Connection Reset while getting %s, try again", url)
        time.sleep(self.config.WAIT_TIME * 5)
    if retry_counter == 4 and retry == True:
      logging.critical("HTTP Error %s while getting %s", url)
      sys.stderr.write("CRITICAL ERROR:HTTP Error %s while getting %s" % url)
      return False

  # mrtopf
  def parse_date(self, s):
    """parse dates like 20121219T160000Z"""
    berlin = timezone('Europe/Berlin')
    year = int(s[0:4])
    month = int(s[4:6])
    day = int(s[6:8])
    hour = int(s[9:11])
    minute = int(s[11:13])
    second = int(s[13:15])
    return datetime.datetime(year, month, day, hour, minute, second, 0, tzinfo=berlin)

  # mrtopf
  def parse_consultation_list_headline(self, line, data):
    """parse the consultation list in case it is in the td next to the headline. This is the case
    for alsdorf and thus the alsdorf parser has to implement this method.
  
    @param line: the tr element which contains the consultation list
    @param data: the data so far
    @return data: the updated data element
    """
    self.consultation_list_start = True # mark that we found the headline, the table will be in the next line
    return data
  
  # mrtopf
  def parse_consultation_list(self, line, data):
    """parse the consultation list like it is for aachen. Here it is in the next line (tr) inside the first td.
    The list itself is a table which is parsed by process_consultation_list
  
    @param line: the tr element which contains the consultation list
    @param data: the data so far
    @return data: the updated data element
    """
    data['consultation'] = self.process_consultation_list(line[0]) # line is the tr, line[0] the td with the table inside
    dates = [m['date'] for m in data['consultation']]
    self.consultation_list_start = False
    return data
  
  # mrtopf
  def process_consultation_list(self, elem):
    """process the "Beratungsfolge" table in elem"""
    elem = elem[0]
    # the first line is pixel images, so skip it, then we need to jump in steps of two
    amount = (len(elem)-1)/2
    result = []
    i = 0
    item = None
    for line in elem:
      if i == 0:
        i=i+1
        continue
      """
      here we need to parse the actual list which can have different forms. A complex example
      can be found at http://ratsinfo.aachen.de/bi/vo020.asp?VOLFDNR=10822
      The first line is some sort of headline with the committee in question and the type of consultation.
      After that 0-n lines of detailed information of meetings with a date, transscript and decision.
      The first line has 3 columns (thanks to colspan) and the others have 7.
  
      Here we make every meeting a separate entry, we can group them together later again if we want to.
      """
      # now we need to parse the actual list
      # those lists
      if len(line) == 3:
        # the order is "color/status", name of committee / link to TOP, more info
        status = line[0].attrib['title'].lower()
        # we define a head dict here which can be shared for the other lines
        # once we find another head line we will create a new one here
        item = {
          'status'  : status,         # color coded status, like "Bereit", "Erledigt"
          'committee' : line[1].text.strip(), # name of committee, e.g. "Finanzausschuss", unfort. without id
          'action'  : line[2].text.strip(), # e.g. "Kenntnisnahme", "Entscheidung"
        }
      # for some obscure reasons sometimes action is missing
      elif len(line) == 2:
        # the order is "color/status", name of committee / link to TOP, more info
        status = line[0].attrib['title'].lower()
        # we define a head dict here which can be shared for the other lines
        # once we find another head line we will create a new one here
        item = {
          'status'  : status,         # color coded status, like "Bereit", "Erledigt"
          'committee' : line[1].text.strip(), # name of committee, e.g. "Finanzausschuss", unfort. without id
        }
      elif len(line) == 7:
        try:
          # this is about line 2 with lots of more stuff to process
          # date can be text or a link with that text
          if len(line[1]) == 1: # we have a link (and ignore it)
            item['date'] = datetime.datetime.strptime(line[1][0].text.strip(), "%d.%m.%Y")
          else:
            item['date'] = datetime.datetime.strptime(line[1].text.strip(), "%d.%m.%Y")
          if len(line[2]):
            form = line[2][0] # form with silfdnr and toplfdnr but only in link (action="to010.asp?topSelected=57023")
            item['silfdnr'] = form[0].attrib['value']
            item['meeting'] = line[3][0].text.strip()     # full name of meeting, e.g. "A/31/WP.16 öffentliche/nichtöffentliche Sitzung des Finanzausschusses"
          else:
            item['silfdnr'] = None # no link to TOP. should not be possible but happens (TODO: Bugreport?)
            item['meeting'] = line[3].text.strip()   # here we have no link but the text is in the TD directly
            logging.warn("Agendaitem in the consultation list on the web page does not contain a link to the actual meeting at meeting %s", item['meeting'])
          item['decision'] = line[4].text.strip()     # e.g. "ungeändert beschlossen"
          toplfdnr = None
          if len(line[6]) > 0:
            form = line[6][0]
            toplfdnr = form[0].attrib['value']
          item['toplfdnr'] = toplfdnr           # actually the id of the transcript 
          result.append(item)
        except (IndexError, KeyError):
          logging.error("ERROR: Serious error in consultation list. Unable to parse.")
          logging.error("Serious error in consultation list. Unable to parse.")
          return []
      i=i+1
    return result

  # mrtopf
  def preprocess_text(self, text):
    """preprocess the incoming text, e.g. do some encoding etc."""
    return text

class TemplateError(Exception):
  def __init__(self, message):
    Exception.__init__(self, message)
