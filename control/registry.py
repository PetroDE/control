"""Talk to a registry"""

import base64
import json
import os
import sys

import requests

from control.shittylogging import log, err
from control.options import options


class Registry:
    """
    Abstraction for communicating with a Docker V2 Registry.

    Insecure registries, V1 registries, and the Docker Hub are not supported.
    """

    def __init__(self, domain, port=None, certdir='/etc/docker/certs.d'):
        """
        Take a domain name and a string port number and create a Registry object.

        This constructor ensures that it can communicate with the registry
        specified in the constructor, so construction will take time dependent
        upon the Internet connection of the machine running Control, as well as
        the performance of the Registry we are communicating with.

        Keyword arguments:
        domain -- the base domain name to connect to. Do not include the
                  protocol to communicate over.
        port   -- a string argument that is the port to connect to (optional)
        """

        self.domain = domain
        self.port = port
        if port:
            self.endpoint = '{}:{}'.format(self.domain, self.port)
        else:
            self.endpoint = self.domain
        # TODO support insecure registries and V1 registries
        self.baseuri = 'https://{}/v2'.format(self.endpoint)
        certdir = '{dir}/{reg}'.format(dir=certdir, reg=self.endpoint)
        self.use_cert = False
        self.session = requests.Session()
        if os.path.isfile(os.path.expanduser('~/.docker/config.json')):
            with open(os.path.expanduser('~/.docker/config.json')) as docker_config_file:
                try:
                    j = json.load(docker_config_file)
                    self.session.auth = tuple(
                        base64.b64decode(
                            j['auths']['https://{}'.format(self.endpoint)]['auth'])
                        .decode('utf-8')
                        .split(':'))
                    log('setting basicauth', level='debug')
                except KeyError:
                    pass
                except ValueError as e:
                    log('Docker config file not valid JSON: {}'.format(e), level='warn')
        if options.no_verify:
            self.certfile = False
            self.use_cert = True
        elif os.path.isdir(certdir):
            # for certfile in map(lambda x: '{}/{}'.format(certdir, x), os.listdir(certdir)):
            for certfile in ('{}/{}'.format(certdir, x) for x in os.listdir(certdir)):
                log('trying certfile {}'.format(certfile), level='debug')
                try:
                    self.session.get(
                        'https://{}/'.format(self.endpoint),
                        verify=certfile)
                except (requests.exceptions.SSLError, OSError) as e:
                    log('Cert file rejected {}: {}'.format(certfile, e), level='debug')
                except:
                    log('Unexpected exception: {}'.format(sys.exc_info()[0]))
                    raise
                else:
                    log('Setting verify', level='debug')
                    self.certfile = certfile
                    self.use_cert = True
                    break
        try:
            r = self.get('https://{}/v0'.format(self.endpoint))
            if r.status_code == 401:
                print('You are not logged into registry {}\nRun docker login'.format(self.endpoint))
                if options.pull:
                    sys.exit(3)
            elif [200, 404] not in r.status_code:
                print('{} {}'.format(r.status_code, r.text))
                if options.pull:
                    sys.exit(3)
        except requests.exceptions.SSLError:
            if not options.no_verify:
                # TODO: don't exit the script, throw an error
                err('Cannot verify that you are connecting to the registry you think you are')
                sys.exit(3)
        except requests.exceptions.ConnectionError as e:
            # TODO: pass through error
            err('registry {reg} could not be contacted: {msg}'.format(reg=self.endpoint,
                msg=e))
            sys.exit(3)

    def get(self, uri):
        """Make a request to the registry.

        Returns a raw requests response. Mostly for internal use, but not
        actively discouraged.
        """

        if self.use_cert:
            return self.session.get(uri, verify=self.certfile)
        return self.session.get(uri)

    def get_info_of_repo(self, repo):
        """Return the json object of the specific repo (image and tag)"""

        # log(json.dumps(reg.get_info_of_repo(base), sort_keys=True, indent=4, separators=(',', ': ')))
        response = self.get(
            '{base}/{image}/manifests/{tag}'.format(
                base=self.baseuri,
                image=repo.image,
                tag=repo.tag))
        if response.status_code == 200:
            return response.json()
        return {}

    def get_id_of_repo(self, repo):
        """Return the Image ID if the image exists, otherwise returns empty string"""

        response = self.get(
            '{base}/{image}/manifests/{tag}'.format(
                base=self.baseuri,
                image=repo.image,
                tag=repo.tag))
        if response.status_code == 200:
            return response.json()['fsLayers'][0]['blobSum']
        return ''

    def get_build_date_of_repo(self, repo):
        """Return the string image build date or empty string if doesn't exist"""

        response = self.get(
            '{base}/{image}/manifests/{tag}'.format(
                base=self.baseuri,
                image=repo.image,
                tag=repo.tag))
        if response.status_code == 200:
            return json.loads(response.json()['history'][0]['v1Compatibility'])['created']
        return ''

    def get_tags_of_image(self, image):
        """Returns the list of tags associated with the image.

        This can take some time because of the way Docker structures this data
        """

        response = self.get(
            '{base}/{image}/tags/list').format(
                base=self.baseuri,
                image=image)
        if response.status_code == 200:
            return response.json()['tags']
        return []
