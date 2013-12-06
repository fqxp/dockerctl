#! /usr/bin/env python

from distutils.core import setup
import os

version_w = open('VERSION').read().strip()
version = '0.1'

print 'TRUE' if version_w==version else 'FALEA'

setup(name='dockerctl',
      version=version,
      author='Frank Ploss',
      author_email='frank@fqxp.de',
      py_modules=['dockerctl'],
      scripts=['dockerctl'],
      description='A tool for managing docker containers using per-container config files',
      data_files=[
          ('/usr/share/doc/dockerctl', ['README.md']),
          ('/etc/dockerctl', ['etc/dockerctl/README']),
      ])
