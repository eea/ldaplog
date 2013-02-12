from werkzeug.local import LocalProxy
import sys
import logging
import flask
from flask.ext.script import Manager
from . import logparser

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

db = LocalProxy(lambda: flask.current_app.extensions['db'])
fixture = Manager()


@fixture.option('-p', '--per-page', dest='per_page', type=int)
def dump(per_page=1000):
    log_session = db.LogSession()
    out = sys.stdout
    records = log_session.query(logparser.LogRecord).order_by('id')
    n = records.count()
    log.info("Dumping %d records (%d per page)", n, per_page)
    for offset in range(0, n, per_page):
        records_page = records.offset(offset).limit(per_page)
        log.info("Offset %d ...", offset)
        for record in records_page:
            row = {k: unicode(getattr(record, k)) for k in
                   ['id', 'time', 'hostname', 'syslog_tag', 'message']}
            flask.json.dump(row, out, sort_keys=True)
            out.write('\n')
    log.info("Dump complete")


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
