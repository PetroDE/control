"""
Specialize Service for services that can't be containers. Images only club
"""

import logging
from os.path import abspath, dirname, isfile, join
from copy import deepcopy

from control.exceptions import InvalidControlfile
from control.repository import Repository
from control.service.service import ImageService


class Buildable(ImageService):
    """
    Okay I lied. There are 3 kinds of services. The problem is that there are
    base images that need to be built, but don't know enough to be long running
    containers. Control doesn't control containers that you use like
    executables. Control handles the starting of long running service daemons
    in development and testing environments.
    """

    service_options = {
        'dockerfile',
        'events',
        'fromline',
    } | ImageService.service_options

    def __init__(self, service, controlfile):
        super().__init__(service, controlfile)
        self.logger = logging.getLogger('control.service.Buildable')
        self.dockerfile = {'dev': '', 'prod': ''}
        self.fromline = {'dev': '', 'prod': ''}

        try:
            self.events = service.pop('events')
        except KeyError:
            self.logger.debug('No events defined')

        try:
            dkrfile = service.pop('dockerfile')
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

        if 'fromline' in service:
            fline = service.pop('fromline')
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
        # for key, val in (
        #         (key, val)
        #         for key, val in service.items()
        #         if key in self.service_options):
        #     self.logger.debug('buildable assigning key %s value %s', key, val)
        #     self.__dict__[key] = val

        if not self.service:
            self.logger.debug('setting service name from guess')
            self.service = Repository.match(self.image).image

        self.logger.debug('Found Buildable %s', self.service)

    def dump_build(self, prod=False, pretty=True):
        """dump out a CLI version of how this image would be built"""
        rep = builder('build', pretty=pretty) \
            .tag(self.image) \
            .path(dirname(self.controlfile)) \
            .file(self.dockerfile['prod'] if prod else self.dockerfile['dev']) \
            .pull(options.pull) \
            .rm(options.no_rm) \
            .force_rm(options.force) \
            .no_cache(not options.cache)
        return rep


    def buildable(self):
        """Check if the service is buildable"""
        return self.dockerfile['dev'] or self.dockerfile['prod']

    def dev_buildable(self):
        """Check if the service is buildable in a dev environment"""
        return self.dockerfile['prod']

    def prod_buildable(self):
        """Check if the service is buildable in a prod environment"""
        return self.dockerfile['prod']
