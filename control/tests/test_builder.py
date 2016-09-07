"""test the cli_builder module"""

import unittest

from control.cli_builder import builder, Argument
from control.exceptions import ControlException


class BuilderFormattingTests(unittest.TestCase):
    """
    Tests to make sure that the builders correctly create newlines when they
    should.
    Tests to make sure that the builders sort flags correctly, and stable sort
    multiple options passed to the same flag.
    """

    def test_no_pretty(self):
        """Everything should show up on one line"""
        result = builder('build', pretty=False).tag('busybox').pull().rm()
        self.assertEqual(str(result),
                         "docker build --pull --rm --tag busybox .")
        result = builder('run', pretty=False).image('busybox')
        self.assertEqual(str(result),
                         "docker run busybox")
        result = builder('run', pretty=False) \
            .detach() \
            .tty() \
            .user('foobar') \
            .hostname('foo') \
            .volume('/mnt:/mnt') \
            .image('busybox') \
            .command('cat')
        self.assertEqual(str(result),
                         "docker run --detach --hostname foo --tty "
                         "--user foobar --volume /mnt:/mnt busybox cat")

    def test_pretty(self):
        """
        Flags should show up one per line. Positional arguments should all be
        on one line.
        """
        result = builder('build').tag('busybox').pull().rm()
        self.assertEqual(str(result),
                         "docker build \\\n\t--pull \\\n\t--rm \\\n\t"
                         "--tag busybox \\\n\t.")
        result = builder('run').image('busybox')
        self.assertEqual(str(result),
                         "docker run busybox")
        result = builder('run') \
            .detach() \
            .tty() \
            .user('foobar') \
            .hostname('foo') \
            .volume('/mnt:/mnt') \
            .image('busybox') \
            .command('cat')
        self.assertEqual(str(result),
                         "docker run \\\n\t--detach \\\n\t--hostname foo \\\n\t"
                         "--tty \\\n\t--user foobar \\\n\t"
                         "--volume /mnt:/mnt \\\n\tbusybox \\\n\tcat")

    def test_sorting(self):
        """
        Make sure that flags are spit out in alphabetized order so they
        easier to visually inspect. But make sure that multiple arguments to
        flags are kept in the order they were specified, this way we don't
        break intentional overrides
        """
        result = builder('run', pretty=False) \
            .image('ubuntu') \
            .tty() \
            .interactive() \
            .volume('/mnt:/mnt') \
            .volume('/home:/home') \
            .volume('/var/foo:/var/foo') \
            .user('1000') \
            .volume('/var/foo:/usr/share/lib/foo') \
            .volume([
                '/var/lib/bucket:/var/lib/bucket',
                '/home:/home',
            ]) \
            .volume({'/var/log/foo:/foo/log'}) \
            .entrypoint('/bin/bash')
        self.assertEqual(str(result),
                         "docker run --entrypoint /bin/bash --interactive --tty "
                         "--user 1000 "
                         "--volume /mnt:/mnt "
                         "--volume /home:/home "
                         "--volume /var/foo:/var/foo "
                         "--volume /var/foo:/usr/share/lib/foo "
                         "--volume /var/lib/bucket:/var/lib/bucket "
                         "--volume /home:/home "
                         "--volume /var/log/foo:/foo/log "
                         "ubuntu")

    def test_single_values_overwrite(self):
        """
        When you set a single value, and then set it again. The later value
        should have precedence
        """
        result = builder('build', pretty=False).tag('foobar').tag('alpine:test')
        self.assertEqual(str(result),
                         "docker build --tag alpine:test .")


class BuildingSetterTests(unittest.TestCase):
    """
    Test any other generic setter behavior that wasn't already tested by
    checking any other functionality
    """

    def test_bool_arg_removal(self):
        """
        Test that passing a False to a boolean setter removes the option
        from output
        """
        result = builder('build', pretty=False).tty(False)
        self.assertEqual(str(result),
                         "docker build .")
        result = result.tty()
        self.assertEqual(str(result),
                         "docker build --tty .")
        result = result.tty(False)
        self.assertEqual(str(result),
                         "docker build .")

    def test_list_arg_invalid_type_raises(self):
        """
        Make sure that if something that doesn't boil down to a string
        raises an exception
        """
        result = builder('run', pretty=False).image('busybox').attach(0)
        self.assertEqual(str(result),
                         "docker run --attach 0 busybox")
        result = builder('run', pretty=False).image('busybox').attach([0])
        self.assertEqual(str(result),
                         "docker run --attach 0 busybox")
        result = builder('run', pretty=False).image('busybox').attach({0})
        self.assertEqual(str(result),
                         "docker run --attach 0 busybox")
        result = builder('run', pretty=False).image('busybox').attach((0))
        self.assertEqual(str(result),
                         "docker run --attach 0 busybox")


class ArgumentTests(unittest.TestCase):
    """Test Arguments on their own"""

    def test_str(self):
        """
        Ensure that Arguments turn into strings without unnecessary extra
        whitespace
        """
        self.assertEqual(str(Argument('-f')), "-f")
        self.assertEqual(str(Argument('--follow', "true")), "--follow true")

    def test_lt(self):
        """Make sure we overrode __lt__ correctly"""
        self.assertLess(Argument('-a'), Argument('-b'))
        self.assertLess(Argument('-a'), Argument('-ab'))
        self.assertLess(Argument('-a', 'foobar'), Argument('-ab'))

    def test_eq(self):
        """Make sure we overrode __eq__ correctly"""
        self.assertEqual(Argument('-a'), Argument('-a'))
        self.assertEqual(Argument('-a'), Argument('-a', 'foobar'))
        self.assertEqual(Argument('-a', 'foobar'), Argument('-a', 'foobar'))
        self.assertNotEqual(Argument('-a'), Argument('-b'))
        self.assertNotEqual(Argument('-a', 'foobar'), Argument('-b', 'foobar'))
        self.assertNotEqual(Argument('-a', 'foobar'), Argument('-b'))


class BuildBuilderTest(unittest.TestCase):
    """Make sure that build output is correct"""

    def test_no_options(self):
        """
        Make sure that with no extra options a valid docker build command is
        created
        """
        result = builder('build')
        self.assertEqual(str(result),
                         "docker build .")
        result = builder('build', pretty=False)
        self.assertEqual(str(result),
                         "docker build .")

    def test_tagged(self):
        """Make sure that a tag is stuck on correctly"""
        result = builder('build', pretty=False).tag('foobar')
        self.assertEqual(str(result),
                         "docker build --tag foobar .")

    def test_nondefault_path(self):
        """
        Make sure that changing the path from the default results in modified
        output
        """
        result = builder('build', pretty=False).tag('foobar').path('build')
        self.assertEqual(str(result),
                         "docker build --tag foobar build")

    def test_broken_path(self):
        """In case you do weird stuff and null out the default path"""
        result = builder('build').path('')
        with self.assertRaises(ControlException):
            str(result)


class RunBuilderTests(unittest.TestCase):
    """make sure that run commands are correct"""

    def test_incompatible_command_raises(self):
        """make sure a command that isn't a list or a string are unhappy"""
        with self.assertRaises(TypeError):
            builder('run').command((0, 1))

    def test_pass_command_list(self):
        """
        docker-py accepts command as a list. I want to be able to pass that
        straight into this library and have it work correctly
        """
        result = builder('run', pretty=False).image('busybox').command(
            ['ps', 'aux']
        )
        self.assertEqual(str(result),
                         "docker run busybox ps aux")

    def test_raises_if_no_image(self):
        """
        docker run needs an image to start a container from, and there's no
        good way to assume a default, so we just force the user to specify an
        image before they try to get the cli command
        """
        result = builder('run').env('FOO=bar').user('1000').detach()
        with self.assertRaises(ControlException):
            str(result)
