"""Install Control"""

import os.path
from setuptools import setup, find_packages

from control.__pkginfo__ import version

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='control',
    version=version,
    description='Build images and manage containers for dev and prod',
    long_description=long_description,
    author='Ezekiel Chopper',
    author_email='echopper@petrode.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    keywords='docker container build ci',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'docker-py ~= 1.7.2',
        'python-dateutil',
        'requests ~= 2.10.0',
        'urllib3',
    ],
    entry_points={
        'console_scripts': ['control=control:run_control']
    }
)
