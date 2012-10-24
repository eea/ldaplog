import re

DATA = [
    {'message': 'conn=1001 fd=16 ACCEPT from IP=127.0.0.1:58286 (IP=0.0.0.0:389)'},
    {'message': 'conn=1001 op=0 BIND dn="" method=128'},
    {'message': 'conn=1001 op=0 RESULT tag=97 err=0 text='},
    {'message': 'conn=1001 op=1 SRCH base="ou=Users,o=EIONET,l=Europe" scope=2 deref=0 filter="(&(objectClass=top)(objectClass=person)(uid=simiamih))"'},
    {'message': 'conn=1001 op=2 BIND dn="uid=simiamih,ou=Users,o=EIONET,l=Europe" method=128'},
    {'message': 'conn=1001 op=2 BIND dn="uid=simiamih,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0'},
    {'message': 'conn=1001 fd=16 ACCEPT from IP=127.0.0.1:58286 (IP=0.0.0.0:389)'},
    {'message': 'conn=1001 fd=16 ACCEPT from IP=127.0.0.1:58286 (IP=0.0.0.0:389)'},
    {'message': 'conn=1001 fd=16 closed (connection lost)'}
]

server_pattern = re.compile(r"""
    conn=(?P<conn_id>[0-9]+)
    \s.+\s
    ACCEPT\sfrom\sIP=(?P<server>.+)\s
    """, re.X)

bind_pattern = re.compile(r"""
    conn=(?P<conn_id>[0-9]+)
    \s.+\s
    BIND\sdn="uid=(?P<user_id>[a-zA-Z0-9]+)
    """, re.X)

close_conn_pattern = re.compile(r"""
    conn=(?P<conn_id>[0-9]+)
    \s.+\sclosed
    """, re.X)


def parse_message(data):

    assert isinstance(data, list)

    for item in data:
        resp = {}
        server_search = re.search(server_pattern, item['message'])
        bind_search = re.search(bind_pattern, item['message'])
        close_conn_search = re.search(close_conn_pattern, item['message'])

        if server_search:
            resp.update(server_search.groupdict())
            resp['status'] = 'connected'
        if bind_search:
            resp.update(bind_search.groupdict())
            resp['status'] = 'login'
        if close_conn_search:
            resp.update(close_conn_search.groupdict())
            resp['status'] = 'closed'

        if resp:
            print resp

parse_message(DATA)
