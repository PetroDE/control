"""Define a base class for a Service"""

import logging

from control.exceptions import InvalidControlfile


class Service:
    """
    Service holds the information that Control needs to manage a
    container/image pair. These are accessible as attributes.
    """

    service_options = {
        'controlfile',
        'service',
    }

    def __init__(self, service, controlfile):
        self.logger = logging.getLogger('control.service.Service')
        self.controlfile = controlfile

        try:
            self.service = service.pop('service')
        except KeyError:
            self.service = ""

        try:
            self.required = service.pop('required')
        except KeyError:
            self.required = not service.pop('optional', False)
        self.logger.debug('Found Service %s', self.service)

    def buildable(self):
        """Check if the service is buildable"""
        return False

    def dev_buildable(self):
        """Check if the service is buildable in a dev environment"""
        return False

    def prod_buildable(self):
        """Check if the service is buildable in a prod environment"""
        return False

    def keys(self):
        """
        Return a list of all the "keys" that make up this "service".

        This exists because Services act like dicts that are intelligent about
        their values.
        """
        return list(self.service_options)

    def __len__(self):
        return 0

    def __getitem__(self, key):
        try:
            return self.__dict__[key]
        except KeyError as e:
            self.logger.debug('service threw a keyerror: %s', e)
            raise e

    def __setitem__(self, key, value):
        if key in self.service_options:
            self.__dict__[key] = value
        else:
            raise KeyError(key)

    def __delitem__(self, key):
        if key == 'image':
            raise KeyError(key)
        elif key in self.service_options:
            del self.__dict__[key]
        else:
            raise KeyError(key)

class ImageService(Service):
    """
    This service type has an image associated with it. As opposed to
    metaservices which don't have an image attribute.
    """

    service_options = {
        'expected_timeout',
        'image',
        'open',
    } | Service.service_options


    def __init__(self, service, controlfile):
        super().__init__(service, controlfile)
        self.logger = logging.getLogger('control.service.ImageService')
        try:
            self.image = service.pop('image')
        except KeyError:
            self.logger.critical('%s missing image', controlfile)
            raise InvalidControlfile(controlfile, 'missing image') from None
        self.expected_timeout = service.pop('expected_timeout', 10)
        try:
            self.open = service.pop('open')
        except KeyError:
            self.logger.debug('No open defined')

        self.logger.debug('Found ImageService %s', self.service)
