"""Read in Controlfiles"""
import copy
import json
import logging
import os
import os.path
import socket
import subprocess
import uuid

from control.exceptions import InvalidControlfile
from control.service import MetaService, Startable, ImageService, create_service
from control.substitution import normalize_service, satisfy_nested_options, _substitute_vars

dn = os.path.dirname
module_logger = logging.getLogger('control.controlfile')


def CountCalls(f):
    """Debugging decorator that counts number of times called and logs return"""
    f.count = 0

    def wrapper(*args, **kwargs):
        """log calls to a function, and the return value"""
        module_logger.debug('%s called. %i', f.__name__, f.count)
        f.count += 1
        ret = f(*args, **kwargs)
        module_logger.debug('returned %s', ret)
        return ret
    return wrapper


class Controlfile:
    """
    A structure for a normalized controlfile

    A Controlfile is a structure that holds information about services,
    a list of transforms, and a list of variables that can be substituted
    into the services.

    There are two kinds of services that Control handles. The first is
    the definition of a service, how to build an image and how to start
    containers based on that image. The second is a metaservice that
    allows you to specify a list of the first kind of services to
    handle in a batch, and allows you to define a list of transforms to
    those service, and a list of variables that may be substituted into
    the service definitions. These will be referred to as a Uniservice
    and a Metaservice, respectively.
    """

    def __init__(self, controlfile_location, force_user=False):
        """
        There's two types of Controlfiles. A multi-service file that
        allows some meta-operations on top of the other kind of
        Controlfile. The second kind is the single service Controlfile.
        Full Controlfiles can reference both kinds files to load in more
        options for meta-services.
        """
        self.logger = logging.getLogger('control.controlfile.Controlfile')
        self.services = {
            "required": MetaService({'service': 'required', 'required': True, 'services': []},
                                    controlfile_location),
            "optional": MetaService({'service': 'optional', 'required': False, 'services': []},
                                    controlfile_location)
        }
        variables = {
            "CONTROL_DIR": dn(dn(dn(os.path.abspath(__file__)))),
            "CONTROL_PATH": dn(dn(os.path.abspath(__file__))),
            "CONTROL_SESSION_UUID": uuid.uuid4(),
            "UID": os.getuid(),
            "GID": os.getgid(),
            "HOSTNAME": socket.gethostname(),
        }
        git = {}
        with subprocess.Popen(['git', 'rev-parse', '--show-toplevel'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as p:
            p.wait()
            if p.returncode == 0:
                root_dir, _ = p.communicate()
                root_dir = root_dir.decode('utf-8').strip()
                git['GIT_ROOT_DIR'] = root_dir
                with subprocess.Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE) as q:
                    q.wait()
                    if q.returncode == 0:
                        branch, _ = q.communicate()
                        git['GIT_BRANCH'] = branch.decode('utf-8').strip()
                with subprocess.Popen(['git', 'rev-parse', 'HEAD'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE) as q:
                    q.wait()
                    if q.returncode == 0:
                        commit, _ = q.communicate()
                        git['GIT_COMMIT'] = commit.decode('utf-8').strip()
                        git['GIT_SHORT_COMMIT'] = git['GIT_COMMIT'][:7]
        variables.update(git)
        variables.update(os.environ)

        data = self.read_in_file(controlfile_location)
        if not data:
            raise InvalidControlfile(controlfile_location, "empty Controlfile")
        # Check if this is a single service Controlfile, if it is, wrap in a
        # metaservice.
        if 'services' not in data:
            # Temporarily create a service to take advantage of service name guessing
            serv = create_service(copy.deepcopy(data), controlfile_location)
            data = {"services": {serv.service: data}}
        # Check if we are running --as-me, if we are, make sure that we start
        # the process with the user's UID and GID
        if force_user:
            if 'options' not in data:
                data['options'] = {}
            if 'user' not in data['options']:
                data['options']['user'] = {}
            data['options']['user']['replace'] = "{UID}:{GID}"

        self.logger.debug("variables to substitute in: %s", variables)

        self.create_service(data, 'all', {}, variables, controlfile_location)

    @classmethod
    def read_in_file(cls, controlfile):
        """Open a file, read it if it's json, complain otherwise"""
        try:
            with open(controlfile, 'r') as f:
                data = json.load(f)
        except ValueError as error:
            raise InvalidControlfile(controlfile, str(error)) from None
        return data

    @CountCalls
    def create_service(self, data, service_name, options, variables, ctrlfile):
        """
        Determine if data is a Metaservice or Uniservice

        Variables only exist to be applied if they have been defined up the
        chain of discovered Controlfiles. You don't get to randomly define a
        variable somewhere in a web of included Controlfiles and have that
        apply everywhere.
        """
        self.logger.debug('Received %i variables', len(variables))
        while 'controlfile' in data:
            ctrlfile = data['controlfile']
            # TODO write a test that gets a FileNotFound thrown from here
            data = self.read_in_file(ctrlfile)
        data['service'] = service_name

        services_in_data = 'services' in data
        services_is_list = isinstance(data.get('services', None), list)
        if services_in_data:
            self.logger.debug('metaservice named %s', service_name)
            self.logger.debug('services_is_list %s', services_is_list)
            self.logger.debug(data)
        # Recursive step
        if services_in_data and not services_is_list:
            self.logger.debug('found Metaservice %s', data['service'])
            metaservice = MetaService(data, ctrlfile)
            opers = satisfy_nested_options(outer=options, inner=data.get('options', {}))
            nvars = copy.deepcopy(variables)
            nvars.update(_substitute_vars(data.get('vars', {}), variables))
            nvars.update(os.environ)
            for name, serv in data['services'].items():
                metaservice.services += self.create_service(serv,
                                                            name,
                                                            opers,
                                                            nvars,
                                                            ctrlfile)
            self.push_service_into_list(metaservice.service, metaservice)
            return metaservice.services
        # No more recursing, we have concrete services now
        try:
            serv = create_service(data, ctrlfile)
        except InvalidControlfile as e:
            self.logger.warning(e)
            return []
        variables['SERVICE'] = serv.service
        if isinstance(serv, ImageService):
            name, service = normalize_service(serv, options, variables)
            self.push_service_into_list(name, service)
            return [name]
        self.push_service_into_list(serv.service, serv)
        return [serv.service]

    def push_service_into_list(self, name, service):
        """
        Given a service, push it into the list of services, and add an entry
        in the metaservices that it belongs in.
        """
        self.services[name] = service
        if service.required:
            self.services['required'].append(name)
        else:
            self.services['optional'].append(name)
        self.logger.debug('added %s to the service list', name)
        self.logger.log(9, self.services[name].__dict__)

    def required_services(self):
        """Return the list of required services"""
        return [s for s in self.services['required'].services
                if not isinstance(self.services[s], MetaService)]

    def get_list_of_services(self):
        """
        Return a list of the services that have been discovered. This was
        used to ensure that Controlfile discovery worked correctly in tests,
        and then I decided it could conceivably be useful for Control.
        """
        return frozenset(self.services.keys())

    def get_all_commands(self):
        """
        Return a joined list of all commands defined across all services
        """
        # for service in self.service:
        #     if (
        #             (isinstance(service, UniService) or
        #              isinstance(service, BuildService)) and
        #             service.commands):
        #         commands |= service.commands.keys()
        # Set comprehension to pull out all the unique keys
        return sorted({
            key
            for key in (
                service.commands.keys()
                for service in self.services
                if isinstance(service, Startable)
            )
        })
