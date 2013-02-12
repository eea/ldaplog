#!/usr/bin/env python

import logging
from ldaplog.app import manager


if __name__ == '__main__':
    logging.basicConfig()
    manager.run()
