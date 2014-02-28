from dockerctl.exceptions import ContainerException
from dockerctl.name_generator import generate_name
from dockerctl.utils import pretty_date, parse_datetime
import docker
import re
import os
import os.path
import yaml


class Container(object):
    """ A `Container` represents a potential or running docker container """

    DOCKER_CONTAINER_DIR = '/etc/dockerctl'

    def __init__(self, name):
        self.name = name
        self._client = None
        self._config = None

    @classmethod
    def available(cls):
        conf_files = filter(lambda fn: fn.endswith('.conf'), os.listdir(cls.DOCKER_CONTAINER_DIR))
        names = map(lambda fn: fn[:-5], conf_files)

        return names

    def start(self, cmd=None, interactive=False):
        if self.is_running():
            container_id = self.get_runtime_id()
            raise ContainerException('Cannot start container %s because it is already running with id %s' %
                            (self.name, container_id))

        self.start_depends()

        container = self.start_without_depends(cmd, interactive=interactive)

        return container['Id']

    def start_depends(self):
        for container_name in self.config().get('depends_on', []):
            container = Container(container_name)
            if not container.is_running():
                container.start()

    def start_without_depends(self, cmd=None, interactive=False):
        image = self.config()['image']
        command = cmd or self.config().get('command')
        environment = self.config().get('environment', {})
        name = '%s-%s' % (self.name, generate_name())

        volumes = {}
        for volume in self.config().get('volumes', []):
            volumes[volume['host_dir']] = volume['container_dir']

        port_bindings = {}
        for port_mapping in self.config().get('ports', []):
            port_bindings[port_mapping['container_port']] = ('127.0.0.1', port_mapping['host_port'])

        links = {}
        for path, alias in self.config().get('links', {}).iteritems():
            linked_container = self.get_running_container_by_image_name(path, running=True)
            path_name = self.matching_name(linked_container, path)
            if path_name:
                links[path_name] = alias

        container = self.client().create_container(
            image,
            detach=not interactive,
            stdin_open=interactive,
            tty=interactive,
            command=command,
            volumes=volumes.values(),
            environment=environment,
            name=name)

        self.client().start(
            container,
            binds=volumes,
            port_bindings=port_bindings,
            links=links)

        return container

    def stop(self):
        if not self.is_running():
            raise ContainerException('Cannot stop container %s because it is not running' % self.name)

        container_id = self.get_runtime_id()
        self.client().stop(container_id)

    def restart(self):
        self.stop()
        self.start()

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
                    '%s:%s -> %s' % (port['HostIp'] if port['HostIp'] else '*', port['HostPort'], container_port)
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
                'ports': '\n            '.join(pretty_ports),
                'volumes': '\n            '.join(pretty_volumes),
            }

    def client(self):
        self._client = self._client or docker.Client()
        return self._client

    def config(self):
        if self._config is None:
            config_filename = '%s/%s.conf' % (self. DOCKER_CONTAINER_DIR, self.name)
            with open(config_filename) as fd:
                self._config = yaml.load(fd)
        return self._config

    def get_runtime_id(self):
        container = self.get_running_container_by_image_name(self.name)

        return container['Id'] if container else None

    def is_running(self):
        return self.get_running_container_by_image_name(self.name) is not None

    def matching_name(self, container, image_name):
        for name in container['Names']:
            mo = re.match(r'^/(.*)-[a-zA-Z_]+$', name)
            if mo and mo.group(1) == image_name:
                return name
        return None

    def get_containers_by_image_name(self, image_name, running=True):
        containers = self.client().containers(all=not running)
        return [container
                for container in containers
                if self.matching_name(container, image_name)]

    def get_running_container_by_image_name(self, image_name):
        containers_and_names = self.get_containers_by_image_name(image_name, running=True)
        if len(containers_and_names) > 1:
            raise ContainerException("More than one instance of container %s is running, which shouldn't happen" % image_name)

        return containers_and_names[0] if len(containers_and_names) == 1 else None
