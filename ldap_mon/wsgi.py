"""
WSGI config for ldap_mon project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ldap_mon.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

HEADER_MAP = {
    'REMOTE_ADDR': 'HTTP_X_FORWARDED_FOR',
    'SCRIPT_NAME': 'HTTP_X_FORWARDED_SCRIPT_NAME',
    'HTTP_HOST': 'HTTP_X_FORWARDED_HOST',
    'wsgi.url_scheme': 'HTTP_X_FORWARDED_SCHEME',
}

def proxy_middleware(app):
    def proxy_fix(environ, start_response):
        for name in HEADER_MAP:
            value = environ.get(HEADER_MAP[name])
            if value:
                environ[name] = value

        return app(environ, start_response)

    return proxy_fix

if os.environ.get('ALLOW_REVERSE_PROXY') == 'on':
    application = proxy_middleware(application)
