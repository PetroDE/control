"""
A Buildable and Startable Service
"""

import logging

from control.service.buildable import Buildable
from control.service.startable import Startable


class BSService(Buildable, Startable):
    """
    The majority of services that Control is controlling will be BSServices.
    They will have a Dockerfile that bulids an image, and that service will be
    directly startable.
    """

    service_options = Buildable.service_options | Startable.service_options
    all_options = Buildable.all_options | Startable.all_options

    def __init__(self, service, controlfile):
        super().__init__(service, controlfile)
        self.logger = logging.getLogger('control.service.BSService')
        self.logger.debug('Found BSService %s', self.service)
