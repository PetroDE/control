#!/usr/bin/env python3
"""Test Controlfile discovery and normalization"""

import json
import os
import tempfile
import unittest

import control


class ControlfileNormalizationTest(unittest.TestCase):
    """
    Test different controlfile schemes to ensure they all layer in
    correctly
    """

    def test_single_service_controlfile(self):
        """Make sure that we don't break single service controlfiles"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = '{}/Controlfile'.format(temp_dir.name)
        conf = {
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
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        ctrlfile = control.Controlfile(controlfile)
        self.assertEqual(ctrlfile.control['services'][0], conf)
        temp_dir.cleanup()

    def test_generating_service_list(self):
        """
        Need to make sure that the service list is generated correctly even
        if a service doesn't define a service name.
        """
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = '{}/Controlfile'.format(temp_dir.name)
        conf = {
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
                    "container": {
                        "name": "baz"
                    }
                }
            ]
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))

        ctrlfile = control.Controlfile(controlfile)
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

    def test_including_controlfiles(self):
        """
        Make sure that single level Controlfile inclusion works correctly,
        it also checks if relative path includes are correctly dereferenced
        from the Controlfile location.
        """
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = '{}/Controlfile'.format(temp_dir.name)
        conf = {
            "services": [
                {
                    "service": "test",
                    "controlfile": "test/Controlfile"
                }
            ]
        }
        service_conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": ["namevolume:/var/log"],
                "dns_search": ["example"]
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        os.mkdir('{}/test'.format(temp_dir.name))
        with open('{}/test/Controlfile'.format(temp_dir.name), 'w') as f:
            f.write(json.dumps(service_conf))
        service_conf.update({"service": "test", "controlfile": "test/Controlfile"})

        ctrlfile = control.Controlfile(controlfile)
        self.assertEqual(ctrlfile.control['services'][0], service_conf)
        self.assertEqual(
            ctrlfile.get_list_of_services(),
            frozenset(['test']))
        temp_dir.cleanup()

    @unittest.skip("this test doesn't demonstrate the behaviour I want yet")
    def test_nested_controlfile_discovery(self):
        """Reference a Controlfile that references other Controlfiles"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile_location = '{}/Controlfile'.format(temp_dir.name)
        conf = {
            "services": [
                {
                    "service": "test",
                    "controlfile": "test/Controlfile"
                }
            ]
        }
        foo_conf = {
            "services": [
                {
                    "service": "foo",
                    "controlfile": "foo/Controlfile"
                }
            ]
        }
        service_conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": ["namevolume:/var/log"],
                "dns_search": ["example"]
            }
        }
        with open(controlfile_location, 'w') as f:
            f.write(json.dumps(conf))
        os.mkdir('{}/test'.format(temp_dir.name))
        with open('{}/test/Controlfile'.format(temp_dir.name), 'w') as f:
            f.write(json.dumps(foo_conf))
        os.mkdir('{}/test/foo'.format(temp_dir.name))
        with open('{}/test/foo/Controlfile'.format(temp_dir.name), 'w') as f:
            f.write(json.dumps(service_conf))
