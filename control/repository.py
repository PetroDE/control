"""A lot of logic to parse out what is the registry, the image, and the tag"""

import re


class Repository:
    """Container class for holding image repository information.

    These values are provided by you in the constructor
    repo.domain --- the domain name of the registry the image is held in
    repo.port   --- the port the registry is hosted at
    repo.image  --- the name of the image, "ubuntu" as an example
    repo.tag    --- the specific tag referenced, "14.04" as an example

    These values are calculated as niceties
    repo.registry --- the full endpoint ready to be wrapped in 'https://{}/' calls
    repo.repo     --- the full name as specified in a FROM line

    Repository also exposes a Repository.match(str) method which can bes used
    without instantiation which will return a Repository object if you only
    have the combined string version of a repo.
    """

    # This matches more than is valid, but not less than is valid. Notably,
    #    * Slash in the registry portion
    #    * Adjacent periods are accepted
    # But, you had an invalid repo name if you hit either of those.
    matcher = re.compile(r'(?:'
                         r'(?P<domain>localhost|(?:[-_\w]+\.[-_\w]+)+|[-_\w]+(?=:))'
                         r'(?::(?P<port>\d{1,5}))?'
                         r'/)?'
                         r'(?P<image>[-_./\w]+)'
                         r'(?::(?P<tag>[-_.\w]+))?')

    def __init__(self, image, tag='latest', domain=None, port=None):
        """Builds a repository object.

        If you only have the combined string version (like from a FROM line of
        a Dockerfile) use Repository.match(str) to construct a Repository

        Usage:
        Repository('ubuntu')
        Repository('ubuntu', '14.04')
        Repository('my-image', 'dev', 'docker.example.com')
        Repository('my-image', 'dev', 'docker.example.com', '5000')
        Repository('my-image', domain='docker.example.com', port='5002')
        """

        self.domain = domain
        self.port = port
        self.image = image
        self.tag = tag
        if domain and port:
            self.registry = '{}:{}'.format(self.domain, self.port)
        elif domain:
            self.registry = self.domain
        else:
            self.registry = None

        if self.registry:
            self.repo = '{}/{}:{}'.format(self.registry, self.image, self.tag)
        else:
            self.repo = '{}:{}'.format(self.image, self.tag)

    def __str__(self):
        return self.repo

    def get_pull_image_name(self):
        """
        This function exists because docker pull is the worst API endpoint.
        docker.Client.pull() does not allow you to specify a registry to pull from,
        but instead believes that ({registry}/){image} is the name of the image.
        """
        if self.registry:
            return "{}/{}".format(self.registry, self.image)
        return self.image

    @classmethod
    def match(cls, text):
        """Uses a regex to construct a Repository. Matches more than is valid,
        but not less than is valid.

        Repository.match('docker.example.com/my-image:dev')
        Repository.match('docker.example.com:5000/my-image:dev')
        Repository.match('docker.example.com/my-image')
        """

        match = Repository.matcher.search(text)
        return Repository(domain=match.group('domain'),
                          port=match.group('port'),
                          image=match.group('image'),
                          tag=match.group('tag') or 'latest')
