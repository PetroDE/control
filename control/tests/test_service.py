"""
Make sure that a service object is aliasing container and host_config
correctly
"""

import unittest

from control import service


class TestService(unittest.TestCase):
    """Test the Service class"""

    def test_build_only(self):
        """
        Test to make sure that controlfiles that only define the name
        of the image tha control should build is handled corrcetly.
        """
        serv = {"image": "test:latest"}
        cntrlfile = "./Controlfile"
        result = service.Service(serv, cntrlfile)
        self.assertEqual(
            result.image,
            "test:latest")
        self.assertEqual(
            result.service,
            "test")
        self.assertEqual(result.container, {})
        self.assertEqual(result.host_config, {})

        serv['service'] = "server"
        result = service.Service(serv, cntrlfile)
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
        result = service.Service(serv, cntrlfile)
        self.assertEqual(
            result.image,
            "busybox")
        self.assertEqual(
            result.service,
            "test")
        self.assertEqual(
            result.container,
            {
                "name": "test",
                "hostname": "test"
            })
        self.assertEqual(result.host_config, {})

        serv['service'] = "server"
        result = service.Service(serv, cntrlfile)
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

    def test_full(self):
        """
        Throw the beans at the thing and make sure that everything makes its
        way into the right spot
        """
        serv = {
            "service": "server",
            "image": "busybox",
            "expected_timeout": 3,
            "required": False,
            "dockerfile": "Dockerfile.example",
            "container": {
                "cmd": "/usr/cat",
                "hostname": "testme",
                "user": "foo",
                "detach": True,
                "stdin_open": True,
                "tty": True,
                "mem_limit": "100m",
                "ports": [8080, (8888, 'udp'), 8443],
                "port_bindings": {8080: ('0.0.0.0', 8080), '8888/udp': 8888},
                "env": ["FOO=bar", "DOMAIN=example.com"],
                "dns": ["8.8.8.8"],
                "volumes": ["/etc", "named:/var/lib", "/mnt/docker:/var/tmp"],
                "volumes_from": ["datacontainer"],
                "network_disabled": True,
                "name": "test",
                "entrypoint": "/bin/bash",
                "cpu_shares": 1,
                "working_dir": "/etc",
                "dns_search": ["example", "example.com"],
                "memswap_limit": 100,
                "labels": {"label": "me"},
                "links": ["networklink"],
                "privileged": True,
                "network_mode": 'bridge',
                "read_only": True,
                "ipc_mode": "shared",
                "shm_size": '100M',
                "cpu_group": 10,
                "cpu_period": 10,
                "group_add": ["cdrom"],
                "devices": "/dev/mdadm",
            }
        }
        cntrlfile = "./Controlfile"
        result = service.Service(serv, cntrlfile)
        self.assertEqual(result.service, "server")
        self.assertEqual(result.image, "busybox")
        self.assertEqual(result.expected_timeout, 3)
        self.assertEqual(result.required, False)
        self.assertEqual(result.dockerfile, "Dockerfile.example")
        # import pytest; pytest.set_trace()
        self.assertEqual(
            result.container,
            {
                "command": "/usr/cat",
                "hostname": "testme",
                "user": "foo",
                "detach": True,
                "stdin_open": True,
                "tty": True,
                "ports": [8080, (8888, 'udp'), 8443],
                "environment": ["FOO=bar", "DOMAIN=example.com"],
                "volumes": ["/etc"],
                "network_disabled": True,
                "name": "test",
                "entrypoint": "/bin/bash",
                "cpu_shares": 1,
                "labels": {"label": "me"},
                "working_dir": "/etc"
            })
        self.assertEqual(
            result.host_config,
            {
                "mem_limit": "100m",
                "port_bindings": {8080: ('0.0.0.0', 8080), '8888/udp': 8888},
                "dns": ["8.8.8.8"],
                "binds": ["named:/var/lib", "/mnt/docker:/var/tmp"],
                "volumes_from": ["datacontainer"],
                "dns_search": ["example", "example.com"],
                "memswap_limit": 100,
                "links": ["networklink"],
                "privileged": True,
                "network_mode": 'bridge',
                "read_only": True,
                "ipc_mode": "shared",
                "shm_size": '100M',
                "cpu_period": 10,
                "group_add": ["cdrom"],
                "devices": "/dev/mdadm",
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
        result = service.Service(serv, cntrlfile)
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
        result = service.Service(serv, cntrlfile)
        self.assertEqual(result.controlfile, "inclusion/Controlfile")
