import re
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

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
        conn = self.connections.setdefault(connection_match.group('id'), {})

        accept_match = self.accept_pattern.search(message)
        if accept_match:
            conn['remote_addr'] = accept_match.group('addr')
            return

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
    for record in session.query(LogRecord):
        parser.handle_record(record.time, record.message)
    return parser.out
