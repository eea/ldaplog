LDAP event monitor
==================
`ldaplog` is an application that reads OpenLDAP log entries, parses
them, and keeps track of the most recent login time of each user on each
server.

Log output from `slapd` needs to be captured, e.g. using `rsyslog`, and
stored in a `MySQL` database. `ldaplog` polls the log database, parses
records, and updates the results in its own database/tables. It also purges old
slapd log records, and any log records from unknown sources, so that the
log database doesn't grow indefinitely.


Installation
============
`ldaplog` requires Python 2.7. Dependencies are listed in
``requirements.txt``. The command to run the web server is listed in
``Procfile``. The easiest way to run the application is with a tool like
`Foreman`, `honcho` or `Sarge`. The ``fab deploy`` command deploys to a
`Sarge` server based on the ``DEPLOYMENT_TARGET`` environment variable.

Before `ldaplog` can parse log records, you need to
create `MYSQL` DATABASE and LOG_DATABASE (and possibly a user that have acces to them)
Those two databases may be the same one (there are no table names collision).

If running manually copy .env.sample file in, say, .env  and provide the necessary info to it
You can run with::

    env `cat .env` python -m ldaplog.manage <command>

Create the tables, including a state table in the rsyslog database::

    env `cat .env` python -m ldaplog.manage syncdb

Run the following command every few minutes to parse new log entries
from the database::

    env `cat .env` python -m ldaplog.manage update

Run the server (devel-mode) with::

    env `cat .env` python -m ldaplog.manage runserver -p <port>

We currently keep the list of users in instance/users.txt file, uid of users
in LDAP, one per line.


Configuration variables
=======================
The following environment variables are used for configuration:

``DEBUG``
    If set to ``on``, the application will start in debug mode. Never
    use in production, it allows for remote code execution.

``PARSER_DEBUG``
    Provide even more debug messages

``DATABASE``
    URI of `ldaplog` application database where statistics will be
    saved.

``LOG_DATABASE``
    URI of MySQL database where `rsyslog` dumps log records. Used by
    the `update` command.

``SECRET_KEY``
    Random secret used for HTTP session security.

``REVERSE_PROXY``
    If set to ``on``, look for HTTP headers set by a proxy, and change
    the request environment accordingly.

``DEPLOYMENT_TARGET``
    Deployment host and directory, used by ``fab deploy``. Example:
    ``edw@capybara:/var/local/ldaplog``.

``SENTRY_DSN``
    Optional Sentry URL to gather errors.

``AUTH_LDAP_SERVER``, ``AUTH_LDAP_DN``
    LDAP server to use for logins in the `ldaplog` web interface.
    Example::

        AUTH_LDAP_SERVER=ldap://ldap2.eionet.europa.eu
        AUTH_LDAP_DN=uid={username},ou=Users,o=EIONET,l=Europe


Configuring rsyslog-mysql
=========================
There is a good howto_ for configuring `rsyslog` to write log entries to
`MySQL`. Here's the gist of it:

.. _howto: http://www.rsyslog.com/doc/rsyslog_mysql.html

1. Make sure the `rsyslog-mysql` backend is installed: ``yum install
   rsyslog-mysql``

2. Create a MySQL database with the rsyslog schema. There is a
   ``createDB.sql`` script (e.g. in
   ``/usr/share/doc/rsyslog-mysql-5.8.10/createDB.sql``). You may have
   to remove the first two lines, they hardcode the database name.

3. Update the configuration file. Add the following lines in the right
   place, then restart the `rsyslog` service::

    $ModLoad ommysql
    local4.* :ommysql:db_host,db_name,db_user,db_password
