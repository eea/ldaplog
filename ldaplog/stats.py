import os
import logging
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

LOGSTATS_DEBUG = (os.environ.get('LOGSTATS_DEBUG') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if LOGSTATS_DEBUG else logging.INFO)

Model = declarative_base()


class Person(Model):

    __tablename__ = 'person'
    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), unique=True)
    last_login = sa.Column(sa.DateTime)

    @classmethod
    def with_uid(cls, uid, session):
        person = session.query(cls).filter_by(uid=uid).first()
        if person:
            return person
        else:
            person = Person(uid=uid)
            session.add(person)
            return person


class Login(Model):

    __tablename__ = 'login'
    id = sa.Column(sa.Integer, primary_key=True)
    time = sa.Column(sa.DateTime)
    success = sa.Column(sa.Boolean)
    hostname = sa.Column(sa.String(128))
    remote = sa.Column(sa.String(128))


def update_stats(session, events):
    for e in events:
        if e['success']:
            Person.with_uid(e['uid'], session).last_login = e['time']
        session.add(Login(time=e['time'],
                          success=e['success'],
                          hostname=e['hostname'],
                          remote=e['remote_addr']))
