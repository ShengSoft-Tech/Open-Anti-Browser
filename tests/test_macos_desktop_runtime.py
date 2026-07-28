import ast
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import launch_app


REPO_ROOT = Path(__file__).resolve().parent.parent
GATEKEEPER_NOTICE_JS = REPO_ROOT / "frontend" / "src" / "lib" / "macosGatekeeperNotice.js"
LAUNCH_APP_SOURCE = REPO_ROOT / "launch_app.py"


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


class QApplicationEventFilterGuardTests(unittest.TestCase):
    """回归防护：05-06 真机 checkpoint 发现 05-02 引入的 `qt_app.installEventFilter(...)`
    会 100% 复现地在 ~2s 内 SIGSEGV（EXC_BAD_ACCESS，栈顶 PySide::typeName）——装在
    QApplication/QCoreApplication 实例上的 event filter 会收到线程内*每个* QObject
    的事件，逼迫 PySide 为每个事件目标构造 Python wrapper；QtQuick 在
    -[NSWindow makeKeyAndOrderFront:] 触发的 focus 分发路径上会把事件送到 PySide
    包不安全的 QObject，读到空的 vtable/d_ptr 槽位后崩溃。修复是重载
    QApplication.event()（只接收送给应用对象自身的事件）。这里用 AST 静态扫描把
    这个反模式钉死，防止它以任何形式（哪怕换了变量名/换了 filter 类名）静默回归。
    """

    def _parse_launch_app(self) -> ast.Module:
        source = LAUNCH_APP_SOURCE.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(LAUNCH_APP_SOURCE))

    def test_no_install_event_filter_call_anywhere_in_launch_app(self) -> None:
        tree = self._parse_launch_app()
        offending_lines = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "installEventFilter"
        ]
        self.assertEqual(
            offending_lines,
            [],
            "launch_app.py 不得再调用 installEventFilter（行号: "
            f"{offending_lines}）—— 该反模式在 macOS 上会导致 SIGSEGV，详见 05-06 "
            "真机 checkpoint 崩溃报告；修复方式是重载 QApplication.event()，而不是"
            "在 QApplication/QCoreApplication 实例上装 app-wide event filter。",
        )

    def test_desktop_application_subclass_overrides_event_not_install_filter(self) -> None:
        tree = self._parse_launch_app()
        app_classes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(base, ast.Name) and base.id == "QApplication"
                for base in node.bases
            )
        ]
        self.assertTrue(
            app_classes,
            "未找到继承 QApplication 的子类 —— Cmd+Q 拦截应通过重载 event() 实现"
            "（而不是 installEventFilter）",
        )
        method_names = {
            item.name
            for cls in app_classes
            for item in cls.body
            if isinstance(item, ast.FunctionDef)
        }
        self.assertIn(
            "event",
            method_names,
            "继承 QApplication 的子类必须重载 event() 来处理 QEvent.Type.Quit（D-07 的"
            "触发源，逻辑仍全部委托给模块级 handle_macos_quit_request）",
        )


if __name__ == "__main__":
    unittest.main()
