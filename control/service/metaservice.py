"""Specialization of Service to have many services"""

from .service import Service


class MetaService(Service):
    """Keep a list of all the services that are included in this metaservice"""
    def __init__(self, service):
        Service.__init__(self, service)
        self.services = []
        self.append = self.services.append

    def __len__(self):
        return len(self.services)

    def __getitem__(self, key):
        return self.services[key]

    def __setitem__(self, key, value):
        self.services[key] = value

    def __delitem__(self, key):
        del self.services[key]

    def __add__(self, other):
        return self.services + other
