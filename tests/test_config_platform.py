import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import config


class ConfigPlatformTests(unittest.TestCase):
    """XPLAT-03: config.py 路径解析必须按平台条件化，Windows 分支逐字不变（零回归）。"""

    def tearDown(self) -> None:
        # 无论用例是否用了 mock，末尾都强制回到真实平台重新求值一次，避免污染其他测试文件。
        importlib.reload(config)

    # ------------------------------------------------------------------
    # macOS 冻结态
    # ------------------------------------------------------------------

    def test_macos_frozen_app_root_is_application_support(self) -> None:
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ):
            importlib.reload(config)
            expected = Path.home() / "Library" / "Application Support" / "Open-Anti-Browser"
            self.assertEqual(config.APP_ROOT, expected)

    def test_macos_frozen_portable_env_var_is_ignored(self) -> None:
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ), patch.dict(os.environ, {"OPEN_ANTI_BROWSER_PORTABLE": "1"}):
            importlib.reload(config)
            expected = Path.home() / "Library" / "Application Support" / "Open-Anti-Browser"
            self.assertEqual(config.APP_ROOT, expected)

    def test_macos_default_chrome_executable_points_into_app_bundle(self) -> None:
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ):
            importlib.reload(config)
            expected = (
                config.ENGINES_DIR
                / "chrome"
                / "Chromium.app"
                / "Contents"
                / "MacOS"
                / "Chromium"
            )
            self.assertEqual(config.DEFAULT_CHROME_EXECUTABLE, expected)
            self.assertTrue(
                str(config.DEFAULT_CHROME_EXECUTABLE).endswith(
                    os.path.join("Chromium.app", "Contents", "MacOS", "Chromium")
                )
            )

    def test_macos_engine_metadata_contains_chrome_and_firefox(self) -> None:
        with patch.object(sys, "platform", "darwin"), patch.object(
            sys, "frozen", True, create=True
        ):
            importlib.reload(config)
            self.assertIn("chrome", config.ENGINE_METADATA)
            self.assertIn("firefox", config.ENGINE_METADATA)
            required_fields = {
                "name",
                "default_executable",
                "system_executable",
                "installer_url",
                "download_name",
                "engine_dir",
                "bundle_dir",
            }
            for engine_key in ("chrome", "firefox"):
                meta = config.ENGINE_METADATA[engine_key]
                self.assertTrue(required_fields.issubset(meta.keys()))

    def test_macos_darwin_branch_does_not_use_sys_executable(self) -> None:
        # Pitfall 4: SYSTEM/DEFAULT 引擎路径的 darwin 分支绝不能出现基于 sys.executable 的路径推导。
        source = Path(config.__file__).read_text(encoding="utf-8")
        block_start = source.index("USERNAME = _current_username()")
        block_end = source.index("DEFAULT_USER_DATA_ROOT = APP_ROOT")
        window = source[block_start:block_end]
        self.assertNotIn("sys.executable", window)

    def test_macos_arm64_kernel_url(self) -> None:
        # 常量是平台无关静态字符串，无需 patch sys.platform。
        url = config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64
        self.assertTrue(url.startswith(config._CHROME_KERNEL_BASE))
        self.assertIn("-1.3", url)
        self.assertIn("_macos_arm64", url)
        self.assertTrue(url.endswith(".zip"))
        self.assertEqual(
            url,
            f"{config._CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip",
        )

    def test_macos_x64_kernel_url(self) -> None:
        # 常量是平台无关静态字符串，无需 patch sys.platform。
        url = config.CHROME_ENGINE_ZIP_URL_MACOS_X64
        self.assertTrue(url.startswith(config._CHROME_KERNEL_BASE))
        self.assertIn("-1.3", url)
        self.assertIn("_macos_x64", url)
        self.assertTrue(url.endswith(".zip"))
        self.assertEqual(
            url,
            f"{config._CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip",
        )

    # ------------------------------------------------------------------
    # 开发态（非冻结）
    # ------------------------------------------------------------------

    def test_dev_mode_writable_root_is_project_root_on_both_platforms(self) -> None:
        for platform_value in ("darwin", "win32"):
            with self.subTest(platform=platform_value):
                with patch.object(sys, "platform", platform_value), patch.object(
                    sys, "frozen", False, create=True
                ):
                    importlib.reload(config)
                    self.assertEqual(config.APP_ROOT, config.PROJECT_ROOT)

    # ------------------------------------------------------------------
    # Windows 分支零回归
    # ------------------------------------------------------------------

    def test_windows_frozen_writable_root_uses_local_appdata(self) -> None:
        with patch.object(sys, "platform", "win32"), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(
            sys, "executable", r"C:\Program Files\Open-Anti-Browser\Open-Anti-Browser.exe"
        ), patch.dict(
            os.environ, {"LOCALAPPDATA": r"C:\Users\tester\AppData\Local"}, clear=False
        ):
            os.environ.pop("OPEN_ANTI_BROWSER_PORTABLE", None)
            importlib.reload(config)
            expected = Path(r"C:\Users\tester\AppData\Local") / "Open-Anti-Browser"
            self.assertEqual(config.APP_ROOT, expected)

    def test_windows_system_and_default_executable_values_unchanged(self) -> None:
        with patch.object(sys, "platform", "win32"):
            importlib.reload(config)
            self.assertEqual(
                config.SYSTEM_CHROME_EXECUTABLE,
                Path(
                    fr"C:\Users\{config.USERNAME}\AppData\Local\Chromium\Application\chrome.exe"
                ),
            )
            self.assertEqual(
                config.SYSTEM_FIREFOX_EXECUTABLE,
                Path(r"C:\Program Files\Mozilla Firefox\firefox.exe"),
            )
            self.assertEqual(
                config.DEFAULT_CHROME_EXECUTABLE,
                config.ENGINES_DIR / "chrome" / "chrome.exe",
            )
            self.assertEqual(
                config.DEFAULT_FIREFOX_EXECUTABLE,
                config.ENGINES_DIR / "firefox" / "firefox.exe",
            )


if __name__ == "__main__":
    unittest.main()
