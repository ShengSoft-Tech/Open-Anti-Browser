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


class MacCloseToTrayTests(unittest.TestCase):
    """macOS 上点关闭按钮不得挂在后台：菜单栏图标易被忽略，且窗口 hide() 后 Dock
    图标点击无法唤回，用户会被困住。macOS 关闭直接走与 Cmd+Q 相同的退出路径；
    Windows/Linux 的最小化到托盘行为不变。"""

    def test_should_close_to_tray_false_on_darwin(self) -> None:
        with patch.object(sys, "platform", "darwin"):
            self.assertFalse(launch_app.should_close_to_tray())

    def test_should_close_to_tray_true_on_win32(self) -> None:
        with patch.object(sys, "platform", "win32"):
            self.assertTrue(launch_app.should_close_to_tray())

    def test_should_close_to_tray_true_on_linux(self) -> None:
        with patch.object(sys, "platform", "linux"):
            self.assertTrue(launch_app.should_close_to_tray())

    def test_close_event_tray_branch_is_gated_on_should_close_to_tray(self) -> None:
        """结构断言：closeEvent 的托盘分支必须同时受 should_close_to_tray() 约束。
        直接跑 closeEvent 需要真实 QApplication，非 GUI 环境下不可行，因此在 AST 上
        断言这个 gate 没有被后续改动摘掉（沿用本文件既有的源码级断言先例）。"""
        source = Path(launch_app.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        close_events = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "closeEvent"
        ]
        self.assertEqual(len(close_events), 1, "预期 launch_app.py 内只有一个 closeEvent 定义")
        guard = close_events[0].body[0]
        self.assertIsInstance(guard, ast.If, "closeEvent 的第一条语句应为托盘分支的 if")
        called = {
            n.func.id
            for n in ast.walk(guard.test)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        self.assertIn(
            "should_close_to_tray",
            called,
            "closeEvent 的托盘分支必须调用 should_close_to_tray() —— 否则 macOS 上点 X "
            "会重新挂在后台且无法从 Dock 唤回",
        )


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
            'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"',
        )

    def test_message_contains_no_dangerous_command_fragments(self) -> None:
        message = launch_app.build_quarantine_failure_message(None)
        for forbidden in ("sudo", "spctl", "--master-disable", "~/Downloads"):
            self.assertNotIn(forbidden, message)

    def test_non_translocated_bundle_message_points_to_its_own_path(self) -> None:
        bundle = Path("/Applications/Open-Anti-Browser.app")
        message = launch_app.build_quarantine_failure_message(bundle)
        self.assertIn(f'xattr -dr com.apple.quarantine "{bundle}"', message)


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


class MacQuitEventLoopConvergenceTests(unittest.TestCase):
    """05-06 真机 checkpoint 二次发现：`event()` 把 `handle_macos_quit_request(...)`
    的返回值当 `if ...: return True` 的早退门禁，导致 `super().event(e)` 永远跑不到
    ——而 `QCoreApplication::event()` 对 `QEvent.Type.Quit` 的默认处理（同步调用
    `quit()`）正是真正让事件循环退出的那一步。跳过它之后：Cmd+Q 按下 → 我们的
    `event()` 吞掉 Quit → `force_exit()` → `closeEvent` 做完真正的 `shutdown()` →
    用 `QTimer.singleShot(0, quit)` 异步再调一次 `quit()`；但这次调用不在「正在
    处理的这个 Quit 事件」的同步调用栈内，在 macOS 上会让 Cocoa 的终止协议重新
    起播、再 post 一个新的 `QEvent.Quit`——又被我们的 `event()` 吞掉，无限循环，
    进程停在约 60% CPU 不退出（`sample` 实测 100% 采样落在 `sendPostedEvents`）。

    这里用 AST 静态扫描钉死两点，防止它以任何形式静默回归：
    (1) `DesktopApplication.event()` 必须无条件把事件转交给 `super().event(e)`，
        不能用 `if ...: return True` 的模式把它短路掉；
    (2) `DesktopMainWindow.force_exit()` 必须以 `_closing` 幂等短路开头，防止
        Quit 事件重入时对正在关闭的窗口重新 `showNormal()`。
    """

    def _parse_launch_app(self) -> ast.Module:
        source = LAUNCH_APP_SOURCE.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(LAUNCH_APP_SOURCE))

    def _find_method(self, tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef | None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        return item
        return None

    def test_event_always_forwards_to_super_event_unconditionally(self) -> None:
        tree = self._parse_launch_app()
        event_method = self._find_method(tree, "DesktopApplication", "event")
        self.assertIsNotNone(event_method, "未找到 DesktopApplication.event()")

        # 全函数（含任意嵌套的 if/for/... 语句块）范围内的 return 必须恰好一条。
        # 注意：不能只数 event_method.body 的顶层语句——旧版缺陷的 `if ...: return
        # True` 分支和收尾的 `return super().event(e)` 在顶层各自只贡献一个节点
        # （`If` 和 `Return`），顶层计数会误判为「只有 1 条 return」而放过缺陷；
        # 必须用 ast.walk 递归进 If 的分支体，才能数到旧版真正的 2 条 return。
        all_returns = [n for n in ast.walk(event_method) if isinstance(n, ast.Return)]
        self.assertEqual(
            len(all_returns),
            1,
            "event() 全函数范围内必须恰好一条 return 语句——不得再用 `if ...: return "
            "True` 的早退模式短路 super().event(e)（那正是 05-06 二次发现的无限"
            "循环成因：QCoreApplication::event() 对 QEvent.Quit 的默认处理被跳过，"
            "quit() 从未在正确的调用栈内同步执行，事件循环永远不退出）",
        )
        (only_return,) = all_returns
        call = only_return.value
        self.assertIsInstance(call, ast.Call, "event() 的唯一 return 必须是一次方法调用")
        assert isinstance(call, ast.Call)
        self.assertIsInstance(call.func, ast.Attribute)
        assert isinstance(call.func, ast.Attribute)
        self.assertEqual(
            call.func.attr,
            "event",
            "event() 必须以 `return super().event(e)` 收尾，把事件交给 Qt 默认处理"
            "（QCoreApplication::event() 对 QEvent.Quit 的默认处理才是真正让事件"
            "循环退出的那一步）",
        )
        self.assertIsInstance(call.func.value, ast.Call)
        assert isinstance(call.func.value, ast.Call)
        self.assertIsInstance(call.func.value.func, ast.Name)
        assert isinstance(call.func.value.func, ast.Name)
        self.assertEqual(
            call.func.value.func.id,
            "super",
            "event() 必须通过 super() 转发，不得绕过基类默认 Quit 处理",
        )

        # handle_macos_quit_request(...) 的返回值不得被用来 gate 一个 if（即不能
        # 出现在任何 ast.If 的 test 表达式里）——那正是旧版 `return True` 早退模式。
        for node in ast.walk(event_method):
            if isinstance(node, ast.If):
                for call_node in ast.walk(node.test):
                    if (
                        isinstance(call_node, ast.Call)
                        and isinstance(call_node.func, ast.Name)
                        and call_node.func.id == "handle_macos_quit_request"
                    ):
                        self.fail(
                            "handle_macos_quit_request(...) 的返回值不得被用作 if "
                            "条件去门禁一个 return——这正是旧版 `return True` 早退"
                            "模式，会让 super().event(e) 永远跑不到，导致 Cmd+Q 无限循环"
                        )

    def test_force_exit_guards_reentrancy_with_closing_flag(self) -> None:
        tree = self._parse_launch_app()
        force_exit_method = self._find_method(tree, "DesktopMainWindow", "force_exit")
        self.assertIsNotNone(force_exit_method, "未找到 DesktopMainWindow.force_exit()")
        assert force_exit_method is not None

        first_stmt = force_exit_method.body[0]
        self.assertIsInstance(
            first_stmt,
            ast.If,
            "force_exit() 第一条语句必须是 `if self._closing: return` 幂等短路——"
            "否则 macOS 上 Quit 事件重入时会对正在关闭的窗口重新 showNormal()",
        )
        assert isinstance(first_stmt, ast.If)
        test_expr = first_stmt.test
        self.assertIsInstance(test_expr, ast.Attribute)
        assert isinstance(test_expr, ast.Attribute)
        self.assertEqual(test_expr.attr, "_closing")
        self.assertTrue(
            any(isinstance(s, ast.Return) for s in first_stmt.body),
            "`if self._closing:` 分支必须 return，短路掉后续的 showNormal()/close()",
        )


if __name__ == "__main__":
    unittest.main()
