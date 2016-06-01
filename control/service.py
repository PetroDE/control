"""
A little bit of trickery to enable single depth indexing of all values of a
service.
"""

from docker.utils import create_host_config
from docker.api import ContainerApiMixin


class Service:
    """Using a dict was turning out to need more code than was necessary.
    """

    service_options = {
        'service', 'image', 'container', 'host_config',
        'required', 'controlfile', 'dockerfile'}
    host_config_options = (
        {*create_host_config.__code__.co_varnames} ^
        {'k', 'l', 'v'})
    container_options = (
        {*ContainerApiMixin.create_container.__code__.co_varnames} ^
        {'self', 'host_config', 'volumes'})

    def __init__(self, service, controlfile):
        self.__dict__['service'] = ""
        self.__dict__['image'] = ""
        self.__dict__['container'] = {}
        self.__dict__['host_config'] = {}
        self.__dict__['expected_timeout'] = 10
        try:
            self.__dict__['container'] = service.pop('container')
        except KeyError:
            pass
        # Set the service name
        try:
            self.__dict__['service'] = service.pop('service')
        except KeyError:
            # If this throws an error the service is improperly formatted
            self.__dict__['service'] = self.container['name']
        # Set whether the service is required
        try:
            self.__dict__['required'] = service.pop('required')
        except KeyError:
            self.__dict__['required'] = not service.pop('optional', False)
        self.__dict__['image'] = service.pop('image', "")
        self.controlfile = service.pop('controlfile', controlfile)

    def __getattr__(self, name):
        if name == 'volumes':
            return list(self.__dict__['container'].get('volumes', set()) ^
                        self.__dict__['host_config'].get('binds', set()))
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
            self.__dict__['host_config']['binds'] = [i for i in value if ":" in i]
            self.__dict__['container']['volumes'] = [i for i in value if ":" not in i]
        elif name == 'env':
            self.__dict__['container']['environment'] = value
        elif name in self.container_options:
            self.container[name] = value
        elif name in self.host_config_options:
            self.host_config[name] = value
        else:
            self.__dict__[name] = value
