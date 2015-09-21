from charming.juju.hookenv import Environment


class Network(object):
    """
    An object holding the methods relating to network operations for the
    current charm.
    """

    def __init__(self, environment):
        self._environment = environment or Environment()

    def open_port(self, port, protocol="TCP"):
        """Open a service network port."""
        cmd = ['open-port']
        cmd.append('{}/{}'.format(port, protocol))
        self._environment.command_runner(cmd)


    def close_port(self, port, protocol="TCP"):
        """Close a service network port"""
        cmd = ['close-port']
        cmd.append('{}/{}'.format(port, protocol))
        self._environment.command_runner(cmd)

    def unit_public_ip(self):
        """Get this unit's public IP address"""
        return self.environment.unit_get('public-address')

    def unit_private_ip(self):
        """Get this unit's private IP address"""
        return self.environment.unit_get('private-address')



