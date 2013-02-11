import os
import sys
import logging
import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy.ext.declarative import declarative_base

DEBUG = (os.environ.get('DEBUG') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG else logging.INFO)

Model = declarative_base()


class Person(Model):

    __tablename__ = 'person'
    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String)
    last_login = sa.Column(sa.DateTime)


def update_stats(session, events):
    for e in events:
        session.add(Person(uid=e['uid'], last_login=e['time']))


def create_app():
    import flask

    DATABASE = os.environ['DATABASE']

    app = flask.Flask(__name__)
    app.debug = DEBUG
    engine = sqlalchemy.create_engine(DATABASE, echo=DEBUG)
    app.extensions['db_engine'] = engine
    Session = sqlalchemy.orm.sessionmaker(bind=engine)

    @app.route('/')
    def home():
        session = Session()
        persons = session.query(Person).all()
        return flask.jsonify({
            'person': [{'uid': p.uid, 'last_login': p.last_login}
                       for p in persons],
        })

    return app


def main():
    import flask
    from flask.ext.script import Manager

    manager = Manager(create_app)

    @manager.command
    def syncdb():
        engine = flask.current_app.extensions['db_engine']
        Model.metadata.create_all(engine)

    manager.run()


if __name__ == '__main__':
    logging.basicConfig()
    main()
