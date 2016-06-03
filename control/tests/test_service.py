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
            str(result.image),
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
            str(result.image),
            "busybox:latest")
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
            str(result.image),
            "busybox:latest")
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
                "tmpfs": ["/mnt/tmpfs"]
            }
        }
        cntrlfile = "./Controlfile"
        result = service.Service(serv, cntrlfile)
        self.assertEqual(result.service, "server")
        self.assertEqual(str(result.image), "busybox:latest")
        self.assertEqual(result.expected_timeout, 3)
        self.assertEqual(result.dockerfile, "Dockerfile.example")
        self.assertEqual(
            result.container,
            {
                "cmd": "/usr/cat",
                "hostname": "testme",
                "user": "foo",
                "detach": True,
                "stdin_open": True,
                "tty": True,
                "ports": [8080, (8888, 'udp'), 8443],
                "env": ["FOO=bar", "DOMAIN=example.com"],
                "volumes": ["/etc"],
                "network_disabled": True,
                "name": "test",
                "entrypoint": "/bin/bash",
                "cpu_shares": 1,
                "labels": {"label": "me"},
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
                "cpu_group": 10,
                "cpu_period": 10,
                "group_add": ["cdrom"],
                "devices": "/dev/mdadm",
                "tmpfs": ["/mnt/tmpfs"]
            })
