import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.models import AppSettings, BrowserProfile, EngineSettings
from backend.services.chrome import launch_chrome_profile
from backend.services.firefox import launch_firefox_profile


def _settings(temp_dir: Path) -> AppSettings:
    return AppSettings(
        user_data_root=str(temp_dir / "browser-data"),
        chrome=EngineSettings(executable_path="", installer_url="", download_path=""),
        firefox=EngineSettings(executable_path="", installer_url="", download_path=""),
    )


class LaunchGeoFallbackTests(unittest.TestCase):
    def test_chrome_launch_continues_when_ip_resolution_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            chrome_exe = temp_dir / "chrome.exe"
            chrome_exe.write_bytes(b"")
            process = Mock(pid=1234)
            profile = BrowserProfile(engine="chrome")

            with (
                patch("backend.services.chrome.bundled_engine_executable", return_value=chrome_exe),
                patch("backend.services.chrome.resolve_geo_profile", side_effect=RuntimeError("geo failed")),
                patch("backend.services.chrome.find_free_port", return_value=9222),
                patch("backend.services.chrome.subprocess.Popen", return_value=process),
            ):
                result = launch_chrome_profile(profile, _settings(temp_dir), temp_dir / "profile")

            self.assertEqual(result["process"], process)
            self.assertEqual(result["geo_profile"]["source"], "fallback")
            self.assertIn("geo failed", result["geo_profile"]["resolve_error"])

    def test_chrome_launch_strips_quarantine_on_darwin(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            chrome_exe = temp_dir / "chrome.exe"
            chrome_exe.write_bytes(b"")
            process = Mock(pid=1234)
            profile = BrowserProfile(engine="chrome")

            with (
                patch("backend.services.chrome.bundled_engine_executable", return_value=chrome_exe),
                patch("backend.services.chrome.resolve_geo_profile", side_effect=RuntimeError("geo failed")),
                patch("backend.services.chrome.find_free_port", return_value=9222),
                patch("backend.services.chrome.subprocess.Popen", return_value=process),
                patch("backend.services.chrome.subprocess.run") as mock_run,
                patch("backend.services.chrome.sys.platform", "darwin"),
            ):
                result = launch_chrome_profile(profile, _settings(temp_dir), temp_dir / "profile")

            self.assertEqual(result["process"], process)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            self.assertEqual(
                call_args.args[0],
                ["xattr", "-dr", "com.apple.quarantine", str(chrome_exe)],
            )

    def test_chrome_launch_skips_quarantine_strip_on_non_darwin(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            chrome_exe = temp_dir / "chrome.exe"
            chrome_exe.write_bytes(b"")
            process = Mock(pid=1234)
            profile = BrowserProfile(engine="chrome")

            with (
                patch("backend.services.chrome.bundled_engine_executable", return_value=chrome_exe),
                patch("backend.services.chrome.resolve_geo_profile", side_effect=RuntimeError("geo failed")),
                patch("backend.services.chrome.find_free_port", return_value=9222),
                patch("backend.services.chrome.subprocess.Popen", return_value=process),
                patch("backend.services.chrome.subprocess.run") as mock_run,
                patch("backend.services.chrome.sys.platform", "win32"),
            ):
                result = launch_chrome_profile(profile, _settings(temp_dir), temp_dir / "profile")

            self.assertEqual(result["process"], process)
            mock_run.assert_not_called()

    def test_chrome_launch_continues_when_quarantine_strip_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            chrome_exe = temp_dir / "chrome.exe"
            chrome_exe.write_bytes(b"")
            process = Mock(pid=1234)
            profile = BrowserProfile(engine="chrome")

            with (
                patch("backend.services.chrome.bundled_engine_executable", return_value=chrome_exe),
                patch("backend.services.chrome.resolve_geo_profile", side_effect=RuntimeError("geo failed")),
                patch("backend.services.chrome.find_free_port", return_value=9222),
                patch("backend.services.chrome.subprocess.Popen", return_value=process),
                patch("backend.services.chrome.subprocess.run", side_effect=OSError("xattr missing")),
                patch("backend.services.chrome.sys.platform", "darwin"),
            ):
                result = launch_chrome_profile(profile, _settings(temp_dir), temp_dir / "profile")

            self.assertEqual(result["process"], process)

    def test_firefox_launch_continues_when_ip_resolution_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            firefox_exe = temp_dir / "firefox.exe"
            firefox_exe.write_bytes(b"")
            process = Mock(pid=4321)
            profile = BrowserProfile(engine="firefox")

            with (
                patch("backend.services.firefox.bundled_engine_executable", return_value=firefox_exe),
                patch("backend.services.firefox.resolve_geo_profile", side_effect=RuntimeError("geo failed")),
                patch("backend.services.firefox.find_free_port", side_effect=[9333, 2829]),
                patch("backend.services.firefox.subprocess.Popen", return_value=process),
            ):
                result = launch_firefox_profile(profile, _settings(temp_dir), temp_dir / "profile")

            self.assertEqual(result["process"], process)
            self.assertEqual(result["geo_profile"]["source"], "fallback")
            self.assertIn("geo failed", result["geo_profile"]["resolve_error"])


if __name__ == "__main__":
    unittest.main()
