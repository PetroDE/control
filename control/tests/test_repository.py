#!/usr/bin/env python3
"""Testing control functionality"""

import unittest

from control.repository import Repository


class RepositoryTest(unittest.TestCase):
    """Tests Repository creation"""

    def test_creation(self):
        """Ensure that minimal options produce a correct Repository object"""
        repository = Repository('ubuntu')
        self.assertTrue(repository.repo == 'ubuntu:latest')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.get_pull_image_name() == 'ubuntu')
        self.assertTrue(repository.tag == 'latest')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)
        self.assertTrue(repository.registry is None)

    def test_tagging(self):
        """Make sure that tagging an image produces the correct result"""
        repository = Repository('ubuntu', '14.04')
        self.assertTrue(repository.repo == 'ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.get_pull_image_name() == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)
        self.assertTrue(repository.registry is None)

    def test_registry(self):
        """Test a registry running on port 443"""
        repository = Repository('ubuntu', '14.04', 'docker.petrode.com')
        self.assertTrue(repository.repo == 'docker.petrode.com/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.get_pull_image_name() == 'docker.petrode.com/ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port is None)
        self.assertTrue(repository.registry == 'docker.petrode.com')

    def test_registry_and_port(self):
        """Test a registry running on port 443"""
        repository = Repository('ubuntu', '14.04', 'docker.petrode.com', '5002')
        self.assertTrue(repository.repo == 'docker.petrode.com:5002/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.get_pull_image_name() == 'docker.petrode.com:5002/ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port == '5002')
        self.assertTrue(repository.registry == 'docker.petrode.com:5002')


class MatcherTest(unittest.TestCase):
    """Test the matcher function that it correctly creates Repositories"""

    def test_matching_only_latest_image(self):
        """Create a repo based on just an image name"""
        repository = Repository.match('ubuntu')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == 'latest')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)

    def test_matching_image(self):
        """Create a repo based on an image name with a tag"""
        repository = Repository.match('ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)

    def test_matching_image_with_domain(self):
        """Create a repo based on an image from a registry"""
        repository = Repository.match('docker.petrode.com/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port is None)

    def test_match_repo_with_registry(self):
        """Create a repo based on an image from a registry running on not 443"""
        repository = Repository.match('docker.petrode.com:5002/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port == '5002')


def suite():
    """Group TestCases together so all the tests run"""
    testsuite = unittest.TestSuite()
    testsuite.addTest(unittest.makeSuite(RepositoryTest))
    testsuite.addTest(unittest.makeSuite(MatcherTest))
    return testsuite

if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
