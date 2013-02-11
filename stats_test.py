from datetime import datetime, timedelta
from nose.tools import assert_equal
from testing_utils import create_memory_db


TIME = datetime(2013, 1, 27, 13, 34, 55)


def _create_session():
    import logstats
    Session = create_memory_db(logstats.Model.metadata)
    return Session()


def test_event_updates_last_login():
    import logstats
    session = _create_session()
    logstats.update_stats(session, [{'uid': 'uzer', 'time': TIME}])
    persons = session.query(logstats.Person).all()
    assert_equal([(p.uid, p.last_login) for p in persons], [('uzer', TIME)])


def test_after_multiple_logins_only_last_is_saved():
    import logstats
    session = _create_session()
    logstats.update_stats(session, [
        {'uid': 'uzer', 'time': TIME - timedelta(seconds=2)},
        {'uid': 'uzer', 'time': TIME},
    ])
    persons = session.query(logstats.Person).all()
    assert_equal([(p.uid, p.last_login) for p in persons], [('uzer', TIME)])
