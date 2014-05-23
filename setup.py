#! /usr/bin/env python

from setuptools import setup

# TODO
# - install python-dev libyaml-dev docker
# - link virtualenv binary

version = open('VERSION').read().strip()

open('dockerctl/version.py', 'w').write("version = '%s'" % version)

setup(name='dockerctl',
      version=version,
      description='A tool for managing docker containers using per-container config files',
      author='Frank Ploss',
      author_email='dockerctl@fqxp.de',
      url='https://github.com/fqxp/dockerctl',
      packages=['dockerctl'],
      scripts=['bin/dockerctl'],
      )
