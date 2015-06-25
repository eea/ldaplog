from flask.ext.admin import expose
from flask.ext.script import Manager
from flask.views import View
from jinja2 import contextfunction
from werkzeug.local import LocalProxy
import auth
import fixtures
import flask
import logging
import logparser
import os
import sqlalchemy.orm
import stats


log = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                                        datefmt='%m-%d %H:%M:%S',
                                        )


class Database(object):

    def __init__(self, app):
        options = {
            'echo': app.config['DEBUG'],
        }

        if app.config['DATABASE'].startswith('mysql'):
            options['pool_recycle'] = 7200  # 2 hours pool recycle

        self.stat_engine = sqlalchemy.create_engine(
            app.config['DATABASE'], encoding='latin1', **options)
        self.StatSession = sqlalchemy.orm.sessionmaker(bind=self.stat_engine)
        self.stat_session = LocalProxy(lambda: self._get_session('stat'))

        self.log_engine = sqlalchemy.create_engine(
            app.config['LOG_DATABASE'], encoding='latin1')
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
    return flask.redirect(flask.url_for('personview.index_view'))


def register_admin(app):
    from flask.ext.admin import Admin
    from flask.ext.admin.contrib.sqla import ModelView
    from flask_admin.menu import MenuLink
    from stats import Person
    from tools import create_excel

    admin = Admin(app)
    db = app.extensions['db']

    class ReadOnlyModelView(ModelView):
        can_create = can_edit = can_delete = False

        @contextfunction
        def get_list_value(self, context, model, name):
            value = super(ReadOnlyModelView, self).get_list_value(
                context, model, name)
            if isinstance(value, str):
                value = unicode(value, 'latin1')
            return value

    class PersonView(ReadOnlyModelView):
        column_searchable_list = ('uid',)
        column_default_sort = ('last_login', True)
        page_size = 10

        skippable_fields = ['id']
        exportable_fields = [
            c.name for c in Person.__table__.columns
            if c.name not in skippable_fields]

        @expose('/export_excel')
        def export_excel(self):
            stat_session = db.StatSession()
            persons = stat_session.query(Person)

            rows = (obj.prepare_export_row(self.exportable_fields)
                    for obj in persons)
            xls = create_excel(
                Person.__tablename__, self.exportable_fields, rows)
            response = flask.make_response(xls)
            response.headers[
                "Content-Type"] = "application/vnd.ms-excel; charset=UTF-8"
            response.headers[
                "Content-Disposition"] = "attachment; filename=persons.xls"
            return response

    admin.add_view(PersonView(stats.Person, db.stat_session,
                              endpoint='personview'))

    class LogRecordView(ReadOnlyModelView):
        column_searchable_list = ('message',)
        page_size = 10

    _admin_log_record = LogRecordView(logparser.LogRecord, db.log_session)
    admin.add_view(_admin_log_record)

    # remove Home from top menu
    del admin._menu[0]
    admin._menu.append(MenuLink("Export", '/admin/personview/export_excel'))

    for view in admin._views:
        (app.before_request_funcs.setdefault(view.blueprint.name, [])
         .append(auth.require_login))

    original_admin_master = (admin.index_view.blueprint.jinja_loader
                             .load(app.jinja_env, 'admin/master.html'))
    original_admin_model_list = (admin.index_view.blueprint.jinja_loader
                                 .load(app.jinja_env, 'admin/model/list.html'))

    @app.context_processor
    def original_admin_master_template():
        return {'original_admin_master': original_admin_master,
                'original_admin_model_list': original_admin_model_list}


class ExportUsers(View):

    def dispatch_request(self):
        stat_session = db.StatSession()
        persons = stat_session.query(stats.Person)
        skippable_fields = ['id']

        exportable_fields = [
            c.name for c in stats.Person.__table__.columns
            if c.name not in skippable_fields]

        rows = list(obj.prepare_export_row(exportable_fields)
                    for obj in persons)
        response = flask.jsonify(rows)
        return response


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

    app.add_url_rule('/export', view_func=ExportUsers.as_view('export'))

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
