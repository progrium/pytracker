#!/usr/bin/python2.5
#
# Copyright 2009 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Updates a Google Calendar with releases from a Pivotal Tracker project.

Dependencies:
  gdata-python-client:
    Download: http://code.google.com/p/gdata-python-client/downloads/list
    Ubuntu package: python-gdata
  beautifulsoup:
    Download: http://www.crummy.com/software/BeautifulSoup/
    Ubuntu package: python-beautifulsoup

To use:
  - Create a ~/.tracker2gcal-auth.ini file containing:
    [tracker]
    username: username
    password: password

    [calendar]
    username: username@google.com
    password: password
  - Get the calendar ID from the "Settings" pane of the calendar in Google
    Calendar.  Example:
    google.com_t60bvmdcq9e2ai7el5lk00ns9s@group.calendar.google.com
  - Get the Tracker Project ID from the URL of the Tracker UI.
  - Run tracker2gcal:
    tracker2gcal.py -t 1728 -c YOUR_CALENDAR_ID
"""

__author__ = 'dcoker@google.com (Doug Coker)'

import ConfigParser
import logging
import optparse
import os
import re
import sys
import time
import urllib

import atom
import atom.service
from BeautifulSoup import BeautifulStoneSoup
import gdata.calendar
import gdata.calendar.service
import gdata.service

import pytracker
import pytrackergoogle


logging.basicConfig(stream=sys.stderr, level=logging.INFO)

_DATESTRING_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')
_DEFAULT_TRACKER_BASE_API_URL = pytracker.DEFAULT_BASE_API_URL


def YMDToSeconds(ds):
  assert _DATESTRING_RE.match(ds)
  return time.mktime(time.strptime(ds, '%Y-%m-%d'))


def YMDPlusOneDay(ds):
  assert _DATESTRING_RE.match(ds)
  next = time.strftime('%Y-%m-%d',
                       time.localtime(time.mktime(
                           time.strptime(ds, '%Y-%m-%d')) + 86400))
  return next


class Calendar(object):
  """Wrapper for the Google Calendar GData API."""

  def __init__(self, calendar_id, auth):
    self.calendar_id = calendar_id

    self.cal_client = gdata.calendar.service.CalendarService()
    self.cal_client.email = auth[0]
    self.cal_client.password = auth[1]
    self.cal_client.source = 'tracker2gcal'
    self.cal_client.ProgrammaticLogin()

    self.feed = self._GetEventFeed()

  def _GetEventFeedUri(self):
    return ('/calendar/feeds/%s/private/full' %
            urllib.quote_plus(self.calendar_id))

  def _GetBatchEventFeedUri(self):
    return self._GetEventFeedUri() + '/batch'

  def _GetEventFeed(self):
    return self.cal_client.GetCalendarEventFeed(uri=self._GetEventFeedUri())

  def Visit(self, filt, callback):
    """Visits all events in the calendar that satisfy filt with callback."""
    events = self._GetEventFeed()
    for event in events.entry:
      if filt(event):
        callback(event)

  def DeleteEventVisitor(self, event):
    """A Visitor that deletes the event."""
    logging.info('deleting %s', event.title.text)
    self.cal_client.DeleteEvent(event.GetEditLink().href)

  def CreateForBatch(self, title, when, content=''):
    """Creates an Event for batch operation.

    Args:
      title: title of event
      when: date only, in %Y/%m/%d format
      content: content event body

    Returns:
      The populated CalendarEventEntry.
    """

    event = gdata.calendar.CalendarEventEntry()
    event.title = atom.Title(text=title)
    event.content = atom.Content(text=content)

    stop = YMDPlusOneDay(when)

    event.when.append(gdata.calendar.When(start_time=when, end_time=stop))

    event.batch_id = gdata.BatchId(text='insert-request')

    return event

  def GetEventFeedForBatch(self):
    """Returns an Event feed intended for batch operations."""
    return gdata.calendar.CalendarEventFeed()

  def RunBatch(self, event_feed):
    """Executes the adds in event_feed."""
    response_feed = self.cal_client.ExecuteBatch(
        event_feed,
        url=self._GetBatchEventFeedUri())
    for entry in response_feed.entry:
      logging.info('id %s / status %s / reason %s',
                   entry.batch_id.text,
                   entry.batch_status.code,
                   entry.batch_status.reason)


def GetCredentials(parser, scope):
  u = parser.get(scope, 'username')
  p = parser.get(scope, 'password')
  assert u
  assert p
  return (u, p)


def main(opts):
  parser = ConfigParser.RawConfigParser()
  parser.read(opts.credentials)

  cal_auth = GetCredentials(parser, 'calendar')
  tracker_auth = GetCredentials(parser, 'tracker')

  c = Calendar(opts.calendar_id, cal_auth)

  if opts.tracker_base_api_url.find('.google.com') != -1:
    tracker_auth = pytrackergoogle.TrackerAtGoogleAuth(*tracker_auth)
  else:
    tracker_auth = pytracker.HostedTrackerAuth(*tracker_auth)

  t = pytracker.Tracker(opts.tracker_id, tracker_auth,
                        base_api_url=opts.tracker_base_api_url)

  # For now, we care only about type:release stories.
  # We could extend this to also include stories with
  # specific tags.
  def FilterForReleases(event):
    return event.title.text.find('[release') != -1
  c.Visit(FilterForReleases, c.DeleteEventVisitor)
  xml = t.GetReleaseStoriesXml()
  soup = BeautifulStoneSoup(xml)

  batch = c.GetEventFeedForBatch()
  releases = soup.stories.findAll('story')
  logging.info('found %d releases', len(releases))
  for e in releases:
    url = e.url.contents[0]
    # can't use .name -- soup would return the tag name.
    title = e.find('name').contents[0]

    # The release date is computed by Tracker and is an estimate of story
    # completion.
    release_date = pytracker.TrackerDatetimeToYMD(
        e.iteration.finish.contents[0])
    suffix = '[release, floating]'
    calendar_date = release_date

    body = (url + '\n\n\n\n'
            '[This event was automatically created based on data from Tracker]')

    # Hard deadlines are special.
    if e.find('deadline'):
      scheduled_date = pytracker.TrackerDatetimeToYMD(e.deadline.contents[0])
      suffix = '[release, hard]'

      # Prefix the event with "SLIPPING" if release > deadline
      scheduled_secs = YMDToSeconds(scheduled_date)
      release_secs = YMDToSeconds(release_date)
      delta = release_secs - scheduled_secs
      if release_secs > scheduled_secs:
        title = 'SLIPPING %.1f days: %s' % (delta / 86400, title)

      calendar_date = scheduled_date

    title = title + ' ' + suffix

    batch.AddInsert(entry=c.CreateForBatch(title, calendar_date, body))

    logging.info('%s: %s / %s', url, title, calendar_date)

  c.RunBatch(batch)


def ParseOpts():
  """Parses the command line arguments and returns a dictionary of flags."""
  parser = optparse.OptionParser()

  default_credentials_file = os.path.join(os.environ['HOME'],
                                          '.tracker2gcal-auth.ini')

  parser.add_option('-u', '--credentials-file', dest='credentials',
                    help='file containing authentication details',
                    default=default_credentials_file)
  parser.add_option('-c', '--calendar-id', dest='calendar_id',
                    help='target calendar id', metavar='ID')
  parser.add_option('-t', '--tracker-id', dest='tracker_id',
                    help='tracker id', metavar='ID', type='int')
  parser.add_option('-b', '--tracker-base-api-url',
                    dest='tracker_base_api_url',
                    help='the base URL of the Tracker API (including trailing '
                    'slash).',
                    default=_DEFAULT_TRACKER_BASE_API_URL)

  (options, _) = parser.parse_args()

  # Check for errors
  errors = False
  if getattr(options, 'tracker_id') is None:
    logging.error('Missing -t/--tracker-id option')
    errors = True

  if not re.match(r'^https?://[^/]+.*/$',
                  getattr(options, 'tracker_base_api_url')):
    logging.error('-b/--tracker-base-api-url does not look like a valid URL.')
    errors = True

  if getattr(options, 'calendar_id') is None:
    logging.error('Missing -c/--calendar-id option')
    errors = True
  else:
    if not re.search(r'@group.calendar.google.com$', options.calendar_id):
      logging.error('%s does not look like a valid calendar ID.',
                    options.calendar_id)
      errors = True

  if errors:
    parser.print_help()
    sys.exit(1)

  return options


if __name__ == '__main__':
  main(ParseOpts())
