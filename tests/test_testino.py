# -*- coding: utf-8 -*-

import unittest

import nose
import pyjade

from testino import Response


document = pyjade.simple_convert('''
html
  body
    div#foo
      p This is foo
    div#bar
      p This is bar
''')


class StubResponse(object):
    def __init__(self, content):
        self.content = content


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.response = Response(StubResponse(document))

    def test_has_one(self):
        el = self.response.one("div#foo")
        assert el.text_content().strip() == "This is foo"

    def test_has_one_fails(self):
        with nose.tools.assert_raises(AssertionError):
            self.response.one("div#fumble")
