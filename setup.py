#!/usr/bin/env python
import os
import re
from setuptools import setup, find_packages

__copyright__ = "Copyright (c) 2018 Cisco and/or its affiliates."
__license__ = "MIT"


PACKAGE_NAME = 'webexteamsarchiver'

PACKAGE_KEYWORDS = [
    'cisco',
    'webex',
    'teams',
    'spark',
    'python',
    'messaging',
]

PACKAGE_CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: System Administrators',
    'Intended Audience :: Telecommunications Industry',
    'Intended Audience :: Information Technology',
    'Natural Language :: English',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Topic :: Communications',
    'Topic :: Communications :: Chat'
]

INSTALLATION_REQUIREMENTS = [
    'webexteamssdk',
    'jinja2',
    'requests',
    'hurry.filesize',
    'bump2version',
]

long_description = open(
    os.path.join(
        os.path.dirname(__file__),
        'README.rst'
    )
).read()

setup(
    name=PACKAGE_NAME,
    author='Felipe de Mello',
    author_email='fdemello@cisco.com',
    version='0.11.0',
    url='https://github.com/CiscoDevNet/webex-teams-archiver',
    description='Room archiver utility for Webex Teams',
    long_description=long_description,
    packages=find_packages('.'),
    include_package_data=True,
    install_requires=INSTALLATION_REQUIREMENTS,
    keywords=' '.join(PACKAGE_KEYWORDS),
    classifiers=PACKAGE_CLASSIFIERS,
    license='MIT; Copyright (c) 2018 Cisco Systems, Inc.'
)