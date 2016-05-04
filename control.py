#!/usr/bin/env python3

"""
PetroDE Control script
  It does stuff(TM)

A script to build Docker images, compile code, run tests, be friendly to
developers, enable local development, check in build configuration next to
code, kiss babies, and be popular.

We really don't expect much of it. /s

Control is a general use build tool. But, it is a developer specific container
support tool. Control should not be used to start images in production.

Exit codes:
1 - Control operation failed, check output
2 - Something failed early (Docker daemon not started, malformed Controlfile)
3 - Operation pre-check failed

Things that are needed:
  - Clearly defined global options when ./control is run
  - Clearly defined options when ./control build is run
  - Override global defaults with Controlfile
  - Override Controlfile settings with CLI arguments
  - Note that docker 1.9 needs docker-py 1.7.x and docker 1.10 needs docker-py 1.8
  - Calling build should remove the old image that was using that name
  - Calling rere should remove the old image after the container has been
    restarted to use the new image

TODO: handle ^C without printing a stack trace, like normal people MOM!
"""

import argparse
import base64
import json
import os
import re
import shutil
import sys
import requests
import dateutil.parser as dup
import docker as Docker

# Shut up requests because the user has to make a conscious choice to be
# insecure
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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


def err(arg):
    log(arg, level='error')


def log(arg, level='info'):
    if (
            level == 'info' or
            level == 'error' or
            (level == 'warn' and options.debug) or
            (level == 'debug' and options.debug)):
        print('[{LEVEL:5s}] {ARG}'.format(LEVEL=level.upper(), ARG=arg), file=sys.stderr)


class Registry:
    """
    Abstraction for communicating with a Docker V2 Registry.

    Insecure registries, V1 registries, and the Docker Hub are not supported.
    """

    def __init__(self, domain, port=None, certdir='/etc/docker/certs.d'):
        """
        Take a domain name and a string port number and create a Registry object.

        This constructor ensures that it can communicate with the registry
        specified in the constructor, so construction will take time dependent
        upon the Internet connection of the machine running Control, as well as
        the performance of the Registry we are communicating with.

        Keyword arguments:
        domain -- the base domain name to connect to. Do not include the
                  protocol to communicate over.
        port   -- a string argument that is the port to connect to (optional)
        """

        self.domain = domain
        self.port = port
        if port:
            self.endpoint = '{}:{}'.format(self.domain, self.port)
        else:
            self.endpoint = self.domain
        # TODO support insecure registries and V1 registries
        self.baseuri = 'https://{}/v2'.format(self.endpoint)
        certdir = '{dir}/{reg}'.format(dir=certdir, reg=self.endpoint)
        self.use_cert = False
        self.session = requests.Session()
        if os.path.isfile(os.path.expanduser('~/.docker/config.json')):
            with open(os.path.expanduser('~/.docker/config.json')) as docker_config_file:
                try:
                    j = json.load(docker_config_file)
                    self.session.auth = tuple(
                        base64.b64decode(
                            j['auths']['https://{}'.format(self.endpoint)]['auth'])
                        .decode('utf-8')
                        .split(':'))
                    log('setting basicauth', level='debug')
                except KeyError:
                    pass
                except ValueError as e:
                    log('Docker config file not valid JSON: {}'.format(e), level='warn')
        if options.no_verify:
            self.certfile = False
            self.use_cert = True
        elif os.path.isdir(certdir):
            # for certfile in map(lambda x: '{}/{}'.format(certdir, x), os.listdir(certdir)):
            for certfile in ('{}/{}'.format(certdir, x) for x in os.listdir(certdir)):
                log('trying certfile {}'.format(certfile), level='debug')
                try:
                    self.session.get(
                        'https://{}/'.format(self.endpoint),
                        verify=certfile)
                except (requests.exceptions.SSLError, OSError) as e:
                    log('Cert file rejected {}: {}'.format(certfile, e), level='debug')
                except:
                    log('Unexpected exception: {}'.format(sys.exc_info()[0]))
                    raise
                else:
                    log('Setting verify', level='debug')
                    self.certfile = certfile
                    self.use_cert = True
                    break
        try:
            r = self.get('https://{}/v0'.format(self.endpoint))
            if r.status_code == 401:
                print('You are not logged into registry {}\nRun docker login'.format(self.endpoint))
                if options.pull:
                    sys.exit(3)
            elif [200, 404] not in r.status_code:
                print('{} {}'.format(r.status_code, r.text))
                if options.pull:
                    sys.exit(3)
        except requests.exceptions.SSLError:
            if not options.no_verify:
                # TODO: don't exit the script, throw an error
                err('Cannot verify that you are connecting to the registry you think you are')
                sys.exit(3)
        except requests.exceptions.ConnectionError as e:
            # TODO: pass through error
            err('registry {reg} could not be contacted: {msg}'.format(reg=self.endpoint,
                msg=e))
            sys.exit(3)

    def get(self, uri):
        """Make a request to the registry.

        Returns a raw requests response. Mostly for internal use, but not
        actively discouraged.
        """

        if self.use_cert:
            return self.session.get(uri, verify=self.certfile)
        return self.session.get(uri)

    def get_info_of_repo(self, repo):
        """Return the json object of the specific repo (image and tag)"""

        # log(json.dumps(reg.get_info_of_repo(base), sort_keys=True, indent=4, separators=(',', ': ')))
        response = self.get(
            '{base}/{image}/manifests/{tag}'.format(
                base=self.baseuri,
                image=repo.image,
                tag=repo.tag))
        if response.status_code == 200:
            return response.json()
        return {}

    def get_id_of_repo(self, repo):
        """Return the Image ID if the image exists, otherwise returns empty string"""

        response = self.get(
            '{base}/{image}/manifests/{tag}'.format(
                base=self.baseuri,
                image=repo.image,
                tag=repo.tag))
        if response.status_code == 200:
            return response.json()['fsLayers'][0]['blobSum']
        return ''

    def get_build_date_of_repo(self, repo):
        """Return the string image build date or empty string if doesn't exist"""

        response = self.get(
            '{base}/{image}/manifests/{tag}'.format(
                base=self.baseuri,
                image=repo.image,
                tag=repo.tag))
        if response.status_code == 200:
            return json.loads(response.json()['history'][0]['v1Compatibility'])['created']
        return ''

    def get_tags_of_image(self, image):
        """Returns the list of tags associated with the image.

        This can take some time because of the way Docker structures this data
        """

        response = self.get(
            '{base}/{image}/tags/list').format(
                base=self.baseuri,
                image=image)
        if response.status_code == 200:
            return response.json()['tags']
        return []


class Repository:
    """Container class for holding image repository information.

    These values are provided by you in the constructor
    repo.domain --- the domain name of the registry the image is held in
    repo.port   --- the port the registry is hosted at
    repo.image  --- the name of the image, "ubuntu" as an example
    repo.tag    --- the specific tag referenced, "14.04" as an example

    These values are calculated as niceties
    repo.registry --- the full endpoint ready to be wrapped in 'https://{}/' calls
    repo.repo     --- the full name as specified in a FROM line

    Repository also exposes a Repository.match(str) method which can bes used
    without instantiation which will return a Repository object if you only
    have the combined string version of a repo.
    """

    # This matches more than is valid, but not less than is valid. Notably,
    #    * Slash in the registry portion
    #    * Adjacent periods are accepted
    # But, you had an invalid repo name if you hit either of those.
    matcher = re.compile(r'(?:'
                         r'(?P<domain>localhost|(?:[-_\w]+\.[-_\w]+)+|[-_\w]+(?=:))'
                         r'(?::(?P<port>\d{1,5}))?'
                         r'/)?'
                         r'(?P<image>[-_./\w]+)'
                         r'(?::(?P<tag>[-_.\w]+))?')

    def __init__(self, image, tag='latest', domain=None, port=None):
        """Builds a repository object.

        If you only have the combined string version (like from a FROM line of
        a Dockerfile) use Repository.match(str) to construct a Repository

        Usage:
        Repository('ubuntu')
        Repository('ubuntu', '14.04')
        Repository('my-image', 'dev', 'docker.example.com')
        Repository('my-image', 'dev', 'docker.example.com', '5000')
        Repository('my-image', domain='docker.example.com', port='5002')
        """

        self.domain = domain
        self.port = port
        self.image = image
        self.tag = tag
        if domain and port:
            self.registry = '{}:{}'.format(self.domain, self.port)
        elif domain:
            self.registry = self.domain
        else:
            self.registry = None

        if self.registry:
            self.repo = '{}/{}:{}'.format(self.registry, self.image, self.tag)
        else:
            self.repo = '{}:{}'.format(self.image, self.tag)

    def get_pull_image_name(self):
        """
        This function exists because docker pull is the worst API endpoint.
        docker.Client.pull() does not allow you to specify a registry to pull from,
        but instead believes that ({registry}/){image} is the name of the image.
        """
        if self.registry:
            return "{}/{}".format(self.registry, self.image)
        return self.image

    @classmethod
    def match(cls, text):
        """Uses a regex to construct a Repository. Matches more than is valid,
        but not less than is valid.

        Repository.match('docker.example.com/my-image:dev')
        Repository.match('docker.example.com:5000/my-image:dev')
        Repository.match('docker.example.com/my-image')
        """

        match = Repository.matcher.search(text)
        return Repository(domain=match.group('domain'),
                          port=match.group('port'),
                          image=match.group('image'),
                          tag=match.group('tag') or 'latest')


class Container(object):
    """
    Container is a data structure for a container. Controlfiles that specify
    containers will be read into this structure and have defaults applied where
    a default has not been explicitly overriden.
    """

    expected_timeout = 10
    conf = {
        'name': '',
        'image': '',
        'hostname': None,
    }

    class ContainerException(Exception):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return self.msg

    class AlreadyExists(ContainerException):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return '''Container already exists: {}'''.format(self.msg)

    class DoesNotExist(ContainerException):
        """A much more useful error than docker-py's standard 404 message"""

        def __init__(self, name):
            self.name = name

        def __str__(self):
            return 'Container does not exist: {}'.format(self.name)

    class VolumePseudoExists(ContainerException):
        """Volumes were probably manually removed, but Docker caches volume's existence"""

        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return '''Docker is having trouble creating a volume. Try looking
            at docker volume ls or try restarting the docker daemon.'''

    class InvalidVolumeName(ContainerException):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return self.msg

    class TransientVolumeCreation(ContainerException):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return '''You cannot create transient volumes in the Controlfile.
            Name your volume, or bind it to the host'''

    class NotRunning(ContainerException):
        pass

    def __init__(self, image, conf):
        try:
            self.expected_timeout = conf.pop('expected_timeout')
        except KeyError:
            pass
        try:
            if 'hostname' not in conf:
                conf['hostname'] = conf['name']
        except KeyError:
            pass
        self.conf.update(conf)
        self.conf['image'] = image

    def get_container_options(self):
        conf_copy = self.conf.copy()
        host_config = {}
        try:
            host_config['binds'] = conf_copy.pop('volumes')
        except KeyError:
            pass
        # This calling create_host_config probably doesn't change the dict
        conf_copy['host_config'] = docker.create_host_config(**host_config)
        return conf_copy

    def create(self):
        log(self.conf, level='debug')
        try:
            return CreatedContainer(
                docker.create_container(**self.get_container_options()),
                self.conf)
        except Docker.errors.NotFound as e:
            if 'chown' in e.explanation.decode('utf-8'):
                raise Container.VolumePseudoExists(e.explanation.decode('utf-8'))
            elif 'volume not found' in e.explanation.decode('utf-8'):
                raise Container.TransientVolumeCreation(e.explanation.decode('utf-8'))
            log(e, level='debug')
            log(e.response, level='debug')
            log(e.explanation.decode('utf-8'), level='debug')
            raise
        except Docker.errors.APIError as e:
            if 'volume name invalid' in e.explanation.decode('utf-8'):
                raise Container.InvalidVolumeName(e.explanation.decode('utf-8'))
            elif 'is already in use by container' in e.explanation.decode('utf-8'):
                raise Container.AlreadyExists(e.explanation.decode('utf-8'))
            log(e, level='debug')
            log(e.response, level='debug')
            log(e.explanation.decode('utf-8'), level='debug')
            raise


class CreatedContainer(Container):
    inspect = {}

    def __init__(self, name, conf={}):
        try:
            self.inspect = docker.inspect_container(name)
            super().__init__(self.inspect['Image'], conf)
        except Docker.errors.NotFound as e:
            log(e, level='debug')
            raise Container.DoesNotExist(name)

    def start(self):
        try:
            docker.start(self.inspect['Id'])
        except Docker.errors.NotFound as e:
            if e.explanation.decode('utf-8') == 'get: volume not found':
                raise Container.InvalidVolumeName('volume not found')
            raise
        else:
            self.inspect = docker.inspect_container(self.inspect['Id'])
        return self.inspect['State']['Running']

    def stop(self):
        docker.stop(self.inspect['Id'], timeout=self.expected_timeout)
        self.inspect = docker.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def kill(self):
        docker.kill(self.inspect['Id'])
        self.inspect = docker.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def remove(self):
        docker.remove_container(self.inspect['Id'], v=True)
        try:
            docker.inspect_container(self.inspect['Id'])
            return False
        except Docker.errors.NotFound:
            return True

    def remove_volumes(self):
        if options.debug:
            log('Docker has removed these volumes:', level='debug')
            for v in (v['Source'] for v in self.inspect['Mounts'] if not os.path.isdir(v['Source'])):
                log('  {}'.format(v), level='debug')
            log('Attempting to remove these volume locations:', level='debug')
            for v in (v['Source'] for v in self.inspect['Mounts'] if os.path.isdir(v['Source'])):
                log('  {}'.format(v), level='debug')
        for vol in self.inspect['Mounts']:
            if vol['Source'].startswith('/var/lib/docker/volumes'):
                log('having docker remove {}'.format(vol['Source']), level='debug')
                try:
                    docker.remove_volume(vol['Name'])
                except Docker.errors.APIError as e:
                    if 'no such volume' in e.explanation.decode('utf-8'):
                        continue
                    log('cannot remove volume: {}'.format(e.explanation.decode('utf-8'), level='info'))
            elif os.path.isdir(vol['Source']):
                log('removing {}'.format(vol['Source']), level='debug')
                try:
                    shutil.rmtree(vol['Source'])
                except PermissionError as e:
                    print('Cannot remove directory {}: {}'.format(vol['Source'], e))
            else:
                log('docker removed volume {}'.format(vol['Source']), level='debug')


def image_is_newer(base):  # TODO: finish
    log('is_image_newer', level='debug')
    if base.image == 'scratch':
        err('Control does not handle building FROM scratch yet')
        sys.exit(1)
    elif not base.registry:
        return True  # Giving up on any kind of intelligence in dealing with the Hub.

    log('Contacting registry at {}'.format(base.registry), level='debug')
    reg = Registry(base.domain, base.port)
    try:
        remote_date = dup.parse(reg.get_build_date_of_repo(base))
    except ValueError:
        log('Image does not exist in registry', level='warn')
        return False
    try:
        local_date = dup.parse(docker.inspect_image(base.repo)['Created'])
    except Docker.errors.NotFound:
        log('Image does not exist locally', level='warn')
        return True
    return remote_date > local_date


def pulling(repo):
    """We make use of the difference between None and False, so explicit
    checking against False or True is necessary.
    """

    if options.pull is False:  # We actually do need to check the difference of None and False
        return False
    elif options.func.__name__ in ['default', 'build'] and not repo.registry and not options.pull:
        return False
    return True


def container_is_running(container):
    try:
        return docker.inspect_container(container)['State']['Running']
    except Docker.errors.NotFound:
        return False
    return False


def container_exists(container):
    try:
        docker.inspect_container(container)
        return True
    except Docker.errors.NotFound:
        return False
    return False


def print_formatted(line):
    if options.debug:
        print('bytes: {}'.format(line))
    if len(line) == 1:
        print(list(line.values())[0].strip())
        return
    if 'error' in line.keys():
        print('\x1b[31m{}\x1b[0m'.format(line['error']))
    if 'id' in line.keys() and (line.keys() not in 'progressDetail' or not line['progressDetail']):
        print('{}: {}'.format(line['id'], line['status']))
        return


def build(args):  # TODO: DRY it up
    if args.debug or args.dry_run:
        print('running docker build')
    if not hasattr(args, 'image') or not args.image:
        err('No image name was specified. Edit your Controlfile or specify with -i')
        sys.exit(3)
    if os.path.isfile(args.dockerfile):
        with open(args.dockerfile, 'r') as f:
            for line in f:
                if line.startswith('FROM'):
                    upstream = Repository.match(line.split()[1])
                    break
    else:
        err('Dockerfile does not exist')
        sys.exit(3)
    if pulling(upstream) and image_is_newer(upstream):
        log('pulling upstream', level='debug')
        for line in (json.loads(l.decode('utf-8').strip()) for l in docker.pull(
                stream=True,
                repository=upstream.get_pull_image_name(),
                tag=upstream.tag)):
            print_formatted(line)
    if not args.dry_run:
        for line in (json.loads(l.decode('utf-8').strip()) for l in docker.build(
                path='.',
                tag=args.image,
                nocache=args.no_cache,
                rm=args.no_rm,
                pull=False,
                dockerfile=args.dockerfile)):
            print_formatted(line)
            if 'error' in line.keys():
                return False
    return True


def build_prod(args):
    if args.pull is None:
        args.pull = True
    if args.debug or args.dry_run:
        print('running docker build')
    if not hasattr(args, 'image') or not args.image:
        err('No image name was specified. Edit your Controlfile or specify with -i')
        sys.exit(3)
    if not args.dry_run:
        for line in (json.loads(l.decode('utf-8').strip()) for l in docker.build(
                path='.',
                tag=args.image,
                nocache=args.no_cache,
                rm=args.no_rm,
                pull=args.pull,
                dockerfile=args.dockerfile)):
            print_formatted(line)
            if 'error' in line.keys():
                return False
    print('writing IMAGES.txt')
    if not args.dry_run:
        with open('IMAGES.txt', 'w') as f:
            f.write('{}\n'.format(args.image))
    return True


def start(args):
    # TODO: normalize all the options
    # TODO: parse {collective} out of options in the controlfile
    if options.name:
        options.container['name'] = options.name
    if options.no_volumes:
        options.container['volumes'] = []
    container = Container(options.image, options.container)

    # check if image is newer, start again if image is newer
    try:
        # TODO: if a container exists but the options don't match, log out that
        # we are starting a container that does not match the merged controlfile
        # and cli options
        container = CreatedContainer(options.container['name'], options.container)
    except Container.DoesNotExist:
        pass  # This will probably be the majority case
    print('Starting {}'.format(options.container['name']))
    try:
        container = container.create()
        container.start()
    except Container.ContainerException as e:
        log('outer start containerexception caught', level='debug')
        err(e)
        exit(1)
    return True


def stop(args):
    try:
        container = CreatedContainer(options.container['name'])
        if options.force:
            print('Killing {}'.format(options.container['name']))
            container.kill()
        else:
            print('Stopping {}'.format(options.container['name']))
            container.stop()
        print('Removing {}'.format(options.container['name']))
        container.remove()
        if options.wipe:
            container.remove_volumes()
    except Container.DoesNotExist:
        print('{} does not exist.'.format(options.container['name']))
    except Exception as e:
        log('unexpected error: {}'.format(e), level='error')
        return False
    return True


def restart(args):
    if not stop(args):
        return False
    return start(args)


def default(args):
    ret = build(args)
    if not ret:
        return ret
    if hasattr(args, 'container') and options.container['name']:
        return restart(args)
    return ret


def main():
    # If you set a value that has a default, set it up above, then you must
    # reference that default here, otherwise it will be clobbered
    parser = argparse.ArgumentParser(description='Control the building and running of images and containers')
    parser.add_argument('-d', '--debug', action='store_true', help='print debug information helpful to developing the control script. This probably won\'t be useful to using the script, consider -v')
    parser.add_argument('-f', '--force', action='store_true', help='be forceful in all things')
    parser.add_argument('-n', '--dry-run', action='store_true', help='Pretend to execute actions, but only log that they happened')
    parser.add_argument('-i', '--image', default=options.image, help='override the tagged name of the image being built')
    parser.add_argument('--name', help='the name to give to the container')
    parser.add_argument('--dockerfile', default=options.dockerfile, help='override the dockerfile used to build the image')
    parser.add_argument('--no-cache', action='store_true', help='do not use the cache')
    parser.add_argument('--pull', action='store_const', const=True, dest='pull', help='pull the image from upstream')
    parser.add_argument('--no-pull', action='store_const', const=False, dest='pull', help='do not pull newer versions of the base image')
    parser.add_argument('--no-volumes', action='store_true', help='override the volumes mentioned in the Controlfile')
    parser.add_argument('--no-verify', action='store_true', help='do not check the validity of the registry\'s SSL cert')
    parser.add_argument('--wipe', action='store_true', help='Make sure that volumes are empty after stopping. May require sudo. THIS IS EXTREMELY DANGEROUS')
    parser.add_argument('-V', '--version', action='version', version='%(prog)s v{}'.format(options.version))
    parser.set_defaults(func=default)
    subparsers = parser.add_subparsers()

    # TODO: add child parsers that handle the individual actions
    build_parser = subparsers.add_parser('build', description='Build an image')
    build_parser.add_argument('-i', '--image', default=options.image, help='override the tagged name of the image being built')
    build_parser.add_argument('--dockerfile', default=options.dockerfile, help='override the dockerfile used to build the image')
    build_parser.add_argument('--no-cache', action='store_true', help='do not use the cache')
    build_parser.add_argument('--no-rm', action='store_false', help='do not remove any images, even on success')
    build_parser.add_argument('--no-verify', action='store_true', help='do not check the validity of the registry\'s SSL cert')
    build_parser.add_argument('--pull', action='store_const', const=True, help='pull the image from upstream')
    build_parser.add_argument('--no-pull', action='store_const', const=False, dest='pull', help='do not pull newer versions of the base image')
    build_parser.set_defaults(func=build)

    buildprod_parser = subparsers.add_parser('build-prod', description='''Build a
            production image. This is the option used by Jenkins. No other options
            will be specified, so pick good defaults. Writes a file IMAGES.txt
            which is a newline delimited file of the images that should be pushed
            to the registry.''')
    buildprod_parser.add_argument('-i', '--image', default=options.image, help='override the tagged name of the image being built')
    buildprod_parser.add_argument('--no-cache', default=True, action='store_true', help='allow the build to use the cache')
    buildprod_parser.add_argument('--no-pull', action='store_const', const=False, dest='pull', help='do not pull newer versions of the base image')
    buildprod_parser.set_defaults(func=build_prod)

    start_parser = subparsers.add_parser('start', description='start a container using an image')
    start_parser.add_argument('-n', '--name', help='the name to give to the container')
    start_parser.add_argument('-i', '--image', help='override the tagged name of the image being built')
    start_parser.add_argument('--no-volumes', action='store_true', help='override the volumes mentioned in the Controlfile')
    start_parser.set_defaults(func=start)

    stop_parser = subparsers.add_parser('stop', description='stop a container. This will inform docker to remove volumes that it can remove')
    stop_parser.add_argument('-f', '--force', action='store_true', help='Do not wait for the container to gracefully shut down')
    stop_parser.add_argument('-w', '--wipe', action='store_true', help='Make sure that volumes are empty after stopping. May require sudo. THIS IS EXTREMELY DANGEROUS')
    stop_parser.set_defaults(func=stop)

    restart_parser = subparsers.add_parser('restart', description='remove a container, and start it up again')
    restart_parser.add_argument('-f', '--force', action='store_true', help='Do not wait for the container to gracefully shut down')
    restart_parser.add_argument('-n', '--name', help='the name to give to the container')
    restart_parser.add_argument('-i', '--image', help='override the tagged name of the image being built')
    restart_parser.add_argument('-w', '--wipe', action='store_true', help='Make sure that volumes are empty after stopping. May require sudo. THIS IS EXTREMELY DANGEROUS')
    restart_parser.add_argument('--no-volumes', action='store_true', help='override the volumes mentioned in the Controlfile')
    restart_parser.set_defaults(func=restart)
    parser.parse_args(namespace=options)

    # Read in a Controlfile if one exists
    if os.path.isfile('Controlfile'):
        with open('Controlfile', 'r') as f:
            try:
                vars(options).update(json.load(f))
            except json.decoder.JSONDecodeError as e:
                err('Malformed Controlfile. Not valid JSON: {}'.format(str(e)))
                sys.exit(2)
    else:
        # TODO: When, eventually, you have to do parsing to override defaults and
        # you move to configparser, change this to print conditionally
        print('No Controlfile. Proceeding with defaults')

    if options.debug:
        print('options={}'.format(vars(options)))

    ret = options.func(options)
    if not ret:
        sys.exit(1)

# Handle global defaults here
options = argparse.Namespace()
opts = vars(options)
opts['debug'] = False
opts['image'] = None
opts['dockerfile'] = 'Dockerfile'
opts['name'] = None
opts['no_cache'] = False
opts['no_rm'] = True
opts['no_verify'] = False
opts['pull'] = None
opts['version'] = '2.0'

# Docker.Client doesn't raise an exception. They just crash the program. This
# is the most graceful way I can save this.
if os.path.exists('/var/run/docker.sock'):
    docker = Docker.Client(base_url='unix://var/run/docker.sock')

if __name__ == '__main__':
    main()
