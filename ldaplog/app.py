import os
import logging
import sqlalchemy.orm
import flask
from flask.ext.script import Manager
from . import logparser
from . import stats
from . import fixtures


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Database(object):

    def __init__(self, app):
        self.stat_engine = sqlalchemy.create_engine(os.environ['DATABASE'])
        self.StatSession = sqlalchemy.orm.sessionmaker(bind=self.stat_engine)

        self.log_engine = sqlalchemy.create_engine(os.environ['LOG_DATABASE'])
        self.LogSession = sqlalchemy.orm.sessionmaker(bind=self.log_engine)


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


def create_app(debug=False):
    app = flask.Flask(__name__)
    app.debug = debug
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    db = app.extensions['db'] = Database(app)
    register_admin(app)

    @app.route('/')
    def home():
        session = db.StatSession()
        persons = session.query(stats.Person).all()
        return flask.jsonify({
            'person': [{'uid': p.uid, 'last_login': unicode(p.last_login)}
                       for p in persons],
        })

    return app


manager = Manager(create_app)

manager.add_option("-d", "--debug", dest="debug", type=bool,
                   default=(os.environ.get('DEBUG') == 'on'))

manager.add_command('fixture', fixtures.fixture)


@manager.command
def syncdb():
    db = flask.current_app.extensions['db']
    stats.Model.metadata.create_all(db.stat_engine)
    logparser.Model.metadata.create_all(db.log_engine)


@manager.command
def update():
    db = flask.current_app.extensions['db']
    stat_session = db.StatSession()
    log_session = db.LogSession()
    events = logparser.parse_sql(log_session)
    stats.update_stats(stat_session, events)
    stat_session.commit()
    log_session.commit()