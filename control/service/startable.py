"""
Define a startable service
"""

import logging
from os.path import isfile

from docker.utils import create_host_config, parse_env_file
from docker.api import ContainerApiMixin

from control.cli_builder import builder
from control.dclient import dclient
from control.repository import Repository
from control.service.service import ImageService

module_logger = logging.getLogger('control.service.startable')


class Startable(ImageService):
    """
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
        'env_file',
        'volumes',
    } | ImageService.service_options

    host_config_options = (
        set(create_host_config.__code__.co_varnames) -
        {
            'cpu_group',
            'k',
            'l',
            'tmpfs'
            'v',
            'binds',
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
        "ports": [],
        "environment": [],
        "entrypoint": [],
    }

    def __init__(self, service, controlfile):
        super().__init__(service, controlfile)
        self.logger = logging.getLogger('control.service.Startable')
        self.container = {}
        self.host_config = {}
        self.volumes = {'shared': [], 'dev': [], 'prod': []}

        # We're going to hold onto this until we're ready to iterate over it
        container_config = service.pop('container', {})

        # Handle the things that we have special requirements to handle
        service_empty = self.service == ""
        if service_empty and 'name' in container_config:
            self.service = container_config['name']
        elif service_empty:
            self.service = Repository.match(self.image).image

        self.services = [self.service]

        env = list({'envfile', 'env_file'} & set(container_config.keys()))
        if len(env) > 0:
            self.env_file = container_config.pop(env[0])
        else:
            self.env_file = ''
        try:
            self.commands = service.pop('commands')
        except KeyError:
            self.commands = {}
            self.logger.debug('No commands defined')
        try:
            vols = container_config.pop('volumes')
            if isinstance(vols, list):
                self.volumes['shared'] = vols
            elif isinstance(vols, dict):
                self.volumes.update(vols)
        except KeyError:
            self.logger.debug('No volumes defined')

        # Now we are ready to iterate over the container configuration.
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                'Accepting these configurations: %s',
                sorted(x for x in container_config.keys() if x in (
                    self.container_options |
                    self.host_config_options |
                    self.abbreviations.keys()
                )))
            self.logger.debug(
                'Throwing out these these options: %s',
                sorted(x for x in container_config.keys() if x not in (
                    self.container_options |
                    self.host_config_options |
                    self.abbreviations.keys()
                )))
        # This is a dumb way to handle abbreviations, but it works for now
        for key, val in ((self.abbreviations[x], y)
                         for x, y in container_config.items()
                         if x in self.abbreviations.keys()):
            self.container[key] = val
        for key, val in ((x, y) for x, y in container_config.items() if x in
                         self.container_options):
            self.container[key] = val
        for key, val in ((x, y) for x, y in container_config.items() if x in
                         self.host_config_options):
            self.host_config[key] = val

        # Set the container's name based on guesses
        if 'name' not in self.container:
            self.container['name'] = self.service
            self.logger.debug('setting container name from guess')
        # Set the container's hostname based on guesses
        if 'hostname' not in self.container:
            self.container['hostname'] = self.container['name']
            self.logger.debug('setting container hostname from guess')

        self.logger.debug('service image: %s', self.image)
        self.logger.debug('service container: %s', self.container)
        self.logger.debug('service host_config: %s', self.host_config)
        self.logger.debug('service volumes: %s', self.volumes)

        self.logger.debug('found Startable %s', self.service)

    def dump_run(self, prod=False, pretty=True):
        """dump out a CLI version of how this container would be started"""
        rep = builder('run', pretty=pretty).image(self.image) \
                .volume(sorted(self.volumes_for(prod)))
        if self.env_file:
            rep = rep.env_file(self.env_file)
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
        return rep.detach()

    def find_volume(self, substr):
        """
        For better error messages, need to find a volume definition by substring
        """
        return [vol
                for vol in self.volumes['dev'] +
                self.volumes['prod'] +
                self.volumes['shared']
                if substr in vol]

    def volumes_for(self, prod):
        """Return a joined list of shared and specific volumes"""
        if prod:
            return self.volumes['shared'] + self.volumes['prod']
        else:
            return self.volumes['shared'] + self.volumes['dev']

    def prepare_container_options(self, prod):
        """
        Call this function to dump out a single dict ready to be passed to
        docker.Client.create_container
        """
        # FOR WHEN YOU CAN UPGRADE TO 3.5
        # hc = dclient.create_host_config(**self.host_config)
        # return {**self.container, **hc}
        self.logger.debug('startable using 3.4 version')
        self.container['volumes'], self.host_config['binds'] = _split_volumes(
            self.volumes_for(prod))
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
        # return list(self.service_options |
        #             {*self.container.keys()} |
        #             {*self.host_config.keys()})
        # TODO: this is wrong
        return list(self.service_options |
                    self.container.keys() |
                    self.host_config.keys())

    def __lt__(self, other):
        return (self.service, self.container['name']) < (other.service, other.container['name'])

    def __eq__(self, other):
        return (self.service, self.container['name']) == (other.service, other.container['name'])

    def __len__(self):
        return len(self.container) + len(self.host_config)

    def __getitem__(self, key):
        if key in self.abbreviations.keys():
            key = self.abbreviations[key]

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
            raise KeyError(key)

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


def _split_volumes(volumes):
    """
    Volumes can be specified in three ways:
    "container_mount_point"
    "host_binding:container_mount_point"
    "host_binding:container_mount_point:ro"

    create_container(volumes: []) wants the full list of container_mount_points
    create_host_config(binds: []) wants ONLY the entries that have host bindings

    This is annoying because container_mount_point will be index 0 or 1
    depending on the number of colons in the string.
    """
    module_logger.debug('%i items: %s', len(volumes), volumes)
    return ([x.split(':')[:2][-1] for x in volumes],
            [x for x in volumes if ":" in x])
