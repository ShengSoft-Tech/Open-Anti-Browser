import unittest
from unittest.mock import patch

from backend.services import synchronizer


class SynchronizerPlatformGateTests(unittest.TestCase):
    def _make_synchronizer(self) -> synchronizer.BrowserSynchronizer:
        return synchronizer.BrowserSynchronizer(
            runtime_resolver=lambda pid: None,
            profile_resolver=lambda pid: None,
        )

    @patch("backend.services.synchronizer.sys.platform", "darwin")
    def test_start_raises_runtime_error_on_non_windows(self):
        sync = self._make_synchronizer()
        with self.assertRaises(RuntimeError) as ctx:
            sync.start("m", ["f"])
        self.assertEqual(str(ctx.exception), "窗口同步仅在 Windows 上可用")

    @patch("backend.services.synchronizer.sys.platform", "darwin")
    def test_start_gate_precedes_argument_validation(self):
        sync = self._make_synchronizer()
        # Even with an empty master_profile_id (which would normally trigger
        # the existing ValueError), the platform gate must fire first.
        with self.assertRaises(RuntimeError) as ctx:
            sync.start("", [])
        self.assertEqual(str(ctx.exception), "窗口同步仅在 Windows 上可用")

    @patch("backend.services.synchronizer.sys.platform", "win32")
    def test_start_on_windows_is_not_gated(self):
        sync = self._make_synchronizer()
        # win32 path is unaffected by the gate: empty master still raises the
        # pre-existing ValueError, not the platform RuntimeError.
        with self.assertRaises(ValueError) as ctx:
            sync.start("", [])
        self.assertEqual(str(ctx.exception), "请选择主浏览器")


if __name__ == "__main__":
    unittest.main()
