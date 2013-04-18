from functools import wraps
import os.path

import flask
import ldap

auth = flask.Blueprint('auth', __name__)
LOGIN_DEFAULT_VIEW = 'views.home'


def authenticate(username, password):
    app = flask.current_app
    conn = ldap.initialize(app.config['AUTH_LDAP_SERVER'])
    conn.protocol_version = ldap.VERSION3
    conn.timeout = app.config['AUTH_LDAP_TIMEOUT']
    user_dn = app.config['AUTH_LDAP_DN'].format(username=username)
    try:
        result = conn.simple_bind_s(user_dn, password)
    except (ldap.INVALID_CREDENTIALS, ldap.UNWILLING_TO_PERFORM):
        return False
    assert result[:2] == (ldap.RES_BIND, [])
    return True


def get_admins():
    acl_file = os.path.join(flask.current_app.instance_path, "users.txt")
    if os.path.exists(acl_file):
        fcontents = open(acl_file).read()
        return fcontents.strip().split("\n")
    return []


@auth.before_app_request
def load_user():
    flask.g.username = flask.session.get('username')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    request = flask.request
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if authenticate(username, password):
            if username in get_admins():
                flask.session['username'] = username
                flask.flash("Logged in as %s" % username, 'success')
                url = request.args.get('next') or flask.url_for(LOGIN_DEFAULT_VIEW)
                return flask.redirect(url)
            else:
                flask.flash("User is not allowed access here", 'error')
        else:
            flask.flash("Bad username or password", 'error')

    return flask.render_template('login.html')


@auth.route('/logout')
def logout():
    del flask.session['username']
    return flask.redirect(flask.url_for(LOGIN_DEFAULT_VIEW))


def require_login():
    """ Make sure someone is logged in. Useful with `before_request` hook. """
    if flask.g.username is None:
        url = flask.url_for('auth.login', next=flask.request.url)
        return flask.redirect(url)


def login_required(func):
    """ Decorator that checks for login. """
    @wraps(func)
    def wrapper(*args, **kwargs):
        rv = require_login()
        if rv is not None:
            return rv
        return func(*args, **kwargs)
    return wrapper
