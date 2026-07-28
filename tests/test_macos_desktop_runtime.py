import sys
import unittest
from unittest.mock import MagicMock, patch

import launch_app


class MacQuitInterceptionTests(unittest.TestCase):
    """D-07: macOS Cmd+Q 必须收敛到既有 force_exit() 路径，Windows/Linux 不拦截。"""

    def test_should_intercept_quit_event_true_on_darwin(self) -> None:
        with patch.object(sys, "platform", "darwin"):
            self.assertTrue(launch_app.should_intercept_quit_event())

    def test_should_intercept_quit_event_false_on_win32(self) -> None:
        with patch.object(sys, "platform", "win32"):
            self.assertFalse(launch_app.should_intercept_quit_event())

    def test_should_intercept_quit_event_false_on_linux(self) -> None:
        with patch.object(sys, "platform", "linux"):
            self.assertFalse(launch_app.should_intercept_quit_event())

    def test_handle_macos_quit_request_calls_force_exit_once_and_returns_true(self) -> None:
        window = MagicMock()
        result = launch_app.handle_macos_quit_request(window)
        window.force_exit.assert_called_once_with()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
