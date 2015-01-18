from dockerctl.exceptions import ClientException
from dockerctl.utils import split_image_and_tag
import docker
import json
import logging

logger = logging.getLogger(__name__)

class DockerPyClient:

    def __init__(self):
        self._client = docker.Client()

    def containers(self, all=False):
        containers = self._client.containers(all=all)

        return [
            {
                'Command': container['Command'],
                'Id':      container['Id'],
                'Image':   container['Image'],
                'Names':   container['Names'],
                'Status':  'EXITED' if container['Status'].startswith('Exited') else 'RUNNING',
            }
            for container in containers
        ]

    def run(self, image, detach=False, tty=False,
            command=None, environment=None, name=None,
            binds=None, port_bindings=None, links=None):
        container = self._client.create_container(
            image,
            detach=detach,
            stdin_open=tty,
            tty=tty,
            command=command,
            volumes=[bind['bind'] for bind in binds.values()],
            environment=environment,
            name=name)

        self._client.start(
            container,
            binds=binds,
            port_bindings=port_bindings,
            links=links)

        return container['Id']

    def stop(self, container_id):
        self._client.stop(container_id)

    def pull(self, image):
        image, tag = split_image_and_tag(image)
        for msg in self._client.pull(image, tag=tag, stream=True):
            json_msg = json.loads(msg)
            progress = '%s ' % json_msg['progress'] if json_msg.has_key('progress') else ''
            status = json_msg.get('status', '')
            logger.info('%s%s' % (progress, status))

    def logs(self, container_id):
        return self._client.logs(container_id)

    def inspect_container(self, container_id):
        return self._client.inspect_container(container_id)

    def remove_container(self, container_id):
        try:
            return self._client.remove_container(container_id)
        except docker.errors.APIError as ex:
            raise ClientException('API error while removing container %s' % container_id, ex)
