import os
import re
import logging
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

PARSER_DEBUG = (os.environ.get('PARSER_DEBUG') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if PARSER_DEBUG else logging.INFO)

Model = declarative_base()


class LogRecord(Model):

    __tablename__ = 'SystemEvents'

    id = sa.Column('ID', sa.Integer, primary_key=True)
    time = sa.Column('ReceivedAt', sa.DateTime)
    hostname = sa.Column('FromHost', sa.String)
    syslog_tag = sa.Column('SysLogTag', sa.String)
    message = sa.Column('Message', sa.Text)


class LogParserState(Model):

    __tablename__ = 'ldapmon_state'

    id = sa.Column(sa.Integer, primary_key=True)
    connkey = sa.Column(sa.String)
    remote_addr = sa.Column(sa.String)


class LogRowAdapter(logging.LoggerAdapter):

    def __init__(self, logger):
        self.logger = logger
        self.record_id = None

    def process(self, msg, kwargs):
        msg += ' (record.id=%r)' % self.record_id
        return (msg, kwargs)


def delete_many(session, model, id_list, per_page=100):
    for offset in range(0, len(id_list), per_page):
        page = id_list[offset:offset + per_page]
        remove_query = session.query(model).filter(model.id.in_(page))
        remove_query.delete(synchronize_session=False)


class LogParser(object):

    connection_pattern = re.compile(r'^conn=(?P<id>\d+) ')
    accept_pattern = re.compile(r' ACCEPT .* IP=(?P<addr>[^:]+):\d+ ')
    bind_pattern = re.compile(r' BIND dn="uid=(?P<uid>[^,]+),.* mech=SIMPLE ')
    close_pattern = re.compile(r' closed$')

    def __init__(self):
        self.connections = {}
        self.out = []
        self.log = LogRowAdapter(log)

    def handle_record(self, time, hostname, syslog_tag, message):
        connection_match = self.connection_pattern.search(message)
        if connection_match is None:
            log.warn("Skipping unparsed message %r", message)
            return
        connkey = ' '.join([
            connection_match.group('id'),
            hostname,
            syslog_tag,
        ])

        accept_match = self.accept_pattern.search(message)
        if accept_match:
            if connkey in self.connections:
                self.log.warning("Found ACCEPT for existing connection")
            self.connections[connkey] = {
                'remote_addr': accept_match.group('addr'),
            }
            return

        else:
            if connkey not in self.connections:
                self.log.warning("Found record with no prior ACCEPT")
                return
            conn = self.connections[connkey]

        close_match = self.close_pattern.search(message)
        if close_match:
            del self.connections[connkey]
            return

        bind_match = self.bind_pattern.search(message)
        if bind_match:
            event = {
                'time': time,
                'hostname': hostname,
                'remote_addr': conn['remote_addr'],
                'uid': bind_match.group('uid'),
            }
            self.out.append(event)
            return

    def parse_sql(self, session):
        for row in session.query(LogParserState):
            self.connections[row.connkey] = {
                'remote_addr': row.remote_addr,
            }
        session.query(LogParserState).delete()
        self.log.debug("Done loading existing connections: %r",
                       self.connections.keys())

        to_remove = []

        for record in session.query(LogRecord).order_by('id'):
            self.log.record_id = record.id
            self.handle_record(record.time, record.hostname,
                               record.syslog_tag, record.message.strip())
            to_remove.append(record.id)

        delete_many(session, LogRecord, to_remove)

        self.log.debug("Dumping existing connections: %r",
                       self.connections.keys())
        session.add_all([LogParserState(connkey=connkey,
                                        remote_addr=conn['remote_addr'])
                         for connkey, conn in self.connections.iteritems()])


_to_dict = lambda row: {c.name: getattr(row, c.name)
                        for c in row.__table__.columns}


def parse_sql(session):
    parser = LogParser()
    parser.parse_sql(session)
    return parser.out
