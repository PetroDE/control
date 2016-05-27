import sys

from .__pkginfo__ import version as __version__


def run_control():
    """run control"""
    from control.control import main
    main(sys.argv[1:])
