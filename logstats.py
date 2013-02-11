import os
import sys
import logging
import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy.ext.declarative import declarative_base

DEBUG = (os.environ.get('DEBUG') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG else logging.INFO)

Model = declarative_base()


class Person(Model):

    __tablename__ = 'person'
    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String)
    last_login = sa.Column(sa.DateTime)


def update_stats(session, events):
    for e in events:
        session.add(Person(uid=e['uid'], last_login=e['time']))


def create_app():
    import flask

    DATABASE = os.environ['DATABASE']

    app = flask.Flask(__name__)
    app.debug = DEBUG
    engine = sqlalchemy.create_engine(DATABASE, echo=DEBUG)
    app.extensions['db_engine'] = engine
    Session = sqlalchemy.orm.sessionmaker(bind=engine)

    @app.route('/')
    def home():
        session = Session()
        persons = session.query(Person).all()
        return flask.jsonify({
            'person': [{'uid': p.uid, 'last_login': p.last_login}
                       for p in persons],
        })

    return app


def _create_log_database_session_cls():
    LOG_DATABASE = os.environ['LOG_DATABASE']
    engine = sqlalchemy.create_engine(LOG_DATABASE)
    return sqlalchemy.orm.sessionmaker(bind=engine)


def main():
    import flask
    from flask.ext.script import Manager
    import logparser

    LogSession = _create_log_database_session_cls()

    manager = Manager(create_app)

    @manager.command
    def syncdb():
        Model.metadata.create_all(flask.current_app.extensions['db_engine'])
        logparser.Model.metadata.create_all(LogSession().bind)

    @manager.command
    def update():
        app = flask.current_app
        Session = sqlalchemy.orm.sessionmaker(bind=app.extensions['db_engine'])
        session = Session()
        log_session = LogSession()
        events = logparser.parse_sql(log_session)
        update_stats(session, events)
        session.commit()
        log_session.commit()

    fixture = Manager()

    @fixture.option('-p', '--per-page', dest='per_page', type=int)
    def dump(per_page=1000):
        log_session = LogSession()
        out = sys.stdout
        records = log_session.query(logparser.LogRecord)
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
        log_session = LogSession()
        for c in range(offset):
            next(infile)
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
        log_session.commit()
        log.debug("Loaded %d rows into database", n)

    manager.add_command('fixture', fixture)
    manager.run()


if __name__ == '__main__':
    logging.basicConfig()
    main()
