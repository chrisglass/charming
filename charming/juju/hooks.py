
class Hooks(object):
    """A convenient handler for hook functions.

    Example::

        hooks = Hooks()

        # register a hook, taking its name from the function name
        @hooks.hook()
        def install():
            pass  # your code here

        # register a hook, providing a custom hook name
        @hooks.hook("config-changed")
        def config_changed():
            pass  # your code here

        if __name__ == "__main__":
            # execute a hook based on the name the program is called by
            hooks.execute(sys.argv)
    """

    def __init__(self, config_save=None):
        super(Hooks, self).__init__()
        self._hooks = {}

        # For unknown reasons, we allow the Hooks constructor to override
        # config().implicit_save.
        if config_save is not None:
            config().implicit_save = config_save

    def register(self, name, function):
        """Register a hook"""
        self._hooks[name] = function

    def execute(self, args):
        """Execute a registered hook based on args[0]"""
        _run_atstart()
        hook_name = os.path.basename(args[0])
        if hook_name in self._hooks:
            try:
                self._hooks[hook_name]()
            except SystemExit as x:
                if x.code is None or x.code == 0:
                    _run_atexit()
                raise
            _run_atexit()
        else:
            raise UnregisteredHookError(hook_name)

    def hook(self, *hook_names):
        """Decorator, registering them as hooks"""
        def wrapper(decorated):
            for hook_name in hook_names:
                self.register(hook_name, decorated)
            else:
                self.register(decorated.__name__, decorated)
                if '_' in decorated.__name__:
                    self.register(
                        decorated.__name__.replace('_', '-'), decorated)
            return decorated
        return wrapper


