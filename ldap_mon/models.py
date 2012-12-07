from django.db import models
from django.conf import settings
from datetime import datetime
import re
import logging


logger = logging.getLogger('ldap_mon.models')


class Server(models.Model):

    host = models.CharField(max_length=512)

    def __unicode__(self):
        return self.host


class User(models.Model):

    username = models.CharField(max_length=256)

    def __unicode__(self):
        return self.username


class Log(models.Model):

    class Meta:
        unique_together = ('user', 'server')

    user = models.ForeignKey(User)
    server = models.ForeignKey(Server)
    date = models.DateTimeField()

    def __unicode__(self):
        return '{} {} - {}'.format(self.user, self.server, self.date)

    @classmethod
    def add(cls, data):
        assert 'date' in data
        date = datetime.strptime(data['date'], '%Y-%m-%d %H:%M:%S')
        server, server_created = Server.objects.get_or_create(host=data['server'])
        user, user_created = User.objects.get_or_create(username=data['user_id'])
        log, log_created= cls.objects.get_or_create(user=user, server=server,
                                                    defaults={'date': date})
        if not log_created and log.date < date:
            log.date = date
            log.save()
        logger.debug('Log added %s' % log)


SERVER_PATTERN = re.compile(r"""
    conn=(?P<conn_id>[0-9]+)
    \s.+\s
    ACCEPT\sfrom\sIP=(?P<server>.+):(?P<port>\d+)\s
    """, re.X)


BIND_PATTERN = re.compile(r"""
    conn=(?P<conn_id>[0-9]+)
    \s.+\s
    BIND\sdn="uid=(?P<user_id>[a-zA-Z0-9]+)
    """, re.X)


def parse_message(data):

    assert isinstance(data, list)

    server = {}
    for item in data:
        resp = dict(item)
        server_search = re.search(SERVER_PATTERN, item['message'])
        bind_search = re.search(BIND_PATTERN, item['message'])

        if server_search:
            server_search_data = server_search.groupdict()
            server[server_search_data['conn_id']] = server_search_data['server']

        if bind_search:
            resp.update(bind_search.groupdict())
            if server.get(resp['conn_id']):
                resp['server'] = server.get(resp['conn_id'])
                Log.add(resp)


def fetch_and_parse(remove=False):
    from fetchlog import DBAgent
    dba = DBAgent(settings.RSYSLOG_DATABASE_URI)
    for strip in dba.get_ldap_messages(remove=remove):
        logger.debug("parsing strip of %d events", len(strip))
        parse_message(strip)
