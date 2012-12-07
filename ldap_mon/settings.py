import os

DEBUG = bool(os.environ.get('DEBUG') == 'on')
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS


_database_uri = os.environ['DATABASE_URI']
if _database_uri.startswith('sqlite:///'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _database_uri[len('sqlite:///'):],
        }
    }
else:
    raise RuntimeError("Can't parse database uri %r" % _database_uri)

RSYSLOG_DATABASE_URI = os.environ['RSYSLOG_DATABASE_URI']

TIME_ZONE = 'Europe/Copenhagen'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True
USE_L10N = True
USE_TZ = False
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = ''
STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATICFILES_DIRS = ()

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf')

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'ldap_mon.urls'

WSGI_APPLICATION = 'ldap_mon.wsgi.application'

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'ldap_mon',
    'gunicorn',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '%(asctime)s %(module)s %(levelname)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'stderr': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'root': {
        'handlers': ['stderr'],
    }
}


_auth_ldap_server = os.environ.get('AUTH_LDAP_SERVER')
if _auth_ldap_server:
    import ldap
    from django_auth_ldap.config import LDAPSearch

    AUTH_LDAP_SERVER_URI = _auth_ldap_server
    AUTH_LDAP_BIND_DN = ""
    AUTH_LDAP_BIND_PASSWORD = ""

    AUTH_LDAP_USER_SEARCH = LDAPSearch("o=EIONET,l=Europe",
                                       ldap.SCOPE_SUBTREE,
                                       "(uid=%(user)s)")

    AUTH_LDAP_USER_ATTR_MAP = {
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    }

    AUTHENTICATION_BACKENDS = (
        'django_auth_ldap.backend.LDAPBackend',
        'django.contrib.auth.backends.ModelBackend',
    )
