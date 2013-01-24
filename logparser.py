import re

_connection_pattern = re.compile(r'^conn=(?P<id>\d+) ')
_accept_pattern = re.compile(r' ACCEPT .* IP=(?P<addr>[^:]+):\d+ ')
_bind_pattern  = re.compile(r' BIND dn="uid=(?P<uid>[^,]+),.* mech=SIMPLE ')

def parse(log_records):
    out = []
    connections = {}

    for time, message in log_records:
        connection_match = _connection_pattern.search(message)
        conn = connections.setdefault(connection_match.group('id'), {})

        accept_match = _accept_pattern.search(message)
        if accept_match:
            conn['remote_addr'] = accept_match.group('addr')
            continue

        bind_match = _bind_pattern.search(message)
        if bind_match:
            event = {
                'time': time,
                'remote_addr': conn['remote_addr'],
                'uid': bind_match.group('uid'),
            }
            out.append(event)
            continue

    return out
