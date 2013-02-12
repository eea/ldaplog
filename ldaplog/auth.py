import flask


auth = flask.Blueprint('auth', __name__)
LOGIN_DEFAULT_VIEW = 'views.home'


def authenticate(username, password):
    # TODO ldap login
    return True


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
            flask.session['username'] = username
            return flask.redirect(flask.url_for(LOGIN_DEFAULT_VIEW))

    return flask.render_template('login.html')
