"""Testing options in nested Controlfiles"""

import unittest

from control.controlfile import satisfy_nested_options


class TestNestedOptions(unittest.TestCase):
    """
    Make sure that we end up with correct options when you discover new
    metaservice Controlfiles.
    """

    def test_suffix(self):
        """
        Make sure that appended options are appended in the right order:
        """
        outer_options = {
            "name": {"suffix": ".outer"},
            "dns_search": {"suffix": ".outer"}
        }
        inner_options = {
            "name": {"suffix": ".inner"},
            "hostname": {"suffix": ".inner"}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['name']['suffix'],
            ".inner.outer")
        self.assertEqual(
            ret['dns_search']['suffix'],
            ".outer")
        self.assertEqual(
            ret['hostname']['suffix'],
            '.inner')

    def test_prefix(self):
        """Make sure prepend works in the other direction from append"""
        outer_options = {
            "name": {"prefix": "outer."},
            "env": {"prefix": "OUTER_"},
        }
        inner_options = {
            "hostname": {"prefix": "inner."},
            "env": {"prefix": "INNER_"},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['env']['prefix'],
            "OUTER_INNER_")
        self.assertEqual(
            ret['name']['prefix'],
            "outer.")
        self.assertEqual(
            ret['hostname']['prefix'],
            "inner.")

    def test_union(self):
        """Make sure that we end up with a union of the two lists"""
        outer_options = {
            "dns_search": {"union": ["outer"]},
            "volumes": {"union": ["outer:/var/outer"]},
        }
        inner_options = {
            "env": {"union": ["INNER=inner"]},
            "dns_search": {"union": ["inner"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            set(ret['dns_search']['union']),
            set(['outer', 'inner']))
        self.assertEqual(
            ret['volumes']['union'],
            {'outer:/var/outer'})
        self.assertEqual(
            ret['env']['union'],
            {'INNER=inner'})

    def test_replace(self):
        """Make sure that the outer value replaces the inner value"""
        outer_options = {
            "image": {"replace": "outer"},
            "user": {"replace": "outer"}
        }
        inner_options = {
            "image": {"replace": "inner"},
            "working_dir": {"replace": "inner"}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['image']['replace'],
            "outer")
        self.assertEqual(
            ret['user']['replace'],
            "outer")
        self.assertEqual(
            ret['working_dir']['replace'],
            "inner")

    @unittest.expectedFailure
    def test_suffix_union(self):
        """
        Make sure that appended options are appended in the right order:
        """
        outer_options = {
            "dns_search": {"suffix": ".outer"}
        }
        inner_options = {
            "dns_search": {"union": ["inner"]}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            set(ret['dns_search']['union']),
            {"inner.outer", "outer"})
        self.assertEqual(
            ret['dns_search']['suffix'],
            '.outer')

    @unittest.expectedFailure
    def test_union_suffix(self):
        """
        Make sure that appended options are appended in the right order:
        """
        outer_options = {
            "dns_search": {"union": ["outer"]}
        }
        inner_options = {
            "dns_search": {"suffix": ".inner"}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            set(ret['dns_search']['union']),
            {"outer"})
        self.assertEqual(
            ret['dns_search']['suffix'],
            '.inner')
