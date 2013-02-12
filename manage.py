#!/usr/bin/env python

import os
import logging
import ldaplog.app


DEBUG = (os.environ.get('DEBUG') == 'on')


if __name__ == '__main__':
    logging.basicConfig()
    ldaplog.app.main(debug=DEBUG)
