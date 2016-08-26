"""The high level operations that Control can perform"""

import json
import logging
import os
from subprocess import Popen
import sys
import tempfile

import dateutil.parser as dup
import docker

from control.container import Container, CreatedContainer
from control.dclient import dclient
from control.exceptions import ContainerDoesNotExist, ContainerException
from control.options import options
from control.registry import Registry
from control.repository import Repository
from control.service import UniService


module_logger = logging.getLogger('control.functions')
module_logger.setLevel(logging.DEBUG)


def image_is_newer(base):
    """
    Check if the image in the registry is newer
    TODO: I don't think this is needed at all
    """
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
    elif (options.command in ['default', 'build'] and
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


def function_dispatch(args, ctrl):
    """Decide which function to call"""
    try:
        return dispatch_dict[options.command](args, ctrl)
    except KeyError:
        pass
    return command(args, ctrl)


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

    for name, service in sorted(((name, ctrl.services[name]) for name in args.services)):
        print('building {}'.format(name))
        module_logger.debug(type(service))
        module_logger.debug(service.__dict__)
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

    for name, service in sorted(((name, ctrl.services[name]) for name in args.services)):
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
            f.write('\n'.join([ctrl.services[x]['image'] for x in args.services]))
            f.write('\n')
    return True


def start(args, ctrl):
    """starting containers"""
    for service in sorted((ctrl.services[name]
                           for name in args.services
                           if isinstance(ctrl.services[name], UniService))):
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
    return True


def stop(args, ctrl):
    """stopping containers"""
    module_logger.debug(", ".join(sorted(args.services)))
    for service in sorted((ctrl.services[name]
                           for name in args.services
                           if isinstance(ctrl.services[name], UniService))):
        try:
            container = CreatedContainer(service['name'], service)
            if options.force:
                print('Killing {}'.format(service['name']))
                container.kill()
            else:
                print('Stopping {}'.format(service['name']))
                container.stop()
            print('Removing {}'.format(service['name']))
            container.remove()
            if options.wipe:
                container.remove_volumes()
        except ContainerDoesNotExist:
            print('{} does not exist.'.format(service['name']))
    return True


def restart(args, ctrl):
    """stop containers, and start them again"""
    if not stop(args, ctrl):
        return False
    return start(args, ctrl)


def opencontainer(args, ctrl):
    """handles opening a container for dev work"""
    if len(args.services) > 1:
        print('Cannot open more than 1 service in 1 call')
        return False
    name = args.services[0]
    try:
        if isinstance(ctrl.services[name]['open'], list):
            (
                ctrl.services[name]['entrypoint'],
                ctrl.services[name]['command']) = (
                    ctrl.services[name]['open'][0],
                    ctrl.services[name]['open'][1:])
        elif isinstance(ctrl.services[name]['open'], str):
            # split on the first space
            ctrl.services[name]['entrypoint'], \
                ctrl.services[name]['command'] = \
                ctrl.services[name]['open'].partition(' ')[::2]
    except KeyError:
        print("'open' not defined for service. Using /bin/sh as entrypoint")
        ctrl.services[name]['entrypoint'] = '/bin/sh'
        ctrl.services[name]['command'] = ''
    ctrl.services[name]['stdin_open'] = True
    ctrl.services[name]['tty'] = True
    try:
        container = CreatedContainer(ctrl.services[name]['name'], ctrl.services[name])
    except ContainerDoesNotExist:
        pass  # We need the container to not exist
    else:
        if not (container.stop() and container.remove()):
            print('could not stop {}'.format(ctrl.services[name]['name']))
            return False
    container = Container(ctrl.services[name]).create()
    os.execlp('docker', 'docker', 'start', '-a', '-i', ctrl.services[name]['name'])


def default(args, ctrl):
    """build containers and restart them"""
    if build(args, ctrl):
        return restart(args, ctrl)
    return False


def command(args, ctrl):
    """
    Call a custom command on a container. If the container wasn't running
    before the command was run, then the container is left in  the same state.
    """
    for service in sorted(
            ctrl.services[name]
            for name in args.services
            if (options.command in ctrl.services[name].commands.keys() or
                    '*' in ctrl.services[name].commands.keys())):
        entry, cmd = service.commands[options.command
                                      if options.command in service.commands.keys()
                                      else '*'
                                     ].partition(' ')[::2]
        service['entrypoint'] = entry
        service['command'] = cmd.format(COMMAND=options.command)

        try:
            container = CreatedContainer(service['name'], service)
            did_not_exist = False
        except ContainerDoesNotExist:
            container = Container(service)
            did_not_exist = True
        if did_not_exist:
            try:
                container = container.create()
                container.start()
            except ContainerException as e:
                module_logger.debug('outer start containerexception caught')
                module_logger.critical(e)
            output = container.logs(from_start=True)
        else:
            output = container.exec(' '.join([service['entrypoint'],
                                              service['command']]))
        for line in (l.decode('utf-8').strip() for l in output):
            print(line)

        if did_not_exist:
            if options.force:
                module_logger.debug('Killing %s', service['name'])
                container.kill()
            else:
                module_logger.debug('Stopping %s', service['name'])
                container.stop()
            module_logger.debug('Removing %s', service['name'])
            container.remove()
            if options.wipe:
                container.remove_volumes()
    return True


dispatch_dict = {
    "start": restart,
    "restart": restart,
    "rere": default,
    "stop": stop,
    "open": opencontainer,
    "build": build,
    "build-prod": build_prod,
    "default": default,
}
