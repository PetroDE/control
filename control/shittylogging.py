"""This is my fault. Shortly we'll be switching to using real logging"""

import sys

from control.options import options


def err(arg):
    log(arg, level='error')


def log(arg, level='info'):
    if (
            level == 'info' or
            level == 'error' or
            (level == 'warn' and options.debug) or
            (level == 'debug' and options.debug)):
        print('[{LEVEL:5s}] {ARG}'.format(LEVEL=level.upper(), ARG=arg), file=sys.stderr)
