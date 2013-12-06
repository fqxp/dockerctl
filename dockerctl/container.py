#! /usr/bin/env python2.7

import datetime
import json
import yaml
import os
import os.path
import re
import subprocess
import sys


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"

def parse_datetime(s):
    return datetime.datetime(*map(int, re.split('[^\d]', s)[:-2]))


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

    def read_config(self):
        config_filename = '%s/%s.conf' % (self. DOCKER_CONTAINER_DIR, self.name)
        with open(config_filename) as fd:
            return yaml.load(fd)

    def read_runtime_id(self):
        id_filename = self.runtime_id_filename()
        if not os.path.exists(id_filename):
            return None
        else:
            return open(id_filename, 'r').read().strip()[:12]

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

        running_ids = self._run_command(['docker', 'ps', '-q']).strip().split('\n')

        return container_id[:12] in running_ids

    def status(self):
        if not self.is_running():
            print('Container %s is not running' % self.name)
        else:
            container_id = self.read_runtime_id()[:12]
            data = json.loads(self._run_command(['docker', 'inspect', container_id]))[0]

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
                'ports': '\n             '.join([
                    '%s:%s -> %s' % (port['HostIp'], port['HostPort'], container_port)
                    for container_port, ports in data['NetworkSettings']['Ports'].iteritems()
                    for port in ports
                ]),
                'volumes': '\n            '.join([
                    '%s -> %s %s' % (host_dir, container_dir, '' if data['VolumesRW'][host_dir] else '[read-only]')
                    for host_dir, container_dir in data['Volumes'].iteritems()
                ]),
            }

    def start(self):
        if self.is_running():
            container_id = self.read_runtime_id()
            raise ContainerException('Cannot start container %s because it is already running with id %s' %
                            (self.name, container_id))

        config = self.read_config()

        self.start_depends()

        image = config['image']
        args = ['docker', 'run', '-d']

        for volume in config.get('volumes', []):
            args += ['-v', '%s:%s' % (volume['host_dir'], volume['container_dir'])]
        for port_mapping in config.get('ports', []):
            args += ['-p', '%d:%d' % (port_mapping['host_port'], port_mapping['container_port'])]
        args += [image]

        container_id = self._run_command(args, verbose=True).strip()
        self.write_runtime_id(container_id)

        return container_id

    def stop(self):

        if not self.is_running():
            raise ContainerException('Cannot stop container %s because it is not running' % self.name)

        container_id = self.read_runtime_id()
        self._run_command(['docker', 'stop', container_id])

        os.remove(self.runtime_id_filename())

    def restart(self):
        self.stop()
        self.start()

    def start_depends(self):
        config = self.read_config()

        for container_name in config.get('depends_on', []):
            container = Container(container_name)
            container.start()

    def _run_command(self, cmd_args, verbose=False):
        if verbose:
            print 'Running ’%s’' % (' '.join(cmd_args))
        output = subprocess.check_output(cmd_args, stderr=subprocess.STDOUT)
        if verbose:
            print 'Success.'
        return output

