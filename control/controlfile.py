"""Read in Controlfiles"""
import json
import logging
import os

from control.service import Service
from control.exceptions import NameMissingFromService, InvalidControlfile

module_logger = logging.getLogger('control.controlfile')

operations = {
    'suffix': lambda x, y: '{}{}'.format(x, y),
    'prefix': lambda x, y: '{}{}'.format(y, x),
    'union': lambda x, y: set(x) | set(y)
}


class Controlfile:
    """A holder for a normalized controlfile"""

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
            "all": {
                "services": []
            },
            "required": {
                "services": []
            },
            "optional": {
                "services": []
            }
        }

        # TODO: make sure to test when there is no Controlfile and catch
        #       that error

        self.open_discovered_controlfile(controlfile_location, options={})

    def open_discovered_controlfile(self, location, options):
        """
        Open a file, discover what kind of Controlfile it is, and hand off
        handling it to the correct function.

        Any paths found to be relative will be expanded out to be full paths.
        This way controlfile paths will be kept correct, and mount points will
        map correctly.

        There will be two handlers:
        - Complex Controlfile: Has append rules, options for all containers in
          the services list, a list of services that potentially references
          other Complex or Leaf Controlfiles
        - Leaf/Service Controlfile: defines only a single service
        """
        try:
            with open(location, 'r') as controlfile:
                data = json.load(controlfile)
                if set(data.keys()) & {'services', 'options'} != set():
                    raise NotImplementedError
        except FileNotFoundError as error:
            self.logger.warning("Cannot open controlfile %s", location)
        except json.decoder.JSONDecodeError as error:
            self.logger.warning("Controlfile %s is malformed: %s", location, error)
        else:
            serv = Service(data, location)
            name, service = normalize_service(serv, options)
            self.push_service_into_list(name, service)

    def push_service_into_list(self, name, service):
        """
        Given a service, push it into the list of services, and add an entry
        in the metaservices that it belongs in.
        """
        self.services[name] = service
        if service.required:
            self.services['required']['services'].append(name)
        else:
            self.services['optional']['services'].append(name)
        self.services['all']['services'].append(name)
        self.logger.info('added %s to the service list', name)

    def get_list_of_services(self):
        """
        Return a list of the services that have been discovered. This was
        used to ensure that Controlfile discovery worked correctly in tests,
        and then I decided it could conceivably be useful for Control.
        """
        return frozenset(
            [s['service'] for s in self.control['services'] if 'service' in s])


# TODO: eventually the global options will go away, switch this back to options then
def normalize_service(service, opers={}):
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
    return service['name'], service


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
