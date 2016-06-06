"""
A little bit of trickery to enable single depth indexing of all values of a
service.
"""

import logging
from copy import deepcopy

from docker.utils import create_host_config
from docker.api import ContainerApiMixin

from control.repository import Repository
from control.exceptions import InvalidControlfile

module_logger = logging.getLogger('control.service')


class Service:
    """Using a dict was turning out to need more code than was necessary.
    """

    service_options = {
        'service', 'image', 'container', 'host_config',
        'required', 'controlfile', 'dockerfile'}
    host_config_options = (
        set(create_host_config.__code__.co_varnames) -
        {'k', 'l', 'v', 'cpu_group', 'tmpfs'})
    container_options = (
        set(ContainerApiMixin.create_container.__code__.co_varnames) -
        {
            'self',
            'dns',
            'host_config',
            'mem_limit',
            'memswap_limit',
            'volumes',
            'volumes_from'
        })
    all_options = container_options | host_config_options | {
        'env',
        'cmd',
        'volumes'
    }

    def __init__(self, service, controlfile):
        self.__dict__['logger'] = logging.getLogger('control.service.Service')
        self.__dict__['service'] = ""
        self.__dict__['image'] = ""
        self.__dict__['container'] = {}
        self.__dict__['host_config'] = {}
        self.__dict__['expected_timeout'] = 10

        serv = deepcopy(service)

        # This is the one thing you actually have to have defined in a
        # Controlfile
        try:
            self.__dict__['image'] = Repository.match(serv.pop('image'))
        except KeyError as e:
            self.logger.info('missing image %s', e)
            raise InvalidControlfile(controlfile, 'missing image')

        # We're going to hold onto this until we're ready to iterate over it
        container_config = serv.pop('container', {})

        # Handle the things that we have special requirements to handle
        # Set the service name
        if 'service' in service:
            self.__dict__['service'] = serv.pop('service')
        elif 'name' in container_config:
            self.__dict__['service'] = container_config['name']
        else:
            self.__dict__['service'] = self.image.image
        # Set whether the service is required
        try:
            self.__dict__['required'] = serv.pop('required')
        except KeyError:
            self.__dict__['required'] = not serv.pop('optional', False)
        self.controlfile = serv.pop('controlfile', controlfile)

        # The rest of the options can be straight assigned
        for key, val in serv.items():
            self.__dict__[key] = val

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
            self.__setattr__(key, val)

        self._fill_in_holes()

    def __getattr__(self, name):
        if name == 'volumes':
            return list(self.__dict__['container'].get('volumes', set()) |
                        self.__dict__['host_config'].get('binds', set()))
        elif name == 'cmd':
            name = 'command'
        elif name == 'env':
            name = 'environment'
        try:
            return self.__dict__['container'][name]
        except KeyError:
            try:
                return self.__dict__['host_config'][name]
            except KeyError:
                raise AttributeError

        return self.container[name]

    def __setattr__(self, name, value):
        if name in self.__dict__:
            self.__dict__[name] = value
        elif name == 'volumes':
            (self.__dict__['container']['volumes'],
             self.__dict__['host_config']['binds']) = _split_volumes(value)
        elif name == 'env':
            self.__dict__['container']['environment'] = value
        elif name == 'cmd':
            self.__dict__['container']['command'] = value
        elif name in self.container_options:
            self.container[name] = value
        elif name in self.host_config_options:
            self.host_config[name] = value
        else:
            self.__dict__[name] = value

    def _fill_in_holes(self):
        """
        After we've read in the whole service, we go in and fill in spots that
        might have been left blank.

        - hastname <= from service name
        """
        if len(self.container) > 0 and 'hostname' not in self.container:
            self.hostname = self.name


def _split_volumes(volumes):
    return ([x for x in volumes if ":" not in x],
            [x for x in volumes if ":" in x])
