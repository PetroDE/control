"""Testing options in nested Controlfiles"""

import unittest

from control.substitution import satisfy_nested_options


class TestSuffixOptions(unittest.TestCase):
    """
    Make sure that options suffix substitutions correctly nest. Test functions
    are named with test_OUTERKIND_INNERKIND

    Definition of suffix:
        Thing being suffixed should ALWAYS end up at the end of the starting object
    """

    def test_singular_singular(self):
        """
        Make sure that individual string suffixes occur correctly

        Outerfile:
        {
            "services": {
                "foo": { "controlfile": "InnerFile" }
            },
            "options": {
                "name": {
                    "suffix": ".foo"
                }
            }
        }

        Innerfile:
        {
            "services": { ... },
            "options": {
                "name": {
                    "suffix": ".bar"
                }
            }
        }

        Joined suffix: ".bar.foo"
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

    def test_singular_list(self):
        """
        The outer layer Controlfile defines a list of suffixes, it is being
        applied to a Controlfile with a singular suffix:

        Outerfile:
        {
            "services": {
                "foo": { "controlfile": "InnerFile" }
            },
            "options": {
                "dns": {
                    "suffix": "bar"
                }
            }
        }

        Innerfile:
        {
            "services": { ... },
            "options": {
                "dns": {
                    "suffix": [ "one", "two" ]
                }
            }
        }

        Joined suffix: [ "one", "two", "bar" ]
        """
        outer_options = {
            "dns": {"suffix": "outer"},
            "volumes": {"suffix": ["outer"]},
        }
        inner_options = {
            "dns": {"suffix": ["one", "two"]},
            "dns_search": {"suffix": ["one", "one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            ['one', 'two', 'outer'])
        self.assertEqual(
            ret['dns_search']['suffix'],
            ['one', 'one.two'])
        self.assertEqual(
            ret['volumes']['suffix'],
            ['outer'])

    def test_singular_dict(self):
        """
        The outer layer Controlfile defines a list of suffixes, it is being
        applied to a Controlfile with a singular suffix:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"suffix": 'outer'},
            "dockerfile": {"suffix": ".outer"},
            "volumes": {"suffix": "outer"}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"suffix": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure singular dict:list suffixes work
            "dns_search": {"suffix": {"dev": "one.two", "shared": "inner"}}, # ensure outer creation works
            "dockerfile": {"suffix": {"dev": "innerdev", "shared": "innershared"}}, # ensure singular dict:singular suffixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            {'shared': ['dev.inner', 'inner', 'outer'], 'dev': ['dev']})
        self.assertEqual(
            ret['dns_search']['suffix'],
            {'dev': 'one.two', 'shared': 'inner'})
        self.assertEqual(
            ret['dockerfile']['suffix'],
            {'dev': 'innerdev', 'shared': 'innershared.outer'})
        self.assertEqual(
            ret['volumes']['suffix'],
            'outer')

    def test_list_singular(self):
        """
        The outer layer Controlfile defines a list of suffixes, it is being
        applied to a Controlfile with a singular suffix:

        Outerfile:
        {
            "services": {
                "foo": { "controlfile": "InnerFile" }
            },
            "options": {
                "name": {
                    "suffix": [ ".one", ".two" ]
                }
            }
        }

        Innerfile:
        {
            "services": { ... },
            "options": {
                "name": {
                    "suffix": ".bar"
                }
            }
        }

        Joined suffix: [ ".bar", ".one", ".two" ]
        """
        outer_options = {
            "dns": {"suffix": ["one", "two"]},
            "volumes": {"suffix": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"suffix": "inner"},
            "dns_search": {"suffix": "one.two"},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            ['inner', 'one', 'two'])
        self.assertEqual(
            ret['dns_search']['suffix'],
            'one.two')
        self.assertEqual(
            ret['volumes']['suffix'],
            ['outer', 'testtwo'])

    def test_list_list(self):
        """
        The outer layer Controlfile defines a list of suffixes, it is being
        applied to a Controlfile with a singular suffix:

        Outerfile:
        {
            "services": {
                "foo": { "controlfile": "InnerFile" }
            },
            "options": {
                "name": {
                    "suffix": [ ".one", ".two" ]
                }
            }
        }

        Innerfile:
        {
            "services": { ... },
            "options": {
                "name": {
                    "suffix": ".bar"
                }
            }
        }

        Joined suffix: [ ".bar", ".one", ".two" ]
        """
        outer_options = {
            "dns": {"suffix": ["one", "two"]},
            "volumes": {"suffix": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"suffix": ["inner"]},
            "dns_search": {"suffix": ["one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            ['inner', 'one', 'two'])
        self.assertEqual(
            ret['dns_search']['suffix'],
            ['one.two'])
        self.assertEqual(
            ret['volumes']['suffix'],
            ['outer', 'testtwo'])

    def test_list_dict(self):
        """
        The outer layer Controlfile defines a list of suffixes, it is being
        applied to a Controlfile with a singular suffix:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"suffix": ["outer"]},
            "dockerfile": {"suffix": [".outer"]},
            "volumes": {"suffix": ["outer"]}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"suffix": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure list dict:list suffixes work
            "dns_search": {"suffix": {"dev": ["one.two"], "shared": ["inner"]}}, # ensure outer creation works
            "dockerfile": {"suffix": {"dev": "innerdev", "shared": "innershared"}}, # ensure list dict:singular suffixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            {'shared': ['dev.inner', 'inner', 'outer'], 'dev': ['dev']})
        self.assertEqual(
            ret['dns_search']['suffix'],
            {'dev': ['one.two'], 'shared': ['inner']})
        self.assertEqual(
            ret['dockerfile']['suffix'],
            {'dev': 'innerdev', 'shared': ['innershared', '.outer']})
        self.assertEqual(
            ret['volumes']['suffix'],
            ['outer'])

    def test_dict_singular(self):
        """
        The outer layer Controlfile defines a dict of suffixes, it is being
        applied to a Controlfile with a singular suffix
        """
        outer_options = {
            "dns": {"suffix": {"dev": ["one", "two"]}},
            "dockerfile": {"suffix": {"dev": ".dev", "prod": ".prod", "shared": ".shared"}},
            "volumes": {"suffix": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"suffix": "inner"}, # ensure dict:list singular suffixes work
            "dns_search": {"suffix": "one.two"}, # ensure outer creation works
            "dockerfile": {"suffix": "dockerfile"}, # ensure dict:singular singular suffixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            {'shared': 'inner', 'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['suffix'],
            'one.two')
        self.assertEqual(
            ret['dockerfile']['suffix'],
            {'dev': '.dev', 'shared': 'dockerfile.shared', 'prod': '.prod'})
        self.assertEqual(
            ret['volumes']['suffix'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_list(self):
        """
        The outer layer Controlfile defines a dict of suffixes, it is being
        applied to a Controlfile with a singular suffix
        """
        outer_options = {
            "dns": {"suffix": {"dev": ["one", "two"]}},
            "dockerfile": {"suffix": {"dev": ".dev", "prod": ".prod", "shared": ".shared"}},
            "volumes": {"suffix": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"suffix": ["inner"]}, # ensure dict:list list suffixes work
            "dns_search": {"suffix": ["one.two"]}, # ensure outer creation works
            "dockerfile": {"suffix": ["dockerfile"]}, # ensure dict:singular list suffixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['suffix'],
            {'shared': ['inner'], 'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['suffix'],
            ['one.two'])
        self.assertEqual(
            ret['dockerfile']['suffix'],
            {'dev': '.dev', 'shared': ['dockerfile', '.shared'], 'prod': '.prod'})
        self.assertEqual(
            ret['volumes']['suffix'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_dict(self):
        """
        The outer layer Controlfile defines a dict of suffixes, it is being
        applied to a Controlfile with a singular suffix
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dockerfile": {"suffix": {"prod": ".outerprod", "shared": ".outer"}},
            "dns": {"suffix": {"prod": "outerprod", "shared": "outer"}},
            "domainname": {"suffix": {"prod": ["outerprod"], "shared": ["outer"]}},
            "volumes": {"suffix": {"prod": ["outerprod"], "shared": ["outer"]}},
            "labels": {"suffix": {"shared": ["outer", "outertwo"], "prod": ["outerprod"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns_search": {"suffix": {"dev": ["one.two"]}}, # ensure outer creation works
            "dockerfile": {"suffix": {"dev": ".innerdev", "shared": ".inner"}}, # ensure dict:singular dict:singular suffixes work
            "dns": {"suffix": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:singular dict:list suffixes work
            "domainname": {"suffix": {"dev": "devinner", "shared": "inner"}}, # ensure dict:list dict:singular suffixes work
            "volumes": {"suffix": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:list dict:list suffixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns_search']['suffix'],
            {'dev': ['one.two']})
        self.assertEqual(
            ret['labels']['suffix'],
            {'shared': ['outer', 'outertwo'], 'prod': ['outerprod']})
        self.assertEqual(
            ret['dockerfile']['suffix'],
            {'dev': '.innerdev', 'shared': '.inner.outer', 'prod': '.outerprod'})
        self.assertEqual(
            ret['dns']['suffix'],
            {'dev': ['innerdev'], 'prod': 'outerprod', 'shared': ['inner', 'outer']})
        self.assertEqual(
            ret['domainname']['suffix'],
            {'dev': 'devinner', 'prod': ['outerprod'], 'shared': ['inner', 'outer']})
        self.assertEqual(
            ret['volumes']['suffix'],
            {'dev': ['innerdev'], 'prod': ['outerprod'], 'shared': ['inner', 'outer']})


class TestPrefixOptions(unittest.TestCase):
    """
    Make sure that options suffix substitutions correctly nest. Test functions
    are named with test_OUTERKIND_INNERKIND

    Definition of prefix:
        Thing being prefixed should ALWAYS end up at the beginning of the starting object
    """

    def test_singular_singular(self):
        """
        Make sure that individual string suffixes occur correctly
        """
        outer_options = {
            "name": {"prefix": "outer."},
            "dns_search": {"prefix": "outer."}
        }
        inner_options = {
            "name": {"prefix": "inner."},
            "hostname": {"prefix": "inner."}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['name']['prefix'],
            "outer.inner.")
        self.assertEqual(
            ret['dns_search']['prefix'],
            "outer.")
        self.assertEqual(
            ret['hostname']['prefix'],
            'inner.')

    def test_singular_list(self):
        """
        The outer layer Controlfile defines a list of prefixes, it is being
        applied to a Controlfile with a singular prefix
        """
        outer_options = {
            "dns": {"prefix": "outer"},
            "volumes": {"prefix": "outer"},
        }
        inner_options = {
            "dns": {"prefix": ["one", "two"]},
            "dns_search": {"prefix": ["one", "one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            ['outer', 'one', 'two'])
        self.assertEqual(
            ret['dns_search']['prefix'],
            ['one', 'one.two'])
        self.assertEqual(
            ret['volumes']['prefix'],
            'outer')

    def test_singular_dict(self):
        """
        The outer layer Controlfile defines a list of prefixes, it is being
        applied to a Controlfile with a singular prefix:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"prefix": "outer"},
            "dockerfile": {"prefix": "outer."},
            "volumes": {"prefix": "outer"}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"prefix": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure singular dict:list prefixes work
            "dns_search": {"prefix": {"dev": "one.two", "shared": "inner"}}, # ensure outer creation works
            "dockerfile": {"prefix": {"dev": "innerdev", "shared": "innershared"}}, # ensure singular dict:singular prefixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            {'shared': ['outer', 'dev.inner', 'inner'], 'dev': ['dev']})
        self.assertEqual(
            ret['dns_search']['prefix'],
            {'dev': 'one.two', 'shared': 'inner'})
        self.assertEqual(
            ret['dockerfile']['prefix'],
            {'dev': 'innerdev', 'shared': 'outer.innershared'})
        self.assertEqual(
            ret['volumes']['prefix'],
            'outer')

    def test_list_singular(self):
        """
        The outer layer Controlfile defines a list of prefixes, it is being
        applied to a Controlfile with a singular prefix:
        """
        outer_options = {
            "dns": {"prefix": ["one", "two"]},
            "volumes": {"prefix": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"prefix": "inner"},
            "dns_search": {"prefix": "one.two"},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            ['one', 'two', 'inner'])
        self.assertEqual(
            ret['dns_search']['prefix'],
            'one.two')
        self.assertEqual(
            ret['volumes']['prefix'],
            ['outer', 'testtwo'])

    def test_list_list(self):
        """
        The outer layer Controlfile defines a list of prefixes, it is being
        applied to a Controlfile with a singular prefix:
        """
        outer_options = {
            "dns": {"prefix": ["one", "two"]},
            "volumes": {"prefix": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"prefix": ["inner"]},
            "dns_search": {"prefix": ["one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            ['one', 'two', 'inner'])
        self.assertEqual(
            ret['dns_search']['prefix'],
            ['one.two'])
        self.assertEqual(
            ret['volumes']['prefix'],
            ['outer', 'testtwo'])

    def test_list_dict(self):
        """
        The outer layer Controlfile defines a list of prefixes, it is being
        applied to a Controlfile with a list of prefixes:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"prefix": ["outer"]},
            "dockerfile": {"prefix": ["outer"]},
            "volumes": {"prefix": ["outer"]}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"prefix": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure list dict:list prefixes work
            "dns_search": {"prefix": {"dev": ["one.two"], "shared": ["inner"]}}, # ensure outer creation works
            "dockerfile": {"prefix": {"dev": "innerdev", "shared": "innershared"}}, # ensure list dict:singular prefixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            {'shared': ['outer', 'dev.inner', 'inner'], 'dev': ['dev']})
        self.assertEqual(
            ret['dns_search']['prefix'],
            {'dev': ['one.two'], 'shared': ['inner']})
        self.assertEqual(
            ret['dockerfile']['prefix'],
            {'dev': 'innerdev', 'shared': ['outer', 'innershared']})
        self.assertEqual(
            ret['volumes']['prefix'],
            ['outer'])

    def test_dict_singular(self):
        """
        The outer layer Controlfile defines a dict of prefixes, it is being
        applied to a Controlfile with a singular prefix
        """
        outer_options = {
            "dns": {"prefix": {"dev": ["one", "two"]}},
            "dockerfile": {"prefix": {"dev": "dev.", "prod": "prod.", "shared": "shared."}},
            "volumes": {"prefix": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"prefix": "inner"}, # ensure dict:list singular prefixes work
            "dns_search": {"prefix": "one.two"}, # ensure outer creation works
            "dockerfile": {"prefix": "dockerfile"}, # ensure dict:singular singular prefixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            {'shared': 'inner', 'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['prefix'],
            'one.two')
        self.assertEqual(
            ret['dockerfile']['prefix'],
            {'dev': 'dev.', 'shared': 'shared.dockerfile', 'prod': 'prod.'})
        self.assertEqual(
            ret['volumes']['prefix'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_list(self):
        """
        The outer layer Controlfile defines a dict of prefixes, it is being
        applied to a Controlfile with a singular prefix
        """
        outer_options = {
            "dns": {"prefix": {"dev": ["one", "two"], "shared": ["outer"]}},
            "dockerfile": {"prefix": {"dev": "dev.", "prod": "prod.", "shared": "shared."}},
            "volumes": {"prefix": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"prefix": ["inner"]}, # ensure dict:list list prefixes work
            "dns_search": {"prefix": ["one.two"]}, # ensure outer creation works
            "dockerfile": {"prefix": ["dockerfile"]}, # ensure dict:singular list prefixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['prefix'],
            {'shared': ['outer', 'inner'], 'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['prefix'],
            ['one.two'])
        self.assertEqual(
            ret['dockerfile']['prefix'],
            {'dev': 'dev.', 'shared': ['shared.', 'dockerfile'], 'prod': 'prod.'})
        self.assertEqual(
            ret['volumes']['prefix'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_dict(self):
        """
        The outer layer Controlfile defines a dict of prefixes, it is being
        applied to a Controlfile with a singular prefix
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dockerfile": {"prefix": {"prod": "outerprod.", "shared": "outer."}},
            "dns": {"prefix": {"prod": "outerprod", "shared": "outer"}},
            "domainname": {"prefix": {"prod": ["outerprod"], "shared": ["outer"]}},
            "volumes": {"prefix": {"prod": ["outerprod"], "shared": ["outer"]}},
            "labels": {"prefix": {"shared": ["outer", "outertwo"], "prod": ["outerprod"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns_search": {"prefix": {"dev": ["one.two"]}}, # ensure outer creation works
            "dockerfile": {"prefix": {"dev": "innerdev.", "shared": "inner."}}, # ensure dict:singular dict:singular prefixes work
            "dns": {"prefix": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:singular dict:list prefixes work
            "domainname": {"prefix": {"dev": "devinner", "shared": "inner"}}, # ensure dict:list dict:singular prefixes work
            "volumes": {"prefix": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:list dict:list prefixes work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns_search']['prefix'],
            {'dev': ['one.two']})
        self.assertEqual(
            ret['labels']['prefix'],
            {'shared': ['outer', 'outertwo'], 'prod': ['outerprod']})
        self.assertEqual(
            ret['dockerfile']['prefix'],
            {'dev': 'innerdev.', 'shared': 'outer.inner.', 'prod': 'outerprod.'})
        self.assertEqual(
            ret['dns']['prefix'],
            {'dev': ['innerdev'], 'prod': 'outerprod', 'shared': ['outer', 'inner']})
        self.assertEqual(
            ret['domainname']['prefix'],
            {'dev': 'devinner', 'prod': ['outerprod'], 'shared': ['outer', 'inner']})
        self.assertEqual(
            ret['volumes']['prefix'],
            {'dev': ['innerdev'], 'prod': ['outerprod'], 'shared': ['outer', 'inner']})


class TestUnionOptions(unittest.TestCase):
    """
    Make sure that options union substitutions correctly nest. Test functions
    are named with test_OUTERKIND_INNERKIND

    Definition of union:
        A union is an operation on a set. Control works to preserve ordering.
        A union operation works similar to suffix, but duplicates are removed.
    """

    def test_singular_singular(self):
        """
        Make sure that individual string unions occur correctly
        """
        outer_options = {
            "name": {"union": "outer"},
            "cap_drop": {"union": "inner"},
            "dns_search": {"union": "outer"},
        }
        inner_options = {
            "name": {"union": "inner"},
            "cap_drop": {"union": "inner"},
            "hostname": {"union": "inner"}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['name']['union'],
            ["inner", "outer"])
        self.assertEqual(
            ret['cap_drop']['union'],
            ["inner"])
        self.assertEqual(
            ret['dns_search']['union'],
            ["outer"])
        self.assertEqual(
            ret['hostname']['union'],
            ['inner'])

    def test_singular_list(self):
        """
        The outer layer Controlfile defines a list of unions, it is being
        applied to a Controlfile with a singular union
        """
        outer_options = {
            "dns": {"union": "outer"},
            "cap_drop": {"union": "inner"},
            "volumes": {"union": "outer"},
        }
        inner_options = {
            "dns": {"union": ["one", "two"]},
            "cap_drop": {"union": ["foo", "inner", "bar"]},
            "dns_search": {"union": ["one", "one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['cap_drop']['union'],
            ["foo", "inner", "bar"])
        self.assertEqual(
            ret['dns']['union'],
            ['one', 'two', 'outer'])
        self.assertEqual(
            ret['dns_search']['union'],
            ['one', 'one.two'])
        self.assertEqual(
            ret['volumes']['union'],
            ['outer'])

    def test_singular_dict(self):
        """
        The outer layer Controlfile defines a list of unions, it is being
        applied to a Controlfile with a singular union:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "cap_drop": {"union": "inner"},
            "dns": {"union": "outer"},
            "dockerfile": {"union": "outer"},
            "volumes": {"union": "outer"}, # ensure inner creation works
        }
        inner_options = {
            "cap_drop": {"union": {"shared": ["inner"]}},
            "dns": {"union": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure singular dict:list unions work
            "dns_search": {"union": {"dev": "one.two", "shared": "inner"}}, # ensure outer creation works
            "dockerfile": {"union": {"dev": "innerdev", "shared": "innershared"}}, # ensure singular dict:singular unions work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['cap_drop']['union'],
            {'shared': ["inner"]})
        self.assertEqual(
            ret['dns']['union'],
            {'shared': ['dev.inner', 'inner', 'outer'], 'dev': ['dev']})
        self.assertEqual(
            ret['dns_search']['union'],
            {'dev': ['one.two'], 'shared': ['inner']})
        self.assertEqual(
            ret['dockerfile']['union'],
            {'dev': ['innerdev'], 'shared': ['innershared', 'outer']})
        self.assertEqual(
            ret['volumes']['union'],
            ['outer'])

    def test_list_singular(self):
        """
        The outer layer Controlfile defines a list of unions, it is being
        applied to a Controlfile with a singular union:
        """
        outer_options = {
            "cap_drop": {"union": ["foo", "outer", "bar"]},
            "dns": {"union": ["one", "two"]},
            "volumes": {"union": ["outer", "testtwo"]},
        }
        inner_options = {
            "cap_drop": {"union": "outer"},
            "dns": {"union": "inner"},
            "dns_search": {"union": "one.two"},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['cap_drop']['union'],
            ['outer', 'foo', 'bar'])
        self.assertEqual(
            ret['dns']['union'],
            ['inner', 'one', 'two'])
        self.assertEqual(
            ret['dns_search']['union'],
            ['one.two'])
        self.assertEqual(
            ret['volumes']['union'],
            ['outer', 'testtwo'])

    def test_list_list(self):
        """
        The outer layer Controlfile defines a list of unions, it is being
        applied to a Controlfile with a singular union:
        """
        outer_options = {
            "dns": {"union": ["one", "two"]},
            "volumes": {"union": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"union": ["one", "inner"]},
            "dns_search": {"union": ["one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['union'],
            ['one', 'inner', 'two'])
        self.assertEqual(
            ret['dns_search']['union'],
            ['one.two'])
        self.assertEqual(
            ret['volumes']['union'],
            ['outer', 'testtwo'])

    def test_list_dict(self):
        """
        The outer layer Controlfile defines a list of unions, it is being
        applied to a Controlfile with a list of unions:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"union": ["outer"]},
            "dockerfile": {"union": ["outer"]},
            "volumes": {"union": ["outer"]}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"union": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure list dict:list unions work
            "dns_search": {"union": {"dev": ["one.two"], "shared": ["inner"]}}, # ensure outer creation works
            "dockerfile": {"union": {"dev": "innerdev", "shared": "innershared"}}, # ensure list dict:singular unions work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['union'],
            {'shared': ['dev.inner', 'inner', 'outer'], 'dev': ['dev']})
        self.assertEqual(
            ret['dns_search']['union'],
            {'dev': ['one.two'], 'shared': ['inner']})
        self.assertEqual(
            ret['dockerfile']['union'],
            {'dev': ['innerdev'], 'shared': ['innershared', 'outer']})
        self.assertEqual(
            ret['volumes']['union'],
            ['outer'])

    def test_dict_singular(self):
        """
        The outer layer Controlfile defines a dict of unions, it is being
        applied to a Controlfile with a singular union
        """
        outer_options = {
            "dns": {"union": {"dev": ["one", "two"]}},
            "dockerfile": {"union": {"dev": "dev.", "prod": "prod.", "shared": "shared."}},
            "volumes": {"union": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"union": "inner"}, # ensure dict:list singular unions work
            "dns_search": {"union": "one.two"}, # ensure outer creation works
            "dockerfile": {"union": "dockerfile"}, # ensure dict:singular singular unions work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['union'],
            {'shared': ['inner'], 'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['union'],
            ['one.two'])
        self.assertEqual(
            ret['dockerfile']['union'],
            {'dev': ['dev.'], 'shared': ['dockerfile', 'shared.'], 'prod': ['prod.']})
        self.assertEqual(
            ret['volumes']['union'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_list(self):
        """
        The outer layer Controlfile defines a dict of unions, it is being
        applied to a Controlfile with a singular union
        """
        outer_options = {
            "dns": {"union": {"dev": ["one", "two"], "shared": ["outer"]}},
            "dockerfile": {"union": {"dev": "dev.", "prod": "prod.", "shared": "shared."}},
            "volumes": {"union": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"union": ["inner"]}, # ensure dict:list list unions work
            "dns_search": {"union": ["one.two"]}, # ensure outer creation works
            "dockerfile": {"union": ["dockerfile"]}, # ensure dict:singular list unions work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['union'],
            {'shared': ['inner', 'outer'], 'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['union'],
            ['one.two'])
        self.assertEqual(
            ret['dockerfile']['union'],
            {'dev': ['dev.'], 'shared': ['dockerfile', 'shared.'], 'prod': ['prod.']})
        self.assertEqual(
            ret['volumes']['union'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_dict(self):
        """
        The outer layer Controlfile defines a dict of unions, it is being
        applied to a Controlfile with a singular union
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dockerfile": {"union": {"prod": "outerprod.", "shared": "outer."}},
            "dns": {"union": {"prod": "outerprod", "shared": "outer"}},
            "domainname": {"union": {"prod": ["outerprod"], "shared": ["outer"]}},
            "volumes": {"union": {"prod": ["outerprod"], "shared": ["outer", "inner"]}},
            "labels": {"union": {"shared": ["outer", "outertwo"], "prod": ["outerprod"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns_search": {"union": {"dev": ["one.two"]}}, # ensure outer creation works
            "dockerfile": {"union": {"dev": "innerdev.", "shared": "inner."}}, # ensure dict:singular dict:singular unions work
            "dns": {"union": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:singular dict:list unions work
            "domainname": {"union": {"dev": "devinner", "shared": "inner"}}, # ensure dict:list dict:singular unions work
            "volumes": {"union": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:list dict:list unions work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns_search']['union'],
            {'dev': ['one.two']})
        self.assertEqual(
            ret['labels']['union'],
            {'shared': ['outer', 'outertwo'], 'prod': ['outerprod']})
        self.assertEqual(
            ret['dockerfile']['union'],
            {'dev': ['innerdev.'], 'shared': ['inner.', 'outer.'], 'prod': ['outerprod.']})
        self.assertEqual(
            ret['dns']['union'],
            {'dev': ['innerdev'], 'prod': ['outerprod'], 'shared': ['inner', 'outer']})
        self.assertEqual(
            ret['domainname']['union'],
            {'dev': ['devinner'], 'prod': ['outerprod'], 'shared': ['inner', 'outer']})
        self.assertEqual(
            ret['volumes']['union'],
            {'dev': ['innerdev'], 'prod': ['outerprod'], 'shared': ['inner', 'outer']})


class TestReplaceOptions(unittest.TestCase):
    """
    Make sure that options replace substitutions correctly nest. Test functions
    are named with test_OUTERKIND_INNERKIND

    Definition of replace:
        Thing being replaced should ALWAYS end up at the end of the starting object
    """

    def test_singular_singular(self):
        """
        Make sure that individual string replacees occur correctly
        """
        outer_options = {
            "name": {"replace": ".outer"},
            "dns_search": {"replace": ".outer"}
        }
        inner_options = {
            "name": {"replace": ".inner"},
            "hostname": {"replace": ".inner"}
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['name']['replace'],
            ".outer")
        self.assertEqual(
            ret['dns_search']['replace'],
            ".outer")
        self.assertEqual(
            ret['hostname']['replace'],
            '.inner')

    def test_singular_list(self):
        """
        The outer layer Controlfile defines a list of replacees, it is being
        applied to a Controlfile with a singular replace:
        """
        outer_options = {
            "dns": {"replace": "outer"},
            "volumes": {"replace": "outer"},
        }
        inner_options = {
            "dns": {"replace": ["one", "two"]},
            "dns_search": {"replace": ["one", "one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            'outer')
        self.assertEqual(
            ret['dns_search']['replace'],
            ['one', 'one.two'])
        self.assertEqual(
            ret['volumes']['replace'],
            'outer')

    def test_singular_dict(self):
        """
        The outer layer Controlfile defines a list of replacees, it is being
        applied to a Controlfile with a singular replace:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"replace": 'outer'},
            "dockerfile": {"replace": ".outer"},
            "volumes": {"replace": "outer"}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"replace": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure singular dict:list replacees work
            "dns_search": {"replace": {"dev": "one.two", "shared": "inner"}}, # ensure outer creation works
            "dockerfile": {"replace": {"dev": "innerdev", "shared": "innershared"}}, # ensure singular dict:singular replacees work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            'outer')
        self.assertEqual(
            ret['dns_search']['replace'],
            {'dev': 'one.two', 'shared': 'inner'})
        self.assertEqual(
            ret['dockerfile']['replace'],
            '.outer')
        self.assertEqual(
            ret['volumes']['replace'],
            'outer')

    def test_list_singular(self):
        """
        The outer layer Controlfile defines a list of replacees, it is being
        applied to a Controlfile with a singular replace:
        """
        outer_options = {
            "dns": {"replace": ["one", "two"]},
            "volumes": {"replace": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"replace": "inner"},
            "dns_search": {"replace": "one.two"},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            ['one', 'two'])
        self.assertEqual(
            ret['dns_search']['replace'],
            'one.two')
        self.assertEqual(
            ret['volumes']['replace'],
            ['outer', 'testtwo'])

    def test_list_list(self):
        """
        The outer layer Controlfile defines a list of replacees, it is being
        applied to a Controlfile with a singular replace:
        """
        outer_options = {
            "dns": {"replace": ["one", "two"]},
            "volumes": {"replace": ["outer", "testtwo"]},
        }
        inner_options = {
            "dns": {"replace": ["inner"]},
            "dns_search": {"replace": ["one.two"]},
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            ['one', 'two'])
        self.assertEqual(
            ret['dns_search']['replace'],
            ['one.two'])
        self.assertEqual(
            ret['volumes']['replace'],
            ['outer', 'testtwo'])

    def test_list_dict(self):
        """
        The outer layer Controlfile defines a list of replacees, it is being
        applied to a Controlfile with a singular replace:
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dns": {"replace": ["outer"]},
            "dockerfile": {"replace": [".outer"]},
            "volumes": {"replace": ["outer"]}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"replace": {"dev": ["dev"], "shared": ["dev.inner", "inner"]}}, # ensure list dict:list replacees work
            "dns_search": {"replace": {"dev": ["one.two"], "shared": ["inner"]}}, # ensure outer creation works
            "dockerfile": {"replace": {"dev": "innerdev", "shared": "innershared"}}, # ensure list dict:singular replacees work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            ['outer'])
        self.assertEqual(
            ret['dns_search']['replace'],
            {'dev': ['one.two'], 'shared': ['inner']})
        self.assertEqual(
            ret['dockerfile']['replace'],
            ['.outer'])
        self.assertEqual(
            ret['volumes']['replace'],
            ['outer'])

    def test_dict_singular(self):
        """
        The outer layer Controlfile defines a dict of replacees, it is being
        applied to a Controlfile with a singular replace
        """
        outer_options = {
            "dns": {"replace": {"dev": ["one", "two"]}},
            "dockerfile": {"replace": {"dev": ".dev", "prod": ".prod", "shared": ".shared"}},
            "volumes": {"replace": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"replace": "inner"}, # ensure dict:list singular replacees work
            "dns_search": {"replace": "one.two"}, # ensure outer creation works
            "dockerfile": {"replace": "dockerfile"}, # ensure dict:singular singular replacees work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            {'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['replace'],
            'one.two')
        self.assertEqual(
            ret['dockerfile']['replace'],
            {'dev': '.dev', 'shared': '.shared', 'prod': '.prod'})
        self.assertEqual(
            ret['volumes']['replace'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_list(self):
        """
        The outer layer Controlfile defines a dict of replacees, it is being
        applied to a Controlfile with a singular replace
        """
        outer_options = {
            "dns": {"replace": {"dev": ["one", "two"]}},
            "dockerfile": {"replace": {"dev": ".dev", "prod": ".prod", "shared": ".shared"}},
            "volumes": {"replace": {"shared": ["outer", "outertwo"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns": {"replace": ["inner"]}, # ensure dict:list list replacees work
            "dns_search": {"replace": ["one.two"]}, # ensure outer creation works
            "dockerfile": {"replace": ["dockerfile"]}, # ensure dict:singular list replacees work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns']['replace'],
            {'dev': ['one', 'two']})
        self.assertEqual(
            ret['dns_search']['replace'],
            ['one.two'])
        self.assertEqual(
            ret['dockerfile']['replace'],
            {'dev': '.dev', 'shared': '.shared', 'prod': '.prod'})
        self.assertEqual(
            ret['volumes']['replace'],
            {'shared': ['outer', 'outertwo']})

    def test_dict_dict(self):
        """
        The outer layer Controlfile defines a dict of replacees, it is being
        applied to a Controlfile with a singular replace
        """
        # pylint: disable=line-too-long
        outer_options = {
            "dockerfile": {"replace": {"prod": ".outerprod", "shared": ".outer"}},
            "dns": {"replace": {"prod": "outerprod", "shared": "outer"}},
            "domainname": {"replace": {"prod": ["outerprod"], "shared": ["outer"]}},
            "volumes": {"replace": {"prod": ["outerprod"], "shared": ["outer"]}},
            "labels": {"replace": {"shared": ["outer", "outertwo"], "prod": ["outerprod"]}}, # ensure inner creation works
        }
        inner_options = {
            "dns_search": {"replace": {"dev": ["one.two"]}}, # ensure outer creation works
            "dockerfile": {"replace": {"dev": ".innerdev", "shared": ".inner"}}, # ensure dict:singular dict:singular replacees work
            "dns": {"replace": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:singular dict:list replacees work
            "domainname": {"replace": {"dev": "devinner", "shared": "inner"}}, # ensure dict:list dict:singular replacees work
            "volumes": {"replace": {"dev": ["innerdev"], "shared": ["inner"]}}, # ensure dict:list dict:list replacees work
        }
        ret = satisfy_nested_options(outer_options, inner_options)
        self.assertEqual(
            ret['dns_search']['replace'],
            {'dev': ['one.two']})
        self.assertEqual(
            ret['labels']['replace'],
            {'shared': ['outer', 'outertwo'], 'prod': ['outerprod']})
        self.assertEqual(
            ret['dockerfile']['replace'],
            {'shared': '.outer', 'prod': '.outerprod'})
        self.assertEqual(
            ret['dns']['replace'],
            {'prod': 'outerprod', 'shared': 'outer'})
        self.assertEqual(
            ret['domainname']['replace'],
            {'prod': ['outerprod'], 'shared': ['outer']})
        self.assertEqual(
            ret['volumes']['replace'],
            {'prod': ['outerprod'], 'shared': ['outer']})
