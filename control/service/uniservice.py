"""
A little bit of trickery to enable single depth indexing of all values of a
service.
"""

import logging
import os.path
import sys
from copy import deepcopy

from docker.utils import create_host_config
from docker.api import ContainerApiMixin

from control.dclient import dclient
from control.repository import Repository
from control.exceptions import InvalidControlfile
from control.service.service import Service

module_logger = logging.getLogger('control.service')


class UniService(Service):
    """
    Service is a bit of an odd bird. It started as just a dict that held the
    configuration for a container, and anything that needed to modify it would
    simply put its data where it needed to go. This spread too much management
    code all over Control.

    Service holds some information that Control needs to manage a
    container/image pair. These are accessible as attributes.

    Anything that defines the container configuration (that docker needs to
    know about) is split across two dicts (because Docker is so good at being
    a magical box that you throw a configuration at and end up with a container
    /s), so Service aliases the difference between these two away by acting as
    a container.

    Anything the docker-py documentation says goes into create_container or
    create_host_config can be subscripted. e.g.:
    - service['name']
    - service['dns']
    - service['working_dir']

    The list of these options changes with each change to docker-py, so
    Control slurps the list of options out so it can double check you.

    Service also has some aliases so that if your Controlfile uses the CLI
    flags as your parameter names, you don't get bitten. Yeah. I'm being
    really nice to you. Unlike those jerks at Docker.

    Oh. One other thing. The attributes can also be accessed by subscript.
    Forcing you to remember which were Control internal, and what are just
    passed through to Docker didn't sit well with me.

    Attributes:
    - service
    - services: used to keep track of this metaservice's services
    - image
    - expected_timeout
    - required
    - controlfile
    - dockerfile: a dockerfile location cqn be guessed from the controlfile
                  location, but if it doesn't exist this will be empty
    - container: a dict ready to be given to create_container, except for
    - host_config: a dict of options ready to be given to create_host_config
    """

    service_options = {
        'container',
        'controlfile',
        'dockerfile',
        'expected_timeout',
        'host_config',
        'image',
        'required',
        'service',
        'services'
    }
    host_config_options = (
        set(create_host_config.__code__.co_varnames) -
        {'k', 'l', 'v', 'cpu_group', 'tmpfs'})

    # Options that have moved to the host_config should be put in there
    # despite them still being accepted by docker-py
    container_options = (
        set(ContainerApiMixin.create_container.__code__.co_varnames) -
        {
            'self',
            'dns',
            'host_config',
            'mem_limit',
            'memswap_limit',
            'volumes_from'
        })

    abbreviations = {
        'cmd': 'command',
        'env': 'environment'
    }

    all_options = (service_options |
                   container_options |
                   host_config_options |
                   abbreviations.keys() |
                   {'volumes'})

    defaults = {
        "dns": [],
        "dns_search": [],
        "volumes_from": [],
        "devices": [],
        "command": [],
        "ports": [],
        "environment": [],
        "entrypoint": []
    }

    def __init__(self, service, controlfile):
        self.logger = logging.getLogger('control.service.Service')
        self.dockerfile = ""
        self.container = {}
        self.host_config = {}
        self.expected_timeout = 10

        serv = deepcopy(service)
        Service.__init__(self, serv)

        # This is the one thing you actually have to have defined in a
        # Controlfile
        # Because later we normalize options, we don't create the Repository
        # object here, we just read in the string
        try:
            self.image = serv.pop('image')
        except KeyError as e:
            self.logger.critical('missing image %s', e)
            raise InvalidControlfile(controlfile, 'missing image')

        # We're going to hold onto this until we're ready to iterate over it
        container_config = serv.pop('container', {})

        # Handle the things that we have special requirements to handle
        # Set the service name
        service_empty = self.service == ""
        if service_empty and 'name' in container_config:
            self.service = container_config['name']
        elif service_empty:
            self.service = Repository.match(self.image).image
        # Set whether the service is required
        # Record the controlfile that this service came from
        self.controlfile = serv.pop('controlfile', controlfile)

        # The rest of the options can be straight assigned
        for key, val in (
                (key, val)
                for key, val in serv.items()
                if key in self.service_options):
            self.__dict__[key] = val

        # Now we are ready to iterate over the container configuration.
        # We do this awkward check to make sure that we don't accidentally
        # do the equivalent of eval'ing a random string that may or may not be
        # malicious.
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                'Accepting these configurations: %s',
                sorted(x for x in container_config.keys() if x in self.all_options))
            self.logger.debug(
                'Throwing out these these options: %s',
                sorted(x for x in container_config.keys() if x not in self.all_options))
        for key, val in ((x, y) for x, y in container_config.items() if x in
                         self.all_options):
            self[key] = val

        self._fill_in_holes()

    def prepare_container_options(self):
        """
        Call this function to dump out a single dict ready to be passed to
        docker.Client.create_container
        """
        hc = dclient.create_host_config(**self.host_config)
        if sys.version_info >= (3, 5):
            return {**self.container, **hc}
        r = self.container.copy()
        r.update(hc)
        return r

    def __len__(self):
        return len(self.container) + len(self.host_config)

    def __getitem__(self, key):
        try:
            key = self.abbreviations[key]
        except KeyError:
            pass  # We don't really care if you aren't using an abbrev
            # we just don't want to branch to do this replacement

        if key == 'volumes':
            return (self.container.get('volumes', []) +
                    self.host_config.get('binds', []))
        elif key in self.container_options:
            return self.container.get(key, self.defaults.get(key, ''))
        elif key in self.host_config_options:
            return self.host_config.get(key, self.defaults.get(key, ''))
        else:
            return self.__dict__[key]

    def __setitem__(self, key, value):
        if key in self.abbreviations.keys():
            key = self.abbreviations[key]

        if key in self.service_options:
            self.__dict__[key] = value
        elif key == 'volumes':
            (self.__dict__['container']['volumes'],
             self.__dict__['host_config']['binds']) = _split_volumes(value)
        elif key in self.container_options:
            self.container[key] = value
        elif key in self.host_config_options:
            self.host_config[key] = value
        else:
            raise KeyError

    def __delitem__(self, key):
        if key == 'image':
            raise KeyError(key)
        if key in self.container.keys():
            del self.container[key]
        elif key in self.host_config.keys():
            del self.host_config[key]
        elif key in self.service_options:
            del self.__dict__[key]
        else:
            raise KeyError(key)

    def _fill_in_holes(self):
        """
        After we've read in the whole service, we go in and fill in spots that
        might have been left blank.

        - hostname <= from service name
        """
        # Set the container's hostname based on guesses
        if len(self.container) > 0 and 'hostname' not in self.container:
            self['hostname'] = self['name']
        # Guess that there's a Dockerfile next to the Controlfile
        directory = os.path.dirname(os.path.abspath(self.controlfile))
        dockerfile = directory + '/Dockerfile'
        if os.path.isfile(dockerfile):
            self.dockerfile = dockerfile
            self.logger.debug('setting dockerfile: %s', self.dockerfile)


def _split_volumes(volumes):
    return ([x for x in volumes if ":" not in x],
            [x for x in volumes if ":" in x])
