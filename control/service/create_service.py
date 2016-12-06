"""
A function that will take the given controlfile and return the correct service
type.
"""

from control.exceptions import InvalidControlfile
from control.service import MetaService, Startable, Buildable, BSService

service_create_matrix = {
    # Metaservice, startable, buildable
    (True, False, False):  lambda d, c: MetaService(d, c),
    (False, True, False):  lambda d, c: Startable(d, c),
    (False, False, True):  lambda d, c: Buildable(d, c),
    (False, True, True):   lambda d, c: BSService(d, c),
}


def create_service(data, controlfile):
    """
    Examine data to determine whether this is a Buildable, Startable, or BS

    throws InvalidControlfile if impure metaservice is found

    Precondition: data must not be None. controlfile must not be None
    """
    if not data:
        raise InvalidControlfile(controlfile, "No data provided. Check if "
                                 "empty service definition")
    try:
        services_in_data = 'services' in data
        return service_create_matrix[(
            services_in_data,
            'container' in data,
            data.get('build', True) and not services_in_data
        )](data, controlfile)
    except KeyError:
        raise InvalidControlfile(
            controlfile,
            "Service is not buildable, startable, nor does it define a list "
            "of services") from None
