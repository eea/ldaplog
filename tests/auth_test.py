from nose.tools import assert_true, assert_false
import flask


def test_admin_views_require_authentication():
    from ldaplog.app import create_app, syncdb

    app = create_app({
        'TESTING': True,
        'DATABASE': 'sqlite:///:memory:',
        'LOG_DATABASE': 'sqlite:///:memory:',
        'SECRET_KEY': 'asdf',
    })

    with app.app_context():
        syncdb()

    @app.route('/_set_username', methods=['POST'])
    def set_username():
        flask.session['username'] = flask.request.form['username'] or None
        return 'ok'

    def redirects_to_login(url):
        resp = client.get(url)

        if resp.status_code == 200:
            return False

        elif (resp.status_code == 302 and
              resp.location.startswith('http://localhost/login')):
            return True

        else:
            raise AssertionError("Unexpected response %r" % resp)

    client = app.test_client()
    for url in ['/admin/', '/admin/personview/',
                '/admin/loginview/', '/admin/logrecordview/']:
        client.post('/_set_username', data={'username': 'somebody'})
        assert_false(redirects_to_login(url))
        client.post('/_set_username', data={'username': ''})
        assert_true(redirects_to_login(url))

    client.post('/_set_username', data={'username': ''})
    assert_false(redirects_to_login('/login'))
    assert_true(redirects_to_login('/_crashme'))
