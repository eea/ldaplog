import re
import logging
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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
    connection_id = sa.Column(sa.Integer)
    remote_addr = sa.Column(sa.String)


class LogRowAdapter(logging.LoggerAdapter):

    def __init__(self, logger):
        self.logger = logger
        self.record_id = None

    def process(self, msg, kwargs):
        msg += ' (record.id=%r)' % self.record_id
        return (msg, kwargs)


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
        connection_id = int(connection_match.group('id'))

        accept_match = self.accept_pattern.search(message)
        if accept_match:
            if connection_id in self.connections:
                self.log.warning("Found ACCEPT for existing connection")
            self.connections[connection_id] = {
                'remote_addr': accept_match.group('addr'),
            }
            return

        else:
            if connection_id not in self.connections:
                self.log.warning("Found record with no prior ACCEPT")
                return
            conn = self.connections[connection_id]

        close_match = self.close_pattern.search(message)
        if close_match:
            del self.connections[connection_id]
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
            self.connections[row.connection_id] = {
                'remote_addr': row.remote_addr,
            }
        session.query(LogParserState).delete()
        self.log.debug("Done loading existing connections: %r",
                       self.connections.keys())

        to_remove = []

        for record in session.query(LogRecord):
            self.log.record_id = record.id
            self.handle_record(record.time, record.hostname,
                               record.syslog_tag, record.message)
            to_remove.append(record.id)

        to_remove = session.query(LogRecord).filter(LogRecord.id.in_(to_remove))
        to_remove.delete(synchronize_session=False)

        self.log.debug("Dumping existing connections: %r",
                       self.connections.keys())
        session.add_all([LogParserState(connection_id=conn_id,
                                        remote_addr=conn['remote_addr'])
                         for conn_id, conn in self.connections.iteritems()])


_to_dict = lambda row: {c.name: getattr(row, c.name)
                        for c in row.__table__.columns}


def parse_sql(session):
    parser = LogParser()
    parser.parse_sql(session)
    return parser.out
