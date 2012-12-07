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


Installation
============
`ldap_mon` requires Python 2.7. Dependencies are listed in
``requirements.txt``. The command to run the web server is listed in
``Procfile``. The easiest way to run the application is with a tool like
`Foreman`, `honcho` or `Sarge`. The ``fab deploy`` command deploys to a
`Sarge` server based on the ``TARGET`` environment variable.


Place the following command in a cron job to read log entries from the
database. The ``remove=on`` flag removes old or irrelevant entries.
Don't forget to set the ``CRON_KEY`` variable.

::

    curl -F 'remove=on' -F 'key=THEKEY' 'http://localhost:38200/fetch_and_parse'


Configuration variables
=======================
The following environment variables are used for configuration:

``DEBUG``
    If set to ``on``, the application will start in debug mode.

``RSYSLOG_DATABASE_URI``
    URI of MySQL database where `rsyslog` dumps log records. Used by
    `fetchlog`.

``DATABASE_URI``
    URI of `ldap_mon` application database where statistics will be
    saved.

``SECRET_KEY``
    Random secret used for session security.

``STATIC_URL``
    URL where static media files are served.

``ALLOW_REVERSE_PROXY``
    If set to ``on``, look for HTTP headers set by a proxy, and change
    the request environment accordingly.

``TARGET``
    Deployment host and directory, used by ``fab deploy``. Example:
    ``edw@capybara:/var/local/ldap_mon``.

``CRON_KEY``
    Secret key used by a cron job when calling `fetch_and_parse`.


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
