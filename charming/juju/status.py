import subprocess
import json

from charming.juju.utils import log


def status_set(workload_state, message):
    """Set the workload state with a message

    Use status-set to set the workload state with a message which is visible
    to the user via juju status. If the status-set command is not found then
    assume this is juju < 1.23 and juju-log the message unstead.

    workload_state -- valid juju workload state.
    message        -- status update message
    """
    valid_states = ['maintenance', 'blocked', 'waiting', 'active']
    if workload_state not in valid_states:
        raise ValueError(
            '{!r} is not a valid workload state'.format(workload_state)
        )
    cmd = ['status-set', workload_state, message]
    try:
        ret = subprocess.call(cmd)
        if ret == 0:
            return
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
    log_message = 'status-set failed: {} {}'.format(workload_state,
                                                    message)
    log(log_message, level='INFO')


def status_get():
    """Retrieve the previously set juju workload state and message

    If the status-get command is not found then assume this is juju < 1.23 and
    return 'unknown', ""

    """
    cmd = ['status-get', "--format=json", "--include-data"]
    try:
        raw_status = subprocess.check_output(cmd)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return ('unknown', "")
        else:
            raise
    else:
        status = json.loads(raw_status.decode("UTF-8"))
        return (status["status"], status["message"])


