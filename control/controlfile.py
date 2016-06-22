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
            "required": MetaService(),
            "optional": MetaService()
        }

        # TODO: make sure to test when there is no Controlfile and catch
        #       that error
        # self.open_discovered_controlfile(controlfile_location, 'all', {})

        # Read in a file
            # Discover if it is a metaservice
            # If yes:
                # for each service:
                    # discover if it is a metaservice
                    # if yes: recurse
                    # if no:
                        # If it references a Controlfile, Read in file
                        # Create service
                        # Push service into (required|optional), metaservice, all
            # If no:
                # Create service
                # Push service into (required|optional), all

        data = self.read_in_file(controlfile_location)
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
        services_is_list = type(data.get('services', None) is list
        if services_in_data and services_is_list:
            metaservice = MetaService(data)
            metaservice.services = data['services']
            self.push_service_into_list(metaservice)
            return []
        elif services_in_data:
            metaservice = MetaService(data)
            opers = satisfy_nested_options(outer=options, inner=data.get('options', {}))
            for name, serv in data['services'].items():
                metaservice.services += self.create_service(serv, name, opers, ctrlfile)
            self.push_service_into_list(metaservice.service, metaservice)
            return metaservice.services
        serv = UniService(data, ctrlfile)
        name, service = normalize_service(serv, opers)
        self.push_service_into_list(name, service)
        return [name]

    # def open_discovered_controlfile(self, location, service, options):
    #     """
    #     Open a file, discover what kind of Controlfile it is, and hand off
    #     handling it to the correct function.

    #     Any paths found to be relative will be expanded out to be full paths.
    #     This way controlfile paths will be kept correct, and mount points will
    #     map correctly.

    #     There will be two handlers:
    #     - Complex Controlfile: Has append rules, options for all containers in
    #       the services list, a list of services that potentially references
    #       other Complex or Leaf Controlfiles
    #     - Leaf/Service Controlfile: defines only a single service
    #     """
    #     try:
    #         with open(location, 'r') as controlfile:
    #             data = json.load(controlfile)
    #             # if set(data.keys()) & {'services', 'options'} != set():
    #             #     raise NotImplementedError
    #     except FileNotFoundError as error:
    #         self.logger.warning("Cannot open controlfile %s", location)
    #     except json.decoder.JSONDecodeError as error:
    #         self.logger.warning("Controlfile %s is malformed: %s", location, error)
    #     preprocessed_services = []
    #     discovered = []
    #     opers = {}
    #     if 'services' in data.keys():
    #         opers = satisfy_nested_options(options, data.get('options', {}))
    #         for sname, sdata in (
    #                 (k, v)
    #                 for k, v in data['services'].items() if 'controlfile' in v):
    #             discovered = self.open_discovered_controlfile(
    #                 sdata['controlfile'],
    #                 sname,
    #                 opers)
    #             # preprocessed_services.append(
    #             #     open_servicefile(sname, sdata['controlfile']))
    #         for sname, sdata in (
    #                 (k, v)
    #                 for k, v in data['services'].items() if 'controlfile' not in v):
    #             sdata['service'] = sname
    #             discovered.append(sname)
    #             preprocessed_services.append(UniService(sdata, controlfile))
    #     else:
    #         serv = UniService(data, location)
    #         discovered.append(serv.service)
    #         preprocessed_services.append(serv)
    #     for serv in preprocessed_services:
    #         name, service = normalize_service(serv, opers)
    #         self.push_service_into_list(name, service)

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
        self.logger.info('added %s to the service list', name)
        self.logger.debug(self.services[name].__dict__)

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
        module_logger.debug("service '%s' %sing %s with %s. %s",
                            service.name, op, key, val, service)
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
