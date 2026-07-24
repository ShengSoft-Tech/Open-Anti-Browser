import importlib
import sys
import unittest
from unittest.mock import patch

from backend.services import window_manager


class WindowManagerPosixTests(unittest.TestCase):
    """在非 Windows 平台上，四个窗口排列函数必须抛出统一的 RuntimeError。"""

    def setUp(self) -> None:
        patcher = patch.object(sys, "platform", "darwin")
        patcher.start()
        self.addCleanup(patcher.stop)
        importlib.reload(window_manager)
        self.addCleanup(lambda: importlib.reload(window_manager))

    def test_list_monitors_raises_on_non_windows(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            window_manager.list_monitors()
        self.assertEqual(str(ctx.exception), "窗口排列仅在 Windows 上可用")

    def test_show_windows_raises_on_non_windows(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            window_manager.show_windows(lambda _pid: None, ["p1"])
        self.assertEqual(str(ctx.exception), "窗口排列仅在 Windows 上可用")

    def test_set_uniform_size_raises_on_non_windows(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            window_manager.set_uniform_size(lambda _pid: None, ["p1"])
        self.assertEqual(str(ctx.exception), "窗口排列仅在 Windows 上可用")

    def test_arrange_windows_raises_on_non_windows(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            window_manager.arrange_windows(lambda _pid: None, ["p1"])
        self.assertEqual(str(ctx.exception), "窗口排列仅在 Windows 上可用")

    def test_stub_function_names_match_windows_signatures(self) -> None:
        # browser_manager.py 具名导入这四个符号，缺一即 ImportError。
        from backend.services.window_manager import (
            arrange_windows,
            list_monitors,
            set_uniform_size,
            show_windows,
        )

        self.assertTrue(callable(list_monitors))
        self.assertTrue(callable(show_windows))
        self.assertTrue(callable(set_uniform_size))
        self.assertTrue(callable(arrange_windows))


class WindowManagerConcurrencyTests(unittest.TestCase):
    """XPLAT-02 concurrency edge: 桩函数无共享可变状态，并发调用相互独立。"""

    def setUp(self) -> None:
        patcher = patch.object(sys, "platform", "darwin")
        patcher.start()
        self.addCleanup(patcher.stop)
        importlib.reload(window_manager)
        self.addCleanup(lambda: importlib.reload(window_manager))

    def test_concurrent_calls_each_raise_independently(self) -> None:
        import threading

        errors: list[BaseException | None] = [None] * 8

        def worker(index: int) -> None:
            try:
                window_manager.list_monitors()
            except RuntimeError as exc:
                errors[index] = exc
            except BaseException as exc:  # pragma: no cover - defensive
                errors[index] = exc

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        for error in errors:
            self.assertIsInstance(error, RuntimeError)
            self.assertEqual(str(error), "窗口排列仅在 Windows 上可用")


@unittest.skipUnless(sys.platform == "win32", "仅在 Windows 上验证 win32 分支未被桩替换")
class WindowManagerWindowsBranchTests(unittest.TestCase):
    def test_win32_branch_functions_are_real_implementations(self) -> None:
        importlib.reload(window_manager)
        monitors = window_manager.list_monitors()
        self.assertIsInstance(monitors, list)


if __name__ == "__main__":
    unittest.main()
