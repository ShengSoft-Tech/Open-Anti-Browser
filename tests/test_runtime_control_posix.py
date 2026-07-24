import sys
import unittest
from unittest.mock import MagicMock, patch

from backend import runtime_control


class RuntimeControlPosixTests(unittest.TestCase):
    """XPLAT-04: start_backend_only 的 Popen creationflags 必须按平台条件化。"""

    def _mock_popen(self, pid: int = 4242) -> MagicMock:
        proc = MagicMock()
        proc.pid = pid
        return proc

    @patch.object(sys, "platform", "darwin")
    @patch("backend.runtime_control.get_backend_only_status")
    @patch("backend.runtime_control._wait_for_port", return_value=True)
    @patch("backend.runtime_control.subprocess.Popen")
    def test_posix_popen_uses_start_new_session_no_creationflags(
        self, mock_popen, _mock_wait, mock_status
    ) -> None:
        mock_popen.return_value = self._mock_popen()
        mock_status.side_effect = [
            {"running": False, "pid": None, "port": 18000, "base_url": "", "docs_url": ""},
            {"running": True, "pid": 4242, "port": 18000, "base_url": "", "docs_url": ""},
        ]

        result = runtime_control.start_backend_only(18000)

        self.assertTrue(result["running"])
        _, kwargs = mock_popen.call_args
        self.assertEqual(kwargs.get("start_new_session"), True)
        self.assertFalse(kwargs.get("creationflags"))

    @patch.object(sys, "platform", "win32")
    @patch("backend.runtime_control.get_backend_only_status")
    @patch("backend.runtime_control._wait_for_port", return_value=True)
    @patch("backend.runtime_control.subprocess.Popen")
    def test_win32_popen_uses_creationflags_no_start_new_session(
        self, mock_popen, _mock_wait, mock_status
    ) -> None:
        mock_popen.return_value = self._mock_popen()
        mock_status.side_effect = [
            {"running": False, "pid": None, "port": 18000, "base_url": "", "docs_url": ""},
            {"running": True, "pid": 4242, "port": 18000, "base_url": "", "docs_url": ""},
        ]

        result = runtime_control.start_backend_only(18000)

        self.assertTrue(result["running"])
        _, kwargs = mock_popen.call_args
        self.assertEqual(
            kwargs.get("creationflags"),
            runtime_control.DETACHED_PROCESS | runtime_control.CREATE_NEW_PROCESS_GROUP,
        )
        self.assertNotIn("start_new_session", kwargs)

    def test_constants_still_defined(self) -> None:
        self.assertTrue(hasattr(runtime_control, "CREATE_NEW_PROCESS_GROUP"))
        self.assertTrue(hasattr(runtime_control, "DETACHED_PROCESS"))


if __name__ == "__main__":
    unittest.main()
