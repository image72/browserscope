#!/usr/bin/python2.5
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License')
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared Models Unit Tests."""

__author__ = 'elsigh@google.com (Lindsey Simon)'

import unittest
import logging

from categories import test_set_params
from models import result_stats
from models.result import ResultParent

import mock_data


class MockTestSetWithAdjustResults(mock_data.MockTestSet):
  def AdjustResults(self, results):
    for values in results.values():
      # Add the raw value to be expando'd and store a munged value in score.
      values['expando'] = values['score']
      values['score'] = int(round(values['score'] / 2.0))
    return results


class ResultTest(unittest.TestCase):

  def testGetMedian(self):
    test_set = mock_data.MockTestSet()
    for scores in ((0, 0, 500), (1, 1, 200),
                   (0, 2, 300), (1, 3, 100), (0, 4, 400)):
      parent = ResultParent.AddResult(
          test_set, '12.2.2.25', mock_data.GetUserAgentString(),
          'apple=%s,banana=%s,coconut=%s' % scores)
      parent.increment_all_counts()
    rankers = test_set.GetRankers('Firefox 3')
    self.assertEqual([0, 2, 300],
                     [ranker.GetMedian() for ranker in rankers])

  def testAddResultIncrementsBrowserCounter(self):
    test_set = mock_data.MockTestSet()
    add_result_params = (
        # ((apple, banana, coconut), firefox_version)
        ((0, 0, 500), '3.0.6'),
        ((1, 1, 200), '3.0.6'),
        ((0, 2, 300), '3.0.6'),
        ((1, 3, 100), '3.5'),
        ((0, 4, 400), '3.5')
        )
    for scores, firefox_version in add_result_params:
      parent = ResultParent.AddResult(
          test_set, '12.2.2.25', mock_data.GetUserAgentString(firefox_version),
          'apple=%s,banana=%s,coconut=%s' % scores)
      parent.increment_all_counts()

    self.assertEqual({'Firefox 3.0.6': 3, 'Firefox 3.5': 2},
                     result_stats.BrowserCounts.GetCounts(test_set.category,
                                                          version_level=3))
    self.assertEqual({'Firefox 3': 5},
                     result_stats.BrowserCounts.GetCounts(test_set.category,
                                                          version_level=1))

  def testGetMedianWithParams(self):
    params = test_set_params.Params('w-params', 'a=b', 'c=d', 'e=f')
    params_str = str(params)
    test_set = mock_data.MockTestSet(params=params)
    for scores in ((1, 0, 2), (1, 1, 1), (0, 2, 200)):
      parent = ResultParent.AddResult(
          test_set, '12.2.2.25', mock_data.GetUserAgentString(),
          'apple=%s,banana=%s,coconut=%s' % scores, params_str=params_str)
      parent.increment_all_counts()
    ranker = test_set.GetTest('coconut').GetRanker('Firefox 3')
    self.assertEqual(2, ranker.GetMedian())

  def testAddResult(self):
    test_set = mock_data.MockTestSet()
    parent = ResultParent.AddResult(
        test_set, '12.2.2.25', mock_data.GetUserAgentString(),
        'apple=1,banana=11,coconut=111')
    expected_results = {
        'apple': 1,
        'banana': 11,
        'coconut': 111,
        }
    self.assertEqual(expected_results, parent.GetResults())

  def testAddResultForTestSetWithAdjustResults(self):
    test_set = MockTestSetWithAdjustResults()
    parent = ResultParent.AddResult(
        test_set, '12.2.2.25', mock_data.GetUserAgentString(),
        'apple=0,banana=80,coconut=200')
    self.assertEqual(0, parent.apple)
    self.assertEqual(80, parent.banana)
    self.assertEqual(200, parent.coconut)
    expected_results = {
        'apple': 0,
        'banana': 40,
        'coconut': 100,
        }
    self.assertEqual(expected_results, parent.GetResults())


  def testAddResultWithExpando(self):
    test_set = MockTestSetWithAdjustResults()
    parent = ResultParent.AddResult(
        test_set, '12.2.2.25', mock_data.GetUserAgentString(),
        'apple=1,banana=49,coconut=499')
    self.assertEqual(1, parent.apple)
    self.assertEqual(49, parent.banana)
    self.assertEqual(499, parent.coconut)
    expected_results = {
        'apple': 1,
        'banana': 25,
        'coconut': 250,
        }
    self.assertEqual(expected_results, parent.GetResults())

  def testAddResultWithParamsLiteralNoneRaises(self):
    # A params_str with a None value is fine, but not a 'None' string
    test_set = mock_data.MockTestSet()
    ua_string = (
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.0; Trident/4.0; '
        'chromeframe; SLCC1; .NET CLR 2.0.5077; 3.0.30729),gzip(gfe),gzip(gfe)')
    self.assertRaises(
        ValueError,
        ResultParent.AddResult, test_set, '12.1.1.1', ua_string,
        'testDisplay=500,testVisibility=200', params_str='None')

  def testGetStatsDataWithParamsEmptyStringRaises(self):
    test_set = mock_data.MockTestSet()
    ua_string = (
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.0; Trident/4.0; '
        'chromeframe; SLCC1; .NET CLR 2.0.5077; 3.0.30729),gzip(gfe),gzip(gfe)')
    self.assertRaises(
        ValueError,
        ResultParent.AddResult, test_set, '12.1.1.1', ua_string,
        'testDisplay=500,testVisibility=200', params_str='')


class ChromeFrameAddResultTest(unittest.TestCase):

  def testAddResult(self):
    chrome_ua_string = ('Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) '
                        'AppleWebKit/530.1 (KHTML, like Gecko) '
                        'Chrome/2.0.169.1 Safari/530.1')
    ua_string = (
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.0; Trident/4.0; '
        'chromeframe; SLCC1; .NET CLR 2.0.5077; 3.0.30729),gzip(gfe),gzip(gfe)')

    test_set = mock_data.MockTestSet()
    parent = ResultParent.AddResult(
        test_set, '12.2.2.25', ua_string, 'apple=1,banana=3,coconut=500',
        js_user_agent_string=chrome_ua_string)
    self.assertEqual(chrome_ua_string,
                     parent.user_agent.js_user_agent_string)
