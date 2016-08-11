#!/usr/bin/env python3
"""Test creation and use of the Container class"""

import os
import random
import unittest
import docker

from control.container import Container


class CreateContainer(unittest.TestCase):
    """
    Ensure that a container class is always created correctly with all
    possible variants of a Controlfile service
    """

    @classmethod
    def setUpClass(cls):
        cls.dclient = docker.Client('unix://var/run/docker.sock')

    def setUp(self):
        # control.options.debug = True
        self.image = ''
        self.conf = {}
        self.container_volumes = []
        self.container_name = 'unittest_createcontainer_{}'.format(
            random.randint(1, 65535))

    def tearDown(self):
        try:
            self.dclient.remove_container(self.container_name, v=True, force=True)
            for vol in self.container_volumes:
                self.dclient.remove_volume(vol)
        except docker.errors.NotFound:
            pass

    def test_happy_path(self):
        """Make sure that the defaults still work"""
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "hostname": "happy_path"
        }
        container = Container(self.conf)
        self.assertEqual(container.service.expected_timeout, 10)
        self.assertEqual(container.service.conf['name'], self.container_name)
        self.assertEqual(container.service.conf['hostname'], "happy_path")
        self.assertEqual(container.service.conf['image'], self.image)

    def test_expected_timeout(self):
        """Test mirroring unspecified values and overriding default timeout"""
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "expected_timeout": 3
        }
        container = Container(self.conf)
        self.assertEqual(container.service.expected_timeout, 3)
        self.assertEqual(container.service.conf['name'], self.container_name)
        self.assertEqual(
            container.service.conf['hostname'],
            self.container_name,
            msg='Unspecified hostname not being mirrored from container name')
        self.assertEqual(container.service.conf['image'], self.image)
        with self.assertRaises(KeyError):
            container.conf['expected_timeout']

    def test_env_var_parsing(self):
        """
        Need to test that environment variables are always getting parsed
        correctly
        """
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "hostname": "grafana",
            "environment": [
                "PASSWORD=password",
            ]
        }
        container = Container(self.image, self.conf)
        conf_copy = container.get_container_options()
        self.assertEqual(conf_copy['environment'][0], self.conf['environment'][0])

    def test_volume_parsing(self):
        """Make sure that volumes get created correctly"""
        image = 'busybox'
        conf = {
            "name": "grafana",
            "hostname": "grafana",
            "volumes": [
                "/var",
                "named-user:/usr",
                "/mnt/usrbin:/usr/bin",
            ]
        }
        container = Container(image, conf)
        conf_copy = container.get_container_options()
        self.assertEqual(conf_copy['image'], image)
        self.assertEqual(conf_copy['host_config']['Binds'][0], conf['volumes'][0])
        self.assertEqual(conf_copy['host_config']['Binds'][1], conf['volumes'][1])
        self.assertEqual(conf_copy['host_config']['Binds'][2], conf['volumes'][2])

    def test_dns_search(self):
        """test that dns search makes it into the host config"""
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "dns_search": [
                "example"
            ]
        }
        container = Container(self.image, self.conf)
        conf_copy = container.get_container_options()
        self.assertEqual(
            conf_copy['host_config']['dns_search'][0],
            "example")

    def test_value_substitution(self):
        """Test name substitution working"""
        self.image = 'busybox'
        self.conf = {
            "name": "{container}.{{{{COLLECTIVE}}}}".format(container=self.container_name),
            "environment": [
                "DOMAIN={{COLLECTIVE}}.petrode.com"
            ],
            "volumes": [
                "/mnt/log/{{COLLECTIVE}}:/var/log"
            ],
            "dns_search": [
                "petrode",
                "{{COLLECTIVE}}.petrode"
            ]
        }
        os.environ['COLLECTIVE'] = 'example'
        container = Container(self.image, self.conf)
        conf_copy = container.get_container_options()
        self.assertEqual(
            conf_copy['name'],
            '{container}.example'.format(container=self.container_name))
        self.assertEqual(
            conf_copy['environment'][0],
            'DOMAIN=example.petrode.com')
        self.assertEqual(
            conf_copy['host_config']['Binds'][0],
            "/mnt/log/example:/var/log")
        self.assertEqual(
            conf_copy['host_config']['dns_search'][1],
            "example.petrode")
        del os.environ['COLLECTIVE']


def setUpModule():
    """Ensure that our test images exist"""
    dclient = docker.Client('unix://var/run/docker.sock')
    dclient.pull('busybox:latest')


if __name__ == '__main__':
    unittest.main()
