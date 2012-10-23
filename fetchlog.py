import os
import re
from peewee import (Model, MySQLDatabase,
                    TextField, IntegerField, DateTimeField, CharField)


db = MySQLDatabase(None)


class LogRow(Model):

    id = IntegerField(db_column='ID', primary_key=True)
    message = TextField(db_column='Message')
    time = DateTimeField(db_column='ReceivedAt')
    host = CharField(db_column='FromHost')
    syslog_tag = CharField(db_column='SysLogTag')

    class Meta:
        database = db
        db_table = 'SystemEvents'


def demo():
    db_pattern = re.compile(r'^mysql\://'
                            r'(?P<user>[^\:]+)\:'
                            r'(?P<passwd>[^\:]+)@'
                            r'(?P<host>[^/]+)/'
                            r'(?P<database>.*)$')
    db.init(**db_pattern.match(os.environ['DATABASE_URI']).groupdict())
    message_pattern = re.compile(r'^conn=(?P<conn>\d+)\s')
    query = LogRow.select()
    connection = {}
    for row in query:
        message = row.message.strip()
        m = message_pattern.match(message)
        if m is None:
            continue
        conn_id = int(m.group('conn'))

        if ' ACCEPT ' in message:
            assert conn_id not in connection
            connection[conn_id] = []

        else:
            assert conn_id in connection
            connection[conn_id].append({'message': message})

            if ' closed (connection lost)' in message:
                this_conn = connection.pop(conn_id)
                print '%d messages in %d' % (len(this_conn), conn_id)

    print 'open connections: %r' % list(connection)


if __name__ == '__main__':
    demo()
