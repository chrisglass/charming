import json

from charming.juju.hookenv import Environment

class Leadership(object):

    def __init__(self, environment=None):
        self.environment = environment or Environment()

    @translate_exc(from_exc=OSError, to_exc=NotImplementedError)
    def is_leader(self):
        """Does the current unit hold the juju leadership

        Uses juju to determine whether the current unit is the leader of its
        peers.
        """
        cmd = ['is-leader', '--format=json']
        result = self.environment.command_runner(cmd)
        return json.loads(result)


    @translate_exc(from_exc=OSError, to_exc=NotImplementedError)
    def leader_get(self, attribute=None):
        """Juju leader get value(s)"""
        cmd = ['leader-get', '--format=json'] + [attribute or '-']
        return json.loads(subprocess.check_output(cmd).decode('UTF-8'))


@translate_exc(from_exc=OSError, to_exc=NotImplementedError)
def leader_set(settings=None, **kwargs):
    """Juju leader set value(s)"""
    # Don't log secrets.
    # log("Juju leader-set '%s'" % (settings), level=DEBUG)
    cmd = ['leader-set']
    settings = settings or {}
    settings.update(kwargs)
    for k, v in settings.items():
        if v is None:
            cmd.append('{}='.format(k))
        else:
            cmd.append('{}={}'.format(k, v))
    subprocess.check_call(cmd)


