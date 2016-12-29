"""Read in Controlfiles"""
import copy
import json
import logging
import os
import os.path
import subprocess

from control.exceptions import InvalidControlfile
from control.service import MetaService, Startable, ImageService, create_service

dn = os.path.dirname
module_logger = logging.getLogger('control.controlfile')

operations = {
    'suffix': '{0}{1}'.format,
    'prefix': '{1}{0}'.format,
    'union': lambda x, y: set(x) | set(y),
    'replace': lambda x, y: y,
}


def CountCalls(f):
    """Debugging decorator that counts number of times called and logs return"""
    f.count = 0

    def wrapper(*args, **kwargs):
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
            "UID": os.getuid(),
            "GID": os.getgid(),
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


# TODO: eventually the global options will go away, switch this back to options then
def normalize_service(service, opers, variables):
    """
    Takes a service, and options and applies the transforms to the service.

    Allowed args:
    - service: must be service object that was created before hand
    - options: a dict of options that define transforms to a service.
      The format must conform to a Controlfile metaservice options
      definition
    Returns: a service with all the transforms applied and all the variables
             substituted in.
    """
    # We check that the Controlfile only specifies operations we support,
    # that way we aren't trusting a random user to accidentally get a
    # random string eval'd.
    for key, op, val in (
            (key, op, val)
            for key, ops in opers.items()
            for op, val in ops.items() if op in operations.keys()):
        module_logger.log(11, "service '%s' %sing %s with '%s'.",
                          service.service, op, key, val)
        try:
            service[key] = operations[op](service[key], val)
        except KeyError as e:
            module_logger.debug(e)
            module_logger.log(11, "service '%s' missing key '%s'",
                              service.service, key)
            module_logger.log(11, service.__dict__)
    for key in service.keys():
        try:
            module_logger.debug('now at %s, passing in %i vars', key, len(variables))
            service[key] = _substitute_vars(service[key], variables)
        except KeyError:
            continue
    return service['service'], service


# used exclusively by visit_every_leaf, but defined outside it so it's only compiled once
substitute_vars_decision_dict = {
    # dict, list, str
    (True, False, False): lambda d, vd: {k: _substitute_vars(v, vd) for k, v in d.items()},
    (False, True, False): lambda d, vd: [x.format(**vd) for x in d],
    (False, False, True): lambda d, vd: d.format(**vd),
    (False, False, False): lambda d, vd: d
}


def _substitute_vars(d, var_dict):
    """
    Visit every leaf and substitute any variables that are found. This function
    is named poorly, it sounds like it should generically visit every and allow
    a function to be applied to each leaf. It does not. I have no need for that
    right now. If I find a need this will probably be the place that that goes.

    Arguments:
    - d does not necessarily need to be a dict
    - var_dict should be a dictionary of variables that can be kwargs'd into
      format
    """
    # DEBUGGING
    module_logger.debug('now at %s', str(d))
    # DEBUGGING
    return substitute_vars_decision_dict[(
        isinstance(d, dict),
        isinstance(d, list) or isinstance(d, set),
        isinstance(d, str)
    )](d, var_dict)


def satisfy_nested_options(outer, inner):
    """
    Merge two Controlfile options segments for nested Controlfiles.

    - Merges appends by having "{{layer_two}}{{layer_one}}"
    - Merges option additions with layer_one.push(layer_two)
    """
    merged = {}
    for key in set(outer.keys()) | set(inner.keys()):
        ops = set(outer.get(key, {}).keys()) | set(inner.get(key, {}).keys())
        val = {}
        # apply outer suffix and prefix to the inner union
        if 'union' in ops:
            # inner_union = [operations['prefix'](operations['suffix'](x, outer.get(key, {}).get('suffix', '')),
            #                                     outer.get(key, {}).get('prefix', ''))
            #                for x in inner.get(key, {}).get('union', [])]
            # if inner_union != []:
            #     val['union'] = set(outer.get(key, {}).get('union', [])) | set(inner.get(key, {}).get('union', []))
            union = set(outer.get(key, {}).get('union', [])) | set(inner.get(key, {}).get('union', []))
            if union:
                val['union'] = union
        elif 'suffix' in ops:
            suffix = operations['suffix'](inner.get(key, {}).get('suffix', ''),
                                          outer.get(key, {}).get('suffix', ''))
            if suffix != '':
                val['suffix'] = suffix
        elif 'prefix' in ops:
            prefix = operations['prefix'](inner.get(key, {}).get('prefix', ''),
                                          outer.get(key, {}).get('prefix', ''))
            if prefix != '':
                val['prefix'] = prefix
        elif 'replace' in ops:
            temp_ = outer.get(key, {}).get('replace', None)
            replace = operations['replace']('', temp_ if temp_ else inner.get(key).get('replace'))
            if replace != '':
                val['replace'] = replace
        merged[key] = val
    return merged
