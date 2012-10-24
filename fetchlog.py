import os
import re
import logging
from peewee import (Model, MySQLDatabase,
                    TextField, IntegerField, DateTimeField, CharField)


log = logging.getLogger(__name__)


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


class DBAgent(object):

    SYSLOG_TAG_PREFIX = 'slapd['

    def __init__(self, database_uri):
        db_pattern = re.compile(r'^mysql\://'
                                r'(?P<user>[^\:]+)\:'
                                r'(?P<passwd>[^\:]+)@'
                                r'(?P<host>[^/]+)/'
                                r'(?P<database>.*)$')
        db.init(**db_pattern.match(database_uri).groupdict())

    def get_ldap_messages(self, remove=False):
        message_pattern = re.compile(r'^conn=(?P<conn>\d+)\s')
        query = LogRow.select()
        strip_map = {}
        strips = []
        rows_to_remove = []

        for row in query:
            if not row.syslog_tag.startswith(self.SYSLOG_TAG_PREFIX):
                rows_to_remove.append(row.id)
                continue

            message = row.message.strip()
            m = message_pattern.match(message)
            if m is None:
                if message.endswith(' not indexed'):
                    rows_to_remove.append(row.id)
                    continue
                raise RuntimeError("Can't parse message %r" % message)

            conn_id = int(m.group('conn'))

            if ' ACCEPT ' in message:
                if conn_id in strip_map:
                    raise RuntimeError("Found 'ACCEPT' for a "
                                       "connection that is in progress")
                strip_map[conn_id] = []

            else:
                if conn_id not in strip_map:
                    raise RuntimeError("Found log message for a connection "
                                       "with no prior ACCEPT")

            strip_map[conn_id].append({'message': message, 'id': row.id})

            if ' closed (connection lost)' in message:
                this_conn = strip_map.pop(conn_id)
                strips.append(this_conn)
                rows_to_remove.extend(item['id'] for item in this_conn)
                log.debug('%d messages in %d', len(this_conn), conn_id)

        log.debug('open connections: %r', list(strip_map))
        log.debug('log entries to remove: %r', rows_to_remove)
        strips.extend(strip_map.values())

        if remove and rows_to_remove:
            with db.transaction():
                count = LogRow.delete().filter(id__in=rows_to_remove).execute()
                if count != len(rows_to_remove):
                    log.warn("Tried to remove %d rows but %d were removed",
                             len(rows_to_remove), count)

        return strips


def demo():
    dba = DBAgent(os.environ['DATABASE_URI'])
    strips = dba.get_ldap_messages(remove=True)
    from pprint import pprint as pp
    pp(strips)


if __name__ == '__main__':
    LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"
    logging.getLogger('peewee.logger').setLevel(logging.INFO)
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
    demo()
