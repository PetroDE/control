"""Define a base class for a Service"""


class Service:
    """Base class for a service"""
    def __init__(self, serv):
        try:
            self.service = serv.pop('service')
        except KeyError:
            self.service = ""

        try:
            self.required = serv.pop('required')
        except KeyError:
            self.required = not serv.pop('optional', False)
