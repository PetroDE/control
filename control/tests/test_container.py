#!/usr/bin/env python3
"""Test creation and use of the Container class"""

from copy import deepcopy
import os
import random
import unittest
import docker

from control.service import create_service
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
        self.conf = {
            "image": 'busybox',
            "container": {
                "name": self.container_name,
                "hostname": "happy_path"
            }
        }
        serv = create_service(deepcopy(self.conf), './Controlfile')
        container = Container(serv)
        self.assertEqual(container.service.expected_timeout, 10)
        self.assertEqual(container.service['name'], self.container_name)
        self.assertEqual(container.service['hostname'], self.conf['container']['hostname'])
        self.assertEqual(container.service.image, self.conf['image'])

    def test_expected_timeout(self):
        """Test mirroring unspecified values and overriding default timeout"""
        self.conf = {
            "image": 'busybox',
            "expected_timeout": 3,
            "container": {
                "name": self.container_name
            }
        }
        serv = create_service(deepcopy(self.conf), './Controlfile')
        container = Container(serv)
        self.assertEqual(container.service.expected_timeout, 3)
        self.assertEqual(container.service['name'], self.container_name)
        self.assertEqual(
            container.service['hostname'],
            self.container_name,
            msg='Unspecified hostname not being mirrored from container name')
        self.assertEqual(container.service.image, self.conf['image'])

    def test_env_var_parsing(self):
        """
        Need to test that environment variables are always getting parsed
        correctly
        """
        self.image = 'busybox'
        self.conf = {
            "image": self.image,
            "container": {
                "name": self.container_name,
                "hostname": "grafana",
                "environment": [
                    "PASSWORD=password",
                ]
            }
        }
        serv = create_service(deepcopy(self.conf), './Controlfile')
        conf_copy = serv.prepare_container_options(prod=False)
        self.assertEqual(conf_copy['environment'][0], self.conf['container']['environment'][0])

    def test_volume_parsing(self):
        """Make sure that volumes get created correctly"""
        self.image = 'busybox'
        self.conf = {
            "image": self.image,
            "container": {
                "name": "grafana",
                "hostname": "grafana",
                "volumes": [
                    "/var",
                    "named-user:/usr",
                    "/mnt/usrbin:/usr/bin",
                ]
            }
        }
        serv = create_service(deepcopy(self.conf), './Controlfile')
        conf_copy = serv.prepare_container_options(prod=False)
        self.assertEqual(conf_copy['host_config']['Binds'][0], self.conf['container']['volumes'][1])
        self.assertEqual(conf_copy['host_config']['Binds'][1], self.conf['container']['volumes'][2])
        self.assertEqual(conf_copy['volumes'][0], '/var')
        self.assertEqual(conf_copy['volumes'][1], '/usr')
        self.assertEqual(conf_copy['volumes'][2], '/usr/bin')

    def test_dns_search(self):
        """test that dns search makes it into the host config"""
        self.image = 'busybox'
        self.conf = {
            "image": self.image,
            "container": {
                "name": self.container_name,
                "dns_search": [
                    "example"
                ]
            }
        }
        serv = create_service(deepcopy(self.conf), './Controlfile')
        conf_copy = serv.prepare_container_options(prod=False)
        self.assertEqual(
            conf_copy['host_config']['DnsSearch'][0],
            self.conf["container"]["dns_search"][0])

    def test_value_substitution(self):
        """Test name substitution working"""
        self.image = 'busybox'
        self.conf = {
            "image": self.image,
            "container": {
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
        }
        os.environ['COLLECTIVE'] = 'example'
        serv = create_service(self.conf, './Controlfile')
        conf_copy = serv.prepare_container_options(prod=False)
        self.assertEqual(
            conf_copy['name'],
            '{container}.{{{{COLLECTIVE}}}}'.format(container=self.container_name))
        self.assertEqual(
            conf_copy['environment'][0],
            'DOMAIN={{COLLECTIVE}}.petrode.com')
        self.assertEqual(
            conf_copy['host_config']['Binds'][0],
            "/mnt/log/{{COLLECTIVE}}:/var/log")
        self.assertEqual(
            conf_copy['volumes'][0],
            "/var/log")
        self.assertEqual(
            conf_copy['host_config']['DnsSearch'][0],
            "petrode")
        self.assertEqual(
            conf_copy['host_config']['DnsSearch'][1],
            "{{COLLECTIVE}}.petrode")
        del os.environ['COLLECTIVE']


def setUpModule():
    """Ensure that our test images exist"""
    dclient = docker.Client('unix://var/run/docker.sock')
    dclient.pull('busybox:latest')


if __name__ == '__main__':
    unittest.main()
