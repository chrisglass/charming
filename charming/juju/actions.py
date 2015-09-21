import json
import os
import subprocess

def action_get(key=None):
    """Gets the value of an action parameter, or all key/value param pairs"""
    cmd = ['action-get']
    if key is not None:
        cmd.append(key)
    cmd.append('--format=json')
    action_data = json.loads(subprocess.check_output(cmd).decode('UTF-8'))
    return action_data


def action_set(values):
    """Sets the values to be returned after the action finishes"""
    cmd = ['action-set']
    for k, v in list(values.items()):
        cmd.append('{}={}'.format(k, v))
    subprocess.check_call(cmd)


def action_fail(message):
    """Sets the action status to failed and sets the error message.

    The results set by action_set are preserved."""
    subprocess.check_call(['action-fail', message])


def action_name():
    """Get the name of the currently executing action."""
    return os.environ.get('JUJU_ACTION_NAME')


def action_uuid():
    """Get the UUID of the currently executing action."""
    return os.environ.get('JUJU_ACTION_UUID')


def action_tag():
    """Get the tag for the currently executing action."""
    return os.environ.get('JUJU_ACTION_TAG')
