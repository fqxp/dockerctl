from dockerctl.container_config import ContainerConfig
from dockerctl.docker_py_client import DockerPyClient
from dockerctl.exceptions import ContainerException, ClientException
from dockerctl.name_generator import generate_name
from dockerctl.utils import pretty_date, parse_datetime
import logging
import re

logger = logging.getLogger(__name__)


class Container(object):
    """ A `Container` represents a potential or running docker container """

    def __init__(self, config, docker_client):
        self.config = config
        self.client = docker_client

    def start(self, cmd=None, interactive=False):
        if self.is_running():
            container_id = self.get_runtime_id()
            raise ContainerException('Cannot start container %s because it is already running with id %s' %
                            (self.config.name, container_id))

        self.remove_exited_containers()
        if self.config.get('autopull', False):
            self.pull()
        self.start_depends()

        container_id = self.start_without_depends(cmd, interactive=interactive)

        return container_id

    def start_depends(self):
        for container_name in self.config.get('depends_on', []):
            config = ContainerConfig(container_name)
            container = Container(config, self.client)
            if not container.is_running():
                container.start()

    def start_without_depends(self, cmd=None, interactive=False):
        image = self.config['image']
        command = cmd or self.config.get('command') or self.config.get('args')
        environment = self.config.get('environment', {})
        name = '%s-%s' % (self.config.name, generate_name())

        volumes = {}
        for volume in self.config.get('volumes', []):
            volumes[volume['host_dir']] = {
                'bind': volume['container_dir'],
                'ro': False
            }

        port_bindings = {}
        for port_mapping in self.config.get('ports', []):
            port_bindings[port_mapping['container_port']] = ('127.0.0.1', port_mapping['host_port'])

        links = {}
        for path, alias in self.config.get('links', {}).iteritems():
            linked_container = self.get_running_container_by_image_name(path)
            path_name = self.matching_name(linked_container, path)
            if path_name:
                links[path_name] = alias

        container_id = self.client.run(
            image,
            detach=not interactive,
            tty=interactive,
            command=command,
            environment=environment,
            name=name,
            binds=volumes,
            port_bindings=port_bindings,
            links=links)

        logger.info('Started container %s with id %s' % (name, container_id))

        return container_id

    def remove_exited_containers(self):
        containers = self.get_containers_by_image_name(self.config.name, only_running=False)
        exited_containers = filter(
            lambda c: c['Status'] == 'EXITED',
            containers
        )
        for container in exited_containers:
            logger.info('Removing exited %s container %s' % (self.config.name, container['Id']))
            try:
                self.client.remove_container(container['Id'])
            except ClientException as ex:
                logger.warn('Could not remove container %s: %s' % (container['Id'], ex))

    def stop(self):
        if not self.is_running():
            raise ContainerException('Cannot stop container %s because it is not running' % self.config.name)

        container_id = self.get_runtime_id()
        self.client.stop(container_id)

    def pull(self):
        image = self.config['image']
        self.client.pull(image)

    def logs(self):
        container_id = self.get_runtime_id()
        print self.client.logs(container_id)

    def status(self):
        if not self.is_running():
            print('Container %s is not running\n' % self.config.name)
        else:
            container_id = self.get_runtime_id()
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
                    '%s:%s -> %s' % (port['HostIp'] if port['HostIp'] else '*', port['HostPort'], container_port)
                    for container_port, ports in data['NetworkSettings']['Ports'].iteritems()
                    for port in (ports if ports else [])
                ]

            print '''\
Container:  %(container_name)s
Id:         %(id)s
Name:       %(name)s
Command:    %(command)s
Created:    %(created)s
Started:    %(started)s
IP address: %(ip_address)s
Ports:      %(ports)s
Volumes:    %(volumes)s
            ''' % {
                'container_name': self.config.name,
                'id': container_id,
                'name': data['Name'][1:],
                'image': data['Image'],
                'command': '%s %s' % (data['Path'], ' '.join(data['Args'])),
                'created': pretty_date(parse_datetime(data['Created'])),
                'started': pretty_date(parse_datetime(data['State']['StartedAt'])),
                'ip_address': data['NetworkSettings']['IPAddress'],
                'ports': '\n            '.join(pretty_ports),
                'volumes': '\n            '.join(pretty_volumes),
            }

    def get_runtime_id(self):
        container = self.get_running_container_by_image_name(self.config.name)

        return container['Id'] if container else None

    def is_running(self):
        return self.get_running_container_by_image_name(self.config.name) is not None

    def get_running_container_by_image_name(self, image_name):
        containers_and_names = self.get_containers_by_image_name(image_name)
        if len(containers_and_names) > 1:
            raise ContainerException("More than one instance of container %s is running, which shouldn't happen" % image_name)

        return containers_and_names[0] if len(containers_and_names) == 1 else None

    def get_containers_by_image_name(self, image_name, only_running=True):
        containers = self.client.containers(all=not only_running)
        return [container
                for container in containers
                if self.matching_name(container, image_name)]

    def matching_name(self, container, image_name):
        for name in container['Names']:
            mo = re.match(r'^/?(.*)-[a-zA-Z0-9_]+$', name)
            if mo and mo.group(1) == image_name:
                return name

        return None
