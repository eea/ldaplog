from datetime import datetime
from nose.tools import assert_equal


def _log_fixture(time, messages):
    return [(time, msg) for msg in messages.strip().splitlines()]


def _create_memory_db(metadata):
    import sqlalchemy, sqlalchemy.orm
    engine = sqlalchemy.create_engine('sqlite:///:memory:', echo=True)
    metadata.create_all(engine)
    return sqlalchemy.orm.sessionmaker(bind=engine)


def _parse_lines(lines):
    import logparser
    parser = logparser.LogParser()
    for l in lines:
        parser.handle_record(*l)
    return parser.out


def _insert_log_records(session, log_records):
    import logparser
    for time, message in log_records:
        session.add(logparser.LogRecord(time=time, message=message))


TIME = datetime(2013, 1, 27, 13, 34, 55)


LOG_ONE_BIND = _log_fixture(TIME, """
conn=1007 fd=18 ACCEPT from IP=127.0.0.1:36676 (IP=0.0.0.0:389)
conn=1007 op=2 BIND dn="uid=uzer,ou=users,o=eionet,l=europe" method=128
conn=1007 op=2 BIND dn="uid=uzer,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
conn=1007 op=2 RESULT tag=97 err=0 text=
conn=1007 op=3 UNBIND
conn=1007 fd=18 closed
""")


def test_parse_one_bind_operation():
    assert_equal(_parse_lines(LOG_ONE_BIND),
                 [{'remote_addr': '127.0.0.1', 'uid': 'uzer', 'time': TIME}])


LOG_INTERLEAVED_BINDS = _log_fixture(TIME, """
conn=1007 fd=18 ACCEPT from IP=127.0.0.1:36676 (IP=0.0.0.0:389)
conn=1008 fd=18 ACCEPT from IP=127.0.0.2:36676 (IP=0.0.0.0:389)
conn=1007 op=2 BIND dn="uid=uz1,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
conn=1008 op=2 BIND dn="uid=uz2,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0
""")


def test_parse_two_interleaved_binds():
    assert_equal(_parse_lines(LOG_INTERLEAVED_BINDS), [
        {'remote_addr': '127.0.0.1', 'uid': 'uz1', 'time': TIME},
        {'remote_addr': '127.0.0.2', 'uid': 'uz2', 'time': TIME},
    ])


def test_parse_records_from_sql():
    import logparser
    Session = _create_memory_db(logparser.Model.metadata)
    session = Session()
    _insert_log_records(session, LOG_ONE_BIND)
    assert_equal(logparser.parse_sql(session),
                 [{'remote_addr': '127.0.0.1', 'uid': 'uzer', 'time': TIME}])

def test_consumed_records_are_removed_from_sql():
    import logparser
    Session = _create_memory_db(logparser.Model.metadata)
    session = Session()
    _insert_log_records(session, LOG_ONE_BIND)
    logparser.parse_sql(session)
    assert_equal(session.query(logparser.LogRecord).all(), [])
