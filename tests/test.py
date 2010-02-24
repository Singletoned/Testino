from flea import TestAgent
from nose.tools import assert_equal

from pesto import dispatcher_app, Response
from pesto.request import Request
from pesto.wsgiutils import with_request_args
dispatcher = dispatcher_app()
match = dispatcher.match

def page(html):
    def page(func):
        def page(request, *args, **kwargs):
            return Response(html % (func(request, *args, **kwargs)))
        return page
    return page

def makeformapp(formhtml, action=None):
    """
    Return a WSGI application that responds to GET requests with the given
    HTML, and POST requests with a dump of the posted info
    """

    if action is None:
        action = "/"

    def app(environ, start_response):

        if environ['REQUEST_METHOD'] == 'GET':
            return Response(
                ['<html><body><form method="POST" action="%s">%s</form></body></html>' % (action, formhtml)]
            )(environ, start_response)

        return Response([
                '; '.join(
                    "%s:<%s>" % (name, value)
                    for (name, value) in sorted(Request(environ).form.allitems())
                )
        ])(environ, start_response)

    return app


class testapp(object):

    @match('/redirect1', 'GET')
    def redirect1(request):
        return Response.redirect('/redirect2')

    @match('/redirect2', 'GET')
    def redirect2(request):
        return Response.redirect('/page1')

    @match('/page1', 'GET')
    @page('''
          <html><body>
          <a href="page1">page 1</a>
          <a href="page2">page 2</a>
          <a href="redirect1">redirect</a>
          </body></html>
    ''')
    def page1(request):
        return {}

    @match('/form-text', 'GET')
    @page('''
          <html><body>
          <form method="POST" action="/postform">
            <input name="a" value="a" type="text" />
            <input name="a" value="" type="text" />
            <input name="b" value="" type="text" />
          </form>
          </body></html>
    ''')
    def form_text(request):
        return {}

    @match('/form-checkbox', 'GET')
    @page('''
          <html><body>
          <form method="POST" action="/postform">
            <input name="a" value="1" type="checkbox" />
            <input name="a" value="2" type="checkbox" />
            <input name="b" value="A" type="checkbox" checked="checked" />
            <input name="b" value="B" type="checkbox" />
          </form>
          </body></html>
    ''')
    def form_checkbox(request):
        return {}

    @match('/form-textarea', 'GET')
    @page('''
          <html><body>
          <form method="POST" action="/postform">
            <textarea name="t"></textarea>
          </form>
          </body></html>
    ''')
    def form_textarea(request):
        return {}


    @match('/postform', 'POST')
    def form_submit(request):
        return Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.form.allitems()))
        ])

    @match('/getform', 'GET')
    def form_submit(request):
        return Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.query.allitems()))
        ])

    @match('/setcookie', 'GET')
    @with_request_args(name=unicode, value=unicode, path=unicode)
    def setcookie(request, name='foo', value='bar', path='/'):
        return Response(['ok']).add_cookie(name, value, path=path)

    @match('/cookies', 'GET')
    @match('/<path:path>/cookies', 'GET')
    def listcookies(request, path=None):
        return Response([
                '; '.join("%s:<%s>" % (name, value.value) for (name, value) in sorted(request.cookies.allitems()))
        ])

def test_click():
    page = TestAgent(dispatcher).get('/page1')
    assert_equal(
        page["//a[1]"].click().request.path_info,
        '/page1'
    )
    assert_equal(
        page["//a[2]"].click().request.path_info,
        '/page2'
    )

def test_css_selectors_are_equivalent_to_xpath():
    page = TestAgent(dispatcher).get('/page1')
    assert_equal(
        list(page.find('//a')),
        list(page.findcss('a'))
    )

def test_get_with_query_is_correctly_handled():
    page = TestAgent(dispatcher).get('/getform?x=1')
    assert_equal(page.body, "x:<1>")

def test_click_follows_redirect():

    response = TestAgent(dispatcher).get('/page1')["//a[text()='redirect']"].click(follow=False)
    assert_equal(response.request.path_info, '/redirect1')

    response = TestAgent(dispatcher).get('/page1')["//a[text()='redirect']"].click(follow=True)
    assert_equal(response.request.path_info, '/page1')

def test_form_text():
    form_page = TestAgent(dispatcher).get('/form-text')
    form = form_page['//form']
    # Check defaults are submitted
    assert_equal(
        form.submit().body,
        "a:<>; a:<a>; b:<>"
    )

    # Now set field values
    form['//input[@name="a"][1]'].value = 'do'
    form['//input[@name="a"][2]'].value = 're'
    form['//input[@name="b"][1]'].value = 'mi'
    assert_equal(
        form.submit().body,
        "a:<do>; a:<re>; b:<mi>"
    )

def test_form_checkbox():
    form_page = TestAgent(dispatcher).get('/form-checkbox')
    form = form_page['//form']
    # Check defaults are submitted
    assert_equal(
        form.submit().body,
        "b:<A>"
    )

    # Now set field values
    form['//input[@name="a"][1]'].checked = True
    form['//input[@name="a"][2]'].checked = True
    form['//input[@name="b"][1]'].checked = False
    form['//input[@name="b"][2]'].checked = True
    assert_equal(
        form.submit().body,
        "a:<1>; a:<2>; b:<B>"
    )

def test_form_textarea():
    form_page = TestAgent(dispatcher).get('/form-textarea')
    form_page['//textarea'].value = 'test'
    assert_equal(
        form_page['//textarea'].form.submit().body,
        't:<test>'
    )

def test_form_select():
    app = makeformapp("""
        <select name="s">
        <option value="o1"></option>
        <option value="o2"></option>
        </select>
    """)
    r = TestAgent(app).get('/')
    r['//select'].value = 'o2'
    assert_equal(r['//form'].submit().body, 's:<o2>')

def test_form_select_multiple():
    app = makeformapp("""
        <select name="s" multiple="">
        <option value="o1"></option>
        <option value="o2"></option>
        <option value="o3"></option>
        </select>
    """)
    r = TestAgent(app).get('/')
    r['//select'].value = ['o1', 'o3']
    assert_equal(r['//form'].submit().body, 's:<o1>; s:<o3>')


def test_form_disabled():
    makeformapp("""
    """)

def test_form_submit_button():
    app = makeformapp('''
        <input id="1" type="submit" name="s" value="1"/>
        <input id="2" type="submit" name="s" value="2"/>
        <input id="3" type="submit" name="t" value="3"/>
        <input id="4" type="image" name="u" value="4"/>
        <button id="5" type="submit" name="v" value="5">click me!</button>
        <button id="6" name="w" value="6">click me!</button>
        <button id="7" type="button" name="x" value="7">don't click me!</button>
    ''')
    form_page = TestAgent(app).get('/')


    assert_equal(form_page['//form'].submit().body, '')

    assert_equal(form_page.findcss('#1').submit().body, 's:<1>')
    assert_equal(form_page.findcss('#2').submit().body, 's:<2>')
    assert_equal(form_page.findcss('#3').submit().body, 't:<3>')
    assert_equal(form_page.findcss('#4').submit().body, 'u:<4>; u.x:<1>; u.y:<1>')
    assert_equal(form_page.findcss('#5').submit().body, 'v:<5>')
    assert_equal(form_page.findcss('#6').submit().body, 'w:<6>')
    try:
        form_page.findcss('#7').submit()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Shouldn't be able to submit a non-submit button")

def test_form_action_fully_qualified_uri_doesnt_error():
    app = makeformapp("", action='http://localhost/')
    r = TestAgent(app).get('/')
    assert_equal(r['//form'].submit().body, '')

def test_form_submit_follows_redirect():
    form_page = TestAgent(dispatcher).get('/form-text')
    form_page['//form'].attrib['method'] = 'get'
    form_page['//form'].attrib['action'] = '/redirect1'
    assert_equal(
        form_page['//form'].submit(follow=True).request.path_info,
        '/page1'
    )

def test_form_attribute_returns_parent_form():
    form_page = TestAgent(dispatcher).get('/form-text')
    assert_equal(form_page['//input[@name="a"]'].form, form_page['//form'][0])

def test_cookies_are_received():
    response = TestAgent(dispatcher).get('/setcookie?name=foo;value=bar;path=/')
    assert_equal(response.cookies['foo'].value, 'bar')
    assert_equal(response.cookies['foo']['path'], '/')

def test_cookies_are_resent():
    response = TestAgent(dispatcher).get('/setcookie?name=foo;value=bar;path=/')
    response = response.get('/cookies')
    assert_equal(response.body, 'foo:<bar>')

def test_cookie_paths_are_observed():
    response = TestAgent(dispatcher).get('/setcookie?name=doobedo;value=dowop;path=/')
    response = response.get('/setcookie?name=dowahdowah;value=beebeebo;path=/private')

    response = response.get('/cookies')
    assert_equal(response.body, 'doobedo:<dowop>')

    response = response.get('/private/cookies')
    assert_equal(response.body, 'doobedo:<dowop>; dowahdowah:<beebeebo>')

def test_back_method_returns_agent_to_previous_state():
    saved = agent = TestAgent(dispatcher).get('/page1')
    agent = agent["//a[.='page 2']"].click()
    assert agent.request.path_info == '/page2'
    agent = agent.back()
    assert agent.request.path_info == '/page1'
    assert agent is saved

def test_back_method_skips_redirects():
    saved = agent = TestAgent(dispatcher).get('/page2')
    agent = agent.get('/redirect1', follow=True)
    assert agent.request.path_info == '/page1'
    agent = agent.back()
    assert agent.request.path_info == '/page2'
    assert agent is saved


