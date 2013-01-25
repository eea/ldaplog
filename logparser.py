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
    host = sa.Column('FromHost', sa.String)
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

    def __init__(self):
        self.connections = {}
        self.out = []
        self.log = LogRowAdapter(log)

    def handle_record(self, time, message):
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

        bind_match = self.bind_pattern.search(message)
        if bind_match:
            event = {
                'time': time,
                'remote_addr': conn['remote_addr'],
                'uid': bind_match.group('uid'),
            }
            self.out.append(event)
            return

    def load_state(self, state):
        self.log.debug("Loading state %r", state)
        for row in state:
            self.connections[row['connection_id']] = {
                'remote_addr': row['remote_addr'],
            }

    def dump_state(self):
        state = [{'connection_id': k, 'remote_addr': v['remote_addr']}
                 for k, v in self.connections.items()]
        self.log.debug("Dumping state %r", state)
        return state

    def parse_sql(self, session):
        to_remove = []

        self.load_state([_to_dict(row) for row in session.query(LogParserState)])
        session.query(LogParserState).delete()

        for record in session.query(LogRecord):
            self.log.record_id = record.id
            self.handle_record(record.time, record.message)
            to_remove.append(record.id)

        to_remove = session.query(LogRecord).filter(LogRecord.id.in_(to_remove))
        to_remove.delete(synchronize_session=False)

        session.add_all([LogParserState(**conn) for conn in self.dump_state()])


_to_dict = lambda row: {c.name: getattr(row, c.name)
                        for c in row.__table__.columns}


def parse_sql(session):
    parser = LogParser()
    parser.parse_sql(session)
    return parser.out
