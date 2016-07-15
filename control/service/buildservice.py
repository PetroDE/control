"""
Specialize Service for services that can't be containers. Images only club
"""

import logging
from os.path import abspath, dirname, isfile, join
from copy import deepcopy

from control.exceptions import InvalidControlfile
from control.service.service import Service
from control.service.uniservice import UniService


class BuildService(Service):
    """
    Okay I lied. There are 3 kinds of services. The problem is that there are
    base images that need to be built, but don't know enough to be long running
    containers. Control doesn't control containers that you use like
    executables. Control handles the starting of long running service daemons
    in development and testing environments.
    """

    service_options = {
        'controlfile',
        'dockerfile',
        'events',
        'fromline',
        'image',
        'required',
        'service',
        'services',
        'volumes',
    }

    def __init__(self, service, controlfile):
        self.logger = logging.getLogger('control.service.BuildService')
        self.dockerfile = {'dev': '', 'prod': ''}
        self.fromline = {'dev': '', 'prod': ''}
        self.events = {}

        serv = deepcopy(service)
        Service.__init__(self, serv)

        try:
            self.image = serv.pop('image')
        except KeyError:
            self.logger.critical('%s missing image', controlfile)
            raise InvalidControlfile(controlfile, 'missing image')

        # Record the controlfile that this service came from
        self.controlfile = serv.pop('controlfile', controlfile)

        try:
            dkrfile = serv.pop('dockerfile')
            if isinstance(dkrfile, dict):
                self.dockerfile = {
                    'dev': abspath(join(dirname(self.controlfile),
                                        dkrfile['dev'])),
                    'prod': abspath(join(dirname(self.controlfile),
                                         dkrfile['prod'])),
                }
            elif dkrfile == "":
                self.dockerfile = {'dev': "", 'prod': ""}
            else:
                self.dockerfile = {
                    'dev': abspath(join(dirname(self.controlfile), dkrfile)),
                    'prod': abspath(join(dirname(self.controlfile), dkrfile)),
                }
            self.logger.debug('setting dockerfile %s', self.dockerfile)
        except KeyError as e:
            # Guess that there's a Dockerfile next to the Controlfile
            dkrfile = join(abspath(dirname(self.controlfile)), 'Dockerfile')
            devfile = dkrfile + '.dev'
            prdfile = dkrfile + '.prod'
            try:
                self.dockerfile['dev'], self.dockerfile['prod'] = {
                    # devProdAreEmpty, DockerfileExists, DevProdExists
                    (True, True, False): lambda f, d, p: (f, f),
                    (True, False, True): lambda f, d, p: (d, p),
                    (True, False, False): lambda f, d, p: ('', ''),
                    # This list is sparsely populated because these are the
                    # only conditions that mean the values need to be guessed
                }[(
                    not self.dockerfile['dev'] and not self.dockerfile['prod'],
                    isfile(dkrfile),
                    isfile(devfile) and isfile(prdfile)
                )](dkrfile, devfile, prdfile)
                self.logger.debug('setting dockerfile: %s', self.dockerfile)
            except KeyError as e:
                self.logger.warning(
                    '%s: problem setting dockerfile: %s missing',
                    self.service,
                    e)

        if 'fromline' in serv:
            fline = serv.pop('fromline')
            if isinstance(fline, dict):
                self.fromline = {
                    'dev': fline.get('dev', ''),
                    'prod': fline.get('prod', '')
                }
            else:
                self.fromline = {
                    'dev': fline,
                    'prod': fline
                }

        # The rest of the options can be straight assigned
        for key, val in (
                (key, val)
                for key, val in serv.items()
                if key in self.service_options):
            self.__dict__[key] = val

    def keys(self):
        """
        Return a list of all the "keys" that make up this "service".

        This exists because Services act like dicts that are intelligent about
        their values.
        """
        # FOR WHEN YOU MOVE TO PYTHON 3.5
        # return list((self.service_options - {'container', 'host_config'}) |
        #             {*self.container.keys()} |
        #             {*self.host_config.keys()} - {'binds'})
        return list(self.service_options)

    def __len__(self):
        return 0

    def __getitem__(self, key):
        try:
            key = UniService.abbreviations[key]
        except KeyError:
            pass  # We don't really care if you aren't using an abbrev
            # we just don't want to branch to do this replacement

        if key in self.service_options:
            return self.__dict__[key]
        return UniService.defaults.get(key, '')

    def __setitem__(self, key, value):
        if key in self.service_options:
            self.__dict__[key] = value
        elif key in UniService.container_options or key in UniService.host_config_options:
            pass
        else:
            raise KeyError

    def __delitem__(self, key):
        if key == 'image':
            raise KeyError(key)
        elif key in self.service_options:
            del self.__dict__[key]
        else:
            raise KeyError(key)
