#!/usr/bin/env python3
"""Testing control functionality"""

import unittest

import control


class RepositoryTest(unittest.TestCase):
    """Tests Repository creation"""

    def test_creation(self):
        """Ensure that minimal options produce a correct Repository object"""
        repository = control.Repository('ubuntu')
        self.assertTrue(repository.repo == 'ubuntu:latest')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == 'latest')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)
        self.assertTrue(repository.registry is None)

    def test_tagging(self):
        """Make sure that tagging an image produces the correct result"""
        repository = control.Repository('ubuntu', '14.04')
        self.assertTrue(repository.repo == 'ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)
        self.assertTrue(repository.registry is None)

    def test_registry(self):
        """Test a registry running on port 443"""
        repository = control.Repository('ubuntu', '14.04', 'docker.petrode.com')
        self.assertTrue(repository.repo == 'docker.petrode.com/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port is None)
        self.assertTrue(repository.registry == 'docker.petrode.com')

    def test_registry_and_port(self):
        """Test a registry running on port 443"""
        repository = control.Repository('ubuntu', '14.04', 'docker.petrode.com', '5002')
        self.assertTrue(repository.repo == 'docker.petrode.com:5002/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port == '5002')
        self.assertTrue(repository.registry == 'docker.petrode.com:5002')

    def test_matching_only_latest_image(self):
        """Create a repo based on just an image name"""
        repository = control.Repository.match('ubuntu')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == 'latest')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)

    def test_matching_image(self):
        """Create a repo based on an image name with a tag"""
        repository = control.Repository.match('ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain is None)
        self.assertTrue(repository.port is None)

    def test_matching_image_with_domain(self):
        """Create a repo based on an image from a registry"""
        repository = control.Repository.match('docker.petrode.com/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port is None)

    def test_matching_image_full_length(self):
        """Create a repo based on an image from a registry running on not 443"""
        repository = control.Repository.match('docker.petrode.com:5002/ubuntu:14.04')
        self.assertTrue(repository.image == 'ubuntu')
        self.assertTrue(repository.tag == '14.04')
        self.assertTrue(repository.domain == 'docker.petrode.com')
        self.assertTrue(repository.port == '5002')

if __name__ == '__main__':
    unittest.main()
