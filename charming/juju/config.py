import copy
import json
import os
import subprocess

from charming.juju.hookenv import Environment

class Config(dict):
    """A dictionary representation of the charm's config.yaml, with some
    extra features:

    - See which values in the dictionary have changed since the previous hook.
    - For values that have changed, see what the previous value was.
    - Store arbitrary data for use in a later hook.

    NOTE: Do not instantiate this object directly - instead call
    ``hookenv.config()``, which will return an instance of :class:`Config`.

    Example usage::

        >>> # inside a hook
        >>> from charmhelpers.core import hookenv
        >>> config = hookenv.config()
        >>> config['foo']
        'bar'
        >>> # store a new key/value for later use
        >>> config['mykey'] = 'myval'


        >>> # user runs `juju set mycharm foo=baz`
        >>> # now we're inside subsequent config-changed hook
        >>> config = hookenv.config()
        >>> config['foo']
        'baz'
        >>> # test to see if this val has changed since last hook
        >>> config.changed('foo')
        True
        >>> # what was the previous value?
        >>> config.previous('foo')
        'bar'
        >>> # keys/values that we add are preserved across hooks
        >>> config['mykey']
        'myval'

    """
    CONFIG_FILE_NAME = '.juju-persistent-config'

    def __init__(self, environment=None, *args, **kw):
        super(Config, self).__init__(*args, **kw)
        self.implicit_save = True
        self._prev_dict = None
        self.environment = environment or Environment()

        self.path = os.path.join(
            self.environment.get_charm_dir(), Config.CONFIG_FILE_NAME)
        if os.path.exists(self.path):
            self.load_previous()
        atexit(self._implicit_save)

    def load_previous(self, path=None):
        """Load previous copy of config from disk.

        In normal usage you don't need to call this method directly - it
        is called automatically at object initialization.

        :param path:

            File path from which to load the previous config. If `None`,
            config is loaded from the default location. If `path` is
            specified, subsequent `save()` calls will write to the same
            path.

        """
        self.path = path or self.path
        with open(self.path) as f:
            self._prev_dict = json.load(f)
        for k, v in copy.deepcopy(self._prev_dict).items():
            if k not in self:
                self[k] = v

    def changed(self, key):
        """Return True if the current value for this key is different from
        the previous value.

        """
        if self._prev_dict is None:
            return True
        return self.previous(key) != self.get(key)

    def previous(self, key):
        """Return previous value for this key, or None if there
        is no previous value.

        """
        if self._prev_dict:
            return self._prev_dict.get(key)
        return None

    def save(self):
        """Save this config to disk.

        If the charm is using the :mod:`Services Framework <services.base>`
        or :meth:'@hook <Hooks.hook>' decorator, this
        is called automatically at the end of successful hook execution.
        Otherwise, it should be called directly by user code.

        To disable automatic saves, set ``implicit_save=False`` on this
        instance.

        """
        with open(self.path, 'w') as f:
            json.dump(self, f)

    def _implicit_save(self):
        if self.implicit_save:
            self.save()


def config(scope=None):
    """Juju charm configuration"""
    config_cmd_line = ['config-get']
    if scope is not None:
        config_cmd_line.append(scope)
    config_cmd_line.append('--format=json')
    try:
        config_data = json.loads(
            subprocess.check_output(config_cmd_line).decode('UTF-8'))
        if scope is not None:
            return config_data
        return Config(config_data)
    except ValueError:
        return None


