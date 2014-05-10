import docker


class DockerPyClient:

    def __init__(self):
        self._client = docker.Client()

    def containers(self, all=False):
        return self._client.containers(all=all)

    def run(self, image, detach=False, stdin_open=False, tty=False,
            command=None, environment=None, name=None,
            binds=None, port_bindings=None, links=None):
        container = self._client.create_container(
            image,
            detach=detach,
            stdin_open=stdin_open,
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

        return container

    def stop(self, container_id):
        self._client.stop(container_id)

    def inspect_container(self, container_id):
        return self._client.inspect_container(container_id)
