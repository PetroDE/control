"""Testing options in nested Controlfiles"""

import unittest

from .context import control


class TestNestedOptions(unittest.TestCase):
    """
    Make sure that we end up with correct options when you discover new
    metaservice Controlfiles.
    """

    def setUp(self):
        self.outer_options = {
            "name": {"suffix": ".outer"},
            "env": {"prefix": "OUTER_"},
            "dns_search": {
                "suffix": ".outer",
                "union": ["outer"],
            },
            "volumes": {"union": ["logdir:/var/log"]}
        }
        self.inner_options = {
            "name": {"suffix": ".inner"},
            "hostname": {"suffix": ".inner"},
            "env": {"prefix": "INNER_"},
            "dns_search": {"union": ["inner"]}
        }
        self.ret = control.Controlfile.satisfy_nested_options(
            self.outer_options,
            self.inner_options)

    def test_suffix(self):
        """Make sure that appended options are appended in the right order"""
        self.assertEqual(
            self.outer_options['name']['suffix'],
            ".outer")
        self.assertEqual(
            self.inner_options['name']['suffix'],
            ".inner")
        self.assertEqual(
            self.ret['name']['suffix'],
            ".inner.outer")
        self.assertEqual(
            set(self.ret['dns_search']['union']),
            {"inner.outer", "outer"})
        self.assertEqual(
            self.ret['hostname']['suffix'],
            '.inner')

    def test_prefix(self):
        """Make sure prepend works in the other direction from append"""
        self.assertEqual(
            self.outer_options['env']['prefix'],
            "OUTER_")
        self.assertEqual(
            self.inner_options['env']['prefix'],
            "INNER_")
        self.assertEqual(
            self.ret['env']['prefix'],
            "OUTER_INNER_")

    def test_union(self):
        """Make sure that we end up with a union of the two lists"""
        self.assertEqual(
            self.outer_options['dns_search']['union'],
            ["outer"])
        self.assertEqual(
            self.inner_options['dns_search']['union'],
            ["inner"])
        self.assertEqual(
            set(self.ret['dns_search']['union']),
            set(['outer', 'inner.outer']))
