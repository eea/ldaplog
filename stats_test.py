from datetime import datetime
from nose.tools import assert_equal
from testing_utils import create_memory_db


TIME = datetime(2013, 1, 27, 13, 34, 55)


def test_event_updates_last_login():
    import logstats
    Session = create_memory_db(logstats.Model.metadata)
    session = Session()
    logstats.update_stats(session, [{'uid': 'uzer', 'time': TIME}])
    persons = session.query(logstats.Person).all()
    assert_equal([(p.uid, p.last_login) for p in persons], [('uzer', TIME)])
