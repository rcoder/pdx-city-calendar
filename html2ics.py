#!/usr/bin/env python

"""
This script generates an iCal version of the HTML calendar of city events 
available at the following URL:

http://www.portlandonline.com/index.cfm?c=26000

It does so by parsing the tabular HTML to extract dates and times, as well as 
other descriptive metadata.
"""

from datetime import datetime
import time
import urllib2
import sys

import lxml.html
import tidy

from icalendar import Calendar, Event

CAL_URL = 'http://www.portlandonline.com/index.cfm?c=26000'

def remove_newlines(s):
    return s.replace('\n', ' ')

def parse_datetime(dt_str):
    return datetime.strptime(dt_str, '%A, %B %d %Y @ %I:%M %p')

def parse_time(t_str):
    return datetime.strptime(t_str, '%I:%M %p').time()

fh = urllib2.urlopen(CAL_URL)
raw_html = fh.read()
# this is dumb, but necessary -- the raw HTML has a bunch of invalid
# tags of the form '<tagname attr="foo"">...' (note the extra double-
# quote!)
clean_html = str(tidy.parseString(raw_html))

doc = lxml.html.document_fromstring(clean_html)

details = []
for detail_table in doc.find_class('subDetail'):
    # each event has a table representation which includes a title, optional
    # decription text, and a handful of key/value attribute pairs
    raw_title = detail_table.cssselect('.subDetailHeaderTitle a')[0].text_content()
    title = remove_newlines(raw_title)
    description = ''
    item_data = {}
    for row in detail_table.cssselect('tr')[1:]:
        attr_label = None
        attr_data = None
        for col in row.cssselect('td'):
            # iterate over label, data pairs and accumulate event attributes
            elem_class = col.attrib['class']
            if elem_class == 'subDetailLabel':
                attr_label = remove_newlines(col.text_content()).lower()
            elif elem_class == 'subDetailData':
                attr_data = remove_newlines(col.text_content())

            if attr_data is not None:
                if attr_label is not None:
                    if attr_label == 'starts':
                        # start times are of the form 'Monday, January 1 2010 @ 12:00 PM'
                        try:
                            attr_data = parse_datetime(attr_data)
                        except ValueError, ve:
                            print >> sys.stderr, "error parsing time string '%s': %s" % (attr_data, ve.message)
                    elif attr_label == 'ends':
                        # ends are simply a time-of-day relative to the start
                        try:
                            attr_data = parse_datetime(attr_data)
                        except ValueError, ve:
                            try:
                                time_of_day = parse_time(attr_data)
                                attr_data = datetime.combine(item_data['starts'].date(), time_of_day)
                            except KeyError, ke:
                                print >> sys.stderr, "relative end time provided w/o start time!"
                            except ValueError, ve:
                                print >> sys.stderr, "error parsing time string '%s': %s" % (attr_data, ve.message)
                    item_data[attr_label] = attr_data
                else:
                    description = attr_data
                attr_label = attr_data = None

    details.append((title, description, item_data))

#import pprint
#pprint.pprint(details)

calendar = Calendar()
for title, description, attributes in details:
    event = Event()
    event.add('summary', title)
    event.add('description', description)
    event.add('dtstart', attributes['starts'])
    event.add('dtend', attributes['ends'])
    calendar.add_component(event)

print calendar.as_string()
