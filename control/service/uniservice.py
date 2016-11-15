"""
A little bit of trickery to enable single depth indexing of all values of a
service.
"""

import logging
from os.path import abspath, dirname, isfile, join
from copy import deepcopy

from docker.utils import create_host_config, parse_env_file
from docker.api import ContainerApiMixin

from control.cli_builder import builder
from control.dclient import dclient
from control.exceptions import InvalidControlfile
from control.options import options
from control.repository import Repository
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
        'commands',
        'container',
        'controlfile',
        'dockerfile',
        'env_file',
        'events',
        'expected_timeout',
        'fromline',
        'host_config',
        'image',
        'open',
        'required',
        'service',
        'services',
        'volumes',
    }

    host_config_options = (
        set(create_host_config.__code__.co_varnames) -
        {
            'cpu_group',
            'k',
            'l',
            'tmpfs'
            'v',
        }
    )

    # Options that have moved to the host_config should be put in there
    # despite them still being accepted by docker-py
    container_options = (
        set(ContainerApiMixin.create_container.__code__.co_varnames) -
        {
            'self',
            'dns',
            'host_config',
            'image',
            'mem_limit',
            'memswap_limit',
            'volumes_from',
            'volumes'
        }
    )

    abbreviations = {
        'cmd': 'command',
        'env': 'environment',
        'envfile': 'env_file',
    }

    all_options = (
        service_options |
        container_options |
        host_config_options |
        abbreviations.keys()
    )

    defaults = {
        "dns": [],
        "dns_search": [],
        "volumes_from": [],
        "devices": [],
        "command": [],
        "ports": [],
        "environment": [],
        "entrypoint": [],
    }

    def __init__(self, service, controlfile):
        self.logger = logging.getLogger('control.service.UniService')
        self.dockerfile = {'dev': '', 'prod': ''}
        self.fromline = {'dev': '', 'prod': ''}
        self.commands = {}
        self.container = {}
        self.host_config = {}
        self.events = {}
        self.expected_timeout = 10
        self.env_file = ''
        self.volumes = []

        serv = deepcopy(service)
        Service.__init__(self, serv)

        # This is the one thing you actually have to have defined in a
        # Controlfile
        # Because later we normalize options, we don't create the Repository
        # object here, we just read in the string
        try:
            self.image = serv.pop('image')
        except KeyError:
            self.logger.critical('%s missing image', controlfile)
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
                # TODO: this is a hack to enable control to start multiple
                # containers from the same image without building that image
                # each time
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
            devfile = join(dkrfile, '.dev')
            prdfile = join(dkrfile, '.prod')
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
            self.logger.debug('setting dockerfile with fallback: %s', self.dockerfile)

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
        self.logger.debug('service image: %s', self.image)
        self.logger.debug('service container: %s', self.container)
        self.logger.debug('service host_config: %s', self.host_config)

        self._fill_in_holes()

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

    def dump_run(self, pretty=True):
        """dump out a CLI version of how this container would be started"""
        rep = builder('run', pretty=pretty).image(self.image) \
                .volume(sorted(self.volumes)) \
                .env_file(self.env_file)
        for k, v in self.container.items():
            rep = {
                'command': rep.command,
                'cpu_shares': rep.cpu_shares,
                'detach': rep.detach,
                'entrypoint': rep.entrypoint,
                'environment': rep.env,
                'hostname': rep.hostname,
                'name': rep.name,
                'ports': rep.publish,
                'stdin_open': rep.interactive,
                'tty': rep.tty,
                'user': rep.user,
                'working_dir': rep.workdir,
            }[k](v)
        for k, v in self.host_config.items():
            rep = {
                'devices': rep.device,
                'dns': rep.dns,
                'dns_search': rep.dns_search,
                'extra_hosts': rep.add_host,
                'ipc_mode': rep.ipc,
                'links': rep.link,
                'volumes_from': rep.volumes_from,
            }[k](v)
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

    def prepare_container_options(self):
        """
        Call this function to dump out a single dict ready to be passed to
        docker.Client.create_container
        """
        # FOR WHEN YOU CAN UPGRADE TO 3.5
        # hc = dclient.create_host_config(**self.host_config)
        # return {**self.container, **hc}
        self.logger.debug('uniservice using 3.4 version')
        self.container['volumes'], self.host_config['binds'] = _split_volumes(self.volumes)
        self.logger.debug('container: %s', self.container)
        self.logger.debug('host_config: %s', self.host_config)
        hc = dclient.create_host_config(**self.host_config)
        r = self.container.copy()
        r['host_config'] = hc
        if self.env_file and isfile(self.env_file):
            # Apply env vars in this order so that envs defined in
            # the Controlfile take precedence over the envfile
            r['environment'] = dict(
                parse_env_file(self.env_file),
                **{
                    x[0]: x[2]
                    for x in [
                        x.partition('=')
                        for x in r.get('environment', [])
                    ]
                }
            )
        elif self.env_file:
            self.logger.warning('Env file is missing: %s', self.env_file)
        self.logger.debug('combined: %s', r)
        return r

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
        return list((self.service_options - {'container', 'host_config'}) |
                    set(self.container.keys()) |
                    set(self.host_config.keys()) - {'binds'})

    def __lt__(self, other):
        return (self.service, self.container['name']) < (other.service, other.container['name'])

    def __eq__(self, other):
        return (self.service, self.container['name']) == (other.service, other.container['name'])

    def __len__(self):
        return len(self.container) + len(self.host_config)

    def __getitem__(self, key):
        try:
            key = self.abbreviations[key]
        except KeyError:
            pass  # We don't really care if you aren't using an abbrev
            # we just don't want to branch to do this replacement

        if key in self.container_options:
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
        # Set the container's name based on guesses
        if len(self.container) > 0 and 'name' not in self.container:
            self['name'] = self['service']
        # Set the container's hostname based on guesses
        if len(self.container) > 0 and 'hostname' not in self.container:
            self['hostname'] = self['name']


def _split_volumes(volumes):
    """
    Volumes can be specified in three ways:
    "container_mount_point"
    "host_binding:container_mount_point"
    "host_binding:container_mount_point:ro"

    create_container(volumes: []) wants the full list of container_mount_points
    create_host_config(binds: []) wants ONLY the host bindings

    This is annoying because container_mount_point will be index 0 or 1
    depending on the number of colons in the string.
    """
    module_logger.debug('%i items: %s', len(volumes), volumes)
    return ([x.split(':')[:2][-1] for x in volumes],
            [x for x in volumes if ":" in x])
