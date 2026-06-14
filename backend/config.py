from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "Open-Anti-Browser"
PORTABLE_MARKER = "portable.mode"


def _is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def _resource_root() -> Path:
    if _is_packaged():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return PROJECT_ROOT


def _writable_root() -> Path:
    if _is_packaged():
        executable_dir = Path(sys.executable).resolve().parent
        if os.environ.get("OPEN_ANTI_BROWSER_PORTABLE") == "1":
            return executable_dir
        if (executable_dir / PORTABLE_MARKER).exists():
            return executable_dir
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    return PROJECT_ROOT


RESOURCE_ROOT = _resource_root()
APP_ROOT = _writable_root()
DATA_DIR = APP_ROOT / "data"
DOWNLOADS_DIR = APP_ROOT / "downloads"
EXTENSIONS_DIR = APP_ROOT / "extensions"
FRONTEND_DIST_DIR = RESOURCE_ROOT / "frontend" / "dist"
ASSETS_DIR = RESOURCE_ROOT / "assets"
ENGINES_DIR = RESOURCE_ROOT / "engines"
BIND_HOST_MARKER = "bind-host.txt"


def _exe_dir() -> Path:
    if _is_packaged():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def _resolve_bind_host() -> str:
    """本地服务监听地址。优先环境变量，其次安装目录的 bind-host.txt（安装时写入），默认仅本机。"""
    override = os.environ.get("OPEN_ANTI_BROWSER_HOST")
    if override and override.strip():
        return override.strip()
    try:
        marker = _exe_dir() / BIND_HOST_MARKER
        if marker.exists():
            value = marker.read_text(encoding="utf-8").strip()
            if value:
                return value
    except OSError:
        pass
    return "127.0.0.1"


BIND_HOST = _resolve_bind_host()


def _current_username() -> str:
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME") or os.environ.get("USER") or "user"


USERNAME = _current_username()
SYSTEM_CHROME_EXECUTABLE = Path(
    fr"C:\Users\{USERNAME}\AppData\Local\Chromium\Application\chrome.exe"
)
SYSTEM_FIREFOX_EXECUTABLE = Path(r"C:\Program Files\Mozilla Firefox\firefox.exe")
DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"
DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox.exe"
DEFAULT_USER_DATA_ROOT = APP_ROOT / "browser-data"
DEFAULT_FIREFOX_WEBRTC_BLOCK_EXTENSION = (
    ASSETS_DIR / "firefox-extensions" / "jid1-5Fs7iTLscUaZBgwr@jetpack.xpi"
)

CHROME_INSTALLER_URL = (
    "https://github.com/adryfish/fingerprint-chromium/releases/download/"
    "144.0.7559.132/ungoogled-chromium_144.0.7559.132-1.1_installer_x64.exe"
)
FIREFOX_INSTALLER_URL = (
    "https://github.com/LoseNine/ruyipage/releases/download/151-ruyi/"
    "firefox-151.0a1.en-US.win64.installer.exe"
)

ENGINE_METADATA = {
    "chrome": {
        "name": "Fingerprint Chromium 144",
        "default_executable": str(DEFAULT_CHROME_EXECUTABLE),
        "system_executable": str(SYSTEM_CHROME_EXECUTABLE),
        "installer_url": CHROME_INSTALLER_URL,
        "download_name": "fingerprint-chromium-144-installer.exe",
        "engine_dir": "chrome",
        "bundle_dir": str(ENGINES_DIR / "chrome"),
    },
    "firefox": {
        "name": "Firefox Fingerprint Browser 151",
        "default_executable": str(DEFAULT_FIREFOX_EXECUTABLE),
        "system_executable": str(SYSTEM_FIREFOX_EXECUTABLE),
        "installer_url": FIREFOX_INSTALLER_URL,
        "download_name": "firefox-fingerprint-151-installer.exe",
        "engine_dir": "firefox",
        "bundle_dir": str(ENGINES_DIR / "firefox"),
    },
}


def bundled_engine_executable(engine: str) -> Path:
    meta = ENGINE_METADATA[str(engine)]
    return Path(meta["default_executable"])
