# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from nose.tools import assert_equal
import unittest
from utils import create_memory_db
from ldaplog import stats

import os.path
TESTS_DIR = os.path.dirname(__file__)

TIME = datetime(2013, 1, 27, 13, 34, 55)
TIME2 = datetime(2014, 1, 27, 13, 34, 55)


def _create_session():
    Session = create_memory_db(stats.Model.metadata)
    return Session()


def test_event_updates_last_login():
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


class TestPerson(unittest.TestCase):
    def setUp(self):
        self.fields = [ c.name for c in stats.Person.__table__.columns if c.name not in ['id'] ]
        self.session = _create_session()

    def test_export_excel_prepare_data_latin(self):
        user = u'uzerâ'.encode('latin1')
        stats.update_stats(self.session, [
            {'uid': user,
            'time': TIME,
            'success': True,
            'hostname': 'ldap2',
            'remote_addr': '10.0.0.2'},
        ])
        persons = self.session.query(stats.Person).all()
        expected = [[user.decode('latin1').encode('utf8'), str(TIME)]]
        results = []
        for person in persons:
            results.append(person.prepare_export_row(self.fields))
        self.assertEqual(results, expected)

    def test_export_excel_prepare_data(self):
        stats.update_stats(self.session, [
            {'uid': 'uzer',
            'time': TIME,
            'success': True,
            'hostname': 'ldap2',
            'remote_addr': '10.0.0.2'},
            {'uid': 'uzer2',
            'time': TIME,
            'success': True,
            'hostname': 'ldap2',
            'remote_addr': '10.0.0.2'},
            {'uid': 'uzer2',
            'time': TIME2,
            'success': True,
            'hostname': 'ldap2',
            'remote_addr': '10.0.0.2'},
        ])
        persons = self.session.query(stats.Person).all()
        expected = [['uzer', str(TIME)], ['uzer2', str(TIME2)]]
        results = []
        for person in persons:
            results.append(person.prepare_export_row(self.fields))
        self.assertEqual(results, expected)

    def test_export_excel(self):
        from ldaplog.tools import create_excel
        rows =  ( r for r in [[u'uzerâ'.encode('utf8'), str(TIME)], ['uzer2', str(TIME2)]] )
        xls = create_excel('tst_excel_export', self.fields, rows)
        expected = open(os.path.join(TESTS_DIR, 'person.xls'), 'r').read()
        self.assertEqual(xls, expected)
