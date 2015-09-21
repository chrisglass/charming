import subprocess

def execute_command(command, command_runner=subprocess.check_output):
    """Execute a shell command and return the output to the caller.

    @param command: A list of executable + arguments, as expected in the
        subprocess module. Example: ["/usr/bin/ls", "-ali"].
    @param command_runner: The command running function to use, mos.tly useful
        for injection at test time. Defaults to subprocess.check_output"""
    return command_runner(command, universal_newlines=True).decode("UTF-8")


