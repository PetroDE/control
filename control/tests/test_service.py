"""
Make sure that a service object is aliasing container and host_config
correctly
"""

import unittest
import os
from os.path import join

from control.exceptions import InvalidControlfile
from control.service import UniService


class TestService(unittest.TestCase):
    """Test the Service class"""

    def test_missing_image(self):
        """
        Make sure that a UniService missing an image is classified as
        incorrect.
        """
        serv = {}
        cntrlfile = "./Controlfile"
        with self.assertRaises(InvalidControlfile):
            result = UniService(serv, cntrlfile)

        serv = {
            "container": {
                "name": "test",
            }
        }
        cntrlfile = "./Controlfile"
        with self.assertRaises(InvalidControlfile):
            result = UniService(serv, cntrlfile)

    def test_build_only(self):
        """
        Test to make sure that controlfiles that only define the name
        of the image tha control should build is handled corrcetly.
        """
        # TODO: Move this into the controlfile test file
        serv = {"image": "test:latest"}
        cntrlfile = "./Controlfile"
        result = UniService(serv, cntrlfile)
        self.assertEqual(
            result.image,
            "test:latest")
        self.assertEqual(
            result.service,
            "test")
        self.assertEqual(result.container, {})
        self.assertEqual(result.host_config, {})

        serv['service'] = "server"
        result = UniService(serv, cntrlfile)
        self.assertEqual(
            result.image,
            "test:latest")
        self.assertEqual(
            result.service,
            "server")
        self.assertEqual(result.container, {})
        self.assertEqual(result.host_config, {})

    def test_basic_runnable(self):
        """
        This container is the bare minimum that you need to run a container
        """
        serv = {
            "image": "busybox",
            "container": {
                "name": "test"
            }
        }
        cntrlfile = "./Controlfile"
        result = UniService(serv, cntrlfile)
        self.assertEqual(result.image, "busybox")
        self.assertEqual(result.service, "test")
        self.assertEqual(
            result.container,
            {
                "name": "test",
                "hostname": "test"
            })
        self.assertEqual(result.host_config, {})

        serv['service'] = "server"
        result = UniService(serv, cntrlfile)
        self.assertEqual(
            result.image,
            "busybox")
        self.assertEqual(
            result.service,
            "server")
        self.assertEqual(
            result.container,
            {
                "name": "test",
                "hostname": "test"
            })
        self.assertEqual(result.host_config, {})

    def test_startable_split_dockerfile(self):
        """
        This container is the bare minimum that you need to run a container
        """
        serv = {
            "image": "busybox",
            "dockerfile": {
                "prod": "MadeProd",
                "dev": "MadeDev",
            },
            "container": {
                "name": "test"
            }
        }
        cntrlfile = "./Controlfile"
        result = UniService(serv, cntrlfile)
        self.assertEqual(result.image, "busybox")
        self.assertEqual(result.service, "test")
        self.assertEqual(
            result.dockerfile['dev'],
            join(os.getcwd(), serv['dockerfile']['dev']))
        self.assertEqual(
            result.dockerfile['prod'],
            join(os.getcwd(), serv['dockerfile']['prod']))
        self.assertEqual(
            result.container,
            {
                "name": "test",
                "hostname": "test"
            })
        self.assertEqual(result.host_config, {})

    def test_full(self):
        """
        Throw the beans at the thing and make sure that everything makes its
        way into the right spot
        """
        serv = {
            "dockerfile": "Dockerfile.example",
            "expected_timeout": 3,
            "image": "busybox",
            "required": False,
            "service": "server",
            "container": {
                "cmd": "/usr/cat",
                "cpu_group": 10,
                "cpu_period": 10,
                "cpu_shares": 1,
                "detach": True,
                "devices": "/dev/mdadm",
                "dns": ["8.8.8.8"],
                "dns_search": ["example", "example.com"],
                "entrypoint": "/bin/bash",
                "env": ["FOO=bar", "DOMAIN=example.com"],
                "group_add": ["cdrom"],
                "hostname": "testme",
                "ipc_mode": "shared",
                "labels": {"label": "me"},
                "links": ["networklink"],
                "mem_limit": "100m",
                "memswap_limit": 100,
                "name": "test",
                "network_disabled": True,
                "network_mode": 'bridge',
                "port_bindings": {8080: ('0.0.0.0', 8080), '8888/udp': 8888},
                "ports": [8080, (8888, 'udp'), 8443],
                "privileged": True,
                "read_only": True,
                "shm_size": '100M',
                "stdin_open": True,
                "tty": True,
                "user": "foo",
                "volumes": ["/etc", "named:/var/lib", "/mnt/docker:/var/tmp"],
                "volumes_from": ["datacontainer"],
                "working_dir": "/etc",
            }
        }
        cntrlfile = "./Controlfile"
        result = UniService(serv, cntrlfile)
        self.assertEqual(result.service, "server")
        self.assertEqual(result.image, "busybox")
        self.assertEqual(result.expected_timeout, 3)
        self.assertEqual(result.required, False)
        self.assertEqual(
            result.dockerfile,
            {
                "prod": join(os.getcwd(), 'Dockerfile.example'),
                "dev": join(os.getcwd(), 'Dockerfile.example'),
            })
        # import pytest; pytest.set_trace()
        self.assertEqual(result.volumes, serv['container']['volumes'])
        self.assertEqual(
            result.container,
            {
                "command": "/usr/cat",
                "cpu_shares": 1,
                "detach": True,
                "entrypoint": "/bin/bash",
                "environment": ["FOO=bar", "DOMAIN=example.com"],
                "hostname": "testme",
                "labels": {"label": "me"},
                "name": "test",
                "network_disabled": True,
                "ports": [8080, (8888, 'udp'), 8443],
                "stdin_open": True,
                "tty": True,
                "user": "foo",
                "working_dir": "/etc"
            })
        self.assertEqual(
            result.host_config,
            {
                "cpu_period": 10,
                "devices": "/dev/mdadm",
                "dns": ["8.8.8.8"],
                "dns_search": ["example", "example.com"],
                "group_add": ["cdrom"],
                "ipc_mode": "shared",
                "links": ["networklink"],
                "mem_limit": "100m",
                "memswap_limit": 100,
                "network_mode": 'bridge',
                "port_bindings": {8080: ('0.0.0.0', 8080), '8888/udp': 8888},
                "privileged": True,
                "read_only": True,
                "shm_size": '100M',
                "volumes_from": ["datacontainer"],
            })
        self.assertNotIn(
            'cpu_group',
            result.host_config,
            msg='Docker API version changed. Control supports 1.21-1.23')

    def test_direct_inclusion(self):
        """Test that the controlfile is set correctly"""
        serv = {
            "image": "busybox",
            "container": {
                "name": "test"
            }
        }
        cntrlfile = "./Controlfile"
        result = UniService(serv, cntrlfile)
        self.assertEqual(result.controlfile, "./Controlfile")

    def test_indirect_inclusion(self):
        """
        The Controlfile passed into the Service constructor will always be the
        place the service was discovered in, but a discovered service can
        point to a Controlfile that will fill out the configuration of this
        service.
        The controlfile member should always be the most complete description
        of the service. If we track this accurately we can guess that the
        directory the Controlfile lives in is also the place where the image
        should be built from. This test makes sure we track it correctly.
        """
        serv = {
            "image": "busybox",
            "controlfile": "inclusion/Controlfile",
            "container": {
                "name": "test"
            }
        }
        cntrlfile = "./Controlfile"
        result = UniService(serv, cntrlfile)
        self.assertEqual(result.controlfile, "inclusion/Controlfile")
