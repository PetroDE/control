"""Test Controlfile discovery and normalization"""

import json
from os.path import join
import tempfile
import unittest

from control.controlfile import Controlfile, satisfy_nested_options


class TestServicefile(unittest.TestCase):
    """Test reading in a single service Controlfile"""
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.controlfile = '{}/Controlfile'.format(self.temp_dir.name)
        self.conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": [
                    "namevolume:/var/log"
                ],
                "dns_search": [
                    "example"
                ]
            }
        }
        with open(self.controlfile, 'w') as f:
            f.write(json.dumps(self.conf))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_service_controlfile(self):
        """Make sure that we don't break single service controlfiles"""
        ctrlfile = Controlfile(self.controlfile)
        self.assertIn('example', ctrlfile.services.keys())
        self.assertEqual(ctrlfile.services['example'].image,
                         self.conf['image'])
        self.assertEqual(ctrlfile.services['example'].controlfile,
                         self.controlfile)
        self.assertEqual(ctrlfile.services['example'].volumes,
                         self.conf['container']['volumes'])
        self.assertEqual(ctrlfile.services['example']['dns_search'],
                         self.conf['container']['dns_search'])


class TestGeneratingServiceList(unittest.TestCase):
    """
    Make sure that the service list is generated correctly, when a
    metaservice exists
    """
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.controlfile = join(self.temp_dir.name, 'Controlfile')
        self.conf = {
            "services": {
                "foo": {
                    "image": "busybox",
                    "container": {
                        "name": "foo",
                        "hostname": "foo"
                    }
                },
                "bar": {
                    "image": "busybox",
                    "container": {
                        "name": "bar",
                        "hostname": "bar"
                    }
                },
                "named": {
                    "services": ["bar", "baz"]
                },
                "baz": {
                    "image": "busybox",
                    "required": False,
                    "container": {
                        "name": "baz"
                    }
                }
            }
        }
        with open(self.controlfile, 'w') as f:
            f.write(json.dumps(self.conf))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generating_service_list(self):
        """
        Need to make sure that the service list is generated correctly even
        if a service doesn't define a service name.
        """
        ctrlfile = Controlfile(self.controlfile)
        self.assertEqual(
            ctrlfile.get_list_of_services(),
            frozenset([
                "foo",
                "bar",
                "baz",
                "named",
                "required",
                "all",
                "optional"]))

    def test_optional_services(self):
        """
        Make sure that containers that aren't required to be started are put
        in the optional services list.
        """
        ctrlfile = Controlfile(self.controlfile)
        self.assertIn(
            'baz',
            ctrlfile.services['all'])
        self.assertIn(
            'baz',
            ctrlfile.services['optional'])
        self.assertNotIn(
            'baz',
            ctrlfile.services['required'])


class TestNestedMetaServices(unittest.TestCase):
    """
    Provide test coverage for option 2 of create_service, where a metaservice
    contains the definitions of more services. Make sure that calls to
    satisfy_nested_options are made correctly.
    """

    def test_suffix(self):
        """Make sure that suffixing works for strings and lists"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = join(temp_dir.name, 'Controlfile')
        conf = {
            "services": {
                "testmeta": {
                    "services": {
                        "test": {
                            "image": "busybox",
                            "container": {
                                "name": "test"
                            }
                        }
                    }
                }
            },
            "options": {
                "name": {"suffix": ".{FOO}"}
            },
            "vars": {
                "FOO": "example"
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        ctrlfile = Controlfile(controlfile)
        self.assertEqual(ctrlfile.services['test']['name'],
                         'test.example')

    def test_prefix(self):
        """Make sure that prefixing works for strings and lists"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = join(temp_dir.name, 'Controlfile')
        conf = {
            "services": {
                "testmeta": {
                    "services": {
                        "test": {
                            "image": "busybox",
                            "container": {
                                "name": "test"
                            }
                        }
                    }
                }
            },
            "options": {
                "image": {"prefix": "registry.example.com/"},
                "name": {"prefix": "{FOO}."}
            },
            "vars": {
                "FOO": "example"
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        ctrlfile = Controlfile(controlfile)
        self.assertEqual(ctrlfile.services['test'].image,
                         'registry.example.com/busybox')
        self.assertEqual(ctrlfile.services['test']['name'],
                         'example.test')

    def test_union(self):
        """Make sure that prefixing works for strings and lists"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = join(temp_dir.name, 'Controlfile')
        conf = {
            "services": {
                "testmeta": {
                    "services": {
                        "test": {
                            "image": "busybox",
                            "container": {
                                "name": "test",
                                "volumes": ["vardata:/var/lib/{FOO}"]
                            }
                        }
                    }
                }
            },
            "options": {
                "volumes": {"union": ["{FOO}:/home"]}
            },
            "vars": {
                "FOO": "example"
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        ctrlfile = Controlfile(controlfile)
        self.assertEqual(ctrlfile.services['test']['volumes'],
                         ['example:/home', 'vardata:/var/lib/example'])

    def test_replace(self):
        """Make sure that prefixing works for strings and lists"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = join(temp_dir.name, 'Controlfile')
        conf = {
            "services": {
                "testmeta": {
                    "services": {
                        "test": {
                            "image": "busybox",
                            "container": {
                                "name": "test",
                            }
                        }
                    }
                }
            },
            "options": {
                "image": {"replace": "registry.{FOO}.com/alpine"}
            },
            "vars": {
                "FOO": "example"
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        ctrlfile = Controlfile(controlfile)
        self.assertEqual(ctrlfile.services['test'].image,
                         'registry.example.com/alpine')
