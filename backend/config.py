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
        if sys.platform == "win32":
            executable_dir = Path(sys.executable).resolve().parent
            if os.environ.get("OPEN_ANTI_BROWSER_PORTABLE") == "1":
                return executable_dir
            if (executable_dir / PORTABLE_MARKER).exists():
                return executable_dir
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / APP_NAME
            return Path.home() / "AppData" / "Local" / APP_NAME
        if sys.platform == "darwin":
            # macOS：忽略 portable 标记与环境变量（D-07），固定写用户级 Application Support，
            # 不使用任何基于 sys.executable 的路径推导（Pitfall 4：.app bundle 内部结构不适用）。
            return Path.home() / "Library" / "Application Support" / APP_NAME
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
if sys.platform == "darwin":
    # 系统级已安装浏览器检测路径（辅助能力，非 XPLAT-03 验收锁定值）。
    # 具体位置属 Claude's Discretion，Phase 2/3 结合内核打包形态校准。
    SYSTEM_CHROME_EXECUTABLE = Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
    SYSTEM_FIREFOX_EXECUTABLE = Path("/Applications/Firefox.app/Contents/MacOS/firefox")  # macOS 无 firefox 内核（D-08），字段保留但不启用
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox"  # 路径存在但文件不存在，天然不可用（D-08）
else:
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

# Chrome kernel engine assets. Single source of truth for BOTH the runtime installer
# download AND the CI engine-bundle fetch — .github/workflows/build-release.yml reads
# CHROME_ENGINE_ZIP_URL from here instead of hardcoding a kernel URL. The -1.4 revision
# adds the pixelscan patch (on top of -1.2's patch 020 speech-synthesis fix); assets
# live on the kernel-149.0.7827.114 release.
_CHROME_KERNEL_BASE = (
    "https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/download/"
    "kernel-149.0.7827.114"
)
CHROME_INSTALLER_URL = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.4_installer_x64.exe"
)
CHROME_ENGINE_ZIP_URL = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.4_windows_x64.zip"
)
# macOS 内核资产（arm64/x64 分开出包，不做 universal binary）。-1.3 revision 标识
# 021 基线（macOS 首次构建），与 Windows 现有 -1.2 区分，同样复用 _CHROME_KERNEL_BASE。
CHROME_ENGINE_ZIP_URL_MACOS_ARM64 = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip"
)
CHROME_ENGINE_ZIP_URL_MACOS_X64 = (
    f"{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip"
)
FIREFOX_INSTALLER_URL = (
    "https://github.com/LoseNine/ruyipage/releases/download/151-ruyi/"
    "firefox-151.0a1.en-US.win64.installer.exe"
)

ENGINE_METADATA = {
    "chrome": {
        "name": "Fingerprint Chromium 149",
        "default_executable": str(DEFAULT_CHROME_EXECUTABLE),
        "system_executable": str(SYSTEM_CHROME_EXECUTABLE),
        "installer_url": CHROME_INSTALLER_URL,
        "download_name": "fingerprint-chromium-149-1.4-installer.exe",
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
