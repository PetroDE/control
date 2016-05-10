#!/usr/bin/env python3
"""Test Controlfile discovery and normalization"""

import json
import os
import tempfile
import unittest

import control


class ControlfileNormalizationTest(unittest.TestCase):
    """
    Test different controlfile schemes to ensure they all layer in
    correctly
    """

    def test_single_service_controlfile(self):
        """Make sure that we don't break single service controlfiles"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = '{}/Controlfile'.format(temp_dir.name)
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
        ret = control.normalize_controlfiles(controlfile_location=controlfile)
        self.assertEqual(ret['services'][0], conf)
        temp_dir.cleanup()

    def test_including_controlfiles(self):
        """Make sure that single level Controlfile inclusion works correctly"""
        temp_dir = tempfile.TemporaryDirectory()
        controlfile = '{}/Controlfile'.format(temp_dir.name)
        conf = {
            "services": [
                {
                    "service": "test",
                    "controlfile": "test/Controlfile"
                }
            ]
        }
        service_conf = {
            "image": "busybox",
            "container": {
                "name": "example",
                "hostname": "example",
                "volumes": ["namevolume:/var/log"],
                "dns_search": ["example"]
            }
        }
        with open(controlfile, 'w') as f:
            f.write(json.dumps(conf))
        os.mkdir('{}/test'.format(temp_dir.name))
        with open('{}/test/Controlfile'.format(temp_dir.name), 'w') as f:
            f.write(json.dumps(service_conf))

        ret = control.normalize_controlfiles(controlfile)
        self.assertEqual(ret['services'][0], service_conf)
