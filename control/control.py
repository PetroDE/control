"""
Definitions of the paths that Control can take. build, restart, etc.

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
import json
import logging
import os
import signal
from subprocess import Popen
import sys
import tempfile
import dateutil.parser as dup

import docker

from control.exceptions import ContainerDoesNotExist, ContainerException
from control.options import options
from control.dclient import dclient
from control.container import Container, CreatedContainer
from control.controlfile import Controlfile
from control.registry import Registry
from control.repository import Repository

module_logger = logging.getLogger('control')
module_logger.setLevel(logging.DEBUG)


def sigint_handler(sig, frame):
    """Gracefully handle receiving ctrl-c"""
    print("Killing builds")
    sys.exit(130)


def image_is_newer(base):  # TODO: finish
    module_logger.debug('is_image_newer')
    if base.image == 'scratch':
        module_logger.critical('Control does not handle building FROM scratch yet')
        sys.exit(1)
    elif not base.registry:
        return True  # Giving up on any kind of intelligence in dealing with the Hub.

    module_logger.debug('Contacting registry at %s', base.registry)
    reg = Registry(base.domain, base.port)
    try:
        remote_date = dup.parse(reg.get_build_date_of_repo(base))
    except ValueError:
        module_logger.warning('Image does not exist in registry')
        return False
    try:
        local_date = dup.parse(dclient.inspect_image(base.repo)['Created'])
    except docker.errors.NotFound:
        module_logger.warning('Image does not exist locally')
        return True
    return remote_date > local_date


def pulling(repo):
    """We make use of the difference between None and False, so explicit
    checking against False or True is necessary.
    """

    if options.pull is False:  # We actually do need to check the difference of None and False
        return False
    elif (options.func.__name__ in ['default', 'build'] and
          not repo.registry and
          not options.pull):
        return False
    return True


def print_formatted(line):
    """Strip off all the useless stuff that Docker doesn't bother to parse out."""
    module_logger.debug('bytes: %s', line)
    if len(line) == 1:
        print(list(line.values())[0].strip())
        return
    if 'error' in line.keys():
        print('\x1b[31m{}\x1b[0m'.format(line['error'].strip()))
    if 'id' in line.keys() and ('progressDetail' not in line.keys() or not line['progressDetail']):
        print('{}: {}'.format(line['id'], line['status']))
        return


def run_event(event, env, service):
    """run pre/postbuild, etc. events"""
    try:
        if isinstance(service.events[event], dict):
            cmd = service.events[event][env]
        else:
            cmd = service.events[event]
    except KeyError:
        return True  # There is no event for this event, or for this env

    path = os.getcwd()
    os.chdir(os.path.dirname(service['dockerfile']['dev']))
    with Popen(cmd, shell=True) as p:
        p.wait()
        if p.returncode != 0:
            print("{} action for {} failed. Will not "
                  "continue building service.".format(event, service['name']))
            return False
    os.chdir(path)
    return True


def build(args, ctrl):  # TODO: DRY it up
    """build a development image"""
    module_logger.debug('running docker build')
    print('building services: {}'.format(", ".join(sorted(args.services))))

    module_logger.debug('all services discovered: %s', ctrl.services.keys())
    module_logger.debug(ctrl.services['all'])
    module_logger.debug(ctrl.services['required'])

    for name, service in ((name, ctrl.services[name]) for name in args.services):
        print('building {}'.format(name))
        module_logger.debug(service['image'])
        module_logger.debug(service['controlfile'])
        module_logger.debug(service['dockerfile']['dev'])

        if not run_event('prebuild', 'dev', service):
            continue
        module_logger.debug('End of prebuild')

        # Crack open the Dockerfile to read the FROM line to check about pulling
        with tempfile.NamedTemporaryFile() as tmpfile:
            upstream = None
            with open(service['dockerfile']['dev'], 'r') as f:
                for line in f:
                    if line.startswith('FROM') and service.fromline['dev']:
                        upstream = Repository.match(service.fromline['dev'].split()[1])
                        module_logger.debug('discovered upstream as %s', upstream)
                        tmpfile.write(bytes(service.fromline['dev'], 'utf-8'))
                    elif line.startswith('FROM'):
                        upstream = Repository.match(line.split()[1])
                        module_logger.debug('discovered upstream as %s', upstream)
                        tmpfile.write(bytes(line, 'utf-8'))
                    else:
                        tmpfile.write(bytes(line, 'utf-8'))
                if not upstream:
                    module_logger.warning('Dockerfile does not exist\n'
                                          'Not continuing with this service')
                    continue
            tmpfile.flush()

            if pulling(upstream) and image_is_newer(upstream):
                module_logger.info('pulling upstream %s', upstream)
                for line in (json.loads(l.decode('utf-8').strip()) for l in dclient.pull(
                        stream=True,
                        repository=upstream.get_pull_image_name(),
                        tag=upstream.tag)):
                    print_formatted(line)
            if not args.dry_run:
                build_args = {
                    'path': os.path.dirname(service['dockerfile']['dev']),
                    'tag': service['image'],
                    'nocache': args.no_cache,
                    'rm': args.no_rm,
                    'pull': False,
                    'dockerfile': tmpfile.name,
                }
                module_logger.debug('docker build args: %s', build_args)
                for line in (json.loads(
                        l.decode('utf-8').strip())
                             for l in dclient.build(**build_args)):
                    print_formatted(line)
                    if 'error' in line.keys():
                        return False

        if not run_event('postbuild', 'dev', service):
            print('{}: Your environment may not have been cleaned up'.format(name))
    return True


def build_prod(args, ctrl):
    """Build an image that has everything in it for production"""
    if args.pull is None:
        args.pull = True
    if args.debug or args.dry_run:
        print('running production build')

    for name, service in ((name, ctrl.services[name]) for name in args.services):
        print('building {}'.format(name))

        if not run_event('prebuild', 'prod', service):
            return False
        module_logger.debug('End of prebuild')

        # Crack open the Dockerfile to read the FROM line to check about pulling
        with tempfile.NamedTemporaryFile() as tmpfile:
            upstream = None
            with open(service['dockerfile']['prod'], 'r') as f:
                module_logger.debug('changing from line: %s', service.fromline['prod'])
                for line in f:
                    if line.startswith('FROM') and service.fromline['prod']:
                        upstream = Repository.match(service.fromline['prod'].split()[1])
                        module_logger.debug('discovered upstream as %s', upstream)
                        tmpfile.write(bytes(service.fromline['prod'], 'utf-8'))
                    elif line.startswith('FROM'):
                        upstream = Repository.match(line.split()[1])
                        module_logger.debug('discovered upstream as %s', upstream)
                        tmpfile.write(bytes(line, 'utf-8'))
                    else:
                        tmpfile.write(bytes(line, 'utf-8'))
                if not upstream:
                    module_logger.warning('Dockerfile does not exist\n'
                                          'Not continuing with this service')
                    continue
            tmpfile.flush()

            if not args.dry_run:
                if not pulling(upstream):
                    for line in (
                            json.loads(l.decode('utf-8').strip())
                            for l in dclient.pull(
                                    stream=True,
                                    repository=upstream.get_pull_image_name(),
                                    tag=upstream.tag)):
                        print_formatted(line)
                build_args = {
                    'path': os.path.dirname(service['dockerfile']['prod']),
                    'tag': service['image'],
                    'nocache': args.no_cache,
                    'rm': args.no_rm,
                    'pull': False,
                    'dockerfile': tmpfile.name,
                }
                module_logger.debug('docker build args: %s', build_args)
                for line in (json.loads(l.decode('utf-8').strip())
                             for l in dclient.build(**build_args)):
                    print_formatted(line)
                    if 'error' in line.keys():
                        return False

        if not run_event('postbuild', 'prod', service):
            print('{}: Your environment may not have been cleaned up'.format(name))
            return False
        module_logger.debug('End of postbuild')
    print('writing IMAGES.txt')
    if not args.dry_run:
        with open('IMAGES.txt', 'w') as f:
            f.write('\n'.join([x['image'] for _, x in args.services.items()]))
            f.write('\n')
    return True


def start(args, ctrl):
    for name, service in ((name, ctrl.services[name]) for name in args.services):
        if options.no_volumes:
            service['volumes'] = []
        container = Container(service)

        # check if image is newer, start again if image is newer
        try:
            # TODO: if a container exists but the options don't match, log out that
            # we are starting a container that does not match the merged controlfile
            # and cli options
            container = CreatedContainer(service['name'], service)
        except ContainerDoesNotExist:
            pass  # This will probably be the majority case
        print('Starting {}'.format(service['name']))
        try:
            container = container.create()
            container.start()
        except ContainerException as e:
            module_logger.debug('outer start containerexception caught')
            module_logger.critical(e)
            exit(1)
    return True


def stop(args, ctrl):
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
        module_logger.critical('unexpected error: %s', e)
        return False
    return True


def restart(args, ctrl):
    if not stop(args):
        return False
    return start(args)


def default(args, ctrl):
    ret = build(args, ctrl)
    if not ret:
        return ret
    if hasattr(args, 'container') and options.container['name']:
        return restart(args, ctrl)
    return ret
    module_logger.debug(vars(args))


def main(args):
    # Shut up requests because the user has to make a conscious choice to be
    # insecure
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    console_loghandler = logging.StreamHandler()
    signal.signal(signal.SIGINT, sigint_handler)

    # If you set a value that has a default, set it up above, then you must
    # reference that default here, otherwise it will be clobbered
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument('-d', '--debug', action='store_true', help='print debug information helpful to developing the control script. This probably won\'t be useful to using the script, consider -v')
    shared_parser.add_argument('-f', '--force', action='store_true', help='be forceful in all things')
    shared_parser.add_argument('-i', '--image', default=options.image, help='override the tagged name of the image being built')
    shared_parser.add_argument('-n', '--name', help='the name to give to the container')
    shared_parser.add_argument('-w', '--wipe', action='store_true', help='Make sure that volumes are empty after stopping. May require sudo. THIS IS EXTREMELY DANGEROUS')
    shared_parser.add_argument('--dry-run', action='store_true', help='Pretend to execute actions, but only log that they happened')
    shared_parser.add_argument('--controlfile', default=options.controlfile, help='override the controlfile that lets control know about the services it needs to manage')
    shared_parser.add_argument('--dockerfile', help='override the dockerfile used to build the image')
    shared_parser.add_argument('--pull', action='store_const', const=True, dest='pull', help='pull the image from upstream')
    shared_parser.add_argument('--no-pull', action='store_const', const=False, dest='pull', help='do not pull newer versions of the base image')
    shared_parser.add_argument('--no-volumes', action='store_true', help='override the volumes mentioned in the Controlfile')
    shared_parser.add_argument('--no-rm', action='store_false', help='do not remove any images, even on success')
    shared_parser.add_argument('--no-verify', action='store_true', help='do not check the validity of the registry\'s SSL cert')

    service_parser = argparse.ArgumentParser(add_help=False)
    service_parser.add_argument('services', type=str, nargs='*', help='specify a list of services to operate on. Defaults to all required services')

    parser = argparse.ArgumentParser(
        description='Control the building and running of images and containers',
        parents=[shared_parser])
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version='%(prog)s v{}'.format(options.version))
    parser.add_argument('--no-cache', action='store_true', help='do not use the cache')
    parser.set_defaults(func=default)
    subparsers = parser.add_subparsers()

    # TODO: add child parsers that handle the individual actions
    build_parser = subparsers.add_parser(
        'build',
        description='Build an image',
        parents=[shared_parser, service_parser])
    build_parser.add_argument('--no-cache', action='store_true', help='do not use the cache')
    build_parser.set_defaults(func=build)

    buildprod_parser = subparsers.add_parser(
        'build-prod',
        description='''Build a production image. This is the option used by
            Jenkins. No other options will be specified, so pick good defaults.
            Writes a file IMAGES.txt which is a newline delimited file of the
            images that should be pushed to the registry.''',
        parents=[shared_parser, service_parser])
    buildprod_parser.add_argument('--cache', action='store_false', dest='no_cache', help='allow the use of the docker cache')
    buildprod_parser.set_defaults(func=build_prod)

    start_parser = subparsers.add_parser(
        'start',
        description='start a container using an image',
        parents=[shared_parser])
    start_parser.set_defaults(func=start)

    stop_parser = subparsers.add_parser(
        'stop',
        description='''stop a container. This will inform docker to remove
            volumes that it can remove''',
        parents=[shared_parser, service_parser])
    stop_parser.set_defaults(func=stop)

    restart_parser = subparsers.add_parser(
        'restart',
        description='remove a container, and start it up again',
        parents=[shared_parser, service_parser])
    restart_parser.set_defaults(func=restart)
    parser.parse_args(args, namespace=options)

    if not dclient:
        print('Docker is not running. Please start docker.', file=sys.stderr)
        sys.exit(2)

    if options.debug:
        console_loghandler.setLevel(logging.DEBUG)
    else:
        console_loghandler.setLevel(logging.INFO)
    module_logger.addHandler(console_loghandler)
    module_logger.debug("switching to debug logging")
    module_logger.debug(vars(options))

    # Read in a Controlfile if one exists
    ctrlfile_location = options.controlfile
    try:
        ctrl = Controlfile(ctrlfile_location)
    except NotImplementedError:
        module_logger.info("That's it")

    # If no services were specified on the command line, default to required
    if len(options.services) == 0:
        options.services = ctrl.required_services()

    # Override image name if only one service discovered
    if options.image and len(options.services) == 1:
        ctrl.services[options.services[0]]['image'] = options.image
        module_logger.debug(vars(ctrl.services[options.services[0]]))
    elif options.image and len(options.services) > 1:
        module_logger.info('Ignoring image specified in arguments. Too many services.')
    # Override container name if only one service
    if options.name and len(options.services) == 1:
        ctrl.services[options.services[0]]['name'] = options.name
        module_logger.debug(vars(ctrl.services[options.services[0]]))
    elif options.name and len(options.services) > 1:
        module_logger.info('Ignoring container name specified in arguments. Too many services to start')
    # Override dockerfile location if only one service discovered
    if options.dockerfile and len(options.services) == 1:
        ctrl.services[options.services[0]]['dockerfile'] = options.image
        module_logger.debug(vars(ctrl.services[options.services[0]]))
    elif options.dockerfile and len(options.services) > 1:
        module_logger.info('Ignoring dockerfile specified in arguments. Too many services.')

    module_logger.debug(vars(options))

    ret = options.func(options, ctrl)

    if not ret:
        sys.exit(1)
