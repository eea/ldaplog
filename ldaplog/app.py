import os
import sys
import logging
import sqlalchemy.orm
from werkzeug.local import LocalProxy
import flask
from flask.ext.script import Manager
from . import logparser
from . import stats


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Database(object):

    def __init__(self, app):
        self.stat_engine = sqlalchemy.create_engine(os.environ['DATABASE'])
        self.StatSession = sqlalchemy.orm.sessionmaker(bind=self.stat_engine)

        self.log_engine = sqlalchemy.create_engine(os.environ['LOG_DATABASE'])
        self.LogSession = sqlalchemy.orm.sessionmaker(bind=self.log_engine)


def create_app(debug=False):
    app = flask.Flask(__name__)
    app.debug = debug
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    db = app.extensions['db'] = Database(app)

    from flask.ext.admin import Admin
    from flask.ext.admin.contrib.sqlamodel import ModelView
    admin = Admin(app)
    _admin_session = db.StatSession()  # TODO should not be global
    admin.add_view(ModelView(stats.Person, _admin_session))
    _admin_log_session = db.LogSession()  # TODO should not be glo
    import logparser
    class LogRecordView(ModelView):
        column_searchable_list = ('message',)
        page_size = 10
    _admin_log_record = LogRecordView(logparser.LogRecord, _admin_log_session)
    admin.add_view(_admin_log_record)

    @app.route('/')
    def home():
        session = db.StatSession()
        persons = session.query(stats.Person).all()
        return flask.jsonify({
            'person': [{'uid': p.uid, 'last_login': unicode(p.last_login)}
                       for p in persons],
        })

    return app


db = LocalProxy(lambda: flask.current_app.extensions['db'])


def main(debug=False):
    if debug:
        log.setLevel(logging.DEBUG)

    manager = Manager(create_app)

    @manager.command
    def syncdb():
        stats.Model.metadata.create_all(db.stat_engine)
        logparser.Model.metadata.create_all(db.log_engine)

    @manager.command
    def update():
        app = flask.current_app
        stat_session = db.StatSession()
        log_session = db.LogSession()
        events = logparser.parse_sql(log_session)
        stats.update_stats(stat_session, events)
        stat_session.commit()
        log_session.commit()

    fixture = Manager()

    @fixture.option('-p', '--per-page', dest='per_page', type=int)
    def dump(per_page=1000):
        log_session = db.LogSession()
        out = sys.stdout
        records = log_session.query(logparser.LogRecord).order_by('id')
        n = records.count()
        log.debug("Dumping %d records (%d per page)", n, per_page)
        for offset in range(0, n, per_page):
            records_page = records.offset(offset).limit(per_page)
            log.debug("Offset %d ...", offset)
            for record in records_page:
                row = {k: unicode(getattr(record, k)) for k in
                       ['id', 'time', 'hostname', 'syslog_tag', 'message']}
                flask.json.dump(row, out, sort_keys=True)
                out.write('\n')
        log.debug("Dump complete")

    @fixture.option('-o', '--offset', dest='offset', default=0, type=int)
    @fixture.option('-l', '--limit', dest='limit', type=int)
    def load(offset=0, limit=None):
        import times
        infile = iter(sys.stdin)
        log_session = db.LogSession()
        for c in range(offset):
            try:
                next(infile)
            except StopIteration:
                log.info("End of file")
                return
        n = 0
        for row_json in infile:
            row = flask.json.loads(row_json)
            del row['id']
            row['time'] = times.to_universal(row['time'], 'UTC')
            record = logparser.LogRecord(**row)
            log_session.add(record)
            n += 1
            if n == limit:
                break
            if n % 100 == 0:
                log_session.flush()
        log_session.commit()
        log.info("Loaded %d rows into database", n)

    manager.add_command('fixture', fixture)
    manager.run()
