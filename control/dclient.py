"""
Centralizing all the docker shenanigans so you can import this once and
have docker ready to go.
"""

import os

import docker


class DockerNotRunning(Exception):
    """
    docker-py doesn't define an exception for this, and in fact will
    murder your application if you attempt to connect while it isn't
    running. We try to be a little gentler.
    """
    pass


# Docker.Client doesn't raise an exception. They just crash the program. This
# is the most graceful way I can save this.
if os.path.exists('/var/run/docker.sock'):
    dclient = docker.Client(base_url='unix://var/run/docker.sock')
else:
    dclient = None
    # raise DockerNotRunning

# Here's a snippet of code for when you have to call a docker function
#
# try:
#     # Do something with docker
# except Docker.errors.NotFound as e:
#     if 'chown' in str(e):
#         raise #A better error
#     elif 'volume not found' in str(e):
#         raise #A better error
#     else:
#         log('You found a new error condition in the Docker API!', level='debug')
#         log(e, level='debug')
#         log(e.response, level='debug')
#         log(e.explanation.decode('utf-8'), level='debug')
#         raise
# except Docker.errors.APIError as e:
#     if 'volume name invalid' in e.explanation.decode('utf-8'):
#         raise #A better error
#     elif 'is already in use by container' in e.explanation.decode('utf-8'):
#         raise #A better error
#     else:
#         log('You found a new error condition in the Docker API!', level='debug')
#         log(e, level='debug')
#         log(e.response, level='debug')
#         log(e.explanation.decode('utf-8'), level='debug')
#         raise
# else:
#     #Magically we made it through
