#!/usr/bin/env python

import os
import logging
from ldaplog.app import manager


def main():
    logging.basicConfig()

    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    if SENTRY_DSN:
        from raven.conf import setup_logging
        from raven.handlers.logging import SentryHandler
        setup_logging(SentryHandler(SENTRY_DSN, level=logging.WARN))

    manager.run()


if __name__ == '__main__':
    main()
