#!/usr/bin/env python
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

"""Tests for pytracker."""

__author__ = 'dcoker@google.com (Doug Coker)'

import unittest
import pytracker

class StoryTest(unittest.TestCase):
  STORY_A = """
    <story>
      <id type="integer">129150</id>
      <story_type>release</story_type>
      <url>http://tracker/story/show/129150</url>
      <current_state>unstarted</current_state>
      <description></description>
      <name>last frontend push before Google IO</name>
      <requested_by>Gorbachev</requested_by>
      <owned_by>Stalin</owned_by>
      <created_at type="datetime">2009/04/17 00:47:50 GMT</created_at>
      <deadline type="datetime">2009/05/21 19:00:00 GMT</deadline>
      <iteration>
        <number>5</number>
        <start type="datetime">2009/05/26 00:00:04 GMT</start>
        <finish type="datetime">2009/06/09 00:00:04 GMT</finish>
      </iteration>
    </story>
  """

  def testFromXmlA(self):
    s = pytracker.Story.FromXml(self.STORY_A)
    self.assertEquals(129150, s.GetStoryId())
    self.assertEquals('release', s.GetStoryType())
    self.assertEquals('http://tracker/story/show/129150', s.GetUrl())
    self.assertEquals('unstarted', s.GetCurrentState())
    self.assertEquals('', s.GetDescription())
    self.assertEquals('Gorbachev', s.GetRequestedBy())
    self.assertEquals('Stalin', s.GetOwnedBy())
    self.assertEquals(1239929270, s.GetCreatedAt())
    self.assertEquals(1242932400, s.GetDeadline())
    self.assertEquals(5, s.GetIteration())

  STORY_B = """
    <story>
      <id type="integer">129150</id>
      <story_type>release</story_type>
      <url>http://tracker/story/show/129150</url>
      <current_state>unstarted</current_state>
      <name>last frontend push before Google IO</name>
      <requested_by>Gorbachev</requested_by>
      <created_at type="datetime">2009/04/17 00:47:50 GMT</created_at>
      <deadline type="datetime">2009/05/21 19:00:00 GMT</deadline>
      <iteration>
        <number>5</number>
        <start type="datetime">2009/05/26 00:00:04 GMT</start>
        <finish type="datetime">2009/06/09 00:00:04 GMT</finish>
      </iteration>
    </story>
  """

  def testFromXmlB(self):
    s = pytracker.Story.FromXml(self.STORY_B)
    self.assertEquals(129150, s.GetStoryId())
    self.assertEquals('release', s.GetStoryType())
    self.assertEquals('http://tracker/story/show/129150', s.GetUrl())
    self.assertEquals('unstarted', s.GetCurrentState())
    # missing fields default to None, but distinguished from empty string!
    self.assertEquals(None, s.GetDescription())
    self.assertEquals('Gorbachev', s.GetRequestedBy())
    self.assertEquals(None, s.GetOwnedBy())
    self.assertEquals(1239929270, s.GetCreatedAt())
    self.assertEquals(1242932400, s.GetDeadline())
    self.assertEquals(5, s.GetIteration())

  STORY_C = """
      <story>
        <id type="integer">1234</id>
        <story_type>bug</story_type>
        <url>http://www.pivotaltracker.com/story/show/1234</url>
        <estimate type="integer">-1</estimate>
        <current_state>started</current_state>
        <description>Now, Scotty!</description>
        <name>More power to shields</name>
        <requested_by>James Kirk</requested_by>
        <owned_by>Montgomery Scott</owned_by>
        <created_at type="datetime">2008/12/10 00:00:00 UTC</created_at>
        <accepted_at type="datetime">2008/12/10 00:00:00 UTC</accepted_at>
        <iteration>
          <number>3</number>
          <start type="datetime">2009/01/05 00:00:02 UTC</start>
          <finish type="datetime">2009/01/19 00:00:02 UTC</finish>
        </iteration>
        <labels>label 1,label 2,label 3</labels>
      </story>
   """

  def testFromXmlC(self):
    s = pytracker.Story.FromXml(self.STORY_C)
    self.assertEquals(1234, s.GetStoryId())
    self.assertEquals('bug', s.GetStoryType())
    self.assertEquals('http://www.pivotaltracker.com/story/show/1234',
                      s.GetUrl())
    self.assertEquals('started', s.GetCurrentState())
    self.assertEquals('Now, Scotty!', s.GetDescription())
    self.assertEquals('More power to shields', s.GetName())
    self.assertEquals('James Kirk', s.GetRequestedBy())
    self.assertEquals('Montgomery Scott', s.GetOwnedBy())
    self.assertEquals(1228867200, s.GetCreatedAt())
    self.assertEquals(None, s.GetDeadline())
    self.assertEquals(3, s.GetIteration())
    self.assertEquals('label 1,label 2,label 3', s.GetLabelsAsString())

  def testAddLabels(self):
    s = pytracker.Story.FromXml(self.STORY_A)
    self.assertEquals(None, s.GetLabelsAsString())  # no labels initially
    s.AddLabel('bbq')
    self.assertEquals('bbq', s.GetLabelsAsString())
    s.AddLabel('alpha')
    self.assertEquals('alpha,bbq', s.GetLabelsAsString())

  def testAddRemoveLabels(self):
    s = pytracker.Story.FromXml(self.STORY_C)
    self.assertEquals('label 1,label 2,label 3', s.GetLabelsAsString())
    s.RemoveLabel('label 1')
    self.assertEquals('label 2,label 3', s.GetLabelsAsString())
    s.AddLabel('label 1')
    self.assertEquals('label 1,label 2,label 3', s.GetLabelsAsString())
    s.RemoveLabel('label 1')
    self.assertEquals('label 2,label 3', s.GetLabelsAsString())
    s.RemoveLabel('label 2')
    self.assertEquals('label 3', s.GetLabelsAsString())
    s.RemoveLabel('label 3')
    self.assertEquals('', s.GetLabelsAsString())
    s.RemoveLabel('label 4')  # removing nonexistant labels is OK!
    self.assertEquals('', s.GetLabelsAsString())

  EMPTY_STORY = """<?xml version="1.0" encoding="utf-8"?><story/>"""

  def testNewStory(self):
    s = pytracker.Story()
    self.assertEquals(self.EMPTY_STORY, s.ToXml())

    s.AddLabel('red')
    self.assertEquals(
        """<?xml version="1.0" encoding="utf-8"?><story>"""
        """<labels>red</labels></story>""", s.ToXml())

    s.AddLabel('green')
    self.assertEquals(
        """<?xml version="1.0" encoding="utf-8"?><story>"""
        """<labels>green,red</labels></story>""", s.ToXml())

    s.SetEstimate(3)
    self.assertEquals(
        """<?xml version="1.0" encoding="utf-8"?><story>"""
        """<estimate>3</estimate><labels>green,red</labels></story>""",
        s.ToXml())

  def testSetDescription(self):
    story = pytracker.Story()
    story.SetDescription('day after day the sun')
    self.assertEquals('day after day the sun', story.GetDescription())
    story.SetDescription('')
    self.assertEquals('', story.GetDescription())
    self.assertEquals('<?xml version="1.0" encoding="utf-8"?><story><description></description></story>',
                      story.ToXml())

  def testSetOwnedBy(self):
    story = pytracker.Story()
    story.SetOwnedBy('dcoker')
    self.assertEquals('<?xml version="1.0" encoding="utf-8"?><story><owned_by>dcoker</owned_by></story>',
                      story.ToXml())

  def testSetReportedBy(self):
    story = pytracker.Story()
    story.SetRequestedBy('dcoker')
    self.assertEquals('<?xml version="1.0" encoding="utf-8"?><story><requested_by>dcoker</requested_by></story>',
                      story.ToXml())

  def testSetDeadline(self):
    story = pytracker.Story()
    story.SetDeadline(1290153802.0)
    self.assertEquals('<?xml version="1.0" encoding="utf-8"?><story><deadline type="datetime">2010/11/19 08:03:22 UTC</deadline></story>',
                      story.ToXml())

  def testSetCreatedAt(self):
    story = pytracker.Story()
    story.SetCreatedAt(1290153802.0)
    self.assertEquals('<?xml version="1.0" encoding="utf-8"?><story><created_at type="datetime">2010/11/19 08:03:22 UTC</created_at></story>',
                      story.ToXml())

if __name__ == '__main__':
  unittest.main()
