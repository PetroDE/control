#!/usr/bin/env python3
"""Module to test Registry functioning"""

import unittest
import docker

import control


class RegistryWrongCert(unittest.TestCase):
    """Tests that ensure that a wrong cert is handled correctly"""

    def setUp(self):
        dclient = docker.Client(base_url='unix://var/run/docker.sock')
        #dclient.

    def test_cannot_read_cert_file(self):
        pass

    def test_wrong_cert_in_dir(self):
        pass


class RegistryPullRepoData(unittest.TestCase):
    """
    Tests to ensure that a registry object hits the correct endpoints to get
    information about a repository.

    There will be lots of mocking.
    """
    pass


def suite():
    """Group TestCases together so all the tests run"""
    testsuite = unittest.TestSuite()
    testsuite.addTest(unittest.makeSuite(RegistryWrongCert))
    testsuite.addTest(unittest.makeSuite(RegistryPullRepoData))
    return testsuite

if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
