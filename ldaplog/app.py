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

        self.log_engine = sqlalchemy.create_engine(app.config['LOG_DATABASE'])
        self.LogSession = sqlalchemy.orm.sessionmaker(bind=self.log_engine)


db = LocalProxy(lambda: flask.current_app.extensions['db'])

views = flask.Blueprint('views', __name__)


@views.route('/_crashme')
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
    _admin_session = db.StatSession()  # TODO should not be global
    admin.add_view(ModelView(stats.Person, _admin_session))
    admin.add_view(ModelView(stats.Login, _admin_session))

    class LogRecordView(ModelView):
        column_searchable_list = ('message',)
        page_size = 10

    _admin_log_session = db.LogSession()  # TODO should not be global
    _admin_log_record = LogRecordView(logparser.LogRecord, _admin_log_session)
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
    app = flask.Flask(__name__)
    app.config.update(config or {})
    app.extensions['db'] = Database(app)
    app.register_blueprint(views)
    app.register_blueprint(auth.auth)
    register_admin(app)
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
    }


manager = Manager(lambda: create_app(config_from_environ()))

manager.add_command('fixture', fixtures.fixture)


@manager.command
def syncdb():
    stats.Model.metadata.create_all(db.stat_engine)
    logparser.Model.metadata.create_all(db.log_engine)


@manager.command
def update():
    stat_session = db.StatSession()
    log_session = db.LogSession()
    events = logparser.parse_sql(log_session)
    stats.update_stats(stat_session, events)
    stat_session.commit()
    log_session.commit()
