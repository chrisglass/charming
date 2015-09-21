import six

from charming.juju.execute import execute_command

# Log levels
CRITICAL = "CRITICAL"
ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"
DEBUG = "DEBUG"


def log(message, level=INFO, command_runner=execute_command):
    """Write a message to the juju log by calling the "juju-log" executable.

    @param message: The message to print to the log (string).
    @param level: The log level to write the log at. Defaults to INFO. Possible
        values: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    @param command_runner: The function to execute with the command in
        parameter. Used for dependency injection in testing."""
    command = ['juju-log']
    if level:
        command += ['-l', level]
    if not isinstance(message, six.string_types):
        message = repr(message)
    command += [message]
    command_runner(command)
