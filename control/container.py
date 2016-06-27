"""Handle the concept of a container."""

import logging
import os
import shutil

import docker

from control.dclient import dclient
from control.shittylogging import log
from control.options import options
from control.exceptions import (
    ContainerAlreadyExists, ContainerDoesNotExist,
    VolumePseudoExists, InvalidVolumeName,
    TransientVolumeCreation
)


class Container:
    """
    Container is a data structure for a container. Controlfiles that specify
    containers will be read into this structure and have defaults applied where
    a default has not been explicitly overriden.
    """

    def __init__(self, service):
        self.service = service
        self.logger = logging.getLogger('control.container.Container')

    def create(self):
        log(self.conf, level='debug')
        try:
            self.service.prepare_container_options()
            return CreatedContainer(
                dclient.create_container(**self.service.container),
                self.service)
        except docker.errors.NotFound as e:
            if 'chown' in e.explanation.decode('utf-8'):
                raise VolumePseudoExists(e.explanation.decode('utf-8'))
            elif 'volume not found' in e.explanation.decode('utf-8'):
                raise TransientVolumeCreation(e.explanation.decode('utf-8'))
            self.logger.debug('Unexpected Docker 404')
            self.logger.debug(e)
            self.logger.debug(e.response)
            self.logger.debug(e.explanation.decode('utf-8'))
            raise
        except docker.errors.APIError as e:
            if 'volume name invalid' in e.explanation.decode('utf-8'):
                raise InvalidVolumeName(e.explanation.decode('utf-8'))
            elif 'is already in use by container' in e.explanation.decode('utf-8'):
                raise ContainerAlreadyExists(e.explanation.decode('utf-8'))
            self.logger.debug('Unexpected Docker API Error')
            self.logger.debug(e)
            self.logger.debug(e.response)
            self.logger.debug(e.explanation.decode('utf-8'))
            raise


class CreatedContainer(Container):
    def __init__(self, name, service):
        Container.__init__(service)
        try:
            self.inspect = dclient.inspect_container(name)
        except docker.errors.NotFound as e:
            self.logger.debug(e)
            raise ContainerDoesNotExist(name)

    def start(self):
        try:
            dclient.start(self.inspect['Id'])
        except docker.errors.NotFound as e:
            if e.explanation.decode('utf-8') == 'get: volume not found':
                raise InvalidVolumeName('volume not found')
            raise
        else:
            self.inspect = dclient.inspect_container(self.inspect['Id'])
        return self.inspect['State']['Running']

    def stop(self):
        dclient.stop(self.inspect['Id'], timeout=self.expected_timeout)
        self.inspect = dclient.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def kill(self):
        dclient.kill(self.inspect['Id'])
        self.inspect = dclient.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def remove(self):
        dclient.remove_container(self.inspect['Id'], v=True)
        try:
            self.inspect = dclient.inspect_container(self.inspect['Id'])
            return False
        except docker.errors.NotFound:
            return True

    def remove_volumes(self):
        if options.debug:
            log('Docker has removed these volumes:', level='debug')
            for v in (v['Source'] for v in self.inspect['Mounts'] if not os.path.isdir(v['Source'])):
                log('  {}'.format(v), level='debug')
            log('Attempting to remove these volume locations:', level='debug')
            for v in (v['Source'] for v in self.inspect['Mounts'] if os.path.isdir(v['Source'])):
                log('  {}'.format(v), level='debug')
        for vol in self.inspect['Mounts']:
            if vol['Source'].startswith('/var/lib/docker/volumes'):
                log('having docker remove {}'.format(vol['Source']), level='debug')
                try:
                    dclient.remove_volume(vol['Name'])
                except docker.errors.APIError as e:
                    if 'no such volume' in e.explanation.decode('utf-8'):
                        continue
                    log('cannot remove volume: {}'.format(e.explanation.decode('utf-8'), level='info'))
            elif os.path.isdir(vol['Source']):
                log('removing {}'.format(vol['Source']), level='debug')
                try:
                    shutil.rmtree(vol['Source'])
                except PermissionError as e:
                    print('Cannot remove directory {}: {}'.format(vol['Source'], e))
            else:
                log('docker removed volume {}'.format(vol['Source']), level='debug')
