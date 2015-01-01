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

import mechanize
import urllib2
import parse
import datetime
import time
import queue
from model.session import Session
from model.attachment import Attachment
from model.submission import Submission
import sys
from lxml import etree
from StringIO import StringIO
import hashlib
#import pprint
import magic
import os
import logging


class Scraper(object):

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
        #if self.options.workfromqueue:
        self.session_queue = queue.Queue('SCRAPEARIS_SESSIONS', config, db)
        self.submission_queue = queue.Queue('SCRAPEARIS_SUBMISSIONS', config, db)
        # system info (PHP/ASP)
        self.template_system = None
        self.urls = None
        self.xpath = None

    def work_from_queue(self):
        """
        Empty queues if they have values. Queues are emptied in the
        following order:
        1. Sessions
        2. Submissions
        """
        while self.session_queue.has_next():
            job = self.session_queue.get()
            self.get_session(session_id=job['key'])
            self.session_queue.resolve_job(job)
        while self.submission_queue.has_next():
            job = self.submission_queue.get()
            self.get_submission(submission_id=job['key'])
            self.submission_queue.resolve_job(job)
        # when everything is done, we remove DONE jobs
        self.session_queue.garbage_collect()
        self.submission_queue.garbage_collect()

    def guess_system(self):
        """
        Tries to find out which SessionNet version we are working with
        and adapts configuration
        """
        time.sleep(self.config.WAIT_TIME)
        # requesting the base URL. This is usually redirected
        try:
            response = self.user_agent.open(self.config.BASE_URL)
        except urllib2.HTTPError, e:
            if e.code == 404:
                sys.stderr.write("URL not found (HTTP 404) error caught: %s\n" % self.config.BASE_URL)
                sys.stderr.write("Please check BASE_URL in your configuration.\n")
                sys.exit(1)
        url = response.geturl()
        assert (url != self.config.BASE_URL), "No redirect"
        if url.endswith('.php'):
            self.template_system = 'PHP'
        elif url.endswith('.asp'):
            self.template_system = 'ASP'
        else:
            logging.critical("Cannot guess template system from URL '%s'", url)
            sys.stderr.write("CRITICAL ERROR: Cannot guess template system from URL '%s'\n" % url)
            # there is no point in going on here.
            sys.exit(1)
        self.urls = self.config.URLS[self.template_system]
        self.xpath = self.config.XPATH[self.template_system]
        logging.info("Found %s template system.", self.template_system)
        if self.options.verbose:
            print "Found %s template system" % self.template_system

    def find_sessions(self, start_date=None, end_date=None):
        """
        Find sessions within a given time frame and add them to the session queue.
        """
        # list of (year, month) tuples to work from
        start_month = start_date.month
        end_months = (end_date.year - start_date.year) * 12 + end_date.month + 1
        monthlist = [(yr, mn) for (yr, mn) in (
            ((m - 1) / 12 + start_date.year, (m - 1) % 12 + 1) for m in range(start_month, end_months)
        )]

        for (year, month) in monthlist:
            url = self.urls['CALENDAR_MONTH_PRINT_PATTERN'] % (year, month)
            logging.info("Looking for sessions in %04d-%02d at %s", year, month, url)
            time.sleep(self.config.WAIT_TIME)
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
                parsed = parse.search(self.urls['SESSION_DETAIL_PARSE_PATTERN'], href)
                if hasattr(self, 'session_queue') and parsed is not None:
                    self.session_queue.add(int(parsed['session_id']))
                    found += 1
            if found == 0:
                logging.info("No sessions found for month %04d-%02d", year, month)
                if self.options.verbose:
                    print "No sessions found for month %04d-%02d\n" % (year, month)

    def get_session(self, session_url=None, session_id=None):
        """
        Load session details for the given detail page URL or numeric ID
        """
        # Read either session_id or session_url from the opposite
        if session_id is not None:
            session_url = self.urls['SESSION_DETAIL_PRINT_PATTERN'] % session_id
        elif session_url is not None:
            parsed = parse.search(self.urls['SESSION_DETAIL_PARSE_PATTERN'], session_url)
            session_id = parsed['session_id']

        logging.info("Getting session %d from %s", session_id, session_url)

        session = Session(numeric_id=session_id)

        time.sleep(self.config.WAIT_TIME)
        response = self.user_agent.open(session_url)
        # forms for later attachment download
        mechanize_forms = mechanize.ParseResponse(response, backwards_compat=False)
        # seek(0) is necessary to reset response pointer.
        response.seek(0)
        html = response.read()
        html = html.replace('&nbsp;', ' ')
        parser = etree.HTMLParser()
        dom = etree.parse(StringIO(html), parser)
        print session_url
        # check for page errors
        try:
            page_title = dom.xpath('//h1')[0].text
            if 'Fehlermeldung' in page_title:
                logging.info("Page %s cannot be accessed due to server error", session_url)
                if self.options.verbose:
                    print "Page %s cannot be accessed due to server error" % session_url
                return
            if 'Berechtigungsfehler' in page_title:
                logging.info("Page %s cannot be accessed due to permissions", session_url)
                if self.options.verbose:
                    print "Page %s cannot be accessed due to permissions" % session_url
                return
        except:
            pass
        try:
            error_h3 = dom.xpath('//h3[@class="smc_h3"]')[0].text.strip()
            if 'Keine Daten gefunden' in error_h3:
                logging.info("Page %s does not contain any agenda items", session_url)
                if self.options.verbose:
                    print "Page %s does not contain agenda items" % session_url
                return
        except:
            pass

        session.original_url = session_url

        # Session title
        try:
            session.title = dom.xpath(self.xpath['SESSION_DETAIL_TITLE'])[0].text
        except:
            logging.critical('Cannot find session title element using XPath SESSION_DETAIL_TITLE')
            raise TemplateError('Cannot find session title element using XPath SESSION_DETAIL_TITLE')

        # Committe link
        try:
            links = dom.xpath(self.xpath['SESSION_DETAIL_COMMITTEE_LINK'])
            for link in links:
                href = link.get('href')
                parsed = parse.search(self.urls['COMMITTEE_DETAIL_PARSE_PATTERN'], href)
                if parsed is not None:
                    session.committee_id = parsed['committee_id']
        except:
            logging.critical('Cannot find link to committee detail page using SESSION_DETAIL_COMMITTEE_LINK_XPATH')
            raise TemplateError('Cannot find link to committee detail page using SESSION_DETAIL_COMMITTEE_LINK_XPATH')

        # Session identifier, date, address etc
        tds = dom.xpath(self.xpath['SESSION_DETAIL_IDENTIFIER_TD'])
        if len(tds) == 0:
            logging.critical('Cannot find table fields using SESSION_DETAIL_IDENTIFIER_TD_XPATH at session ' + session_url)
            raise TemplateError('Cannot find table fields using SESSION_DETAIL_IDENTIFIER_TD_XPATH at session ' + session_url)
        else:
            for n in range(0, len(tds)):
                try:
                    tdcontent = tds[n].text.strip()
                    nextcontent = tds[n + 1].text.strip()
                except:
                    continue
                if tdcontent == 'Sitzung:':
                    session.identifier = nextcontent
                elif tdcontent == 'Gremium:':
                    session.committee_name = nextcontent
                elif tdcontent == 'Datum:':
                    datestring = nextcontent
                    if tds[n + 2].text == 'Zeit:':
                        if (n + 3) in tds and tds[n + 3].text is not None:
                            datestring + ' ' + tds[n + 3].text
                    session.date_start = datestring
                elif tdcontent == 'Raum:':
                    session.address = " ".join(tds[n + 1].xpath('./text()'))
                elif tdcontent == 'Bezeichnung:':
                    session.description = nextcontent
            if not hasattr(session, 'identifier'):
                logging.critical('Cannot find session identifier using XPath SESSION_DETAIL_IDENTIFIER_TD')
                raise TemplateError('Cannot find session identifier using XPath SESSION_DETAIL_IDENTIFIER_TD')

        # Agendaitems
        found_attachments = []
        rows = dom.xpath(self.xpath['SESSION_DETAIL_AGENDA_ROWS'])
        if len(rows) == 0:
            logging.critical('Cannot find agenda using XPath SESSION_DETAIL_AGENDA_ROWS')
            #raise TemplateError('Cannot find agenda using XPath SESSION_DETAIL_AGENDA_ROWS')
            agendaitems = {}
            session.agendaitems = agendaitems.values()
        else:
            agendaitems = {}
            agendaitem_id = None
            public = True
            for row in rows:
                row_id = row.get('id')
                row_classes = row.get('class').split(' ')
                fields = row.xpath('td')
                number = fields[0].xpath('./text()')
                if len(number) > 0:
                    number = number[0]
                if number == []:
                    number = None
                if row_id is not None:
                    # Agendaitem main row
                    agendaitem_id = row_id.rsplit('_', 1)[1]
                    agendaitems[agendaitem_id] = {}
                    agendaitems[agendaitem_id]['id'] = int(agendaitem_id)
                    if number is not None:
                        agendaitems[agendaitem_id]['number'] = number
                    agendaitems[agendaitem_id]['subject'] = "; ".join(fields[1].xpath('./text()'))
                    agendaitems[agendaitem_id]['public'] = public
                    # submission links
                    links = row.xpath(self.xpath['SESSION_DETAIL_AGENDA_ROWS_SUBMISSION_LINK'])
                    submissions = []
                    for link in links:
                        href = link.get('href')
                        if href is None:
                            continue
                        parsed = parse.search(self.urls['SUBMISSION_DETAIL_PARSE_PATTERN'], href)
                        if parsed is not None:
                            submission = Submission(numeric_id=int(parsed['submission_id']),
                                                    identifier=link.text)
                            submissions.append(submission)
                            # Add submission to submission queue
                            if hasattr(self, 'submission_queue'):
                                self.submission_queue.add(int(parsed['submission_id']))
                    if len(submissions):
                        agendaitems[agendaitem_id]['submissions'] = submissions
                    """
                    Note: we don't scrape agendaitem-related attachments for now,
                    based on the assumption that they are all found via submission
                    detail pages. All we do here is get a list of attachment IDs
                    in found_attachments
                    """
                    #attachments = []
                    forms = row.xpath('.//form')
                    for form in forms:
                        for hidden_field in form.xpath('input'):
                            if hidden_field.get('name') != 'DT':
                                continue
                            attachment_id = hidden_field.get('value')
                            #attachments.append(attachment_id)
                            found_attachments.append(attachment_id)
                    #if len(attachments):
                    #    agendaitems[agendaitem_id]['attachments'] = attachments
                # Alternative für smc_tophz wegen Version 4.3.5 bi (Layout 3)
                elif ('smc_tophz' in row_classes) or (row.get('valign') == 'top' and row.get('debug') == '3'):
                    # additional (optional row for agendaitem)
                    label = fields[1].text
                    value = fields[2].text
                    if label is not None and value is not None:
                        label = label.strip()
                        value = value.strip()
                        if label in ['Ergebnis:', 'Beschluss:', 'Beratungsergebnis:']:
                            if value in self.config.RESULT_STRINGS:
                                agendaitems[agendaitem_id]['result'] = self.config.RESULT_STRINGS[value]
                            else:
                                logging.warn("String '%s' not found in configured RESULT_STRINGS", value)
                                if self.options.verbose:
                                    print "WARNING: String '%s' not found in RESULT_STRINGS\n" % value
                                agendaitems[agendaitem_id]['result'] = value
                        elif label == 'Bemerkung:':
                            agendaitems[agendaitem_id]['result_note'] = value
                        elif label == 'Abstimmung:':
                            agendaitems[agendaitem_id]['voting'] = value
                        else:
                            logging.critical("Agendaitem info label '%s' is unknown", label)
                            raise ValueError('Agendaitem info label "%s" is unknown' % label)

                elif 'smcrowh' in row_classes:
                    # Subheading (public / nonpublic part)
                    if fields[0].text is not None and "Nicht öffentlich" in fields[0].text.encode('utf-8'):
                        public = False
            #print json.dumps(agendaitems, indent=2)
            session.agendaitems = agendaitems.values()

        # session-related attachments
        containers = dom.xpath(self.xpath['SESSION_DETAIL_ATTACHMENTS'])
        for container in containers:
            classes = container.get('class')
            if classes is None:
                continue
            classes = classes.split(' ')
            if self.xpath['SESSION_DETAIL_ATTACHMENTS_CONTAINER_CLASSNAME'] not in classes:
                continue
            attachments = []
            rows = container.xpath('.//tr')
            for row in rows:
                forms = row.xpath('.//form')
                for form in forms:
                    #print "Form: ", form
                    name = " ".join(row.xpath('./td/text()')).strip()
                    for hidden_field in form.xpath('input'):
                        if hidden_field.get('name') != 'DT':
                            continue
                        attachment_id = hidden_field.get('value')
                        # make sure to add only those which aren't agendaitem-related
                        if attachment_id not in found_attachments:
                            attachment = Attachment(
                                identifier=attachment_id,
                                name=name
                            )
                            # Traversing the whole mechanize response to submit this form
                            for mform in mechanize_forms:
                                #print "Form found: '%s'" % mform
                                for control in mform.controls:
                                    if control.name == 'DT' and control.value == attachment_id:
                                        #print "Found matching form: ", control.name, control.value
                                        attachment = self.get_attachment_file(attachment, mform)
                            attachments.append(attachment)
                            found_attachments.append(attachment_id)
            if len(attachments):
                session.attachments = attachments

        oid = self.db.save_session(session)
        if self.options.verbose:
            logging.info("Session %d stored with _id %s", session_id, oid)

        # TODO: add this committee to the queue
        # TODO: read session participants

    def get_submission(self, submission_url=None, submission_id=None):
        """
        Load submission (Vorlage) details for the submission given by detail page URL
        or numeric ID
        """
        # Read either submission_id or submission_url from the opposite
        if submission_id is not None:
            submission_url = self.urls['SUBMISSION_DETAIL_PRINT_PATTERN'] % submission_id
        elif submission_url is not None:
            parsed = parse.search(self.urls['SUBMISSION_DETAIL_PARSE_PATTERN'], submission_url)
            submission_id = parsed['submission_id']

        logging.info("Getting submission %d from %s", submission_id, submission_url)
        submission = Submission(numeric_id=submission_id)
        try_until = 1
        try_counter = 0
        try_found = False
        
        while (try_counter < try_until):
            try_counter += 1
            try_found = False
            time.sleep(self.config.WAIT_TIME)
            try:
                response = self.user_agent.open(submission_url)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    sys.stderr.write("URL not found (HTTP 404) error caught: %s\n" % submission_url)
                    sys.stderr.write("Please check BASE_URL in your configuration.\n")
                    sys.exit(1)
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
                    try_until = 3
                    try_found = True
                    logging.info("Original RIS Server Bug, restart scraping submission %s", submission_url)
            except:
                pass
            if (try_found == False):
            # check for page errors
                try:
                    if 'Fehlermeldung' in page_title:
                        logging.info("Page %s cannot be accessed due to server error", submission_url)
                        if self.options.verbose:
                            print "Page %s cannot be accessed due to server error" % submission_url
                        return
                    if 'Berechtigungsfehler' in page_title:
                        logging.info("Page %s cannot be accessed due to permissions", submission_url)
                        if self.options.verbose:
                            print "Page %s cannot be accessed due to permissions" % submission_url
                        return
                except:
                    pass
        
                submission.original_url = submission_url
        
                # Session title
                try:
                    stitle = dom.xpath(self.xpath['SUBMISSION_DETAIL_TITLE'])
                    submission.title = stitle[0].text
                except:
                    logging.critical('Cannot find submission title element using XPath SUBMISSION_DETAIL_TITLE')
                    raise TemplateError('Cannot find submission title element using XPath SUBMISSION_DETAIL_TITLE')
        
                # Submission identifier, date, type etc
                tds = dom.xpath(self.xpath['SUBMISSION_DETAIL_IDENTIFIER_TD'])
                if len(tds) == 0:
                    logging.critical('Cannot find table fields using XPath SUBMISSION_DETAIL_IDENTIFIER_TD')
                    logging.critical('HTML Dump:' + html)
                    raise TemplateError('Cannot find table fields using XPath SUBMISSION_DETAIL_IDENTIFIER_TD')
                else:
                    current_category = None
                    for n in range(0, len(tds)):
                        try:
                            tdcontent = tds[n].text.strip()
                        except:
                            continue
                        if tdcontent == 'Name:':
                            submission.identifier = tds[n + 1].text.strip()
                        elif tdcontent == 'Art:':
                            submission.type = tds[n + 1].text.strip()
                        elif tdcontent == 'Datum:':
                            submission.date = tds[n + 1].text.strip()
                        elif tdcontent == 'Name:':
                            submission.identifier = tds[n + 1].text.strip()
                        elif tdcontent == 'Betreff:':
                            submission.subject = '; '.join(tds[n + 1].xpath('./text()'))
                        elif tdcontent == 'Referenzvorlage:':
                            link = tds[n + 1].xpath('a')[0]
                            href = link.get('href')
                            parsed = parse.search(self.urls['SUBMISSION_DETAIL_PARSE_PATTERN'], href)
                            submission.superordinate = {
                                'identifier': link.text.strip(),
                                'numeric_id': parsed['submission_id']
                            }
                            # add superordinate submission to queue
                            if hasattr(self, 'submission_queue'):
                                self.submission_queue.add(parsed['submission_id'])
                        # subordinate submissions are added to the queue
                        elif tdcontent == 'Untergeordnete Vorlage(n):':
                            current_category = 'subordinates'
                            for link in tds[n + 1].xpath('a'):
                                href = link.get('href')
                                parsed = parse.search(self.urls['SUBMISSION_DETAIL_PARSE_PATTERN'], href)
                                if hasattr(self, 'submission_queue') and parsed is not None:
                                    #add subordinate submission to queue
                                    self.submission_queue.add(parsed['submission_id'])
                        else:
                            if current_category == 'subordinates':
                                for link in tds[n + 1].xpath('a'):
                                    href = link.get('href')
                                    parsed = parse.search(self.urls['SUBMISSION_DETAIL_PARSE_PATTERN'], href)
                                    if hasattr(self, 'submission_queue') and parsed is not None:
                                        self.submission_queue.add(parsed['submission_id'])
        
                    if not hasattr(submission, 'identifier'):
                        logging.critical('Cannot find session identifier using SESSION_DETAIL_IDENTIFIER_TD_XPATH')
                        raise TemplateError('Cannot find session identifier using SESSION_DETAIL_IDENTIFIER_TD_XPATH')
        
                # "Beratungsfolge"(list of sessions for this submission)
                # This is currently not parsed for scraping, but only for
                # gathering session-attachment ids fpr later exclusion
                found_attachments = []
                rows = dom.xpath(self.xpath['SUBMISSION_DETAIL_AGENDA_ROWS'])
                for row in rows:
                    formfields = row.xpath('.//input[@type="hidden"][@name="DT"]')
                    if len(formfields):
                        attachment_id = formfields[0].get('value')
                        if attachment_id is not None:
                            found_attachments.append(attachment_id)
        
                # submission-related attachments
                submission.attachments = []
                containers = dom.xpath(self.xpath['SUBMISSION_DETAIL_ATTACHMENTS'])
                for container in containers:
                    try:
                        classes = container.get('class').split(' ')
                    except:
                        continue
                    if self.xpath['SUBMISSION_DETAIL_ATTACHMENTS_CONTAINER_CLASSNAME'] not in classes:
                        continue
                    rows = container.xpath('.//tr')
                    for row in rows:
                        forms = row.xpath('.//form')
                        for form in forms:
                            name = " ".join(row.xpath('./td/text()')).strip()
                            for hidden_field in form.xpath('input[@name="DT"]'):
                                attachment_id = hidden_field.get('value')
                                if attachment_id in found_attachments:
                                    continue
                                attachment = Attachment(
                                    identifier=attachment_id,
                                    name=name)
                                #print attachment_id
                                # Traversing the whole mechanize response to submit this form
                                #print mechanize_forms
                                for mform in mechanize_forms:
                                    #print "Form found: '%s'" % mform
                                    for control in mform.controls:
                                        if control.name == 'DT' and control.value == attachment_id:
                                            attachment = self.get_attachment_file(attachment, mform)
                                            submission.attachments.append(attachment)
        
                # forcing overwrite=True here
                oid = self.db.save_submission(submission)

    def get_attachment_file(self, attachment, form):
        """
        Loads the attachment file from the server and stores it into
        the attachment object given as a parameter. The form
        parameter is the mechanize Form to be submitted for downloading
        the attachment.

        The attachment parameter has to be an object of type
        model.attachment.Attachment.
        """
        time.sleep(self.config.WAIT_TIME)
        logging.info("Getting attachment '%s'", attachment.identifier)
        if self.options.verbose:
            print "Getting attachment '%s'" % attachment.identifier
        mechanize_request = form.click()
        #print form
        try:
            mform_response = mechanize.urlopen(mechanize_request)
            mform_url = mform_response.geturl()
            if self.list_in_string(self.urls['ATTACHMENT_DOWNLOAD_TARGET'], mform_url):
                #print "Response headers:", mform_response.info()
                attachment.content = mform_response.read()
                #print attachment.content
                attachment.mimetype = magic.from_buffer(attachment.content, mime=True)
                attachment.filename = self.make_attachment_filename(attachment.identifier, attachment.mimetype)
            else:
                logging.warn("Unexpected form target URL '%s'", mform_url)
                if self.options.verbose:
                    sys.stderr.write("Unexpected form target URL '%s'\n" % mform_url)
        except mechanize.HTTPError as e:
            logging.warn("HTTP Error: code %s, info: %s", e.code, e.msg)
            if self.options.verbose:
                print "HTTP-FEHLER:", e.code, e.msg
        return attachment

    def make_attachment_path(self, identifier):
        """
        Creates a reconstructable foder hierarchy for attachments
        """
        sha1 = hashlib.sha1(identifier).hexdigest()
        firstfolder = sha1[0:1]   # erstes Zeichen von der Checksumme
        secondfolder = sha1[1:2]  # zweites Zeichen von der Checksumme
        ret = (self.config.ATTACHMENT_FOLDER + os.sep + str(firstfolder) + os.sep +
            str(secondfolder))
        return ret

    def make_attachment_filename(self, identifier, mimetype):
        ext = 'dat'
        if mimetype in self.config.FILE_EXTENSIONS:
            ext = self.config.FILE_EXTENSIONS[mimetype]
        if ext == 'dat':
            logging.warn("No entry in config.FILE_EXTENSIONS for '%s'", mimetype)
            sys.stderr.write("WARNING: No entry in config.FILE_EXTENSIONS for '%s'\n" % mimetype)
        # Verhindere Dateinamen > 255 Zeichen
        identifier = identifier[:192]
        return identifier + '.' + ext

    def save_attachment_file(self, content, identifier, mimetype):
        """
        Creates a reconstructable folder hierarchy for attachments
        """
        folder = self.make_attachment_path(identifier)
        if not os.path.exists(folder):
            os.makedirs(folder)
        path = folder + os.sep + self.make_attachment_filename(self, identifier, mimetype)
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


class TemplateError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
