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
import json
# import logging
import os
import sys
import dateutil.parser as dup

import docker

from control.options import options
from control.dclient import dclient
from control.registry import Registry
from control.repository import Repository
from control.container import Container, CreatedContainer
from control.shittylogging import err, log


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
        local_date = dup.parse(dclient.inspect_image(base.repo)['Created'])
    except docker.errors.NotFound:
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
        return dclient.inspect_container(container)['State']['Running']
    except docker.errors.NotFound:
        return False
    return False


def container_exists(container):
    try:
        dclient.inspect_container(container)
        return True
    except docker.errors.NotFound:
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
        for line in (json.loads(l.decode('utf-8').strip()) for l in dclient.pull(
                stream=True,
                repository=upstream.get_pull_image_name(),
                tag=upstream.tag)):
            print_formatted(line)
    if not args.dry_run:
        for line in (json.loads(l.decode('utf-8').strip()) for l in dclient.build(
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
        for line in (json.loads(l.decode('utf-8').strip()) for l in dclient.build(
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


def main(args):
    # Shut up requests because the user has to make a conscious choice to be
    # insecure
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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
