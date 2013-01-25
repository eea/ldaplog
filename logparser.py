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


class LogParser(object):

    connection_pattern = re.compile(r'^conn=(?P<id>\d+) ')
    accept_pattern = re.compile(r' ACCEPT .* IP=(?P<addr>[^:]+):\d+ ')
    bind_pattern = re.compile(r' BIND dn="uid=(?P<uid>[^,]+),.* mech=SIMPLE ')

    def __init__(self):
        self.connections = {}
        self.out = []

    def handle_record(self, time, message):
        connection_match = self.connection_pattern.search(message)
        connection_id = connection_match.group('id')

        accept_match = self.accept_pattern.search(message)
        if accept_match:
            if connection_id in self.connections:
                log.warn("Found ACCEPT for existing connection")
            self.connections[connection_id] = {
                'remote_addr': accept_match.group('addr'),
            }
            return

        else:
            if connection_id not in self.connections:
                log.warn("Found record for connection with no prior ACCEPT")
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


def parse_sql(session):
    parser = LogParser()
    to_remove = []
    query = session.query(LogRecord)

    for record in query:
        parser.handle_record(record.time, record.message)
        to_remove.append(record.id)

    rows_to_remove = query.filter(LogRecord.id.in_(to_remove))
    rows_to_remove.delete(synchronize_session=False)

    return parser.out
