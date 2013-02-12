from datetime import datetime, timedelta
from nose.tools import assert_equal
from utils import create_memory_db


TIME = datetime(2013, 1, 27, 13, 34, 55)


def _create_session():
    from ldaplog import stats
    Session = create_memory_db(stats.Model.metadata)
    return Session()


def test_event_updates_last_login():
    from ldaplog import stats
    session = _create_session()
    stats.update_stats(session, [
        {'uid': 'uzer',
         'time': TIME,
         'success': True,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.2'},
    ])
    persons = session.query(stats.Person).all()
    assert_equal([(p.uid, p.last_login) for p in persons], [('uzer', TIME)])


def test_failed_bind_does_not_update_last_login():
    from ldaplog import stats
    session = _create_session()
    stats.update_stats(session, [
        {'uid': 'uzer',
         'time': TIME,
         'success': False,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.2'},
    ])
    persons = session.query(stats.Person).all()
    assert_equal([(p.uid, p.last_login) for p in persons], [])


def test_after_multiple_logins_only_last_is_saved():
    from ldaplog import stats
    session = _create_session()
    stats.update_stats(session, [
        {'uid': 'uzer',
         'time': TIME - timedelta(seconds=2),
         'success': True,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.2'},
        {'uid': 'uzer',
         'time': TIME,
         'success': True,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.2'},
    ])
    persons = session.query(stats.Person).all()
    assert_equal([(p.uid, p.last_login) for p in persons], [('uzer', TIME)])


def test_log_bind_attempts_for_each_server():
    from ldaplog import stats
    t1 = TIME + timedelta(seconds=1)
    t2 = TIME + timedelta(seconds=2)
    session = _create_session()
    stats.update_stats(session, [
        {'uid': 'uzer',
         'time': t1,
         'success': True,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.2'},
        {'uid': 'uzer',
         'time': t1,
         'success': True,
         'hostname': 'ldap3',
         'remote_addr': '10.0.0.3'},
        {'uid': 'uzer',
         'time': t2,
         'success': True,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.4'},
    ])
    logins = session.query(stats.Login).all()
    assert_equal([(b.time, b.hostname, b.remote) for b in logins], [
        (t1, 'ldap2', '10.0.0.2'),
        (t1, 'ldap3', '10.0.0.3'),
        (t2, 'ldap2', '10.0.0.4'),
    ])


def test_log_bind_success_status():
    from ldaplog import stats
    session = _create_session()
    stats.update_stats(session, [
        {'uid': 'uzer',
         'time': TIME,
         'success': True,
         'hostname': 'ldap1',
         'remote_addr': '10.0.0.2'},
        {'uid': 'uzer',
         'time': TIME,
         'success': False,
         'hostname': 'ldap2',
         'remote_addr': '10.0.0.2'},
    ])
    logins = session.query(stats.Login).all()
    assert_equal([(b.hostname, b.success) for b in logins], [
        ('ldap1', True),
        ('ldap2', False),
    ])
