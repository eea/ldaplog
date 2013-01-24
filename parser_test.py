import unittest
from datetime import datetime
from nose.tools import assert_equal


def _log_fixture(time, messages):
    return [(time, msg) for msg in messages.strip().splitlines()]

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
    assert_equal(parse(LOG_ONE_BIND),
                 [{'remote_addr': '127.0.0.1', 'uid': 'uzer', 'time': TIME}])


import re

_accept_pattern = re.compile(r' ACCEPT .* IP=(?P<addr>[^:]+):\d+ ')
_bind_pattern  = re.compile(r' BIND dn="uid=(?P<uid>[^,]+),.* mech=SIMPLE ')

def parse(log_records):
    out = []
    state = {}

    for time, message in log_records:
        accept_match = _accept_pattern.search(message)
        if accept_match:
            state['remote_addr'] = accept_match.group('addr')
            continue

        bind_match = _bind_pattern.search(message)
        if bind_match:
            event = {
                'time': time,
                'remote_addr': state['remote_addr'],
                'uid': bind_match.group('uid'),
            }
            out.append(event)
            continue

    return out
