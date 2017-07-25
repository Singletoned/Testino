# -*- coding: utf-8 -*-

import unittest.mock

import nose
import pyjade
import requests_mock

from testino import Response, XPath, WSGIAgent, BaseAgent, MissingFieldError, MissingFormError


document = pyjade.simple_convert('''
html
  body
    div#foo
      p This is foo
    div#bar
      p This is bar
    a#bumble(href="/bumble")
      button Bumble
    a#famble(href="/famble")
      button Famble
''')


form_document = pyjade.simple_convert('''
html
  body
    form(action="/result_page")
      input(name="flibble")
''')


def wsgi_app(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return [b"This is a WSGI app"]


def test_WSGIAgent():
    agent = WSGIAgent(wsgi_app)
    response = agent.get("/")
    assert response.content == b"This is a WSGI app"


@requests_mock.mock()
def test_BaseAgent(mock_requests):
    mock_requests.get("http://example.com/foo", text='This is not a WSGI app')
    agent = BaseAgent("http://example.com")
    response = agent.get("/foo")
    assert response.content == b"This is not a WSGI app"


class StubResponse(object):
    def __init__(self, content):
        self.content = content
        self.url = "http://www.example.com/flibble"
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.status_code = 999


class TestResponse(unittest.TestCase):
    def setUp(self):
        self.mock_agent = unittest.mock.Mock()
        self.response = Response(StubResponse(document), agent=self.mock_agent)

    def test_repr(self):
        assert str(self.response) == "<Request 999 /flibble>"

    def test_path(self):
        path = self.response.path
        assert path == "/flibble"

    def test_mime_type(self):
        assert self.response.mime_type == "text/html"

    def test_charset(self):
        assert self.response.charset == "utf-8"

    def test_one(self):
        el = self.response.one("div#foo")
        assert el.text_content().strip() == "This is foo"

    def test_one_fails(self):
        with nose.tools.assert_raises(AssertionError):
            self.response.one("div#fumble")

    def test_one_xpath(self):
        el = self.response.one(XPath("//div[@id='foo']"))
        assert el.text_content().strip() == "This is foo"

    def test_one_fails_xpath(self):
        with nose.tools.assert_raises(AssertionError):
            self.response.one(XPath("//div[@id='fumble']"))

    def test_has_one(self):
        assert self.response.has_one("div#foo")

    def test_has_one_fails(self):
        assert not self.response.has_one("div#fumble")

    def test_all(self):
        els = self.response.all("div")
        assert len(els) == 2
        assert isinstance(els, tuple)

    def test_has_text(self):
        assert self.response.has_text("This is foo")

    def test_has_text_fails(self):
        assert not self.response.has_text("Say hello to Mr Flibble")

    def test_click_contains(self):
        self.response.click(contains="Bumble")
        expected_calls = [unittest.mock.call.get('/bumble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_click_contains_index(self):
        self.response.click(contains="ble", index=1)
        expected_calls = [unittest.mock.call.get('/famble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_click_id(self):
        self.response.click("#bumble")
        expected_calls = [unittest.mock.call.get('/bumble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_missing_form(self):
        with nose.tools.assert_raises(MissingFormError) as e:
            form = self.response.get_form()
        assert str(e.exception) == "MissingFormError: No form found on the page"


class TestForm(unittest.TestCase):
    def setUp(self):
        self.agent = WSGIAgent(wsgi_app)
        self.response = Response(
            StubResponse(form_document), agent=self.agent)

    def test_input(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        assert self.response.has_one("input[value='flamble']")

    def test_submit_data(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        result = form.submit_data()
        expected = {'flibble': "flamble"}
        assert result == expected

    def test_submit(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        expected_path = form.action
        page = form.submit()
        assert page.path == expected_path

    def test_non_string_value(self):
        form = self.response.get_form()
        form['flibble'] = 1

    def test_missing_field(self):
        form = self.response.get_form()
        with nose.tools.assert_raises(MissingFieldError) as e:
            form['_xyz_'] = "foo"
        assert str(e.exception) == "MissingFieldError: Field _xyz_ cannot be found"
