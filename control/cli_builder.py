"""
Sorry for the confusion, the cli_builder builds docker commands. The cli_args
module builds the cli parser for control.

I apologize for the amount of disgusting in this file, but I really didn't want
to manually enumerate all of these lists by writing the full functions.
"""

from control.exceptions import ControlException

bool_args = [
    ('no_cache', {'arg': '--no-cache', 'doc': 'add --no-cache to the command'}),
    ('pull', {'arg': '--pull', 'doc': 'add --pull to the command'}),
    ('rm', {'arg': '--rm', 'doc': 'add --rm to the command'}),
]

single_args = [
    ('path', {'arg': '--file', 'doc': 'override default Dockerfile location'}),
    ('tag', {'arg': '--tag', 'doc': 'tag the image that is built'}),
]

set_args = [
    ('attach', {'arg': '--attach', 'doc': 'add an --attach to the list of '
                                          'arguments'}),
]


def builder(command, **kwarg):
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
        'build': Builder(command, **kwarg),
        'exec': Builder(command, **kwarg),
        'rm': Builder(command, **kwarg),
        'rmi': Builder(command, **kwarg),
        'run': RunBuilder(command, **kwarg),
        'stop': Builder(command, **kwarg)
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
            self.sep = '\\\n\t'
        else:
            self.sep = ' '
        self.bargs = {}
        self.sargs = {}
        self.largs = {}

    def __str__(self):
        list_args = sorted(
            [Argument(k) for k, v in self.bargs.items()] +
            [Argument(k, v) for k, v in self.sargs.items()] +
            [Argument(k, v)
             for k, vs in self.largs.items()
             for v in vs])
        return 'docker {cmd}{sep}{args}'.format(
            sep=self.sep,
            cmd=self.cmd,
            args=self.sep.join(str(x) for x in list_args))


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
            return '{}{sep}{i}{sep}{cmd}'.format(s, sep=self.sep, i=self.image_, cmd=self.command_)
        else:
            return '{}{sep}{i}'.format(s, sep=self.sep, i=self.image_)


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
        elif not value and arg in self.args:
            del self.args[arg]
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


def set_setter(name, arg, doc=None):
    """Generates setters for set value arguments"""
    def setter(self, value):  # pylint: disable=missing-docstring
        if arg not in self.largs:
            self.largs[arg] = set()

        if value and (isinstance(value, list) and isinstance(value, set)):
            self.largs[arg] |= value
        elif value and isinstance(value, str):
            self.largs[arg].add(value)
        else:
            raise AttributeError(value)
        return self
    setter.__doc__ = doc
    setter.__name__ = name
    return setter


for n, v in bool_args:
    setattr(Builder, n, bool_setter(n, **v))
for n, v in single_args:
    setattr(Builder, n, single_setter(n, **v))
for n, v in set_args:
    setattr(Builder, n, set_setter(n, **v))
