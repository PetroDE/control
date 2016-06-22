"""Read in Controlfiles"""
import json
import logging

from control.service import MetaService, UniService

module_logger = logging.getLogger('control.controlfile')

operations = {
    'suffix': lambda x, y: '{}{}'.format(x, y),
    'prefix': lambda x, y: '{}{}'.format(y, x),
    'union': lambda x, y: set(x) | set(y)
}


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

        data = self.read_in_file(controlfile_location)
        if 'services' not in data:
            serv = UniService(data, controlfile_location)
            data = {"services": {serv.service: data}}
        self.create_service(data, 'all', {}, controlfile_location)

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

    def create_service(self, data, service_name, options, ctrlfile):
        """determine if data is a Metaservice or Uniservice"""
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
            for name, serv in data['services'].items():
                metaservice.services += self.create_service(serv, name, opers, ctrlfile)
            self.push_service_into_list(metaservice.service, metaservice)
            return metaservice.services
        else:
            serv = UniService(data, ctrlfile)
            name, service = normalize_service(serv, options)
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
def normalize_service(service, opers):
    """
    Takes a service, and options and applies the transforms to the service.

    Allowed args:
    - service: must be service object that was created before hand
    - options: a dict of options that define transforms to a service.
      The format must conform to a Controlfile metaservice options
      definition
    Returns: a dict of the normalized service
    """
    # We check that the Controlfile only specifies operations we support,
    # that way we aren't trusting a random user to accidentally get a
    # random string eval'd.
    for key, op, val in (
            (key, op, val)
            for key, ops in opers.items()
            for op, val in ops.items() if op in operations.keys()):
        module_logger.log(11, "service '%s' %sing %s with '%s'. %s",
                          service.service, op, key, val, service)
        service[key] = operations[op](service[key], val)
    return service['service'], service


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
