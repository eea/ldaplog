import os
import re
import logging
import logging.handlers
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

PARSER_DEBUG = (os.environ.get('PARSER_DEBUG') == 'on')
PARSER_DEBUG_LOG = os.environ.get('PARSER_DEBUG_LOG')
PARSER_CHUNK = int(os.environ.get('PARSER_CHUNK', 1000))

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if PARSER_DEBUG else logging.INFO)

if PARSER_DEBUG_LOG:
    _debug_handler = logging.handlers.WatchedFileHandler(PARSER_DEBUG_LOG)
    _debug_handler.setLevel(logging.DEBUG)
    log.addHandler(_debug_handler)


Model = declarative_base()


class LogRecord(Model):

    __tablename__ = 'SystemEvents'

    id = sa.Column('ID', sa.Integer, primary_key=True)
    time = sa.Column('ReceivedAt', sa.DateTime)
    hostname = sa.Column('FromHost', sa.String(128))
    syslog_tag = sa.Column('SysLogTag', sa.String(128))
    message = sa.Column('Message', sa.Text)


class LogParserState(Model):

    __tablename__ = 'ldapmon_state'

    id = sa.Column(sa.Integer, primary_key=True)
    connkey = sa.Column(sa.String(100))
    remote_addr = sa.Column(sa.String(100))


class LogRowAdapter(logging.LoggerAdapter):

    def __init__(self, logger):
        self.logger = logger
        self.record_id = None

    def process(self, msg, kwargs):
        extra = kwargs.setdefault('extra', {})
        extra.setdefault('data', {})['record.id'] = self.record_id
        return (msg, kwargs)


def delete_many(session, model, id_list, per_page=100):
    for offset in range(0, len(id_list), per_page):
        page = id_list[offset:offset + per_page]
        remove_query = session.query(model).filter(model.id.in_(page))
        remove_query.delete(synchronize_session=False)


class LogParser(object):

    connection_pattern = re.compile(r'^conn=(?P<id>\d+) ')
    accept_pattern = re.compile(r' ACCEPT .* IP=(?P<addr>.+):\d+ ')
    bind_pattern = re.compile(r' BIND dn="uid=(?P<uid>[^,]+),.* ')
    close_pattern = re.compile(r' closed$')
    result_pattern = re.compile(r' RESULT tag=97 err=(?P<err>\d+) ')
    skip_patterns = [
        re.compile(r'^daemon: shutdown requested and initiated\.$'),
        re.compile(r'^slapd shutdown: waiting'),
        re.compile(r'^slapd stopped.$'),
        re.compile(r'^slapd starting$'),
        re.compile(r'^@\(\#\) \$OpenLDAP: slapd \d+.\d+.\d+ '),
        re.compile(r'^bdb_monitor_db_open: monitoring disabled'),
        re.compile(r'bdb_substring_candidates.* not indexed'),
    ]

    def __init__(self):
        self.connections = {}
        self.out = []
        self.log = LogRowAdapter(log)

    def handle_record(self, time, hostname, syslog_tag, message):
        connection_match = self.connection_pattern.search(message)
        if connection_match is None:
            if not any(p.search(message) for p in self.skip_patterns):
                self.log.warning("Skipping unparsed message %r", message)
            return
        connkey = ' '.join([
            connection_match.group('id'),
            hostname,
            syslog_tag,
        ])

        def register_connection(remote_addr):
            self.connections[connkey] = {
                'remote_addr': remote_addr,
            }

        accept_match = self.accept_pattern.search(message)
        if accept_match:
            if connkey in self.connections:
                self.log.warning("Found ACCEPT for existing connection")
            register_connection(accept_match.group('addr'))
            return

        else:
            if connkey not in self.connections:
                self.log.warning("Found record with no prior ACCEPT")
                register_connection('unknown')
            conn = self.connections[connkey]

        close_match = self.close_pattern.search(message)
        if close_match:
            del self.connections[connkey]
            return

        bind_match = self.bind_pattern.search(message)
        if bind_match:
            conn['bind'] = {
                'time': time,
                'hostname': hostname,
                'remote_addr': conn['remote_addr'],
                'uid': bind_match.group('uid'),
            }
            return

        bind_event = conn.pop('bind', None)
        result_match = self.result_pattern.search(message)
        if result_match and bind_event is not None:
            bind_event['success'] = (result_match.group('err') == '0')
            self.out.append(bind_event)
            return

    def parse_sql(self, session):
        for row in session.query(LogParserState):
            self.connections[row.connkey] = {
                'remote_addr': row.remote_addr,
            }
        session.query(LogParserState).delete()
        self.log.debug("Done loading existing connections: %r",
                       self.connections.keys())

        records = session.query(LogRecord).order_by('id')
        count = records.count()
        more = count > PARSER_CHUNK
        to_remove = []
        log.info("Fetching %d records out of %d...", PARSER_CHUNK, count)
        for record in records.limit(PARSER_CHUNK):
            self.log.record_id = record.id
            if isinstance(record.message, str):
                record.message = unicode(record.message, 'utf8')
            self.handle_record(record.time, record.hostname,
                               record.syslog_tag, record.message.strip())
            to_remove.append(record.id)

        delete_many(session, LogRecord, to_remove)

        self.log.debug("Dumping existing connections: %r",
                       self.connections.keys())
        session.add_all([LogParserState(connkey=connkey,
                                        remote_addr=conn['remote_addr'])
                         for connkey, conn in self.connections.iteritems()])
        return more


_to_dict = lambda row: {c.name: getattr(row, c.name)
                        for c in row.__table__.columns}


def parse_sql(session):
    parser = LogParser()
    more = parser.parse_sql(session)
    return parser.out, more
