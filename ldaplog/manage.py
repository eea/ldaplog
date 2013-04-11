#!/usr/bin/env python

import os
import logging
from ldaplog.app import manager


def configure_logging(level):
    stderr = logging.StreamHandler()
    stderr.setLevel(level)
    stderr.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logging.getLogger().addHandler(stderr)


def main():
    DEBUG = (os.environ.get('DEBUG') == 'on')
    configure_logging(level=logging.DEBUG if DEBUG else logging.INFO)

    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    if SENTRY_DSN:
        from raven.conf import setup_logging
        from raven.handlers.logging import SentryHandler
        setup_logging(SentryHandler(SENTRY_DSN, level=logging.WARN))

    manager.run()


if __name__ == '__main__':
    main()
