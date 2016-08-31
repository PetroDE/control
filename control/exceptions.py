"""Exceptions that Control will raise internally to signal error conditions"""


class ControlException(BaseException):
    """
    Base exception for Control. There's going to be a lot of these.
    Because Docker(TM)
    """


# Controlfile Exceptions
class NameMissingFromService(ControlException):
    """The name of this service cannot be deduced from the service dict"""


class InvalidControlfile(ControlException):
    """
    The Controlfile does not conform to the requirements.
    Either, it is not valid json, or you didn't specify an image name to use.
    """


# Container Exceptions
class ContainerException(ControlException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class ContainerAlreadyExists(ContainerException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return '''Container already exists: {}'''.format(self.msg)


class ContainerDoesNotExist(ContainerException):
    """A much more useful error than docker-py's standard 404 message"""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Container does not exist: {}'.format(self.name)


class ContainerNotRunning(ContainerException):
    """The container is not running"""


class VolumePseudoExists(ContainerException):
    """Volumes were probably manually removed, but Docker caches volume's existence"""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return '''Docker is having trouble creating a volume. Try looking
        at docker volume ls or try restarting the docker daemon.'''


class InvalidVolumeName(ContainerException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class TransientVolumeCreation(ContainerException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return '''You cannot create transient volumes in the Controlfile.
        Name your volume, or bind it to the host'''


# Image exceptions
class ImageNotFound(ControlException):
    def __init__(self, image):
        self.image = image

    def __str__(self):
        return '''Image does not exist: {}'''.format(self.image)
