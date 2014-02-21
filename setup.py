#! /usr/bin/env python

from distutils.core import setup

version = open('VERSION').read().strip()

open('dockerctl/version.py', 'w').write('version = %s' % version)

setup(name='dockerctl',
      version=version,
      author='Frank Ploss',
      author_email='frank@fqxp.de',
      packages=['dockerctl'],
      scripts=['bin/dockerctl'],
      description='A tool for managing docker containers using per-container config files',
      install_requires=[
          'docker-py==0.2.3',
      ],
      data_files=[
          ('/usr/share/doc/dockerctl', ['README.md', 'doc/example.yml']),
          ('/etc/dockerctl', ['etc/dockerctl/README']),
      ])
