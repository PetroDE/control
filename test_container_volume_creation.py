#!/usr/bin/env python3
"""Test creation of volumes when containers are being created"""

import random
import unittest
import docker

import control


class VolumeCreationTests(unittest.TestCase):
    """
    Double check that volumes are being created correctly. A later class will
    check that they are being removed correctly.
    """

    @classmethod
    def setUpClass(cls):
        cls.dclient = docker.Client('unix://var/run/docker.sock')

    def setUp(self):
        # control.options.debug = True
        self.image = ''
        self.conf = {}
        self.container_volumes = []
        self.container_name = 'unittest_volumecreation_{}'.format(
            random.randint(1, 65535))

    def tearDown(self):
        try:
            self.dclient.remove_container(self.container_name, v=True, force=True)
            for vol in self.container_volumes:
                self.dclient.remove_volume(vol)
        except docker.errors.NotFound:
            pass

    @unittest.expectedFailure
    def test_anon_volumes(self):
        """
        Make sure that anonymous volumes are correctly registered

        Currently unimplemented and will fail
        """
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "hostname": "busybox",
            "volumes": ["/var"]
        }
        container = control.Container(self.image, self.conf).create()
        container.start()
        self.assertEqual(len(container.inspect['Mounts']), 1)
        self.assertEqual(len(container.inspect['Mounts'][0]['Name']), 65)
        self.assertEqual(container.inspect['Mounts'][0]['Destination'], '/var')
        self.assertTrue(
            container.inspect['Mounts'][0]['Source'].startswith(
                '/var/lib/docker/volumes'),
            msg="Unexpected mount source: {}".format(
                container.inspect['Mount'][0]['Source']))

    def test_named_volumes(self):
        """Make sure that named volumes are correctly registered"""
        volume_name = "control_unittest_volume{}".format(random.randint(1, 65535))
        self.container_volumes.append(volume_name)
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "hostname": "busybox",
            "volumes": ["{}:/var".format(volume_name)]
        }
        container = control.Container(self.image, self.conf).create()
        container.start()
        self.assertEqual(len(container.inspect['Mounts']), 1)
        self.assertEqual(len(container.inspect['Mounts'][0]['Name']), len(volume_name))
        self.assertEqual(container.inspect['Mounts'][0]['Destination'], '/var')
        self.assertTrue(
            container.inspect['Mounts'][0]['Source'].startswith(
                '/var/lib/docker/volumes'),
            msg="Unexpected mount source: {}".format(
                container.inspect['Mounts'][0]['Source']))

    def test_mounted_volumes(self):
        """Make sure that mounted volumes are correctly registered"""
        import tempfile

        temp_dir = tempfile.TemporaryDirectory()
        self.image = 'busybox'
        self.conf = {
            "name": self.container_name,
            "hostname": "busybox",
            "volumes": ["{}:/var".format(temp_dir.name)]
        }
        container = control.Container(self.image, self.conf).create()
        container.start()
        self.assertEqual(len(container.inspect['Mounts']), 1)
        self.assertEqual(container.inspect['Mounts'][0]['Destination'], '/var')
        self.assertTrue(
            container.inspect['Mounts'][0]['Source'] == temp_dir.name,
            msg="Unexpected mount source: {}".format(
                container.inspect['Mounts'][0]['Source']))
        temp_dir.cleanup()


def setUpModule():
    """Ensure that our test images exist"""
    dclient = docker.Client('unix://var/run/docker.sock')
    dclient.pull('busybox:latest')


if __name__ == '__main__':
    unittest.main()
