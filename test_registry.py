#!/usr/bin/env python3
"""Module to test Registry functioning"""

import unittest

import control


class RegistryWrongCert(unittest.TestCase):
    """Tests that ensure that a wrong cert is handled correctly"""
    NotImplemented


class RegistryCertReadPermissions(unittest.TestCase):
    """
    Test to make sure messaging is good for cases when the certificate
    for the registry cannot be read
    """
    NotImplemented


class RegistryPullRepoData(unittest.TestCase):
    """
    Tests to ensure that a registry object hits the correct endpoints to get
    information about a repository.

    There will be lots of mocking.
    """
    NotImplemented


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RegistryWrongCert))
    suite.addTest(unittest.makeSuite(RegistryCertReadPerms))
    suite.addTest(unittest.makeSuite(RegistryPullRepoData))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
