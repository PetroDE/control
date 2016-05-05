#!/usr/bin/env python3
"""Test Controlfile discovery and normalization"""

import unittest

import control


class ControlfileNormalizationTest(unittest.TestCase):
    """
    Test different controlfile schemes to ensure they all layer in
    correctly
    """

    def test_single_service_controlfile(self):
        """Make sure that we don't break single service controlfiles"""
        #tempfile = 
        conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": [
                    "namevolume:/var/log"
                ],
                "dns_search": [
                    "example"
                ]
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
