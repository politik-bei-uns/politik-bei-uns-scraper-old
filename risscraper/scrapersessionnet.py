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

import mechanize
import urllib2
import parse
import datetime
import time
import queue
import sys
from lxml import etree
from StringIO import StringIO
import hashlib
import magic
import os
import logging

from model.body import Body
from model.person import Person
from model.membership import Membership
from model.organization import Organization
from model.meeting import Meeting
from model.consultation import Consultation
from model.paper import Paper
from model.agendaitem import AgendaItem
from model.file import File

class ScraperSessionNet(object):

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
      self.person_queue = queue.Queue('SESSIONNET_PERSON', config, db)
      self.meeting_queue = queue.Queue('SESSIONNET_MEETING', config, db)
      self.paper_queue = queue.Queue('SESSIONNET_PAPER', config, db)
    # system info (PHP/ASP)
    self.template_system = None
    self.urls = None
    self.xpath = None

  def work_from_queue(self):
    """
    Empty queues if they have values. Queues are emptied in the
    following order:
    1. Persons
    2. Meetings
    3. Papers
    """
    while self.person_queue.has_next():
      job = self.person_queue.get()
      #self.get_person(committee_id=job['key'])
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
    Tries to find out which SessionNet version we are working with
    and adapts configuration
    """
    time.sleep(self.config['scraper']['wait_time'])
    # requesting the base URL. This is usually redirected
    #try:
    #  response = self.user_agent.open(self.config['scraper']['base_url'])
    #except urllib2.HTTPError, e:
    #  if e.code == 404:
    #    sys.stderr.write("URL not found (HTTP 404) error caught: %s\n" % self.config['scraper']['base_url'])
    #    sys.stderr.write("Please check BASE_URL in your configuration.\n")
    #    sys.exit(1)
    #url = response.geturl()
    #assert (url != self.config['scraper']['base_url']), "No redirect"
    #if url.endswith('.php'):
    #  self.template_system = 'php'
    #elif url.endswith('.asp'):
    #  self.template_system = 'asp'
    #else:
    #  logging.critical("Cannot guess template system from URL '%s'", url)
    #  sys.stderr.write("CRITICAL ERROR: Cannot guess template system from URL '%s'\n" % url)
    #  # there is no point in going on here.
    #  sys.exit(1)
    self.urls = self.config['scraper'][self.config['scraper']['type']]['urls']
    self.xpath = self.config['scraper'][self.config['scraper']['type']]['xpath']


  def find_person(self):
    """
    Load committee details for the given detail page URL or numeric ID
    """
    # Read either person_id or committee_url from the opposite
    user_overview_url = self.urls['PERSON_OVERVIEW_PRINT_PATTERN'] % self.config['scraper']['base_url']
    logging.info("Getting user overview from %s", user_overview_url)
    
    time.sleep(self.config['scraper']['wait_time'])
    response = self.get_url(user_overview_url)
    if not response:
      return
    
    # seek(0) is necessary to reset response pointer.
    response.seek(0)
    html = response.read()
    html = html.replace('&nbsp;', ' ')
    parser = etree.HTMLParser()
    dom = etree.parse(StringIO(html), parser)
    
    trs = dom.xpath(self.xpath['PERSONLIST_LINES'])
    for tr in trs:
      current_person = None
      link = tr.xpath('.//a')
      if len(link):
        parsed = parse.search(self.urls['PERSON_DETAIL_PARSE_PATTERN'], link[0].get('href'))
        if not parsed:
          parsed = parse.search(self.urls['PERSON_DETAIL_PARSE_PATTERN_ALT'], link[0].get('href'))
        if parsed:
          person_id = parsed['person_id']
          current_person = Person(originalId=person_id)
      if current_person:
        tds = tr.xpath('.//td')
        if len(tds):
          if len(tds[0]):
            person_name = tds[0][0].text.strip()
            if person_name:
              current_person.name = person_name
        if len(tds) > 1:
          person_party = tds[1].text.strip()
          if person_party:
            for party_alias in self.config['scraper']['party_alias']:
              if party_alias[0] == person_party:
                person_party = party_alias[1]
                break
            new_organization = Organization(originalId=person_party,
                                            name=person_party,
                                            classification='party')
            new_membership = Membership(originalId=unicode(person_id) + '-' + person_party,
                                        organization=new_organization)
            current_person.membership = [new_membership]
        if current_person:
          if hasattr(self, 'person_queue'):
            self.person_queue.add(current_person.originalId)
          self.db.save_person(current_person)
    return

  """
  def get_person(self, person_url=None, person_id=None):
    ""
    Load committee details for the given detail page URL or numeric ID
    ""
    # Read either person_id or committee_url from the opposite
    if person_id is not None:
      person_url = self.urls['COMMITTEE_DETAIL_PRINT_PATTERN_FULL'] % person_id
    elif person_url is not None:
      parsed = parse.search(self.urls['COMMITTEE_DETAIL_PARSE_PATTERN_FULL'], person_url)
      person_id = parsed['person_id']
  
    logging.info("Getting meeting (committee) %d from %s", person_id, person_url)
    
    organisation = Organisation(numeric_id=person_id)
    
    time.sleep(self.config['scraper']['wait_time'])
    response = self.get_url(person_url)
    if not response:
      return
    
    # seek(0) is necessary to reset response pointer.
    response.seek(0)
    html = response.read()
    html = html.replace('&nbsp;', ' ')
    parser = etree.HTMLParser()
    dom = etree.parse(StringIO(html), parser)
    
    trs = dom.xpath(self.xpath['COMMITTEE_LINES'])
    for tr in trs:
      tds = tr.xpath('.//td')
      print tds
      if tr.get('class') == 'smcrowh':
        print tds[0].text
      else:
        for td in tds:
          print td[0].text
    return
  """
  
  def get_person_organization(self, person_organization_url=None, person_id=None):
    """
    Load committee details for the given detail page URL or numeric ID
    """
    # Read either committee_id or committee_url from the opposite
    if person_id is not None:
      person_committee_url = self.urls['PERSON_ORGANIZATION_PRINT_PATTERN'] % (self.config['scraper']['base_url'], person_id)
    elif person_organization_url is not None:
      parsed = parse.search(self.urls['PERSON_ORGANIZATION_PRINT_PATTERN'], person_organization_url)
      person_id = parsed['person_id']
  
    logging.info("Getting person %d organizations from %s", person_id, person_committee_url)
    
    person = Person(originalId=person_id)
    
    time.sleep(self.config['scraper']['wait_time'])
    response = self.get_url(person_committee_url)
    if not response:
      return
    
    # seek(0) is necessary to reset response pointer.
    response.seek(0)
    html = response.read()
    html = html.replace('&nbsp;', ' ')
    parser = etree.HTMLParser()
    dom = etree.parse(StringIO(html), parser)
    
    trs = dom.xpath(self.xpath['PERSON_ORGANIZATION_LINES'])
    organisations = []
    memberships = []
    for tr in trs:
      tds = tr.xpath('.//td')
      long_info = False
      if len(tds) == 5:
        long_info = True
      if len(tds) == 5 or len(tds) == 2:
        if tds[0].xpath('.//a'):
          href = tds[0][0].get('href')
          href_tmp = href.split('&')
          # delete __cgrname when it's there
          if len(href_tmp) == 2:
            if href_tmp[1][0:10] == '__cgrname=':
              href = href_tmp[0]
          parsed = parse.search(self.urls['ORGANIZATION_DETAIL_PARSE_PATTERN'], href)
          if not parsed:
            parsed = parse.search(self.urls['ORGANIZATION_DETAIL_PARSE_PATTERN_FULL'], href)
          if parsed is not None:
            new_organisation = Organization(originalId=int(parsed['committee_id']))
            new_organisation.name = tds[0][0].text
        else:
          new_organisation = Organization(originalId=tds[0].text)
        if new_organisation and long_info:
          new_membership = Membership()
          membership_original_id = originalId=unicode(person_id) + '-' + unicode(new_organisation.originalId)
          if tds[2].text:
            new_membership.role = tds[2].text
          if tds[3].text:
            new_membership.startDate = tds[3].text
            membership_original_id += '-' + tds[3].text
          if tds[4].text:
            new_membership.endDate = tds[4].text
            membership_original_id += '-' + tds[4].text
          new_membership.originalId = membership_original_id
          new_membership.organization = new_organisation
          memberships.append(new_membership)
        else:
          if not new_organisation:
            logging.error("Bad Table Structure in %s", person_committee_url)
    if memberships:
      person.membership = memberships
    oid = self.db.save_person(person)
    logging.info("Person %d stored with _id %s", person_id, oid)
    return

  def get_person_committee_presence(self, person_id=None, person_url=None):
    # URL is like ???
    # TODO
    pass

  def find_meeting(self, start_date=None, end_date=None):
    """
    Find meetings (sessions) within a given time frame and add them to the session queue.
    """
    # list of (year, month) tuples to work from
    start_month = start_date.month
    end_months = (end_date.year - start_date.year) * 12 + end_date.month + 1
    monthlist = [(yr, mn) for (yr, mn) in (
      ((m - 1) / 12 + start_date.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
    )]
  
    for (year, month) in monthlist:
      url = self.urls['CALENDAR_MONTH_PRINT_PATTERN'] % (self.config['scraper']['base_url'], year, month)
      logging.info("Looking for meetings (sessions) in %04d-%02d at %s", year, month, url)
      time.sleep(self.config['scraper']['wait_time'])
      response = self.user_agent.open(url)
      html = response.read()
      html = html.replace('&nbsp;', ' ')
      parser = etree.HTMLParser()
      dom = etree.parse(StringIO(html), parser)
      found = 0
      for link in dom.xpath('//a'):
        href = link.get('href')
        if href is None:
          continue
        parsed = parse.search(self.urls['MEETING_DETAIL_PARSE_PATTERN'], href)
        if hasattr(self, 'meeting_queue') and parsed is not None:
          self.meeting_queue.add(int(parsed['meeting_id']))
          found += 1
      if found == 0:
        logging.info("No meetings(sessions) found for month %04d-%02d", year, month)
  

  def get_meeting(self, meeting_url=None, meeting_id=None):
    """
    Load meeting details for the given detail page URL or numeric ID
    """
    # Read either meeting_id or meeting_url from the opposite
    if meeting_id is not None:
      meeting_url = self.urls['MEETING_DETAIL_PRINT_PATTERN'] % (self.config["scraper"]["base_url"], meeting_id)
    elif meeting_url is not None:
      parsed = parse.search(self.urls['MEETING_DETAIL_PARSE_PATTERN'], meeting_url)
      meeting_id = parsed['meeting_id']
  
    logging.info("Getting meeting (session) %d from %s", meeting_id, meeting_url)
  
    meeting = Meeting(originalId=meeting_id)
    
    time.sleep(self.config['scraper']['wait_time'])
    response = self.get_url(meeting_url)
    if not response:
      return
    
    # forms for later document download
    mechanize_forms = mechanize.ParseResponse(response, backwards_compat=False)
    # seek(0) is necessary to reset response pointer.
    response.seek(0)
    html = response.read()
    html = html.replace('&nbsp;', ' ')
    parser = etree.HTMLParser()
    dom = etree.parse(StringIO(html), parser)
    # check for page errors
    try:
      page_title = dom.xpath('//h1')[0].text
      if 'Fehlermeldung' in page_title:
        logging.info("Page %s cannot be accessed due to server error", meeting_url)
        return
      if 'Berechtigungsfehler' in page_title:
        logging.info("Page %s cannot be accessed due to permissions", meeting_url)
        return
    except:
      pass
    try:
      error_h3 = dom.xpath('//h3[@class="smc_h3"]')[0].text.strip()
      if 'Keine Daten gefunden' in error_h3:
        logging.info("Page %s does not contain any agenda items", meeting_url)
        return
      if 'Fehlercode: 1104' in error_h3:
        logging.info("Page %s cannot be accessed due to permissions", meeting_url)
        return
    except:
      pass
  
    meeting.originalUrl = meeting_url
    # Session title
    try:
      meeting.name = dom.xpath(self.xpath['MEETING_DETAIL_TITLE'])[0].text
    except:
      logging.critical('Cannot find session title element using XPath MEETING_DETAIL_TITLE')
      raise TemplateError('Cannot find session title element using XPath MEETING_DETAIL_TITLE')
  
    # Committe link
    #try:
    #  links = dom.xpath(self.xpath['MEETING_DETAIL_COMMITTEE_LINK'])
    #  for link in links:
    #    href = link.get('href')
    #    parsed = parse.search(self.urls['COMMITTEE_DETAIL_PARSE_PATTERN'], href)
    #    if parsed is not None:
    #      meeting.committees = [Commitee(numeric_id=int(parsed['committee_id']))]
    #      if hasattr(self, 'committee_queue'):
    #        self.committee_queue.add(int(parsed['committee_id']))
    #except:
    #  logging.critical('Cannot find link to committee detail page using MEETING_DETAIL_COMMITTEE_LINK_XPATH')
    #  raise TemplateError('Cannot find link to committee detail page using MEETING_DETAIL_COMMITTEE_LINK_XPATH')
  
    # Meeting identifier, date, address etc
    tds = dom.xpath(self.xpath['MEETING_DETAIL_IDENTIFIER_TD'])
    if len(tds) == 0:
      logging.critical('Cannot find table fields using MEETING_DETAIL_IDENTIFIER_TD_XPATH at session ' + meeting_url)
      raise TemplateError('Cannot find table fields using MEETING_DETAIL_IDENTIFIER_TD_XPATH at session ' + meeting_url)
    else:
      for n in range(0, len(tds)):
        try:
          tdcontent = tds[n].text.strip()
          nextcontent = tds[n + 1].text.strip()
        except:
          continue
        if tdcontent == 'Sitzung:':
          meeting.shortName = nextcontent
        # We don't need this any more because it's scraped in committee detail page(?)
        #elif tdcontent == 'Gremium:':
        #  meeting.committee_name = nextcontent
        elif tdcontent == 'Datum:':
          start = nextcontent
          end = nextcontent
          if tds[n + 2].text == 'Zeit:':
            if tds[n + 3].text is not None:
              times = tds[n + 3].text.replace(' Uhr', '').split('-')
              start = start + ' ' + times[0]
              if len(times) > 1:
                end = end + ' ' + times[1]
              else:
                end = start
            meeting.start = start
            meeting.end = end
        elif tdcontent == 'Raum:':
          meeting.address = " ".join(tds[n + 1].xpath('./text()'))
        elif tdcontent == 'Bezeichnung:':
          meeting.description = nextcontent
        # sense?
        #if not hasattr(meeting, 'originalId'):
        #  logging.critical('Cannot find session identifier using XPath MEETING_DETAIL_IDENTIFIER_TD')
        #  raise TemplateError('Cannot find session identifier using XPath MEETING_DETAIL_IDENTIFIER_TD')
  
    # Agendaitems
    found_files = []
    rows = dom.xpath(self.xpath['MEETING_DETAIL_AGENDAITEM_ROWS'])
    if len(rows) == 0:
      no_agendaitem_check = dom.xpath('//h5')
      no_agendaitem = False
      for item in no_agendaitem_check:
        if item.text.strip() == 'Keine Daten gefunden.':
          no_agendaitem = True
      if no_agendaitem:
        logging.warn("Meeting without agendaitems found in %s" % meeting_url)
      else:
        logging.critical('Cannot find agenda using XPath MEETING_DETAIL_AGENDAITEM_ROWS at meeting %s' % meeting_url)
        raise TemplateError('Cannot find agenda using XPath MEETING_DETAIL_AGENDAITEM_ROWS at %s' % meeting_url)
      meeting.agendaitem = []
    else:
      agendaitems = []
      agendaitem_id = None
      public = True
      agendaitem = None
      for row in rows:
        row_id = row.get('id')
        row_classes = row.get('class').split(' ')
        fields = row.xpath('td')
        number = fields[0].xpath('./text()')
        if len(number) > 0:
          number = number[0]
        else:
          # when theres a updated notice theres an additional spam
          number = fields[0].xpath('.//span/text()')
          if len(number) > 0:
            number = number[0]
        if number == []:
          number = None
        if row_id is not None:
          # Agendaitem main row
          # first: save agendaitem from before
          if agendaitem:
            agendaitems.append(agendaitem)
          # create new agendaitem
          agendaitem = AgendaItem(originalId=int(row_id.rsplit('_', 1)[1]))
          if number is not None:
            agendaitem.number = number
          # in some ris this is a link, sometimes not. test both.
          if len(fields[1].xpath('./a/text()')):
            agendaitem.name = "; ".join(fields[1].xpath('./a/text()'))
          elif len(fields[1].xpath('./text()')):
            agendaitem.name = "; ".join(fields[1].xpath('./text()'))
          # ignore no agendaitem information
          if agendaitem.name == 'keine Tagesordnungspunkte':
            agendaitem = None
            continue
          agendaitem.public = public
          # paper links
          links = row.xpath(self.xpath['MEETING_DETAIL_AGENDAITEM_ROWS_PAPER_LINK'])
          consultations = []
          papers = []
          for link in links:
            href = link.get('href')
            if href is None:
              continue
            # links to papers
            parsed = parse.search(self.urls['PAPER_DETAIL_PARSE_PATTERN'], href)
            if parsed is not None:
              consultation = Consultation(originalId=unicode(agendaitem.originalId) + unicode(parsed['paper_id']))
              consultation.paper = Paper(originalId=int(parsed['paper_id'])) #, name=link.text #TODO: da stehen ab und an Zusatzinfos drin. Wohin damit?
              consultations.append(consultation)
              # Add paper to paper queue
              if hasattr(self, 'paper_queue'):
                self.paper_queue.add(int(parsed['paper_id']))
          if len(consultations) == 1:
            agendaitem.consultation = consultations[0]
          elif len(consultations) > 1:
            logging.warn('Multible Papers found in an Agendaitem at %s' % meeting_url)
          
          """
          Note: we don't scrape agendaitem-related documents for now,
          based on the assumption that they are all found via paper
          detail pages. All we do here is get a list of document IDs
          in found_files
          """
          # find links
          links = row.xpath('.//a[contains(@href,"getfile.")]')
          for link in links:
            if not link.xpath('.//img'):
              file_link = self.config['scraper']['base_url'] + link.get('href')
              file_id = file_link.split('id=')[1].split('&')[0]
              found_files.append(file_id)
          # find forms
          forms = row.xpath('.//form')
          for form in forms:
            for hidden_field in form.xpath('input'):
              if hidden_field.get('name') != 'DT':
                continue
              file_id = hidden_field.get('value')
              found_files.append(file_id)
        # Alternative für smc_tophz wegen Version 4.3.5 bi (Layout 3)
        elif ('smc_tophz' in row_classes) or (row.get('valign') == 'top' and row.get('debug') == '3'):
          # additional (optional row for agendaitem)
          label = fields[1].text
          value = fields[2].text
          if label is not None and value is not None:
            label = label.strip()
            value = value.strip()
            if label in ['Ergebnis:', 'Beschluss:', 'Beratungsergebnis:']:
              new_result_string = ''
              for result_string in self.config['scraper']['result_strings']:
                if result_string[0] == value:
                  new_result_string = result_string[1]
                  break
              if not new_result_string:
                new_result_string = self.db.save_result_string(value)
                logging.warn("String '%s' not found in configured RESULT_STRINGS", value)
              agendaitem.result = new_result_string
            elif label in ['Bemerkung:', 'Abstimmung:']:
              agendaitem.result_details = value
            # What's this?
            #elif label == 'Abstimmung:':
            #  agendaitems[agendaitem_id]['voting'] = value
            else:
              logging.critical("Agendaitem info label '%s' is unknown", label)
              raise ValueError('Agendaitem info label "%s" is unknown' % label)
        elif 'smcrowh' in row_classes:
          # Subheading (public / nonpublic part)
          if fields[0].text is not None and "Nicht öffentlich" in fields[0].text.encode('utf-8'):
            public = False
      meeting.agendaItem = agendaitems

    # meeting-related documents
    containers = dom.xpath(self.xpath['MEETING_DETAIL_FILES'])
    for container in containers:
      classes = container.get('class')
      if classes is None:
        continue
      classes = classes.split(' ')
      if self.xpath['MEETING_DETAIL_FILES_CONTAINER_CLASSNAME'] not in classes:
        continue
      invitations = []
      resultsProtocol = None
      verbatimProtocol = None
      auxiliaryFile = []
      rows = container.xpath('.//tr')
      for row in rows:
        if not row.xpath('.//form'):
          links = row.xpath('.//a')
          for link in links:
            # ignore additional pdf icon links
            if not link.xpath('.//img'):
              name = ' '.join(link.xpath('./text()')).strip()
              file_link = self.config['scraper']['base_url'] + link.get('href')
              file_id = file_link.split('id=')[1].split('&')[0]
              if file_id in found_files:
                continue
              file = File(
                originalId=file_id,
                name=name,
                originalUrl=file_link,
                originalDownloadPossible = True)
              file = self.get_file(file=file, link=file_link)
              if 'Einladung' in name:
                invitations.append(file)
              elif 'Niederschrift' in name:
                if resultsProtocol:
                  logging.warn('Two resultsProtocols found at %s' % meeting_url)
                else:
                  resultsProtocol = file
              else:
                auxiliaryFile.append(file)
              found_files.append(file_id)
        else:
          forms = row.xpath('.//form')
          for form in forms:
            name = " ".join(row.xpath('./td/text()')).strip()
            for hidden_field in form.xpath('input'):
              if hidden_field.get('name') != 'DT':
                continue
              file_id = hidden_field.get('value')
              # make sure to add only those which aren't agendaitem-related
              if file_id not in found_files:
                file = File(
                  originalId=file_id,
                  name=name,
                  originalDownloadPossible = False
                )
                # Traversing the whole mechanize response to submit this form
                for mform in mechanize_forms:
                  for control in mform.controls:
                    if control.name == 'DT' and control.value == file_id:
                      file = self.get_file(file, mform)
                if 'Einladung' in name:
                  invitations.append(file)
                elif 'Niederschrift' in name:
                  if resultsProtocol:
                    logging.warn('Two resultsProtocols found at %s' % meeting_url)
                  else:
                    resultsProtocol = file
                else:
                  auxiliaryFile.append(file)
                found_files.append(file_id)
      if len(invitations):
        meeting.invitation = invitations
      if resultsProtocol:
        meeting.resultsProtocol = resultsProtocol
      if verbatimProtocol:
        meeting.verbatimProtocol = verbatimProtocol
      if len(auxiliaryFile):
        meeting.auxiliaryFile = auxiliaryFile
    oid = self.db.save_meeting(meeting)
    logging.info("Meeting %d stored with _id %s", meeting_id, oid)


  def get_paper(self, paper_url=None, paper_id=None):
    """
    Load paper details for the paper given by detail page URL
    or numeric ID
    """
    # Read either paper_id or paper_url from the opposite
    if paper_id is not None:
      paper_url = self.urls['PAPER_DETAIL_PRINT_PATTERN'] % (self.config["scraper"]["base_url"], paper_id)
    elif paper_url is not None:
      parsed = parse.search(self.urls['PAPER_DETAIL_PARSE_PATTERN'], paper_url)
      paper_id = parsed['paper_id']
  
    logging.info("Getting paper %d from %s", paper_id, paper_url)
    
    paper = Paper(originalId=paper_id)
    try_until = 1
    try_counter = 0
    try_found = False
    
    while (try_counter < try_until):
      try_counter += 1
      try_found = False
      time.sleep(self.config['scraper']['wait_time'])
      try:
        response = self.user_agent.open(paper_url)
      except urllib2.HTTPError, e:
        if e.code == 404:
          sys.stderr.write("URL not found (HTTP 404) error caught: %s\n" % paper_url)
          sys.stderr.write("Please check BASE_URL in your configuration.\n")
          sys.exit(1)
        elif e.code == 502 or e.code == 500:
          try_until = 4
          try_found = True
          if try_until == try_counter:
            logging.error("Permanent error in %s after 4 retrys.", paper_url)
            return
          else:
            logging.info("Original RIS Server Bug, restart fetching paper %s", paper_url)
      if not response:
        return
      mechanize_forms = mechanize.ParseResponse(response, backwards_compat=False)
      response.seek(0)
      html = response.read()
      html = html.replace('&nbsp;', ' ')
      parser = etree.HTMLParser()
      dom = etree.parse(StringIO(html), parser)
      # Hole die Seite noch einmal wenn unbekannter zufällig auftretender Fehler ohne Fehlermeldung ausgegeben wird (gefunden in Duisburg, vermutlich kaputte Server Config)
      try:
        page_title = dom.xpath('//h1')[0].text
        if 'Fehler' in page_title:
          try_until = 4
          try_found = True
          if try_until == try_counter:
            logging.error("Permanent error in %s after 3 retrys, proceed.", paper_url)
          else:
            logging.info("Original RIS Server Bug, restart scraping paper %s", paper_url)
      except:
        pass
      if (try_found == False):
        # check for page errors
        try:
          if 'Fehlermeldung' in page_title:
            logging.info("Page %s cannot be accessed due to server error", paper_url)
            return
          if 'Berechtigungsfehler' in page_title:
            logging.info("Page %s cannot be accessed due to permissions", paper_url)
            return
        except:
          pass
    
        paper.originalUrl = paper_url
        superordinated_papers = []
        subordinated_papers = []
        
        # Paper title
        try:
          stitle = dom.xpath(self.xpath['PAPER_DETAIL_TITLE'])
          paper.title = stitle[0].text
        except:
          logging.critical('Cannot find paper title element using XPath PAPER_DETAIL_TITLE')
          raise TemplateError('Cannot find paper title element using XPath PAPER_DETAIL_TITLE')
      
        # Paper identifier, date, type etc
        tds = dom.xpath(self.xpath['PAPER_DETAIL_IDENTIFIER_TD'])
        if len(tds) == 0:
          logging.critical('Cannot find table fields using XPath PAPER_DETAIL_IDENTIFIER_TD')
          logging.critical('HTML Dump:' + html)
          raise TemplateError('Cannot find table fields using XPath PAPER_DETAIL_IDENTIFIER_TD')
        else:
          current_category = None
          for n in range(0, len(tds)):
            try:
              tdcontent = tds[n].text.strip()
            except:
              continue
            if tdcontent == 'Name:':
              paper.nameShort = tds[n + 1].text.strip()
            # TODO: Dereferenzierung von Paper Type Strings
            elif tdcontent == 'Art:':
              paper.paperType = tds[n + 1].text.strip()
            elif tdcontent == 'Datum:':
              paper.publishedDate = tds[n + 1].text.strip()
            elif tdcontent == 'Betreff:':
              paper.name = '; '.join(tds[n + 1].xpath('./text()'))
            elif tdcontent == 'Aktenzeichen:':
              paper.reference = tds[n + 1].text.strip()
            elif tdcontent == 'Referenzvorlage:':
              link = tds[n + 1].xpath('a')[0]
              href = link.get('href')
              parsed = parse.search(self.urls['PAPER_DETAIL_PARSE_PATTERN'], href)
              superordinated_paper = Paper(originalId=parsed['paper_id'], nameShort=link.text.strip())
              superordinated_papers.append(superordinated_paper)
              # add superordinate paper to queue
              if hasattr(self, 'paper_queue'):
                self.paper_queue.add(parsed['paper_id'])
            # subordinate papers are added to the queue
            elif tdcontent == 'Untergeordnete Vorlage(n):':
              current_category = 'subordinates'
              for link in tds[n + 1].xpath('a'):
                href = link.get('href')
                parsed = parse.search(self.urls['PAPER_DETAIL_PARSE_PATTERN'], href)
                subordinated_paper = Paper(originalId=parsed['paper_id'], nameShort=link.text.strip())
                subordinated_papers.append(subordinated_paper)
                if hasattr(self, 'paper_queue') and parsed is not None:
                  # add subordinate paper to queue
                  self.paper_queue.add(parsed['paper_id'])
            elif tdcontent == u'Anträge zur Vorlage:':
              current_category = 'todo'
              pass #TODO: WTF is this?
            else:
              if current_category == 'subordinates' and len(tds) > n+1:
                for link in tds[n + 1].xpath('a'):
                  href = link.get('href')
                  parsed = parse.search(self.urls['PAPER_DETAIL_PARSE_PATTERN'], href)
                  subordinated_paper = Paper(originalId=parsed['paper_id'], nameShort=link.text.strip())
                  subordinated_papers.append(subordinated_paper)
                  if hasattr(self, 'paper_queue') and parsed is not None:
                    self.paper_queue.add(parsed['paper_id'])
          if len(subordinated_papers):
            paper.subordinatedPaper = subordinated_papers
          if len(superordinated_papers):
            paper.superordinatedPaper = superordinated_papers
          if not hasattr(paper, 'originalId'):
            logging.critical('Cannot find paper identifier using MEETING_DETAIL_IDENTIFIER_TD')
            raise TemplateError('Cannot find paper identifier using MEETING_DETAIL_IDENTIFIER_TD')
      
        # "Beratungsfolge"(list of sessions for this paper)
        # This is currently not parsed for scraping, but only for
        # gathering session-document ids for later exclusion
        found_files = [] #already changed: found_files, files. todo: document_foo
        rows = dom.xpath(self.xpath['PAPER_DETAIL_AGENDA_ROWS'])
        for row in rows:
          # find forms
          formfields = row.xpath('.//input[@type="hidden"][@name="DT"]')
          for formfield in formfields:
            file_id = formfield.get('value')
            if file_id is not None:
              found_files.append(file_id)
          # find links
          links = row.xpath('.//a[contains(@href,"getfile.")]')
          for link in links:
            if not link.xpath('.//img'):
              file_link = self.config['scraper']['base_url'] + link.get('href')
              file_id = file_link.split('id=')[1].split('&')[0]
              found_files.append(file_id)
        # paper-related documents
        files = []
        containers = dom.xpath(self.xpath['PAPER_DETAIL_FILES'])
        for container in containers:
          try:
            classes = container.get('class').split(' ')
          except:
            continue
          if self.xpath['PAPER_DETAIL_FILES_CONTAINER_CLASSNAME'] not in classes:
            continue
          rows = container.xpath('.//tr')
          for row in rows:
            # seems that we have direct links
            if not row.xpath('.//form'):
              links = row.xpath('.//a')
              for link in links:
                # ignore additional pdf icon links
                if not link.xpath('.//img'):
                  name = ' '.join(link.xpath('./text()')).strip()
                  file_link = self.config['scraper']['base_url'] + link.get('href')
                  file_id = file_link.split('id=')[1].split('&')[0]
                  if file_id in found_files:
                    continue
                  file = File(
                    originalId=file_id,
                    name=name,
                    originalUrl=file_link,
                    originalDownloadPossible = True)
                  file = self.get_file(file=file, link=file_link)
                  files.append(file)
                  found_files.append(file_id)
                  
            # no direct link, so we have to handle forms
            else:
              forms = row.xpath('.//form')
              for form in forms:
                name = " ".join(row.xpath('./td/text()')).strip()
                for hidden_field in form.xpath('input[@name="DT"]'):
                  file_id = hidden_field.get('value')
                  if file_id in found_files:
                    continue
                  file = File(
                    originalId=file_id,
                    name=name,
                    originalDownloadPossible = False)
                  # Traversing the whole mechanize response to submit this form
                  for mform in mechanize_forms:
                    for control in mform.controls:
                      if control.name == 'DT' and control.value == file_id:
                        file = self.get_file(file=file, form=mform)
                        files.append(file)
                        found_files.append(file_id)
        if len(files):
          paper.mainFile = files[0]
        if len(files) > 1:
          paper.auxiliaryFile = files[1:]
        oid = self.db.save_paper(paper)

  def get_file(self, file, form=None, link=None):
    """
    Loads the file from the server and stores it into
    the file object given as a parameter. The form
    parameter is the mechanize Form to be submitted for downloading
    the file.
  
    The file parameter has to be an object of type
    model.file.File.
    """
    logging.info("Getting file '%s'", file.originalId)
    if form:
      mechanize_request = form.click()
    elif link:
      mechanize_request = mechanize.Request(link)
    else:
      logging.warn("No form or link provided")
      
    retry_counter = 0
    while retry_counter < 4:
      retry = False
      try:
        mform_response = mechanize.urlopen(mechanize_request)
        retry_counter = 4
        mform_url = mform_response.geturl()
        if not self.list_in_string(self.urls['FILE_DOWNLOAD_TARGET'], mform_url) and form:
          logging.warn("Unexpected form target URL '%s'", mform_url)
          return file
        file.content = mform_response.read()
        if ord(file.content[0]) == 32 and ord(file.content[1]) == 10:
          file.content = file.content[2:]
        file.mimetype = magic.from_buffer(file.content, mime=True)
        file.filename = self.make_filename(file)
      except mechanize.HTTPError as e:
        if e.code == 502 or e.code == 500:
          retry_counter = retry_counter + 1
          retry = True
          logging.info("HTTP Error %s while getting %s, try again" % (e.code, url))
          time.sleep(self.config['scraper']['wait_time'] * 5)
        else:
          logging.critical("HTTP Error %s while getting %s", e.code, url)
          return
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

  def list_in_string(self, stringlist, string):
    """
    Tests if one of the strings in stringlist in contained in string.
    """
    for lstring in stringlist:
      if lstring in string:
        return True
    return False

  def get_url(self, url):
    retry_counter = 0
    while retry_counter < 4:
      retry = False
      try:
        response = self.user_agent.open(url)
        return response
      except urllib2.HTTPError,e:
        if e.code == 502 or e.code == 500:
          retry_counter = retry_counter + 1
          retry = True
          logging.info("HTTP Error %s while getting %s, try again" % (e.code, url))
          time.sleep(self.config['scraper']['wait_time'] * 5)
        else:
          logging.critical("HTTP Error %s while getting %s", e.code, url)
          sys.stderr.write("CRITICAL ERROR:HTTP Error %s while getting %s" % (e.code, url))
    if retry_counter == 4 and retry == True:
      logging.critical("HTTP Error %s while getting %s", url)
      sys.stderr.write("CRITICAL ERROR:HTTP Error %s while getting %s" % url)
      return False

class TemplateError(Exception):
  def __init__(self, message):
    Exception.__init__(self, message)
