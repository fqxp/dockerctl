import docker


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

    def run(self, image, detach=False, stdin_open=False, tty=False,
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

    def inspect_container(self, container_id):
        return self._client.inspect_container(container_id)

    def remove_container(self, container_id):
        return self._client.remove_container(container_id)
