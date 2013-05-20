import os
import logging
import sqlalchemy.orm
from werkzeug.local import LocalProxy
import flask
from flask.ext.script import Manager
from . import logparser
from . import stats
from . import fixtures
from . import auth


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Database(object):

    def __init__(self, app):
        self.stat_engine = sqlalchemy.create_engine(app.config['DATABASE'])
        self.StatSession = sqlalchemy.orm.sessionmaker(bind=self.stat_engine)
        self.stat_session = LocalProxy(lambda: self._get_session('stat'))

        self.log_engine = sqlalchemy.create_engine(app.config['LOG_DATABASE'])
        self.LogSession = sqlalchemy.orm.sessionmaker(bind=self.log_engine)
        self.log_session = LocalProxy(lambda: self._get_session('log'))

        app.teardown_request(self.cleanup_sessions)

    def _get_context(self):
        appctx = flask._request_ctx_stack.top
        if not hasattr(appctx, 'db'):
            appctx.db = {}
        return appctx.db

    def _get_session(self, name):
        ctx = self._get_context()
        if name not in ctx:
            if name == 'stat':
                session = self.StatSession()
            elif name == 'log':
                session = self.LogSession()
            else:
                raise RuntimeError('Unknown session type %r' % (name,))
            print 'new session %r (%d)' % (name, id(session.connection()))
            ctx[name] = session
        return ctx[name]

    def cleanup_sessions(self, err=None):
        ctx = self._get_context()
        for k in list(ctx):
            ctx.pop(k).rollback()


db = LocalProxy(lambda: flask.current_app.extensions['db'])

views = flask.Blueprint('views', __name__)


@views.route('/_crashme')
@auth.login_required
def crashme():
    raise RuntimeError("Crashing, as requested")


@views.route('/')
def home():
    return flask.redirect(flask.url_for('admin.index'))


def register_admin(app):
    from flask.ext.admin import Admin
    from flask.ext.admin.contrib.sqlamodel import ModelView

    admin = Admin(app)
    db = app.extensions['db']

    class ReadOnlyModelView(ModelView):
        can_create = can_edit = can_delete = False

    class PersonView(ReadOnlyModelView):
        column_searchable_list = ('uid',)
        column_default_sort = ('last_login', True)

    admin.add_view(PersonView(stats.Person, db.stat_session))
    admin.add_view(ReadOnlyModelView(stats.Login, db.stat_session))

    class LogRecordView(ReadOnlyModelView):
        column_searchable_list = ('message',)
        page_size = 10

    _admin_log_record = LogRecordView(logparser.LogRecord, db.log_session)
    admin.add_view(_admin_log_record)

    for view in admin._views:
        (app.before_request_funcs.setdefault(view.blueprint.name, [])
                .append(auth.require_login))

    original_admin_master = (admin.index_view.blueprint.jinja_loader
                             .load(app.jinja_env, 'admin/master.html'))

    @app.context_processor
    def original_admin_master_template():
        return {'original_admin_master': original_admin_master}


def create_app(config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    try:
        app.config.from_pyfile('settings.py')
    except IOError, e:
        app.config.update(config or {})
    app.extensions['db'] = Database(app)
    app.register_blueprint(views)
    app.register_blueprint(auth.auth)
    register_admin(app)
    if app.config.get('REVERSE_PROXY'):
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)
    return app


def config_from_environ():
    return {
        'DEBUG': (os.environ.get('DEBUG') == 'on'),
        'DATABASE': os.environ.get('DATABASE'),
        'LOG_DATABASE': os.environ.get('LOG_DATABASE'),
        'SECRET_KEY': os.environ.get('SECRET_KEY'),
        'AUTH_LDAP_TIMEOUT': 10,
        'AUTH_LDAP_SERVER': os.environ.get('AUTH_LDAP_SERVER'),
        'AUTH_LDAP_DN': os.environ.get('AUTH_LDAP_DN'),
        'ALLOW_REVERSE_PROXY': (os.environ.get('DEBUG') == 'on'),
    }


manager = Manager(lambda: create_app(config_from_environ()))

manager.add_command('fixture', fixtures.fixture)


@manager.command
def syncdb():
    stats.Model.metadata.create_all(db.stat_engine)
    logparser.Model.metadata.create_all(db.log_engine)


@manager.command
def update():
    more = True
    while more:
        stat_session = db.StatSession()
        log_session = db.LogSession()
        events, more = logparser.parse_sql(log_session)
        stats.update_stats(stat_session, events)
        stat_session.commit()
        log_session.commit()


@manager.option('-p', '--port', type=int, default=5000)
def tornado(port):
    from tornado.web import Application, FallbackHandler
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    app = flask.current_app
    wsgi_container = WSGIContainer(app)
    wsgi_container._log = lambda *args, **kwargs: None
    handlers = [('.*', FallbackHandler, {'fallback': wsgi_container})]
    tornado_app = Application(handlers, debug=app.debug)
    http_server = HTTPServer(tornado_app)
    http_server.listen(port)
    log.info("Hambar109 Tornado listening on port %r", port)
    IOLoop.instance().start()
