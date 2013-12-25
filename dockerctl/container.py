#! /usr/bin/env python2.7

import docker
from dockerctl.utils import pretty_date, parse_datetime
from dockerctl.name_generator import generate_name
import datetime
import json
import yaml
import os
import os.path
import re
import subprocess
import sys


class ContainerException(Exception):
    pass


class Container(object):

    DOCKER_CONTAINER_DIR = '/etc/dockerctl'

    @classmethod
    def available(cls):
        conf_files = filter(lambda fn: fn.endswith('.conf'), os.listdir(cls.DOCKER_CONTAINER_DIR))
        names = map(lambda fn: fn[:-5], conf_files)

        return names

    def __init__(self, name):
        self.name = name
        self._client = None
        self._config = None

    def client(self):
        if self._client is None:
            self._client = docker.Client()
        return self._client

    def config(self):
        if self._config is None:
            config_filename = '%s/%s.conf' % (self. DOCKER_CONTAINER_DIR, self.name)
            with open(config_filename) as fd:
                self._config = yaml.load(fd)
        return self._config

    def get_runtime_id(self):
        container = self.get_container_by_name(self.name)

        return container['Id'] if container else None

    def get_container_by_name(self, name):
        containers = self.client().containers()
        for container in containers:
            for n in container['Names']:
                if re.match(r'^/%s#[a-zA-Z_]+$' % name, n):
                    return container
        return None

    def matching_name(self, name):
        containers = self.client().containers()
        for container in containers:
            for n in container['Names']:
                if re.match(r'^/%s#[a-zA-Z_]+$' % name, n):
                    return n
        return None

    def is_running(self):
        return self.get_container_by_name(self.name) is not None

    def status(self):
        if not self.is_running():
            print('Container %s is not running' % self.name)
        else:
            container_id = self.get_runtime_id()
            data = self.client().inspect_container(container_id)
            pretty_volumes = []
            pretty_ports = []

            if data['Volumes']:
                pretty_volumes = [
                    '%s -> %s %s' % (host_dir, container_dir, '' if data['VolumesRW'][host_dir] else '[read-only]')
                    for host_dir, container_dir in data['Volumes'].iteritems()
                ]
            if data['NetworkSettings'] and data['NetworkSettings']['Ports']:
                pretty_ports = [
                    '%s:%s -> %s' % (port['HostIp'] if port['HostIp'] else '0.0.0.0', port['HostPort'], container_port)
                    for container_port, ports in data['NetworkSettings']['Ports'].iteritems()
                    for port in (ports if ports else [])
                ]

            print '''CONTAINER:  %(container_name)s
Id:         %(id)s
Name:       %(name)s
Command:    %(command)s
Created:    %(created)s
Started:    %(started)s
IP address: %(ip_address)s
Ports:      %(ports)s
Volumes:    %(volumes)s
            ''' % {
                'container_name': self.name,
                'id': container_id,
                'name': data['Name'][1:],
                'image': data['Image'],
                'command': ' '.join(data['Config']['Cmd']),
                'created': pretty_date(parse_datetime(data['Created'])),
                'started': pretty_date(parse_datetime(data['State']['StartedAt'])),
                'ip_address': data['NetworkSettings']['IPAddress'],
                'ports': '\n             '.join(pretty_ports),
                'volumes': '\n            '.join(pretty_volumes),
            }

    def start(self):
        if self.is_running():
            container_id = self.get_runtime_id()
            raise ContainerException('Cannot start container %s because it is already running with id %s' %
                            (self.name, container_id))

        self.start_depends()

        container = self.start_without_depends()

        return container['Id']

    def start_without_depends(self):
        image = self.config()['image']
        command = self.config().get('command')
        name = '%s#%s' % (self.name, generate_name())
        container = self.client().create_container(image, detach=True, command=command, name=name)

        volumes = {}
        for volume in self.config().get('volumes', []):
            volumes[volume['host_dir']] = volume['container_dir']

        port_bindings = {}
        for port_mapping in self.config().get('ports', []):
            port_bindings[port_mapping['host_port']] = port_mapping['container_port']

        links = {}
        for path, alias in self.config().get('links', {}).iteritems():
            path_name = self.matching_name(path)
            if path_name:
                links[path_name] = alias

        import pprint
        pprint.pprint(container)
        pprint.pprint(volumes)
        pprint.pprint(port_bindings)
        pprint.pprint(links)
        self.client().start(container, binds=volumes, port_bindings=port_bindings, links=links)

        return container

    def stop(self):
        if not self.is_running():
            raise ContainerException('Cannot stop container %s because it is not running' % self.name)

        container_id = self.get_runtime_id()
        self.client().stop(container_id)

    def restart(self):
        self.stop()
        self.start()

    def start_depends(self):
        for container_name in self.config().get('depends_on', []):
            container = Container(container_name)
            container.start()
