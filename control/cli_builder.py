"""
Sorry for the confusion, the cli_builder builds docker commands. The cli_args
module builds the cli parser for control.

I apologize for the amount of disgusting in this file, but I really didn't want
to manually enumerate all of these lists by writing the full functions.

TODO: Even more strict refactor into:
    Builder
    TargetsBuilder
    TargetArgsBuilder
so the file is shorter and the tests don't have to be as redundant as they are.
"""

from control.exceptions import ControlException

bool_args = [
    ('no_cache', {'arg': '--no-cache', 'doc': 'add --no-cache to the command'}),
    ('force', {'arg': '--force', 'doc': 'pass --force to the command'}),
    ('force_rm', {'arg': '--force-rm', 'doc': 'always remove intermediates'}),
    ('pull', {'arg': '--pull', 'doc': 'add --pull to the command'}),
    ('rm', {'arg': '--rm', 'doc': 'add --rm to the command'}),
    ('detach', {'arg': '--detach', 'doc': 'run the container in the background'}),
    ('interactive', {'arg': '--interactive', 'doc': 'keep STDIN open even if '
                                                    'not attached'}),
    ('tty', {'arg': '--tty', 'doc': 'emulate a TTY for the container to write '
                                    'output to'}),
]

single_args = [
    ('cpu_shares', {'arg': '--cpu-shares', 'doc': 'relative weight of usage of '
                                                  'shared CPU'}),
    ('file', {'arg': '--file', 'doc': 'override default Dockerfile location'}),
    ('tag', {'arg': '--tag', 'doc': 'tag the image that is built'}),
    ('entrypoint', {'arg': '--entrypoint', 'doc': 'set/override an entrypoint '
                                                  'for the container'}),
    ('hostname', {'arg': '--hostname', 'doc': 'set a hostname for the container'}),
    ('ipc', {'arg': '--ipc', 'doc': 'IPC namespace to use'}),
    ('name', {'arg': '--name', 'doc': 'Specify a container name'}),
    ('time', {'arg': '--time', 'doc': 'seconds to wait'}),
    ('user', {'arg': '--user', 'doc': 'specify a username or UID for the '
                                      'processes to be spawned under'}),
    ('workdir', {'arg': '--workdir', 'doc': 'working directory in the container'}),
]

list_args = [
    ('attach', {'arg': '--attach', 'doc': 'add an --attach to the list of '
                                          'arguments'}),
    ('add_host', {'arg': '--add-host', 'doc': 'add host to ip mapping, string '
                                              'in the format: host:ip'}),
    ('device', {'arg': '--device', 'doc': 'pass through device to container'}),
    ('dns', {'arg': '--dns', 'doc': 'set custom DNS servers'}),
    ('dns_opt', {'arg': '--dns-opt', 'doc': 'set DNS options'}),
    ('dns_search', {'arg': '--dns-search', 'doc': 'set a DNS search path'}),
    ('env', {'arg': '--env', 'doc': 'add an environment variable to the '
                                    'container'}),
    ('env_file', {'arg': '--env-file', 'doc': 'specify a file to add '
                                              'additional environment vars to '
                                              'the container'}),
    ('expose', {'arg': '--expose', 'doc': 'bind a port on the host and pass '
                                          'through to the container'}),
    ('group_add', {'arg': '--group-add', 'doc': 'additional groups to join'}),
    ('link', {'arg': '--link', 'doc': 'specify a link to another container'}),
    ('publish', {'arg': '--publish', 'doc': 'open the port in the container '
                                            'to the host'}),
    ('volume', {'arg': '--volume', 'doc': 'bind a volume to the container'}),
    ('volumes_from', {'arg': '--volumes-from', 'doc': 'bind volumes from a '
                                                      'container to this one'}),
]


def builder(command, *args, **kwargs):
    """Choose a builder class to start from"""
    # commands = {
    #     'attach', 'build', 'commit', 'cp', 'create', 'diff', 'events',
    #     'exec', 'export', 'history', 'images', 'import', 'info', 'inspect',
    #     'kill', 'load', 'login', 'logout', 'logs', 'network', 'node', 'pause',
    #     'port', 'ps', 'pull', 'push', 'rename', 'restart', 'rm', 'rmi', 'run',
    #     'save', 'search', 'service', 'start', 'stats', 'stop', 'swarm', 'tag',
    #     'top', 'unpause', 'update', 'version', 'volume',
    # }
    return {
        'build': BuildBuilder(command, *args, **kwargs),
        'exec': ExecBuilder(command, *args, **kwargs),
        'rm': ContainerBuilder(command, *args, **kwargs),
        'rmi': ContainerBuilder(command, *args, **kwargs),
        'run': RunBuilder(command, *args, **kwargs),
        'stop': ContainerBuilder(command, *args, **kwargs)
    }[command]


class Builder:
    """
    Capably builds docker bash invocations. Docker-py should be capable of
    doing this, but there's a long list of that kind of stuff.

    Flags take an optional boolean value. The flag is added to the list of
    arguments if the value is True, and it will be removed if the value is
    False.

    Some arguments accept a single value. Setting this will override any
    previous value.

    Some arguments take a variable number of values (volumes for containers).
    Calling it multiple times will add each new value to the list that will be
    on the command line. You may also pass a list of values to the function.
    """

    def __init__(self, cmd, pretty=True):
        self.cmd = cmd
        if pretty:
            self.sep = ' \\\n\t'
        else:
            self.sep = ' '
        self.bargs = {}
        self.sargs = {}
        self.largs = {}
        self.positional = ''

    def __str__(self):
        concat_args = self.sep.join(str(x) for x in sorted(
            [Argument(k) for k, v in self.bargs.items()] +
            [Argument(k, v) for k, v in self.sargs.items()] +
            [Argument(k, v)
             for k, vs in self.largs.items()
             for v in vs]))
        if concat_args:
            return 'docker {cmd}{sep}{args}{sep}{pos}'.format(
                sep=self.sep,
                cmd=self.cmd,
                args=concat_args,
                pos=self.positional)
        else:
            return 'docker {cmd} {pos}'.format(
                cmd=self.cmd,
                pos=self.positional)


class BuildBuilder(Builder):
    """
    docker build needs a positional argument containing where docker should
    tar up and send to the server to build the image.
    """

    def __init__(self, cmd, pretty=True):
        super(BuildBuilder, self).__init__(cmd, pretty=pretty)
        self.positional = '.'

    def path(self, path):
        """set the path for docker build to find image contents in"""
        self.positional = path
        return self

    def __str__(self):
        if not self.positional:
            raise ControlException('No path declared. Cannot create docker build command')
        return super(BuildBuilder, self).__str__()


class RunBuilder(Builder):
    """docker run is very special, because image is a positional argument
    that does not have an associated (optional) flag, mostly because Docker is
    bad at building CLI utilities."""

    def __init__(self, cmd, pretty=True):
        super(RunBuilder, self).__init__(cmd, pretty=pretty)
        self.image_ = ''
        self.command_ = ''

    def image(self, name):
        """set the image that the container should be using"""
        self.image_ = name
        return self

    def command(self, value):
        """run this command from the entrypoint"""
        if isinstance(value, list):
            self.command_ = ' '.join(value)
        elif isinstance(value, str):
            self.command_ = value
        else:
            raise TypeError(value)
        return self

    def __str__(self):
        if not self.image_:
            raise ControlException('No image declared. Cannot create docker run command')
        s = super(RunBuilder, self).__str__()
        if self.command_:
            return '{}{i}{sep}{cmd}'.format(s, sep=self.sep, i=self.image_, cmd=self.command_)
        else:
            return '{}{i}'.format(s, i=self.image_)


class ExecBuilder(Builder):
    """
    docker exec takes a container a "command" and "args". This is, naturally,
    needlessly complex. The ExecBuilder takes the standard options, a container,
    and a command.
    """

    def __init__(self, cmd, pretty=True):
        super(ExecBuilder, self).__init__(cmd, pretty=pretty)
        self.container_ = ''
        self.command_ = ''

    def container(self, name):
        """set the container the exec should be using"""
        self.container_ = name
        return self

    def command(self, value):
        """run this command from the entrypoint"""
        if isinstance(value, list):
            self.command_ = ' '.join(value)
        elif isinstance(value, str):
            self.command_ = value
        else:
            raise TypeError(value)
        return self

    def __str__(self):
        if not self.container_:
            raise ControlException('No container declared. Cannot create docker exec command')
        if not self.command_:
            raise ControlException('No command declared. Cannot create docker exec command')
        s = super(ExecBuilder, self).__str__()
        return '{}{i}{sep}{cmd}'.format(s,
                                        sep=self.sep,
                                        i=self.container_,
                                        cmd=self.command_)


class ContainerBuilder(Builder):
    """
    Several docker commands take the standard list of options, but want a list
    of containers passed to them as a positional arguments.
    """

    def __init__(self, cmd, pretty=True):
        super(ContainerBuilder, self).__init__(cmd, pretty=pretty)
        self.container_ = []

    def __str__(self):
        if not self.container_:
            # You are correct, rmi will error out saying 'container' instead of
            # image. Deal with it.
            raise ControlException('No container declared. Cannot create '
                                   'docker {} command'.format(self.cmd))
        self.positional = ' '.join(self.container_)
        return super(ContainerBuilder, self).__str__()

    def container(self, value):
        """pass a container (or list of containers) to rm"""
        if value and isinstance(value, list):
            self.container_ += value
        elif value and isinstance(value, set):
            self.container_ += list(value)
        elif value and isinstance(value, str):
            self.container_.append(value)
        else:
            self.container_.append(str(value))
        return self


class Argument:
    """Allow for sorting of arguments correctly"""
    def __init__(self, flag, value=''):
        self.flag = flag
        self.value = value

    def __str__(self):
        if self.value:
            return '{f} {v}'.format(f=self.flag, v=self.value)
        else:
            return self.flag

    def __lt__(self, other):
        return self.flag < other.flag

    def __eq__(self, other):
        return self.flag == other.flag


def bool_setter(name, arg, doc=None):
    """Generates setters for boolean values"""
    def setter(self, value=True):  # pylint: disable=missing-docstring
        if value:
            self.bargs[arg] = value
        elif not value and arg in self.bargs:
            del self.bargs[arg]
        return self
    setter.__doc__ = doc
    setter.__name__ = name
    return setter


def single_setter(name, arg, doc=None):
    """Generates setters for single value arguments"""
    def setter(self, value):  # pylint: disable=missing-docstring
        if value:
            self.sargs[arg] = value
        return self
    setter.__doc__ = doc
    setter.__name__ = name
    return setter


def list_setter(name, arg, doc=None):
    """Generates setters for set value arguments"""
    def setter(self, value):  # pylint: disable=missing-docstring
        if arg not in self.largs:
            self.largs[arg] = []

        if value and isinstance(value, list):
            self.largs[arg] += [str(x) for x in value]
        elif isinstance(value, set):
            self.largs[arg] += [str(x) for x in value]
        elif value and isinstance(value, str):
            self.largs[arg].append(value)
        else:
            self.largs[arg].append(str(value))
        return self
    setter.__doc__ = doc
    setter.__name__ = name
    return setter


for n, v in bool_args:
    setattr(Builder, n, bool_setter(n, **v))
for n, v in single_args:
    setattr(Builder, n, single_setter(n, **v))
for n, v in list_args:
    setattr(Builder, n, list_setter(n, **v))
