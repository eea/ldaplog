from datetime import datetime
from nose.tools import assert_equal, assert_dict_contains_subset
from utils import create_memory_db


def assert_records_match(a, b):
    assert_equal(len(a), len(b))
    for ax, bx in zip(a, b):
        assert_dict_contains_subset(bx, ax)


def _log_fixture(time, hostname, messages):
    return [(time, hostname, 'slapd[41]:', msg)
            for msg in messages.strip().splitlines()]


def _parse_lines(lines):
    import logparser
    parser = logparser.LogParser()
    for l in lines:
        parser.handle_record(*l)
    return parser.out


def _insert_log_records(session, log_records):
    import logparser
    for time, hostname, syslog_tag, message in log_records:
        kwargs = {
            'time': time,
            'hostname': hostname,
            'syslog_tag': syslog_tag,
            'message': message,
        }
        session.add(logparser.LogRecord(**kwargs))


TIME = datetime(2013, 1, 27, 13, 34, 55)


LOG_ONE_BIND = _log_fixture(TIME, 'ldap2', """
conn=1007 fd=18 ACCEPT from IP=127.0.0.1:36676 (IP=0.0.0.0:389)
conn=1007 op=2 BIND dn="uid=uzer,ou=users,o=eionet,l=europe" method=128
conn=1007 op=2 BIND dn="uid=uzer,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
conn=1007 op=2 RESULT tag=97 err=0 text=
conn=1007 op=3 UNBIND
conn=1007 fd=18 closed
""")


def test_parse_one_bind_operation():
    assert_records_match(_parse_lines(LOG_ONE_BIND), [
        {'hostname': 'ldap2',
         'remote_addr': '127.0.0.1',
         'uid': 'uzer',
         'time': TIME},
    ])


LOG_INTERLEAVED_BINDS = _log_fixture(TIME, 'ldap2', """
conn=1007 fd=18 ACCEPT from IP=127.0.0.1:36676 (IP=0.0.0.0:389)
conn=1008 fd=18 ACCEPT from IP=127.0.0.2:36676 (IP=0.0.0.0:389)
conn=1007 op=2 BIND dn="uid=uz1,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
conn=1008 op=2 BIND dn="uid=uz2,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
""")


def test_parse_two_interleaved_binds():
    assert_records_match(_parse_lines(LOG_INTERLEAVED_BINDS), [
        {'remote_addr': '127.0.0.1', 'uid': 'uz1', 'time': TIME},
        {'remote_addr': '127.0.0.2', 'uid': 'uz2', 'time': TIME},
    ])


LOG_REUSED_CONNECTION_ID = _log_fixture(TIME, 'ldap2', """
conn=1007 fd=18 ACCEPT from IP=127.0.0.1:36676 (IP=0.0.0.0:389)
conn=1007 op=2 BIND dn="uid=uz1,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
conn=1007 fd=18 closed
conn=1007 fd=19 ACCEPT from IP=127.0.0.2:36676 (IP=0.0.0.0:389)
conn=1007 op=2 BIND dn="uid=uz2,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
""")


def test_connection_ids_can_be_reused():
    assert_records_match(_parse_lines(LOG_REUSED_CONNECTION_ID), [
        {'remote_addr': '127.0.0.1', 'uid': 'uz1', 'time': TIME},
        {'remote_addr': '127.0.0.2', 'uid': 'uz2', 'time': TIME},
    ])


def test_parse_records_from_sql():
    import logparser
    Session = create_memory_db(logparser.Model.metadata)
    session = Session()
    _insert_log_records(session, LOG_ONE_BIND)
    assert_records_match(logparser.parse_sql(session), [
        {'remote_addr': '127.0.0.1', 'uid': 'uzer', 'time': TIME},
    ])

def test_consumed_records_are_removed_from_sql():
    import logparser
    Session = create_memory_db(logparser.Model.metadata)
    session = Session()
    _insert_log_records(session, LOG_ONE_BIND)
    logparser.parse_sql(session)
    assert_records_match(session.query(logparser.LogRecord).all(), [])


LOG_CHUNKS_1 = _log_fixture(TIME, 'ldap2', """
conn=1007 fd=18 ACCEPT from IP=127.0.0.1:36676 (IP=0.0.0.0:389)
""")

LOG_CHUNKS_2 = _log_fixture(TIME, 'ldap2', """
conn=1007 op=2 BIND dn="uid=uzer,ou=users,o=eionet,l=europe" method=128
conn=1007 op=2 BIND dn="uid=uzer,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
conn=1007 op=2 RESULT tag=97 err=0 text=
conn=1007 op=3 UNBIND
conn=1007 fd=18 closed
""")

def test_state_is_saved_for_unclosed_connections():
    import logparser
    Session = create_memory_db(logparser.Model.metadata)
    session = Session()
    _insert_log_records(session, LOG_CHUNKS_1)
    assert_records_match(logparser.parse_sql(session), [])
    assert_equal(session.query(logparser.LogParserState).count(), 1)
    _insert_log_records(session, LOG_CHUNKS_2)
    assert_records_match(logparser.parse_sql(session), [
        {'remote_addr': '127.0.0.1', 'uid': 'uzer', 'time': TIME},
    ])
    assert_equal(session.query(logparser.LogParserState).count(), 0)


HOST1 = 'ldap1'
HOST2 = 'ldap2'
PID41 = 'slapd[41]:'
PID88 = 'slapd[88]:'
IP1 = '10.0.0.1'
IP2 = '10.0.0.2'
IP3 = '10.0.0.3'

LOG_MIXED_SOURCES = [
    (TIME, HOST1, PID41, 'conn=1007 fd=18 ACCEPT from IP=' + IP1 +
                         ':36676 (IP=0.0.0.0:389)'),
    (TIME, HOST2, PID41, 'conn=1007 fd=18 ACCEPT from IP=' + IP2 +
                         ':36676 (IP=0.0.0.0:389)'),
    (TIME, HOST1, PID88, 'conn=1007 fd=18 ACCEPT from IP=' + IP3 +
                         ':36676 (IP=0.0.0.0:389)'),

    (TIME, HOST1, PID41, 'conn=1007 op=2 BIND dn="uid=uzer,ou=Users,'
                         'o=EIONET,l=Europe" mech=SIMPLE ssf=0'),
    (TIME, HOST2, PID41, 'conn=1007 op=2 BIND dn="uid=uzer,ou=Users,'
                         'o=EIONET,l=Europe" mech=SIMPLE ssf=0'),
    (TIME, HOST1, PID88, 'conn=1007 op=2 BIND dn="uid=uzer,ou=Users,'
                         'o=EIONET,l=Europe" mech=SIMPLE ssf=0'),

    (TIME, HOST1, PID41, 'conn=1007 op=2 RESULT tag=97 err=0 text='),
    (TIME, HOST2, PID41, 'conn=1007 op=2 RESULT tag=97 err=0 text='),
    (TIME, HOST1, PID88, 'conn=1007 op=2 RESULT tag=97 err=0 text='),
]


def test_discriminate_host_and_pid_with_same_connid():
    assert_records_match(_parse_lines(LOG_MIXED_SOURCES), [
        {'hostname': HOST1, 'remote_addr': IP1},
        {'hostname': HOST2, 'remote_addr': IP2},
        {'hostname': HOST1, 'remote_addr': IP3},
    ])
