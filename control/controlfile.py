"""Read in Controlfiles"""
import copy
import json
import logging
import os.path
import subprocess

from control.service import MetaService, UniService

dn = os.path.dirname
module_logger = logging.getLogger('control.controlfile')

operations = {
    'suffix': '{}{}'.format,
    'prefix': '{}{}'.format,
    'union': lambda x, y: set(x) | set(y)
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

    def __init__(self, controlfile_location):
        """
        There's two types of Controlfiles. A multi-service file that
        allows some meta-operations on top of the other kind of
        Controlfile. The second kind is the single service Controlfile.
        Full Controlfiles can reference both kinds files to load in more
        options for meta-services.
        """
        self.logger = logging.getLogger('control.controlfile.Controlfile')
        self.services = {
            "required": MetaService({'service': 'required', 'required': True}),
            "optional": MetaService({'service': 'optional', 'required': False})
        }
        variables = {
            "CONTROL_DIR": dn(dn(dn(os.path.abspath(__file__)))),
            "CONTROL_PATH": dn(dn(os.path.abspath(__file__))),
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
                commit_file = '.git/HEAD'
                with subprocess.Popen(['git', 'symbolic-ref', '-q', 'HEAD'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE) as q:
                    q.wait()
                    if q.returncode == 0:
                        ref_path, _ = q.communicate()
                        ref_path = ref_path.decode('utf-8').strip()
                        git['GIT_BRANCH'] = os.path.basename(ref_path)
                        commit_file = os.path.join('.git', ref_path)

                with open(os.path.join(root_dir, commit_file), 'r') as f:
                    git_commit = f.read().strip()
                    git['GIT_COMMIT'] = git_commit
                    git['GIT_SHORT_COMMIT'] = git_commit[:7]
        variables.update(git)
        variables.update(os.environ)

        data = self.read_in_file(controlfile_location)
        if 'services' not in data:
            serv = UniService(data, controlfile_location)
            data = {"services": {serv.service: data}}
        self.logger.debug("variables to substitute in: %s", variables)
        self.create_service(data, 'all', {}, variables, controlfile_location)

    def read_in_file(self, controlfile):
        """Open a file, read it if it's json, complain otherwise"""
        try:
            with open(controlfile, 'r') as f:
                data = json.load(f)
        except FileNotFoundError as error:
            self.logger.warning("Cannot open controlfile %s", controlfile)
        except json.decoder.JSONDecodeError as error:
            self.logger.warning("Controlfile %s is malformed: %s", controlfile, error)
        else:
            return data
        return None

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
            data = self.read_in_file(ctrlfile)
        data['service'] = service_name

        services_in_data = 'services' in data
        services_is_list = isinstance(data.get('services', None), list)
        if services_in_data and services_is_list:
            metaservice = MetaService(data)
            metaservice.services = data['services']
            self.push_service_into_list(metaservice.service, metaservice)
            return []
        elif services_in_data:
            metaservice = MetaService(data)
            opers = satisfy_nested_options(outer=options, inner=data.get('options', {}))
            nvars = copy.deepcopy(variables)
            nvars.update(_substitute_vars(data.get('vars', {}), variables))
            for name, serv in data['services'].items():
                metaservice.services += self.create_service(serv,
                                                            name,
                                                            opers,
                                                            nvars,
                                                            ctrlfile)
            self.push_service_into_list(metaservice.service, metaservice)
            return metaservice.services
        else:
            serv = UniService(data, ctrlfile)
            name, service = normalize_service(serv, options, variables)
            self.push_service_into_list(name, service)
            return [name]

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
                if isinstance(self.services[s], UniService)]

    def get_list_of_services(self):
        """
        Return a list of the services that have been discovered. This was
        used to ensure that Controlfile discovery worked correctly in tests,
        and then I decided it could conceivably be useful for Control.
        """
        return self.services.keys()


def open_servicefile(service, location):
    """
    Read in a service from a Controlfile that defines only a single service
    This function does not catch exceptions. It is the caller's
    responsibility to catch FileNotFoundError and JSONDecoderError.
    """
    with open(location, 'r') as controlfile:
        data = json.load(controlfile)
    data['service'] = service
    serv = UniService(data, location)
    return serv


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
        service[key] = operations[op](service[key], val)
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
            inner_union = [
                operations['prefix'](
                    operations['suffix'](
                        x,
                        outer.get(key, {}).get('suffix', '')),
                    outer.get(key, {}).get('prefix', ''))
                for x in inner.get(key, {}).get('union', [])]
            if inner_union != []:
                val['union'] = set(inner_union) | set(outer.get(key, {}).get('union', []))
        if 'suffix' in ops:
            suffix = operations['suffix'](inner.get(key, {}).get('suffix', ''),
                                          outer.get(key, {}).get('suffix', ''))
            if suffix != '':
                val['suffix'] = suffix
        if 'prefix' in ops:
            prefix = operations['prefix'](inner.get(key, {}).get('prefix', ''),
                                          outer.get(key, {}).get('prefix', ''))
            if prefix != '':
                val['prefix'] = prefix
        merged[key] = val
    return merged
