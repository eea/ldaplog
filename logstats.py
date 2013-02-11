import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

Model = declarative_base()


class Person(Model):

    __tablename__ = 'person'
    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String)
    last_login = sa.Column(sa.DateTime)


def update_stats(session, events):
    for e in events:
        session.add(Person(uid=e['uid'], last_login=e['time']))
