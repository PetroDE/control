"""Specialization of Service to have many services"""

from .service import Service


class MetaService(Service):
    """Keep a list of all the services that are included in this metaservice"""

    service_options = Service.service_options

    def __init__(self, service, controlfile):
        super().__init__(service, controlfile)
        if len(set(service.keys()) & {'required', 'optional'}) == 0:
            service['required'] = False
        # Controlfile passes in the data dict for impure metaservices before
        # it recurses, so this takes the list of it is pure, and defaults to an
        # empty list if it isn't
        self.services = service['services'] if isinstance(service['services'], list) else []
        self.append = self.services.append

    def __len__(self):
        return len(self.services)

    def __getitem__(self, key):
        return self.services[key]

    def __setitem__(self, key, value):
        self.services[key] = value

    def __delitem__(self, key):
        del self.services[key]

    def __str__(self):
        return "".join(["{'", self.service, "': ", str(self.services), "}"])
