"""Build cli arguments"""

import argparse

# from control.functions import (build, build_prod, restart, stop, default,
#                                opencontainer)
from control.options import options


def build_parser():
    """Need a basic parser that is capable of reading in a Controlfile"""
    parser = argparse.ArgumentParser(
        description='Control the building and running of images and containers')

    parser.add_argument('command', type=str, nargs='?', help='the command that Control '
                        'will run.')
    parser.add_argument(
        'services', type=str, nargs='*', help='specify a list of services to '
        'operate on. Defaults to all required services')

    parser.add_argument(
        '-c', '--controlfile', default=options.controlfile, help='override the '
        'controlfile that lets control know about the services it needs to '
        'manage')
    parser.add_argument(
        '-d', '--debug', action='store_true', help='print debug information '
        'helpful to developing the control script. This probably won\'t be '
        'useful to using the script, consider -v')
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version='%(prog)s v{}'.format(options.version))

    parser.add_argument(
        '-f', '--force', action='store_true', help='be forceful in all things')
    parser.add_argument(
        '-i', '--image', default=options.image, help='override the tagged '
        'name of the image being built')
    parser.add_argument(
        '-n', '--name', help='the name to give to the container')
    parser.add_argument(
        '-r', '--replace', action='store_true', help='Use with container '
        'commands. If the container is running the command will take the '
        'container down and run the command exclusively in the container.')
    parser.add_argument(
        '-w', '--wipe', action='store_true', help='Make sure that volumes are '
        'empty after stopping. May require sudo. THIS IS EXTREMELY DANGEROUS')
    parser.add_argument(
        '--dry-run', action='store_true', help='Pretend to execute actions, '
        'but only log that they happened')
    parser.add_argument(
        '--dockerfile', help='override the dockerfile used to build the image')
    parser.add_argument(
        '--cache', action='store_false',
        help='allow the use of the docker cache')
    parser.add_argument(
        '--no-cache', action='store_true', dest='cache',
        help='do not use the cache')
    parser.add_argument(
        '--pull', action='store_const', const=True, dest='pull', help='pull '
        'the image from upstream')
    parser.add_argument(
        '--no-pull', action='store_const', const=False, dest='pull', help='do '
        'not pull newer versions of the base image')
    parser.add_argument(
        '--no-volumes', action='store_true', help='override the volumes '
        'mentioned in the Controlfile')
    parser.add_argument(
        '--no-rm', action='store_false', help='do not remove any images, even '
        'on success')
    parser.add_argument(
        '--no-verify', action='store_true', help='do not check the validity '
        'of the registry\'s SSL cert')

    return parser


def add_command_parser(parser, ctrl, cmd):
    """
    Now that the controlfile has been read in, we can find all of the commands
    that can be run on services
    """
    ls = ctrl.get_all_commands()
    if cmd in ls:
        pass
    global options  # pylint: disable=global-variable-not-assigned

    # If you set a value that has a default, set it up above, then you must
    # reference that default here, otherwise it will be clobbered
    # shared_parser = argparse.ArgumentParser(add_help=False)

    # parser.set_defaults(func=default)
    # subparsers = parser.add_subparsers()

    # TODO: add child parsers that handle the individual actions
    # build_parser = subparsers.add_parser(
    #     'build',
    #     description='Build an image',
    #     parents=[shared_parser, service_parser])
    # buildprod_parser = subparsers.add_parser(
    #     'build-prod',
    #     description='''Build a production image. This is the option used by
    #         Jenkins. No other options will be specified, so pick good defaults.
    #         Writes a file IMAGES.txt which is a newline delimited file of the
    #         images that should be pushed to the registry.''',
    #     parents=[shared_parser, service_parser])
    # start_parser = subparsers.add_parser(
    #     'start',
    #     description='start a container using an image',
    #     parents=[shared_parser, service_parser])
    # stop_parser = subparsers.add_parser(
    #     'stop',
    #     description='''stop a container. This will inform docker to remove
    #         volumes that it can remove''',
    #     parents=[shared_parser, service_parser])
    # restart_parser = subparsers.add_parser(
    #     'restart',
    #     description='remove a container, and start it up again',
    #     parents=[shared_parser, service_parser])
    # rere_parser = subparsers.add_parser(
    #     'rere',
    #     description='rere a container using an image',
    #     parents=[shared_parser, service_parser])
    # open_parser = subparsers.add_parser(
    #     'open',
    #     description='Open a shell in the container instead of the usual entrypoint',
    #     parents=[shared_parser, service_parser])
    # build_parser.set_defaults(cache=True, pull=True, func=build)
    # buildprod_parser.set_defaults(cache=False, pull=True, func=build_prod)
    # start_parser.set_defaults(func=restart)
    # stop_parser.set_defaults(func=stop)
    # restart_parser.set_defaults(func=restart)
    # rere_parser.set_defaults(cache=True, func=default)
    # open_parser.set_defaults(func=opencontainer)
