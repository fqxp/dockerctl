#! /usr/bin/env python2.7

import docker
from dockerctl.utils import pretty_date, parse_datetime
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
    DOCKER_RUN_DIR = '/var/run/dockerctl'

    @classmethod
    def available(cls):
        conf_files = filter(lambda fn: fn.endswith('.conf'), os.listdir(cls.DOCKER_CONTAINER_DIR))
        names = map(lambda fn: fn[:-5], conf_files)

        return names

    def __init__(self, name):
        self.name = name
        self.client = docker.Client()

    def read_config(self):
        config_filename = '%s/%s.conf' % (self. DOCKER_CONTAINER_DIR, self.name)
        with open(config_filename) as fd:
            return yaml.load(fd)

    def read_runtime_id(self):
        id_filename = self.runtime_id_filename()
        if not os.path.exists(id_filename):
            return None
        else:
            return open(id_filename, 'r').read().strip()

    def write_runtime_id(self, container_id):
        if not os.path.exists(self.DOCKER_RUN_DIR):
            os.makedirs(self.DOCKER_RUN_DIR)
        open(self.runtime_id_filename(), 'w').write(container_id)

    def runtime_id_filename(self):
        return os.path.join(self.DOCKER_RUN_DIR, self.name)

    def is_running(self):
        container_id = self.read_runtime_id()
        if container_id is None:
            return False

        running_ids = map(lambda container: container['Id'], self.client.containers(quiet=True))

        return container_id in running_ids

    def status(self):
        if not self.is_running():
            print('Container %s is not running' % self.name)
        else:
            container_id = self.read_runtime_id()
            data = self.client.inspect_container(container_id)
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
            container_id = self.read_runtime_id()
            raise ContainerException('Cannot start container %s because it is already running with id %s' %
                            (self.name, container_id))

        self.start_depends()

        config = self.read_config()
        image = config['image']

        volumes = dict()
        for volume in config.get('volumes', []):
            volumes[volume['host_dir']] = volume['container_dir']

        port_bindings = dict()
        for port_mapping in config.get('ports', []):
            port_bindings[port_mapping['host_port']] = port_mapping['container_port']

        container = self.client.create_container(image, detach=True, ports=port_bindings.keys())
        self.client.start(container, binds=volumes, port_bindings=port_bindings)
        self.write_runtime_id(container['Id'])

        return container['Id']

    def stop(self):

        if not self.is_running():
            raise ContainerException('Cannot stop container %s because it is not running' % self.name)

        container_id = self.read_runtime_id()
        self.client.stop(container_id)

        os.remove(self.runtime_id_filename())

    def restart(self):
        self.stop()
        self.start()

    def start_depends(self):
        config = self.read_config()

        for container_name in config.get('depends_on', []):
            container = Container(container_name)
            container.start()
