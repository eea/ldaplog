LDAP event monitor
==================
`ldap_mon` is an application that reads OpenLDAP log entries, parses
them, and keeps track of the most recent login time of each user on each
server.

Log output from `slapd` needs to be captured, e.g. using `rsyslog`, and
stored in a `MySQL` database. `ldap_mon` polls the log database, parses
records, and updates the results in its own database. It also purges old
slapd log records, and any log records from unknown sources, so that the
log database doesn't grow indefinitely.