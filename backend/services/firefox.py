from __future__ import annotations

import ctypes
import json
import os
import random
import shutil
import subprocess
import tempfile
import time
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..models import AppSettings, BrowserProfile, ExtraFingerprintField
from ..config import DEFAULT_FIREFOX_WEBRTC_BLOCK_EXTENSION, bundled_engine_executable
from .network import (
    LocalHttpProxyBridge,
    build_firefox_no_proxy_list,
    fallback_geo_profile,
    find_free_port,
    kill_process_tree,
    proxy_to_profile_proxy,
    remove_directory,
    resolve_geo_profile,
)


DEFAULT_SCREEN_PROFILES = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1600, "height": 900},
    {"width": 1680, "height": 1050},
    {"width": 1920, "height": 1080},
    {"width": 1920, "height": 1200},
    {"width": 2160, "height": 1440},
    {"width": 2560, "height": 1440},
    {"width": 2560, "height": 1600},
]
DEFAULT_WEBGL_PROFILES = [
    {
        "vendor": "Mozilla",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5090 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0",
        "glsl_version": "WebGL GLSL ES 3.00",
        "unmasked_vendor": "Google Inc. (NVIDIA)",
        "unmasked_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5090 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "max_texture_size": 16384,
        "max_cube_map_texture_size": 16384,
        "max_texture_image_units": 32,
        "max_vertex_attribs": 16,
        "aliased_point_size_max": 1024,
        "max_viewport_dim": 32767,
    },
    {
        "vendor": "Mozilla",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0",
        "glsl_version": "WebGL GLSL ES 3.00",
        "unmasked_vendor": "Google Inc. (NVIDIA)",
        "unmasked_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "max_texture_size": 16384,
        "max_cube_map_texture_size": 16384,
        "max_texture_image_units": 32,
        "max_vertex_attribs": 16,
        "aliased_point_size_max": 1024,
        "max_viewport_dim": 32767,
    },
    {
        "vendor": "Mozilla",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5070 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0",
        "glsl_version": "WebGL GLSL ES 3.00",
        "unmasked_vendor": "Google Inc. (NVIDIA)",
        "unmasked_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5070 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "max_texture_size": 16384,
        "max_cube_map_texture_size": 16384,
        "max_texture_image_units": 32,
        "max_vertex_attribs": 16,
        "aliased_point_size_max": 1024,
        "max_viewport_dim": 32767,
    },
    {
        "vendor": "Mozilla",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0",
        "glsl_version": "WebGL GLSL ES 3.00",
        "unmasked_vendor": "Google Inc. (NVIDIA)",
        "unmasked_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "max_texture_size": 16384,
        "max_cube_map_texture_size": 16384,
        "max_texture_image_units": 32,
        "max_vertex_attribs": 16,
        "aliased_point_size_max": 1024,
        "max_viewport_dim": 32767,
    },
    {
        "vendor": "Mozilla",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0",
        "glsl_version": "WebGL GLSL ES 3.00",
        "unmasked_vendor": "Google Inc. (NVIDIA)",
        "unmasked_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "max_texture_size": 16384,
        "max_cube_map_texture_size": 16384,
        "max_texture_image_units": 32,
        "max_vertex_attribs": 16,
        "aliased_point_size_max": 1024,
        "max_viewport_dim": 32767,
    },
    {
        "vendor": "Mozilla",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "version": "WebGL 2.0",
        "glsl_version": "WebGL GLSL ES 3.00",
        "unmasked_vendor": "Google Inc. (NVIDIA)",
        "unmasked_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "max_texture_size": 16384,
        "max_cube_map_texture_size": 16384,
        "max_texture_image_units": 32,
        "max_vertex_attribs": 16,
        "aliased_point_size_max": 1024,
        "max_viewport_dim": 32767,
    },
]
DEFAULT_HARDWARE_CONCURRENCY = [8, 12, 16, 20, 24, 32]
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def firefox_supports_fpfile(executable_path: str | Path) -> bool:
    path = Path(executable_path)
    if not path.exists():
        return False
    profile_dir = Path(tempfile.mkdtemp(prefix="openanti-firefox-check-"))
    fingerprint_file = profile_dir / "fingerprint.txt"
    fingerprint_file.write_text(
        "webdriver:0\ntimezone:Asia/Shanghai\nlanguage:zh-CN,zh,en-US\n",
        encoding="utf-8",
        newline="\n",
    )
    remote_port = find_free_port()
    marionette_port = _find_distinct_free_port(remote_port)
    command = [
        str(path),
        f"--remote-debugging-port={remote_port}",
        "--no-remote",
        "--marionette",
        "--marionette-port",
        str(marionette_port),
        "--profile",
        str(profile_dir),
        "--width=1200",
        "--height=900",
        f"--fpfile={fingerprint_file}",
        "about:blank",
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            cwd=str(path.parent),
        )
        time.sleep(3)
        return process.poll() is None
    except Exception:
        return False
    finally:
        try:
            if "process" in locals():
                kill_process_tree(process.pid)
        except Exception:
            pass
        remove_directory(profile_dir)


def launch_firefox_profile(
    profile: BrowserProfile,
    app_settings: AppSettings,
    user_data_dir: Path,
) -> dict[str, Any]:
    executable_path = bundled_engine_executable("firefox")
    if not executable_path.exists():
        raise FileNotFoundError(f"Firefox 内核不存在：{executable_path}")
    proxy_config = proxy_to_profile_proxy(profile.proxy.model_dump(mode="json"))
    try:
        geo_profile = resolve_geo_profile(
            proxy_config,
            profile.firefox.fingerprint.auto_timezone,
            strict=False,
        )
    except Exception as exc:
        geo_profile = fallback_geo_profile(exc)
    proxy_bridge = None
    browser_proxy = proxy_config["server"] if proxy_config else None
    if proxy_config and proxy_config["username"] is not None:
        if proxy_config["scheme"] not in ("http", "https"):
            raise ValueError("Firefox 账号代理目前仅支持 http/https。")
        proxy_bridge = LocalHttpProxyBridge(proxy_config).start()
        browser_proxy = proxy_bridge.local_proxy

    user_data_dir.mkdir(parents=True, exist_ok=True)
    fingerprint_result = _prepare_fingerprint_file(profile, user_data_dir, geo_profile)
    fingerprint_file = fingerprint_result["path"]
    width, height = _resolve_window_size(
        profile.firefox.startup.window_size,
        fingerprint_result.get("screen_profile"),
    )
    installed_extensions = _prepare_firefox_extensions(profile, app_settings, user_data_dir)
    remote_debugging_port = find_free_port()
    marionette_port = _find_distinct_free_port(remote_debugging_port)
    _write_firefox_user_js(
        user_data_dir / "user.js",
        browser_proxy,
        width,
        height,
        bool(installed_extensions),
        no_proxy_list=build_firefox_no_proxy_list(profile.proxy_bypass_rules),
        marionette_port=marionette_port,
    )
    _write_firefox_pref_override(user_data_dir / "prefs.js", "marionette.port", marionette_port)

    launch_args: list[str] = [
        str(executable_path),
        f"--remote-debugging-port={remote_debugging_port}",
        "--no-remote",
        "--marionette",
        "--marionette-port",
        str(marionette_port),
        "--profile",
        str(user_data_dir),
        f"--width={width}",
        f"--height={height}",
        f"--fpfile={fingerprint_file}",
    ]

    for raw_arg in profile.firefox.launch_args:
        raw_arg = str(raw_arg or "").strip()
        if raw_arg:
            launch_args.append(raw_arg)

    startup_urls = [item.strip() for item in profile.firefox.startup.open_urls if str(item).strip()]
    if startup_urls:
        launch_args.extend(startup_urls)

    process = subprocess.Popen(
        launch_args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        cwd=str(executable_path.parent),
        env={**os.environ},
    )

    return {
        "process": process,
        "command": launch_args,
        "proxy_bridge": proxy_bridge,
        "proxy_bridge_url": proxy_bridge.local_proxy if proxy_bridge else None,
        "remote_debugging_port": remote_debugging_port,
        "marionette_port": marionette_port,
        "geo_profile": geo_profile,
        "fingerprint_file": str(fingerprint_file),
        "fingerprint_profile": fingerprint_result["items"],
        "installed_extensions": [str(item) for item in installed_extensions],
    }


def _prepare_fingerprint_file(
    profile: BrowserProfile,
    user_data_dir: Path,
    geo_profile: dict[str, Any],
) -> dict[str, Any]:
    fingerprint = profile.firefox.fingerprint
    screen_profile = _pick_screen_profile(fingerprint.screen.mode, fingerprint.screen.width, fingerprint.screen.height)
    webgl_profile = _pick_webgl_profile(fingerprint.webgl.mode, fingerprint.webgl.model_dump(mode="json"))
    hardware_concurrency = _pick_hardware_concurrency(
        fingerprint.hardware_concurrency_mode,
        fingerprint.hardware_concurrency,
    )
    webrtc_profile = _pick_webrtc_profile(
        fingerprint.webrtc.mode,
        fingerprint.webrtc.local_ip,
        fingerprint.webrtc.public_ip or geo_profile.get("ip"),
    )

    fp_items: dict[str, Any] = {
        "webdriver": 0,
        "timezone": geo_profile["timezone"] if fingerprint.auto_timezone else (fingerprint.timezone or geo_profile["timezone"]),
        "font_system": fingerprint.font_system or "windows",
        "canvas": random.randint(1, 999999),
        "language": _build_language_value(fingerprint.language or geo_profile["language"]),
    }

    if webrtc_profile.get("local_webrtc"):
        fp_items["local_webrtc"] = webrtc_profile["local_webrtc"]
    if webrtc_profile.get("public_webrtc"):
        fp_items["public_webrtc"] = webrtc_profile["public_webrtc"]
    if hardware_concurrency:
        fp_items["hardwareConcurrency"] = hardware_concurrency
    if screen_profile:
        fp_items["width"] = screen_profile["width"]
        fp_items["height"] = screen_profile["height"]
    if webgl_profile:
        for target_key, source_key in [
            ("webgl.vendor", "vendor"),
            ("webgl.renderer", "renderer"),
            ("webgl.version", "version"),
            ("webgl.glsl_version", "glsl_version"),
            ("webgl.unmasked_vendor", "unmasked_vendor"),
            ("webgl.unmasked_renderer", "unmasked_renderer"),
            ("webgl.max_texture_size", "max_texture_size"),
            ("webgl.max_cube_map_texture_size", "max_cube_map_texture_size"),
            ("webgl.max_texture_image_units", "max_texture_image_units"),
            ("webgl.max_vertex_attribs", "max_vertex_attribs"),
            ("webgl.aliased_point_size_max", "aliased_point_size_max"),
            ("webgl.max_viewport_dim", "max_viewport_dim"),
        ]:
            value = webgl_profile.get(source_key)
            if value not in (None, ""):
                fp_items[target_key] = value

    for extra_field in fingerprint.extra_fields:
        if isinstance(extra_field, ExtraFingerprintField):
            key = extra_field.key.strip()
            value = extra_field.value.strip()
        else:
            key = str(getattr(extra_field, "key", "") or "").strip()
            value = str(getattr(extra_field, "value", "") or "").strip()
        if key and value:
            fp_items[key] = value

    output_path = Path(profile.firefox.fingerprint_file_path or user_data_dir / "fingerprint.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_keys = [
        "webdriver",
        "local_webrtc",
        "public_webrtc",
        "timezone",
        "font_system",
        "hardwareConcurrency",
        "webgl.vendor",
        "webgl.renderer",
        "webgl.version",
        "webgl.glsl_version",
        "webgl.unmasked_vendor",
        "webgl.unmasked_renderer",
        "webgl.max_texture_size",
        "webgl.max_cube_map_texture_size",
        "webgl.max_texture_image_units",
        "webgl.max_vertex_attribs",
        "webgl.aliased_point_size_max",
        "webgl.max_viewport_dim",
        "width",
        "height",
        "canvas",
        "language",
    ]
    lines = []
    emitted = set()
    for key in ordered_keys:
        value = fp_items.get(key)
        if value in (None, ""):
            continue
        lines.append(f"{key}:{value}")
        emitted.add(key)
    for key, value in fp_items.items():
        if key in emitted or value in (None, ""):
            continue
        lines.append(f"{key}:{value}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {
        "path": output_path,
        "items": fp_items,
        "screen_profile": screen_profile,
        "webgl_profile": webgl_profile,
        "hardware_concurrency": hardware_concurrency,
        "webrtc_profile": webrtc_profile,
    }


def _write_firefox_user_js(
    path: Path,
    browser_proxy: str | None,
    width: int,
    height: int,
    has_extensions: bool = False,
    no_proxy_list: str = "",
    marionette_port: int | None = None,
) -> None:
    prefs = {
        "browser.shell.checkDefaultBrowser": False,
        "browser.aboutConfig.showWarning": False,
        "toolkit.telemetry.reportingpolicy.firstRun": False,
    }
    if browser_proxy:
        parsed = browser_proxy.replace("http://", "").replace("https://", "")
        host, port = parsed.split(":", 1)
        prefs["network.proxy.type"] = 1
        prefs["network.proxy.http"] = host
        prefs["network.proxy.http_port"] = int(port)
        prefs["network.proxy.ssl"] = host
        prefs["network.proxy.ssl_port"] = int(port)
        prefs["network.proxy.socks"] = host
        prefs["network.proxy.socks_port"] = int(port)
        prefs["network.proxy.socks_remote_dns"] = True
        if no_proxy_list:
            prefs["network.proxy.no_proxies_on"] = no_proxy_list
    else:
        prefs["network.proxy.type"] = 0

    prefs["privacy.window.maxInnerWidth"] = int(width)
    prefs["privacy.window.maxInnerHeight"] = int(height)
    if marionette_port:
        prefs["marionette.port"] = int(marionette_port)
    if has_extensions:
        prefs["extensions.autoDisableScopes"] = 0
        prefs["extensions.enabledScopes"] = 15
        prefs["extensions.startupScanScopes"] = 15
        prefs["extensions.installDistroAddons"] = False
        prefs["xpinstall.signatures.required"] = False

    lines = [f'user_pref("{key}", { _to_js_value(value) });' for key, value in prefs.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_firefox_pref_override(path: Path, key: str, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    replacement = f'user_pref("{key}", { _to_js_value(value) });'
    lines: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if f'user_pref("{key}"' in line:
                continue
            lines.append(line)
    lines.append(replacement)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prepare_firefox_extensions(profile: BrowserProfile, app_settings: AppSettings, user_data_dir: Path) -> list[Path]:
    extension_sources: list[Path] = []
    if profile.firefox.fingerprint.load_webrtc_block_extension and DEFAULT_FIREFOX_WEBRTC_BLOCK_EXTENSION.exists():
        extension_sources.append(DEFAULT_FIREFOX_WEBRTC_BLOCK_EXTENSION)

    disabled_ids = set(profile.firefox.disabled_global_extension_ids or [])
    for extension in app_settings.managed_extensions:
        if extension.engine != "firefox" or not extension.enabled or extension.id in disabled_ids:
            continue
        value = str(extension.stored_path or "").strip()
        if value:
            extension_sources.append(Path(value))

    for raw_path in profile.firefox.extension_paths:
        value = str(raw_path or "").strip()
        if value:
            extension_sources.append(Path(value))

    if not extension_sources:
        return []

    extensions_dir = user_data_dir / "extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    installed_paths: list[Path] = []
    copied_signatures: set[str] = set()
    for source in extension_sources:
        if not source.exists():
            raise FileNotFoundError(f"Firefox 扩展不存在：{source}")
        signature = str(source.resolve()).lower()
        if signature in copied_signatures:
            continue
        copied_signatures.add(signature)
        target_name = _firefox_extension_install_filename(source)
        target = extensions_dir / target_name
        shutil.copy2(source, target)
        installed_paths.append(target)
    return installed_paths


def _find_distinct_free_port(*used_ports: int | None) -> int:
    used = {int(port) for port in used_ports if port}
    for _ in range(20):
        port = find_free_port()
        if port not in used:
            return port
    raise RuntimeError("无法分配 Firefox 自动化端口")


def _firefox_extension_install_filename(source: Path) -> str:
    addon_id = _read_firefox_extension_addon_id(source)
    safe_name = _safe_firefox_extension_id_filename(addon_id)
    if safe_name:
        return safe_name
    return source.name if source.suffix.lower() == ".xpi" else f"{source.name}.xpi"


def _read_firefox_extension_addon_id(source: Path) -> str:
    manifest = _read_firefox_extension_manifest(source)
    if not manifest:
        return ""
    gecko = manifest.get("browser_specific_settings", {}).get("gecko", {})
    addon_id = gecko.get("id")
    if not addon_id:
        gecko = manifest.get("applications", {}).get("gecko", {})
        addon_id = gecko.get("id")
    return str(addon_id or "").strip()


def _read_firefox_extension_manifest(source: Path) -> dict[str, Any]:
    try:
        if source.is_file() and (source.suffix.lower() in {".xpi", ".zip"} or zipfile.is_zipfile(source)):
            with zipfile.ZipFile(source) as zip_file:
                with zip_file.open("manifest.json") as manifest_file:
                    raw = manifest_file.read().decode("utf-8")
            manifest = json.loads(raw)
            return manifest if isinstance(manifest, dict) else {}
        if source.is_dir():
            manifest_path = source / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                return manifest if isinstance(manifest, dict) else {}
    except Exception:
        return {}
    return {}


def _safe_firefox_extension_id_filename(addon_id: str) -> str:
    value = str(addon_id or "").strip()
    if not value:
        return ""
    if any(char in value for char in '\\/:*?"<>|'):
        return ""
    if Path(value).name != value:
        return ""
    return f"{value}.xpi"


def _resolve_window_size(window_size: str | None, screen_profile: dict[str, int] | None = None) -> tuple[int, int]:
    if window_size and "," in str(window_size):
        width, height = str(window_size).split(",", 1)
        try:
            width_int = max(800, int(width.strip()))
            height_int = max(600, int(height.strip()))
            return width_int, height_int
        except Exception:
            pass
    if screen_profile:
        return _build_window_size(screen_profile)
    return _build_window_size(_get_windows_primary_screen_size())


def _to_js_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _pick_screen_profile(mode: str, width: int | None, height: int | None) -> dict[str, int] | None:
    if mode == "manual" and width and height:
        return {"width": int(width), "height": int(height)}
    if mode == "random":
        return dict(random.choice(DEFAULT_SCREEN_PROFILES))
    return None


def _pick_webgl_profile(mode: str, values: dict[str, Any]) -> dict[str, Any] | None:
    if mode == "manual":
        return {key: value for key, value in values.items() if key != "mode" and value not in (None, "")}
    if mode == "random":
        return dict(random.choice(DEFAULT_WEBGL_PROFILES))
    return None


def _pick_hardware_concurrency(mode: str, value: int | None) -> int | None:
    if mode == "manual" and value:
        return int(value)
    if mode == "random":
        return random.choice(DEFAULT_HARDWARE_CONCURRENCY)
    return None


def _pick_webrtc_profile(mode: str, local_ip: str | None, public_ip: str | None) -> dict[str, str | None]:
    if mode == "manual":
        return {
            "local_webrtc": str(local_ip or "").strip() or None,
            "public_webrtc": str(public_ip or "").strip() or None,
        }
    if mode == "random":
        return {
            "local_webrtc": _build_private_ip(),
            "public_webrtc": str(public_ip or "").strip() or None,
        }
    return {"local_webrtc": None, "public_webrtc": str(public_ip or "").strip() or None}


def _build_private_ip() -> str:
    network_type = random.choice(["192", "10", "172"])
    if network_type == "192":
        return f"192.168.{random.randint(0, 255)}.{random.randint(2, 254)}"
    if network_type == "10":
        return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(2, 254)}"
    return f"172.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(2, 254)}"


@lru_cache(maxsize=1)
def _get_windows_primary_screen_size() -> dict[str, int]:
    try:
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        if width > 0 and height > 0:
            return {"width": width, "height": height}
    except Exception:
        pass
    return {"width": 1280, "height": 800}


def _build_window_size(screen_profile: dict[str, int]) -> tuple[int, int]:
    width = int(screen_profile["width"])
    height = int(screen_profile["height"])
    if width <= 1366:
        width_margin = random.randint(60, 120)
        height_margin = random.randint(120, 170)
    elif width <= 1920:
        width_margin = random.randint(80, 180)
        height_margin = random.randint(130, 220)
    else:
        width_margin = random.randint(120, 260)
        height_margin = random.randint(150, 260)
    return max(1200, width - width_margin), max(720, height - height_margin)


def _build_language_value(language: str) -> str:
    values: list[str] = []
    for item in str(language or "en-US").split(","):
        item = item.strip()
        if item and item not in values:
            values.append(item)
    if not values:
        values.append("en-US")
    root = values[0].split("-")[0]
    if root and root not in values:
        values.append(root)
    if "en-US" not in values:
        values.append("en-US")
    return ",".join(values)
