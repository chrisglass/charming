from unittest import TestCase
from charming.juju.hookenv import log


class LogTest(TestCase):


    def setUp(self):
        self.commands = []

    def fake_runner(self, command):
        self.commands.append(command)

    def test_write_default_log_message(self):
        """
        Passing simply a string to the log() call prints a message at INFO
        level.
        """
        log("Test", command_runner=self.fake_runner)
        expected = [["juju-log", "-l", "INFO", "Test"]]
        self.assertEqual(expected, self.commands)
