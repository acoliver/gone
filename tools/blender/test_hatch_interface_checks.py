"""Process-boundary checks for the shared Godot seal/pocket guard."""
import subprocess
import unittest
from unittest.mock import patch

import hatch_interface_checks as checks


class HatchInterfaceChecksTest(unittest.TestCase):
    def check_result(self, code, stdout, stderr=""):
        result = subprocess.CompletedProcess([], code, stdout, stderr)
        with patch.object(checks.subprocess, "run", return_value=result) as run:
            checks.check_interfaces(self, None, {"variants": []}, [], {})
        return run.call_args.args[0]

    def test_invokes_the_tracked_interface_runner(self):
        command = self.check_result(0, "INTERFACE_GUARD PASS\n")
        self.assertEqual(command[-1], str(checks.ROOT / "tests/hatch_interface_guard.gd"))

    def test_propagates_guard_failure(self):
        with self.assertRaises(AssertionError):
            self.check_result(1, "INTERFACE_GUARD seal miss\n")

    def test_rejects_zero_exit_without_guard_success(self):
        with self.assertRaises(AssertionError):
            self.check_result(0, "", "ERROR: Failed to load script\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
