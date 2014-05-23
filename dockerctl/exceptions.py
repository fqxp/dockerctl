class ContainerException(Exception):
    """ Exception thrown by the Container class """
    pass


class ClientException(Exception):
    def __init__(self, msg, inner=None):
        self.msg = msg
        self.inner = inner

    def __str__(self):
        return '%s %s' % (self.msg, self.inner)
