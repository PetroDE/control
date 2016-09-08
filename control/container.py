"""Handle the concept of a container."""

import logging
import os
import shutil

import docker

from control.dclient import dclient
from control.options import options
from control.exceptions import (
    ContainerAlreadyExists, ContainerDoesNotExist,
    VolumePseudoExists, InvalidVolumeName,
    TransientVolumeCreation, ImageNotFound
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
        """create a container"""
        try:
            return CreatedContainer(
                dclient.create_container(
                    self.service.image,
                    **self.service.prepare_container_options()),
                self.service)
        except docker.errors.NotFound as e:
            if 'chown' in e.explanation.decode('utf-8'):
                raise VolumePseudoExists(e.explanation.decode('utf-8')) from None
            elif 'volume not found' in e.explanation.decode('utf-8'):
                raise TransientVolumeCreation(e.explanation.decode('utf-8')) from None
            elif 'No such image' in e.explanation.decode('utf-8'):
                raise ImageNotFound(self.service.image) from None

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
    """Handle things you can do to a running container"""

    def __init__(self, name, service):
        Container.__init__(self, service)
        self.exec_ids = []
        self.logger = logging.getLogger('control.container.CreatedContainer')
        if not service['name']:
            raise ContainerDoesNotExist(service.service)
        try:
            self.inspect = dclient.inspect_container(name)
        except docker.errors.NotFound as e:
            self.logger.debug(e)
            raise ContainerDoesNotExist(name)

    def check(self):
        """
        Update the inspect dict, even though there shouldn't have been a state
        transition.
        """
        self.inspect = dclient.inspect_container(self.inspect['Id'])

    def start(self):
        """Start a created container"""
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
        """stop a running container"""
        dclient.stop(self.inspect['Id'], timeout=self.service.expected_timeout)
        self.inspect = dclient.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def kill(self):
        """kill a running container"""
        dclient.kill(self.inspect['Id'])
        self.inspect = dclient.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def remove(self):
        """remove a stopped container"""
        dclient.remove_container(self.inspect['Id'], v=True)
        try:
            self.inspect = dclient.inspect_container(self.inspect['Id'])
            return False
        except docker.errors.NotFound:
            return True

    def logs(self, from_start=False, timestamps=False):
        """
        Get the logs from a container. Defaults to logs from the creation
        of the generator. Specify from_start=True to get all logs back to container
        creation.
        """
        return dclient.logs(container=self.inspect['Name'],
                            stdout=True,
                            stderr=True,
                            stream=True,
                            timestamps=timestamps,
                            tail="all" if from_start else 0)

    def exec(self, cmd):
        """
        Run a command inside the container. Returns a generator with the
        output
        """
        execd = dclient.exec_create(container=self.service['name'], cmd=cmd, tty=True)
        self.exec_ids.append(execd['Id'])
        return dclient.exec_start(execd['Id'], stream=True)

    def get_exec(self):
        """Return the top exec id in the stack"""
        return self.exec_ids[-1]

    def inspect_exec(self):
        """Return the inspect dict for the top exec"""
        return dclient.exec_inspect(self.get_exec())

    def remove_volumes(self):
        """Any volumes that were in use by the container will be removed"""
        if options.debug:
            self.logger.debug('Docker has removed these volumes:')
            for v in (v['Source']
                      for v in self.inspect['Mounts']
                      if not os.path.isdir(v['Source'])):
                self.logger.debug('  %s', v)
            self.logger.debug('Attempting to remove these volume locations:')
            for v in (v['Source']
                      for v in self.inspect['Mounts']
                      if os.path.isdir(v['Source'])):
                self.logger.debug('  %s', v)
        for vol in self.inspect['Mounts']:
            if vol['Source'].startswith('/var/lib/docker/volumes'):
                self.logger.debug('having docker remove %s', vol['Source'])
                try:
                    dclient.remove_volume(vol['Name'])
                except docker.errors.APIError as e:
                    if 'no such volume' in e.explanation.decode('utf-8'):
                        continue
                    self.logger.warning('cannot remove volume: %s',
                                        e.explanation.decode('utf-8'))
            elif os.path.isdir(vol['Source']):
                self.logger.debug('removing %s', vol['Source'])
                try:
                    shutil.rmtree(vol['Source'])
                except PermissionError as e:
                    self.logger.warning('Cannot remove directory %s: %s',
                                        vol['Source'], e)
            else:
                self.logger.debug('docker removed volume %s', vol['Source'])
