from django.utils import unittest


DATASET_1 = [
    {'message': 'conn=1001 fd=16 ACCEPT from IP=127.0.0.1:58286 (IP=0.0.0.0:389)', 'date': '2012-07-03 23:06:42'},
    {'message': 'conn=1001 op=0 BIND dn="" method=128', 'date': '2012-07-03 23:06:42'},
    {'message': 'conn=1001 op=0 RESULT tag=97 err=0 text=', 'date': '2012-07-03 23:06:42'},
    {'message': 'conn=1001 op=1 SRCH base="ou=Users,o=EIONET,l=Europe" scope=2 deref=0 filter="(&(objectClass=top)(objectClass=person)(uid=simiamih))"', 'date': '2012-07-03 23:06:42'},
    {'message': 'conn=1001 op=2 BIND dn="uid=johndoe,ou=Users,o=EIONET,l=Europe" method=128', 'date': '2012-07-03 23:06:42'},
    {'message': 'conn=1001 op=2 BIND dn="uid=johndoe,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0', 'date': '2012-07-03 23:06:42'},

    {'message': 'conn=1001 fd=16 ACCEPT from IP=127.0.0.2:8080 (IP=0.0.0.0:389)', 'date': '2012-08-03 23:06:42'},
    {'message': 'conn=1001 op=17 BIND dn="uid=johnsmith,ou=Users,o=EIONET,l=Europe" method=128', 'date': '2012-08-03 23:06:42'},
    {'message': 'conn=1001 op=17 BIND dn="uid=johnsmith,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0', 'date': '2012-08-03 23:06:45'},
    {'message': 'conn=1001 op=17 BIND dn="uid=johnsmith,ou=Users,o=EIONET,l=Europe" mech=SIMPLE ssf=0', 'date': '2012-08-03 23:06:42'},

    {'message': 'conn=1001 fd=16 closed (connection lost)', 'date': '2012-07-03 23:06:42'}
]


class LdapMonTestCase(unittest.TestCase):

    def setUp(self):
       from ldap_mon.models import parse_message
       data = parse_message(DATASET_1)

    def test_parse_message(self):
        from ldap_mon.models import Log
        logs = Log.objects.all()
        self.assertEqual(2, logs.count())

    def test_parse_message_log_date(self):
        from ldap_mon.models import Log
        log = Log.objects.filter(user__username='johndoe',
                                 server__hostname='127.0.0.1')
        self.assertEqual(1, log.count())
        self.assertEqual('2012-07-03 23:06:42', str(log[0].date))

        log = Log.objects.filter(user__username='johnsmith',
                                 server__hostname='127.0.0.2')
        self.assertEqual(1, log.count())
        self.assertEqual('2012-08-03 23:06:45', str(log[0].date))

    def test_parse_message_users(self):
        from ldap_mon.models import User
        user = User.objects.filter(username='johndoe')
        self.assertEqual(1, user.count())

        user = User.objects.filter(username='johnsmith')
        self.assertEqual(1, user.count())

    def test_parse_message_servers(self):
        from ldap_mon.models import Server
        server = Server.objects.filter(hostname='127.0.0.1')
        self.assertEqual(1, server.count())

        server = Server.objects.filter(hostname='127.0.0.2')
        self.assertEqual(1, server.count())
