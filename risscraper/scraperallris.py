# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Ernesto Ruge, Christian Scholz
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
import HTMLParser

from model.body import Body
from model.person import Person
from model.membership import Membership
from model.organization import Organization
from model.meeting import Meeting
from model.consultation import Consultation
from model.paper import Paper
from model.agendaitem import AgendaItem
from model.file import File

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
    self.user_agent.addheaders = [('User-agent', config['scraper']['user_agent_name'])]
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
    self.user_agent.addheaders = [('User-agent', config['scraper']['user_agent_name'])]

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
      self.get_person_organization(person_id=job['key'])
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
    self.person_queue.garbage_collect()
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
    find_person_url = self.config['scraper']['base_url'] + 'kp041.asp?template=xyz&selfaction=ws&showAll=true&PALFDNRM=1&kpdatfil=&filtdatum=filter&kpname=&kpsonst=&kpampa=99999999&kpfr=99999999&kpamfr=99999999&kpau=99999999&kpamau=99999999&searchForm=true&search=Suchen'
    print "Getting person overview from %s" % (find_person_url)
    
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
      
      # now retrieve person details such as organization memberships etc.
      # we also get the age (but only that, no date of birth)
      person = Person(originalId=int(elem['kplfdnr']))
      if elem['link_kp']:
        person.originalUrl = elem['link_kp']
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
        if person_party in self.config['scraper']['party_alias']:
          person_party = self.config['scraper']['party_alias'][person_party]
        new_organization = Organization(originalId=person_party, name=person_party, classification='party')
        person.membership = [Membership(originalId=unicode(person.originalId) + '-' + person_party, organization=new_organization)]
      
      if elem['link_kp'] is not None:
        if hasattr(self, 'person_queue'):
          self.person_queue.add(person.originalId)
      else:
        logging.info("Person %s %s has no link", person.firstname, person.lastname)
      oid = self.db.save_person(person)
        
  
  def find_meeting(self, start_date=None, end_date=None):
    """
    Find meetings within a given time frame and add them to the meeting queue.
    """
    meeting_find_url = self.config['scraper']['allris']['meeting_find_url'] % (self.config['scraper']['base_url'], start_date.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y"))
    logging.info("Getting meeting overview from %s", meeting_find_url)
    
    parser = etree.XMLParser(recover=True)
    
    r = self.get_url(meeting_find_url)
    if not r:
      return
    
    xml = r.text.encode('ascii','xmlcharrefreplace') 
    root = etree.fromstring(xml, parser=parser)
    for item in root:
      if item.tag == 'list':
        root = item
        break
    for item in root.iterchildren():
      raw_meeting = {}
      for e in item.iterchildren():
        raw_meeting[e.tag] = e.text
      meeting = Meeting(originalId=int(raw_meeting['silfdnr']))
      meeting.start = self.parse_date(raw_meeting['sisbvcs'])
      meeting.end = self.parse_date(raw_meeting['sisevcs'])
      meeting.name = raw_meeting['siname']
      meeting.originalUrl = "%sto010.asp?SILFDNR=%s&options=4" % (self.config['scraper']['base_url'], raw_meeting['silfdnr'])
      meeting.name = raw_meeting['sitext']
      meeting.organization_name = raw_meeting['grname']
      # meeting.description = raw_meeting['sitext'] # WHAT TO DO WITH THIS
      oid = self.db.save_meeting(meeting)
      self.meeting_queue.add(meeting.originalId)
      

  def get_organization(self, organization_id=None, organization_url=None):
    pass
  
  def get_person(self, person_id=None, person_url=None):
    # we dont need this(?)
    pass
  
  def get_person_organization(self, person_id=None, organization_url=None):
    url = "%skp020.asp?KPLFDNR=%s&history=true" % (self.config['scraper']['base_url'], person_id)
    logging.info("Getting person organization from %s", url)
    response = self.get_url(url)
    if not url:
      return
    tree = html.fromstring(response.text)
      
    memberships = []
    person = Person(originalId=person_id)
    # maps name of type to form name and membership type
    type_map = {
      u'Rat der Stadt' : {'mtype' : 'parliament', 'field' : 'PALFDNR'},
      u'Parlament' : {'mtype' : 'parliament', 'field' : 'PALFDNR'},
      u'Fraktion' : {'mtype' : 'organisation', 'field' : 'FRLFDNR'},
      'Fraktionen': {'mtype' : 'parliament', 'field' : 'FRLFDNR'},
      u'Ausschüsse' : {'mtype' : 'organization', 'field' : 'AULFDNR'},
      'Stadtbezirk': {'mtype' : 'parliament', 'field' : 'PALFDNR'},
      'BVV': {'mtype' : 'parliament', 'field' : 'PALFDNR'}
    }

    # obtain the table with the membership list via a simple state machine
    mtype = "parliament"
    field = 'PALFDNR'
    old_group_id = None         # for checking if it changes
    old_group_name = None       # for checking if it changes
    group_id = None             # might break otherwise
    table = tree.xpath('//*[@id="rismain_raw"]/table[2]')
    if len(table):
      table = table[0]
      for line in table.findall("tr"):
        if line[0].tag == "th":
          what = line[0].text.strip()
          print "YYYYYYYYYYYY"
          print what
          print 'Wahlperiode' in what
          field = None
          field_list = None
          if what in type_map:
            mtype = type_map[what]['mtype']
            field = type_map[what]['field']
          elif 'Wahlperiode' in what:
            mtype = 'parliament'
            field_list = ['KPLFDNR', 'AULFDNR'] # 'FRLFDNR'
          elif "Auskünfte gemäß BVV" in what:
            break
          else:
            logging.error("Unknown organization type %s at person detail page %s", what, person_id)
            continue
        else:
          if "Keine Information" in line.text_content():
            # skip because no content is available
            continue
          
          # Empty line = strange stuff comes after this
          if len(list(line)) < 2:
            break
          
          # first get the name of group
          group_name = line[1].text_content()
          organization = Organization(name=group_name)
          
          organization.classification = mtype
  
          # now the first col might be a form with more useful information which will carry through until we find another one
          # with it. we still check the name though
          form = line[0].find("form")
          print form
          if form is not None:
            if field:
              group_id = int(form.find("input[@name='%s']" % field).get("value"))
            elif field_list:
              for field in field_list:
                temp_form = form.find("input[@name='%s']" % field)
                if temp_form is not None:
                  group_id = int(temp_form.get("value"))
            organization.originalId = group_id
            old_group_id = group_id # remember it for next loop
            old_group_name = group_name # remember it for next loop
          else:
            # we did not find a form. We assume that the old group still applies but we nevertheless check if the groupname is still the same
            if old_group_name != group_name:
              logging.warn("Group name differs but we didn't get a form with new group id: group name=%s, old group name=%s, old group id=%s at url %s", group_name, old_group_name, old_group_id, url)
              organization.originalId = None
            else:
              organization.originalId = old_group_id
          membership = Membership(organization=organization)
          membership.originalId = unicode(person_id) + '-' + unicode(group_id)
          
          # TODO: create a list of functions so we can index them somehow
          function = line[2].text_content()
          raw_date = line[3].text_content()
          # parse the date information
          if "seit" in raw_date:
            dparts = raw_date.split()
            membership.endDate = dparts[-1]
          elif "Keine" in raw_date or raw_date.strip() == '':
            # no date information available
            start_date = end_date = None
          else:
            dparts = raw_date.split()
            membership.startDate = dparts[0]
            membership.endDate = dparts[-1]
          if organization.originalId is not None:
            memberships.append(membership)
          else:
            logging.warn("Bad organization at %s" % (url))
          
      person.membership = memberships
      oid = self.db.save_person(person)
  
  def get_person_organization_presence(self, person_id=None, person_url=None):
    # URL is like si019.asp?SILFDNR=5672
    # TODO
    pass
  

  def get_meeting(self, meeting_url=None, meeting_id=None):
    """
    Load meeting details (e.g. agendaitems) for the given detail page URL or numeric ID
    """
    meeting_url = "%sto010.asp?selfaction=ws&template=xyz&SILFDNR=%s" % (self.config['scraper']['base_url'], meeting_id)
    
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
    h = HTMLParser.HTMLParser()
    xml = str(r.text.encode('ascii','xmlcharrefreplace'))
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml, parser=parser)
    
    meeting = Meeting(originalId=meeting_id)

    # special area
    special = {}
    for item in root[0].iterchildren():
      special[item.tag] = item.text
    # Woher kriegen wir das Datum? Nur über die Übersicht?
    #if 'sisb' in special:
    #if 'sise' in special:
    if 'saname' in special:
      meeting.type = special['saname']
    # head area
    head = {}
    for item in root[1].iterchildren():
      head[item.tag] = item.text
    if 'sitext' in head:
      meeting.name = head['sitext']
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
      agendaitem = AgendaItem()
      
      agendaitem.originalId = int(elem['tolfdnr'])
      if elem['toostLang'] == u'öffentlich':
        agendaitem.public = True
      else:
        agendaitem.public = False
      #agendaitem.name = elem['totext1']
      # get agenda detail page
      # TODO: Own Queue
      time.sleep(self.config['scraper']['wait_time'])
      agendaitem_url = '%sto020.asp?selfaction=ws&template=xyz&TOLFDNR=%s' % (self.config['scraper']['base_url'], agendaitem.originalId)
      logging.info("Getting agendaitem %d from %s", agendaitem.originalId, agendaitem_url)
      
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
              agendaitem.resolution_text = h.unescape(etree.tostring(add_item[0][1][0]))
            except:
              logging.warn("Unable to parse resolution text at %s", agendaitem_url)
          else:
            add_agenda_item[add_item.tag] = h.unescape(add_item.text)
        agendaitem.name = add_agenda_item['toptext']
        
        consultation = Consultation(originalId=unicode(agendaitem.originalId) + unicode(int(elem['volfdnr'])))
        if 'voname' in add_agenda_item:
          consultation.paper = Paper(originalId = int(elem['volfdnr']), name=add_agenda_item['voname'])
        else:
          consultation.paper = Paper(originalId = int(elem['volfdnr']))
        agendaitem.consultation = [consultation]
        if 'vobetr' in add_agenda_item:
          if add_agenda_item['vobetr'] != agendaitem.name:
            logging.warn("different values for name: %s and %s", agendaitem.name, add_agenda_item['vobetr'])
        if hasattr(self, 'paper_queue'):
          self.paper_queue.add(int(elem['volfdnr']))
        if "nowDate" not in add_agenda_item:
          # something is broken with this so we don't store it
          logging.warn("Skipping broken agenda at ", agendaitem_url)
        else:
          agendaitem.result = add_agenda_item['totyp']
        agendaitems.append(agendaitem)
    meeting.agendaItem = agendaitems
    
    oid = self.db.save_meeting(meeting)
    logging.info("Meeting %d stored with _id %s", meeting_id, oid)
    

  def get_paper(self, paper_url=None, paper_id=None):
    """
    Load paper details for the paper given by detail page URL
    or numeric ID
    """
    paper_url = '%svo020.asp?VOLFDNR=%s' % (self.config['scraper']['base_url'], paper_id)
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
        text = response.text
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
                  # gets originalId. is there something else at this position? (will break)
                  data['relatedPaper'] = [Paper(originalId=line[3][0][0][1][0].get('href').split('=')[1].split('&')[0])]
            
            # Lot's of scraping just because of the date (?)
            elif headline == "beratungsfolge":
              # the actual list will be in the next row inside a table, so we only set a marker
              self.consultation_list_start = True
            elif self.consultation_list_start:
              elem = line[0][0]
              # the first line is pixel images, so skip it, then we need to jump in steps of two
              amount = (len(elem)-1)/2
              consultations = []
              date_list = []
              i = 0
              item = None
              for elem_line in elem:
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
                new_consultation = Consultation()
                new_consultation.status = elem_line[0].attrib['title'].lower()
                if len(elem_line) == 3:
                  # the order is "color/status", name of committee / link to TOP, more info
                  # we define a head dict here which can be shared for the other lines
                  # once we find another head line we will create a new one here
                  new_consultation.role = elem_line[2].text.strip()
                  
                    #'committee' : elem_line[1].text.strip(), # name of committee, e.g. "Finanzausschuss", unfort. without id
                # for some obscure reasons sometimes action is missing
                elif len(elem_line) == 2:
                  # the order is "color/status", name of committee / link to TOP, more info
                  status = elem_line[0].attrib['title'].lower()
                  # we define a head dict here which can be shared for the other lines
                  # once we find another head line we will create a new one here
                    #'committee' : elem_line[1].text.strip(), # name of committee, e.g. "Finanzausschuss", unfort. without id
                elif len(elem_line) == 7:
                  try:
                    # this is about line 2 with lots of more stuff to process
                    # date can be text or a link with that text
                    if len(elem_line[1]) == 1: # we have a link (and ignore it)
                      date_list.append(datetime.datetime.strptime(elem_line[1][0].text.strip(), "%d.%m.%Y"))
                    else:
                      date_list.append(datetime.datetime.strptime(elem_line[1].text.strip(), "%d.%m.%Y"))
                    if len(elem_line[2]):
                      form = elem_line[2][0] # form with silfdnr and toplfdnr but only in link (action="to010.asp?topSelected=57023")
                      new_consultation.meeting = [Meeting(originalId=form[0].attrib['value'])]
                      #item['meeting'] = elem_line[3][0].text.strip()     # full name of meeting, e.g. "A/31/WP.16 öffentliche/nichtöffentliche Sitzung des Finanzausschusses"
                    else:
                      #no link to TOP. should not be possible but happens (TODO: Bugreport?)
                      #item['meeting'] = elem_line[3].text.strip()   # here we have no link but the text is in the TD directly - will be scaped as meeting
                      logging.warn("AgendaItem in consultation list on the web page does not contain a link to the actual meeting at paper %s", paper_url)
                    toplfdnr = None
                    if len(elem_line[6]) > 0:
                      form = elem_line[6][0]
                      toplfdnr = form[0].attrib['value']
                    if toplfdnr:
                      new_consultation.originalId = "%s-%s" % (toplfdnr, paper_id)
                      new_consultation.agendaItem = AgendaItem(originalId=toplfdnr)           # actually the id of the transcript
                      new_consultation.agendaItem.result = elem_line[4].text.strip()     # e.g. "ungeändert beschlossen"
                      consultations.append(new_consultation)
                    else:
                      logging.error("missing agendaItem ID in consultation list at %s" % paper_url)
                  except (IndexError, KeyError):
                    logging.error("ERROR: Serious error in consultation list. Unable to parse.")
                    logging.error("Serious error in consultation list. Unable to parse.")
                    return []
                i=i+1
              # Theory: we don't need this at all, because it's scraped at meeting
              #data['consultations'] = consultations
              self.consultation_list_start = False # set the marker to False again as we have read it
          last_headline = headline
          # we simply ignore the rest (there might not be much more actually)
        # the actual text comes after the table in a div but it's not valid XML or HTML this using regex
        data['docs'] = self.body_re.findall(response.text)
        first_date = False
        for single_date in date_list:
          if first_date:
            if single_date < first_date:
              first_date = single_date
          else:
            first_date = single_date
        paper = Paper(originalId = paper_id)
        paper.originalUrl = paper_url
        paper.name = data['betreff']
        paper.description = data['docs']
        paper.type = data['drucksache-art']
        if first_date:
          paper.publishedDate = first_date.strftime("%Y-%m-%d")
        # see theory above
        #if 'consultations' in data:
        #  paper.consultation = data['consultations']
        paper.auxiliaryFile = []
        # get the attachments step 1 (Drucksache)
        file_1 = self.attachment_1_css(doc)
        if len(file_1):
          if file_1[0].value:
            href = '%sdo027.asp' % self.config['scraper']['base_url']
            originalId = file_1[0].value
            name = 'Drucksache'
            file = File(
              originalId=originalId,
              name=name)
            file = self.get_file(file, href, True)
            paper.mainFile = file
        # get the attachments step 2 (additional attachments)
        files = self.attachments_css(doc)
        if len(files) > 0:
          if len(files[0]) > 1:
            if files[0][1][0].text.strip() == "Anlagen:":
              for tr in files[0][2:]:
                link = tr[0][0]
                href = "%s%s" % (self.config['scraper']['base_url'], link.attrib["href"])
                name = link.text
                originalId = str(int(link.attrib["href"].split('/')[4]))
                file = File(
                  originalId=originalId,
                  name=name)
                file = self.get_file(file, href)
                paper.auxiliaryFile.append(file)
        if not len(paper.auxiliaryFile):
          del paper.auxiliaryFile
        oid = self.db.save_paper(paper)
        return
      except (KeyError, IndexError):
        if try_counter < 3:
          logging.info("Try again: Getting paper %d from %s", paper_id, paper_url)
          try_counter += 1
        else:
          logging.error("Failed getting paper %d from %s", paper_id, paper_url)
          return
    
  def get_file(self, file, file_url, post=False):
    """
    Loads the file file from the server and stores it into
    the file object given as a parameter. The form
    parameter is the mechanize Form to be submitted for downloading
    the file.

    The file parameter has to be an object of type
    model.file.File.
    """
    time.sleep(self.config['scraper']['wait_time'])
    logging.info("Getting file '%s'", file.originalId)
    
    file_backup = file
    logging.info("Getting file %s from %s", file.originalId, file_url)
    
    if post:
      print file_url
      file_file = self.get_url(file_url, post_data={'DOLFDNR': file.originalId, 'options': '64'})
    else:
      file_file = self.get_url(file_url)
      if not file:
        logging.error("Error downloading file %", file_url)
        return file
    file.content = file_file.content
    # catch strange magic exception
    try:
      file.mimetype = magic.from_buffer(file.content, mime=True)
    except magic.MagicException:
      logging.warn("Warning: unknown magic error at file %s from %s", file.originalId, file_url)
      return file_backup
    file.filename = self.make_filename(file)
    return file

  def make_filename(self, file):
    ext = 'dat'
    
    try:
      name = file.name
    except AttributeError:
      name = file.originalId
    
    for extension in self.config['file_extensions']:
      if extension[0] == file.mimetype:
        ext = extension[1]
        break
    if ext == 'dat':
      logging.warn("No entry in config:main:file_extensions for %s at file id %s", file.mimetype, file.originalId)
    # Verhindere Dateinamen > 255 Zeichen
    name = name[:192]
    return name + '.' + ext

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
        time.sleep(self.config['scraper']['wait_time'] * 5)
    if retry_counter == 4 and retry == True:
      logging.critical("HTTP Error %s while getting %s", url)
      sys.stderr.write("CRITICAL ERROR:HTTP Error while getting %s" % url)
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

class TemplateError(Exception):
  def __init__(self, message):
    Exception.__init__(self, message)
