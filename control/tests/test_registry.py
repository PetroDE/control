#!/usr/bin/env python3
"""Module to test Registry functioning"""

import os
import tempfile
import unittest
import docker

from control.container import DoesNotExist
from control.registry import Registry


class RegistryWrongCert(unittest.TestCase):
    """Tests that ensure that a wrong cert is handled correctly"""

    @classmethod
    def setUpClass(cls):
        cls.dclient = docker.Client(base_url='unix://var/run/docker.sock')

    def setUp(self):
        self.endpoint = 'docker.petrode.com'
        self.temp_dir = tempfile.TemporaryDirectory()
        os.mkdir('{}/{}'.format(self.temp_dir.name, self.endpoint))

    def tearDown(self):
        self.temp_dir.cleanup()

    @unittest.skip("Registry crashes the program")
    def test_cannot_read_cert_file(self):
        """
        If control cannot read the ssl cert, docker may have a fit that it
        cannot talk to the registry
        """
        cert_file_name = '{}/{}/cert.pem'.format(self.temp_dir.name, self.endpoint)
        cert_file = open(cert_file_name, 'w')
        cert_file.close()
        os.chmod(cert_file_name, 0o000)
        with self.assertRaises(DoesNotExist):
            Registry('docker.petrode.com', certdir=self.temp_dir.name)

    @unittest.skip("Registry crashes the program")
    def test_wrong_cert_in_dir(self):
        """
        There is a certificate in the directory, but it does not authenticate
        the endpoint
        """
        cert_file_name = '{}/{}/cert.pem'.format(self.temp_dir.name, self.endpoint)
        cert_file = open(cert_file_name, 'w')
        cert_file.write(
            """
            -----BEGIN CERTIFICATE-----
            MIIGFjCCA/6gAwIBAgIJANV5duKcqimtMA0GCSqGSIb3DQEBCwUAMIGaMQswCQYD
            VQQGEwJVUzERMA8GA1UECBMIQ29sb3JhZG8xEzARBgNVBAcTCkJyb29tZmllbGQx
            DzANBgNVBAoTBlZlc21pcjEQMA4GA1UECxMHUGV0cm9ERTEZMBcGA1UEAxMQamly
            YS5wZXRyb2RlLmNvbTElMCMGCSqGSIb3DQEJARYWa3JvYmVydHNvbkBwZXRyb2Rl
            LmNvbTAeFw0xNTA1MDgwMDEwMTVaFw0yNTA1MDUwMDEwMTVaMIGaMQswCQYDVQQG
            EwJVUzERMA8GA1UECBMIQ29sb3JhZG8xEzARBgNVBAcTCkJyb29tZmllbGQxDzAN
            BgNVBAoTBlZlc21pcjEQMA4GA1UECxMHUGV0cm9ERTEZMBcGA1UEAxMQamlyYS5w
            ZXRyb2RlLmNvbTElMCMGCSqGSIb3DQEJARYWa3JvYmVydHNvbkBwZXRyb2RlLmNv
            bTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBALtoxmuUSUdo8C1CUBl9
            3mhT77JtRYZV2Y+L9mu0puBC3MmOvmDjVAMU6a/0o5uGmW5HWxkZCVrE0gecttNx
            ngGZW3+Uxvprh3MbyyvQUuL5iOreXRVy0KzGsFC1SLbb6j3peBayIovBgnf4VC/j
            2VswdwOPh/Ol9FppZY/ORpV/IcSEcG8JmW9FhXvO5bphC+1/6amp2R8utJ84Fct/
            +waoOEOr9zRdby/GNip9UQqyju+jmGR1BnVHnLRDKWmsXECIQD9l/K5DGSy8K9L+
            VJoLUTcKKsrpVRC2DXgrzb5rkw015nsDu4Pnsbv+7svxkeJXyjfhchkjlMqmnta4
            U9AmRYJ9x3ofFRf7FvM3eUxRWs7ftDOw+9LYXuJqjdH6spnKELrpaz8GGStLiOFW
            iVGP3prSfidCiQ6v5k9qyiVnDYWgDVMYMh3b4d0JZpm60ZvF6g7JgL5RIodvX4LZ
            IbSY2dXsEsTgHbeuQHQTjsAsrgnnoC1zTg4rShKYOG9Jdz0xpbWNVDyk5d5y39Dh
            Oj2DoeCUaZ4FIv4pH9s93OVN0WpDIKlsBvcwOZip/H38MYNSvwhuzmsD6Li4kyA/
            XAp8m1oJsCcn16+S27P6HTKsnvcodmv2/3Ba2mfmR0YIU2AQT33cx92V4Gla1RIj
            unp34Z/R4NSU9XmzstJUXXTVAgMBAAGjXTBbMB0GA1UdDgQWBBRXhH2ShsmpFBzw
            F176g0mwZ9bpdjAfBgNVHSMEGDAWgBRXhH2ShsmpFBzwF176g0mwZ9bpdjAMBgNV
            HRMEBTADAQH/MAsGA1UdDwQEAwIBBjANBgkqhkiG9w0BAQsFAAOCAgEAjxCwoaa4
            f3PrqpPFV4FchkkpaxwMhmcyePPcDb5GiUS1arNG3jemus3F4UkEk5wF+ajGkc1T
            k0ukq0ckH5iqKhvIRlO1vaxQUufJwK9Ke6dfSpRXUjv7oSRVGuy0ycbyZJS2OmAo
            O6VG19h98utMBAPpuIRVOd9Bzm3yhcq7b2nvqQLBmA3+/Ud81sZQQZAxP1xXyuxd
            ApBbOdjvD3AST1kInUDBVroxxk2Cqq+9P274tVwZmZoXEWiW2V85jGYfaIt2JPUv
            XqhzMrckZdHhJf2p8hTrqkmXdisHm0QR+qiQdRWdYvkJOvUwpVveYwYBGYG4r4BN
            AoPpemdWikpEE2AdXZ+H/qOKBWxo9de6MVZV+KHPxE6504ciUfyK6uvaTCoCxeB0
            Sbky5qcI9O0uvUpkZ8vvXLXr/yaM5H3bBqHTKjPXVSnQTaim2e7+rLD45JxReI54
            pkuMg0FDJDzqd9YEMo4zlqlwEb6Wl6SmOxZjXm6aXt29ESbG/+joZqKzrxI6CDl7
            72ClhEY2+j0+rfF5zDctE4i7GeQLz23u82kgkv6qj+Q4KTJs9I0Lkf+yV99QVn5J
            KbihXm0CkXOgZi+26V7xZcRszD7gc4730ipepwb0Q9R3YL5Efs2Ck+Auu7HW1Mf6
            46GzCLC1doUjCIKYdJll+y0RhMsGSJVWfLc=
            -----END CERTIFICATE-----
            """)
        cert_file.close()
        os.chmod(cert_file_name, 0o444)
        with self.assertRaises(DoesNotExist):
            Registry('docker.petrode.com', certdir=self.temp_dir.name)


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
