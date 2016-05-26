#!/usr/bin/env python3
"""Test Controlfile discovery and normalization"""

import json
import os
import tempfile
import unittest

from control.controlfile import Controlfile


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
        self.assertIn('example', ctrlfile.control['services'])
        self.assertEqual(ctrlfile.control['services']['example'], self.conf)


class TestGeneratingServiceList(unittest.TestCase):
    """
    Make sure that the service list is generated correctly, when a
    metaservice exists
    """
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.controlfile = '{}/Controlfile'.format(self.temp_dir.name)
        self.conf = {
            "services": [
                {
                    "service": "foo",
                    "image": "busybox",
                    "container": {
                        "name": "foo",
                        "hostname": "foo"
                    }
                },
                {
                    "service": "bar",
                    "image": "busybox",
                    "container": {
                        "name": "bar",
                        "hostname": "bar"
                    }
                },
                {
                    "service": "named",
                    "services": ["bar", "baz"]
                },
                {
                    "image": "busybox",
                    "required": False,
                    "container": {
                        "name": "baz"
                    }
                }
            ]
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
            ctrlfile.control['services']['all'])
        self.assertIn(
            'baz',
            ctrlfile.control['services']['optional'])
        self.assertNotIn(
            'baz',
            ctrlfile.control['services']['required'])


class TestIncludingControlfiles(unittest.TestCase):
    """Make sure that controlfiles to a service are read in correctly"""
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.controlfile = '{}/Controlfile'.format(self.temp_dir.name)
        self.conf = {
            "services": [
                {
                    "service": "test",
                    "controlfile": "test/Controlfile"
                }
            ]
        }
        self.service_conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": ["namevolume:/var/log"],
                "dns_search": ["example"]
            }
        }
        with open(self.controlfile, 'w') as f:
            f.write(json.dumps(self.conf))
        os.mkdir('{}/test'.format(self.temp_dir.name))
        with open('{}/test/Controlfile'.format(self.temp_dir.name), 'w') as f:
            f.write(json.dumps(self.service_conf))
        self.service_conf.update({"service": "test", "controlfile": "test/Controlfile"})

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_including_controlfiles(self):
        """
        Make sure that single level Controlfile inclusion works correctly,
        it also checks if relative path includes are correctly dereferenced
        from the Controlfile location.
        """
        ctrlfile = Controlfile(self.controlfile)
        self.assertEqual(ctrlfile.control['services'][0], self.service_conf)
        self.assertEqual(
            ctrlfile.get_list_of_services(),
            frozenset(['test']))

    @unittest.skip("Not Implemented")
    def test_updated_relative_paths(self):
        """
        Volumes and controlfile references need to be updated when Controlfiles
        are discovered and read in
        """
        # TODO: test this stuff


class TestDeeplyNestedControlfiles(unittest.TestCase):
    """
    Make sure that many recursive inclusions are handled correctly
    """
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.controlfile_location = '{}/Controlfile'.format(self.temp_dir.name)
        self.conf = {
            "services": [
                {
                    "service": "test",
                    "controlfile": "test/Controlfile"
                }
            ]
        }
        self.foo_conf = {
            "services": [
                {
                    "service": "foo",
                    "controlfile": "foo/Controlfile"
                }
            ]
        }
        self.service_conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": ["namevolume:/var/log"],
                "dns_search": ["example"]
            }
        }
        with open(self.controlfile_location, 'w') as f:
            f.write(json.dumps(self.conf))
        os.mkdir('{}/test'.format(self.temp_dir.name))
        with open('{}/test/Controlfile'.format(self.temp_dir.name), 'w') as f:
            f.write(json.dumps(self.foo_conf))
        os.mkdir('{}/test/foo'.format(self.temp_dir.name))
        with open('{}/test/foo/Controlfile'.format(self.temp_dir.name), 'w') as f:
            f.write(json.dumps(self.service_conf))

    def tearDown(self):
        self.temp_dir.cleanup()

    @unittest.skip("this test doesn't demonstrate the behaviour I want yet")
    def test_nested_controlfile(self):
        """Reference a Controlfile that references other Controlfiles"""

if __name__ == '__main__':
    unittest.main()
