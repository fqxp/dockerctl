import json
import logging
import subprocess


logger = logging.getLogger(__name__)

class DockerCmdlineClient:

    DOCKER = 'docker'

    def __init__(self):
        pass

    def _run_cmd(self, cmd):
        logger.debug('Running %s' % (' '.join(arg.replace('\\', '\\\\').replace(' ', '\\ ') for arg in cmd)))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output, _) = process.communicate()
        if process.returncode != 0:
            logger.error('Command failed (%d): %s' % (process.returncode, output))
            raise Exception('Command failed (%d): %s' % (process.returncode, output))
        else:
            logger.debug('Return code %d' % process.returncode)
        return output

    def containers(self, all=False):
        cmd = [self.DOCKER, 'ps', '--no-trunc=true']
        if all:
            cmd.append('-a')
        output = self._run_cmd(cmd)
        lines = output.splitlines()[1:]
        containers = []
        for line in lines:
            words = line.split()
            containers.append({
                'Id': words[0],
                'Image': words[1],
                'Names': words[-1].split(','),
            })
        return containers

    def run(self, image, detach=False, tty=False,
            command=None, environment=None, name=None,
            binds=None, port_bindings=None, links=None):
        cmd = [self.DOCKER, 'run']

        if detach: cmd.append('-d')
        if tty:    cmd.append('-t')
        if name:   cmd.append('--name=%s' % name)
        for key, value in (environment or {}).iteritems():
            cmd.append('--env=%(key)s=%(value)s' % {
                'key': key,
                'value': value})
        for key, value in (binds or {}).iteritems():
            cmd.append('--volume=%(host_dir)s:%(container_dir)s:%(access)s' % {
                'host_dir': key,
                'container_dir': value['bind'],
                'access': 'ro' if value['ro'] else 'rw'})
        for key, value in (port_bindings or {}).iteritems():
            cmd.append('--publish=%(ip_addr)s:%(host_port)s:%(container_port)s' % {
                'ip_addr': value[0],
                'host_port': value[1],
                'container_port': key,
            })
        for key, value in (links or {}).iteritems():
            cmd.append('--link=%(name)s:%(alias)s' % {
                'name': key,
                'alias': value
            })
        cmd.append(image)
        if command: cmd.extend(command.split())

        container_id = self._run_cmd(cmd)
        return container_id

    def stop(self, container_id):
        self._run_cmd([self.DOCKER, 'stop', container_id])

    def inspect_container(self, container_id):
        output = self._run_cmd([self.DOCKER, 'inspect', container_id])
        return json.loads(output)[0]

