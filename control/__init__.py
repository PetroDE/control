import sys

from .__pkginfo__ import version as __version__

# Shut up requests because the user has to make a conscious choice to be
# insecure
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def run_control():
    """run control"""
    from control.control import main
    main(sys.argv[1:])
