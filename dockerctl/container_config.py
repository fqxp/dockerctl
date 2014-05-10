import os
import os.path
import yaml


class ContainerConfig(dict):

    DOCKER_CONTAINER_DIR = '/etc/dockerctl'

    def __init__(self, name):
        self.name = name
        self.read_config()

    @classmethod
    def available(cls):
        conf_files = filter(lambda fn: fn.endswith('.conf'), os.listdir(cls.DOCKER_CONTAINER_DIR))
        configs = map(lambda fn: ContainerConfig(fn[:-5]), conf_files)

        return configs

    def read_config(self):
        config_filename = '%s/%s.conf' % (self.DOCKER_CONTAINER_DIR, self.name)
        with open(config_filename) as fd:
            self.update(yaml.load(fd))

