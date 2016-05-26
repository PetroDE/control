"""Handle global defaults here"""

import argparse

options = argparse.Namespace()
opts = vars(options)
opts['debug'] = False
opts['image'] = None
opts['dockerfile'] = 'Dockerfile'
opts['name'] = None
opts['no_cache'] = False
opts['no_rm'] = True
opts['no_verify'] = False
opts['pull'] = None
opts['version'] = '2.0'
