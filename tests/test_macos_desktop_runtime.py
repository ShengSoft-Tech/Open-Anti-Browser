import re
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import launch_app


REPO_ROOT = Path(__file__).resolve().parent.parent
GATEKEEPER_NOTICE_JS = REPO_ROOT / "frontend" / "src" / "lib" / "macosGatekeeperNotice.js"


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


class BundleRootResolutionTests(unittest.TestCase):
    """D-12: 从可执行文件路径推导 .app bundle 根目录。"""

    def test_resolves_bundle_root_from_nested_executable(self) -> None:
        executable = "/Applications/Open-Anti-Browser.app/Contents/MacOS/Open-Anti-Browser"
        result = launch_app.resolve_app_bundle_root(executable)
        self.assertEqual(result, Path("/Applications/Open-Anti-Browser.app"))

    def test_returns_none_for_non_bundle_executable(self) -> None:
        result = launch_app.resolve_app_bundle_root("/usr/local/bin/python3")
        self.assertIsNone(result)


class TranslocationDetectionTests(unittest.TestCase):
    """RESEARCH Pitfall 4: 用 /AppTranslocation/ 子串判定，不调用私有 API。"""

    def test_detects_translocated_path(self) -> None:
        translocated = (
            "/private/var/folders/xx/abc/T/AppTranslocation/"
            "1234-5678/d/Open-Anti-Browser.app"
        )
        self.assertTrue(launch_app.is_translocated_path(translocated))

    def test_canonical_install_path_is_not_translocated(self) -> None:
        self.assertFalse(
            launch_app.is_translocated_path("/Applications/Open-Anti-Browser.app")
        )


class StripQuarantineFromBundleTests(unittest.TestCase):
    """D-12: 递归剥离整个 bundle 的 quarantine 属性，不真的执行 xattr。"""

    @patch("launch_app.subprocess.run")
    def test_calls_xattr_dr_exactly_once_with_expected_args(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        bundle = Path("/Applications/Open-Anti-Browser.app")

        succeeded, message = launch_app.strip_quarantine_from_bundle(bundle)

        mock_run.assert_called_once_with(
            ["xattr", "-dr", "com.apple.quarantine", str(bundle)],
            capture_output=True,
            text=True,
        )
        self.assertTrue(succeeded)
        self.assertEqual(message, "")

    @patch("launch_app.subprocess.run")
    def test_nonzero_returncode_reports_failure_with_stderr(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="Operation not permitted\n")
        bundle = Path("/Applications/Open-Anti-Browser.app")

        succeeded, message = launch_app.strip_quarantine_from_bundle(bundle)

        self.assertFalse(succeeded)
        self.assertEqual(message, "Operation not permitted")


class QuarantineCommandTargetTests(unittest.TestCase):
    def test_translocated_bundle_targets_canonical_install_path(self) -> None:
        translocated = Path(
            "/private/var/folders/xx/abc/T/AppTranslocation/1234/d/Open-Anti-Browser.app"
        )
        self.assertEqual(
            launch_app.quarantine_command_target(translocated),
            launch_app.CANONICAL_INSTALL_BUNDLE,
        )

    def test_none_bundle_targets_canonical_install_path(self) -> None:
        self.assertEqual(
            launch_app.quarantine_command_target(None), launch_app.CANONICAL_INSTALL_BUNDLE
        )

    def test_non_translocated_bundle_targets_its_own_path(self) -> None:
        bundle = Path("/Applications/Open-Anti-Browser.app")
        self.assertEqual(launch_app.quarantine_command_target(bundle), str(bundle))


class BuildQuarantineFailureMessageTests(unittest.TestCase):
    """D-12a: 兜底提示是预期主路径的措辞，且命令与前端常量逐字一致。"""

    def test_translocated_scenario_matches_frontend_constant(self) -> None:
        message = launch_app.build_quarantine_failure_message(None)
        js_source = GATEKEEPER_NOTICE_JS.read_text(encoding="utf-8")
        match = re.search(
            r"GATEKEEPER_XATTR_COMMAND\s*=\s*'([^']+)'", js_source
        )
        self.assertIsNotNone(match, "未能在 macosGatekeeperNotice.js 中找到 GATEKEEPER_XATTR_COMMAND")
        expected_command = match.group(1)
        self.assertIn(expected_command, message)
        self.assertEqual(
            expected_command,
            "xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app",
        )

    def test_message_contains_no_dangerous_command_fragments(self) -> None:
        message = launch_app.build_quarantine_failure_message(None)
        for forbidden in ("sudo", "spctl", "--master-disable", "~/Downloads"):
            self.assertNotIn(forbidden, message)

    def test_non_translocated_bundle_message_points_to_its_own_path(self) -> None:
        bundle = Path("/Applications/Open-Anti-Browser.app")
        message = launch_app.build_quarantine_failure_message(bundle)
        self.assertIn(f"xattr -dr com.apple.quarantine {bundle}", message)


class MaybeStripQuarantineTests(unittest.TestCase):
    """D-12: 三重前置守卫，非 darwin/非冻结态/推导不出 bundle 根时零调用 subprocess.run。"""

    @patch("launch_app.subprocess.run")
    def test_non_darwin_returns_none_without_touching_subprocess(self, mock_run: MagicMock) -> None:
        with patch.object(sys, "platform", "win32"):
            result = launch_app.maybe_strip_quarantine()
        self.assertIsNone(result)
        mock_run.assert_not_called()

    @patch("launch_app.subprocess.run")
    def test_non_frozen_darwin_returns_none_without_touching_subprocess(
        self, mock_run: MagicMock
    ) -> None:
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", False, create=True
        ):
            result = launch_app.maybe_strip_quarantine()
        self.assertIsNone(result)
        mock_run.assert_not_called()

    @patch("launch_app.subprocess.run")
    @patch("launch_app.resolve_app_bundle_root", return_value=None)
    def test_unresolvable_bundle_returns_none_without_touching_subprocess(
        self, mock_resolve: MagicMock, mock_run: MagicMock
    ) -> None:
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ):
            result = launch_app.maybe_strip_quarantine()
        self.assertIsNone(result)
        mock_run.assert_not_called()

    @patch("launch_app.subprocess.run")
    @patch(
        "launch_app.resolve_app_bundle_root",
        return_value=Path("/Applications/Open-Anti-Browser.app"),
    )
    def test_successful_strip_returns_none(
        self, mock_resolve: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ):
            result = launch_app.maybe_strip_quarantine()
        self.assertIsNone(result)

    @patch("launch_app.subprocess.run")
    @patch(
        "launch_app.resolve_app_bundle_root",
        return_value=Path("/Applications/Open-Anti-Browser.app"),
    )
    def test_failed_strip_returns_failure_message(
        self, mock_resolve: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="Operation not permitted")
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ):
            result = launch_app.maybe_strip_quarantine()
        self.assertIsNotNone(result)
        self.assertIn("xattr -dr com.apple.quarantine", result)


if __name__ == "__main__":
    unittest.main()
