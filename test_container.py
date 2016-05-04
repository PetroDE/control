#!/usr/bin/env python3
"""Test creation and use of the Container class"""

import os
import random
import unittest
import docker

import control


class CreateContainer(unittest.TestCase):
    """
    Ensure that a container class is always created correctly with all
    possible variants of a Controlfile service
    """

    def test_happy_path(self):
        """Make sure that the defaults still work"""
        image = 'busybox'
        conf = {"name": "grafana", "hostname": "grafana"}
        container = control.Container(image, conf)
        self.assertEqual(container.expected_timeout, 10)
        self.assertEqual(container.conf['image'], image)

    def test_expected_timeout(self):
        """Make sure that the defaults still work"""
        image = 'busybox'
        conf = {
            "name": "grafana",
            "hostname": "grafana",
            "expected_timeout": 3
        }
        container = control.Container(image, conf)
        self.assertEqual(container.expected_timeout, 3)
        self.assertEqual(container.conf['image'], image)
        with self.assertRaises(KeyError):
            container.conf['expected_timeout']

    def test_env_var_parsing(self):
        """
        Need to test that environment variables are always getting parsed
        correctly
        """
        image = 'busybox'
        conf = {
            "name": "grafana",
            "hostname": "grafana",
            "environment": [
                "PASSWORD=password",
            ]
        }
        container = control.Container(image, conf)
        conf_copy = container.__get_container_options()
        self.assertEqual(conf_copy['environment'][0], conf['environment'][0])

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
        container = control.Container(image, conf)
        conf_copy = container.__get_container_options()
        self.assertEqual(conf_copy['image'], image)
        self.assertEqual(conf_copy['host_config']['Binds'][0], conf['volumes'][0])
        self.assertEqual(conf_copy['host_config']['Binds'][1], conf['volumes'][1])
        self.assertEqual(conf_copy['host_config']['Binds'][2], conf['volumes'][2])

    def test_value_substitution(self):
        """Test name substitution working"""
        os.environ['COLLECTIVE'] = 'example'
        image = 'busybox'
        conf = {
            "name": "grafana.{COLLECTIVE}",
            "hostname": "grafana",
            "environment": [
                "DOMAIN={COLLECTIVE}.petrode.com"
            ],
            "volumes": [
                "/mnt/log/{COLLECTIVE}:/var/log"
            ]
        }
        os.environ['COLLECTIVE'] = 'example'
        container = control.Container(image, conf)
        self.assertEqual(container.conf['name'], image)
        del os.environ['COLLECTIVE']


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

    @unittest.expectedFailure
    def test_anon_volumes(self):
        """
        Make sure that anonymous volumes are correctly registered

        Currently unimplemented and will fail
        """
        image = 'busybox'
        conf = {
            "name": self.container_name,
            "hostname": "busybox",
            "volumes": ["/var"]
        }
        container = control.Container(image, conf).create()
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
        image = 'busybox'
        conf = {
            "name": self.container_name,
            "hostname": "busybox",
            "volumes": ["{}:/var".format(volume_name)]
        }
        container = control.Container(image, conf).create()
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
        image = 'busybox'
        conf = {
            "name": self.container_name,
            "hostname": "busybox",
            "volumes": ["{}:/var".format(temp_dir.name)]
        }
        container = control.Container(image, conf).create()
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


def suite():
    """Group TestCases together so all the tests run"""
    testsuite = unittest.TestSuite()
    testsuite.addTest(unittest.makeSuite(CreateContainer))
    testsuite.addTest(unittest.makeSuite(VolumeCreationTests))
    return testsuite


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
