from __future__ import annotations

import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any

from ..config import bundled_engine_executable
from ..models import AppSettings, BrowserProfile
from .network import (
    LocalHttpProxyBridge,
    build_chrome_proxy_bypass_list,
    fallback_geo_profile,
    find_free_port,
    proxy_to_profile_proxy,
    resolve_geo_profile,
)


CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
DEFAULT_HARDWARE_CONCURRENCY = [4, 8, 12, 16, 24, 32]


def launch_chrome_profile(
    profile: BrowserProfile,
    app_settings: AppSettings,
    user_data_dir: Path,
) -> dict[str, Any]:
    executable_path = bundled_engine_executable("chrome")
    if not executable_path.exists():
        raise FileNotFoundError(f"Chrome 内核不存在：{executable_path}")

    proxy_config = proxy_to_profile_proxy(profile.proxy.model_dump(mode="json"))
    chrome_fp = profile.chrome.fingerprint
    try:
        geo_profile = resolve_geo_profile(
            proxy_config,
            chrome_fp.auto_timezone,
            strict=False,
        )
    except Exception as exc:
        geo_profile = fallback_geo_profile(exc)
    remote_debugging_port = find_free_port()
    seed = chrome_fp.seed if chrome_fp.seed is not None else _fallback_seed()
    hardware_concurrency = _resolve_hardware_concurrency(
        chrome_fp.hardware_concurrency_mode,
        chrome_fp.hardware_concurrency,
    )
    resolved_language = _normalize_language_value(
        chrome_fp.language or geo_profile["language"] or chrome_fp.accept_language
    )
    resolved_accept_language = _resolve_accept_language(chrome_fp.accept_language, resolved_language)
    resolved_timezone = geo_profile["timezone"] if chrome_fp.auto_timezone else (chrome_fp.timezone or geo_profile["timezone"])
    launch_args: list[str] = [
        str(executable_path),
        f"--user-data-dir={user_data_dir}",
        f"--remote-debugging-port={remote_debugging_port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--password-store=basic",
        f"--fingerprint={seed}",
    ]

    _prepare_chrome_language_preferences(user_data_dir, resolved_language, resolved_accept_language)
    _upsert_arg(launch_args, "--lang", resolved_language)
    _upsert_arg(launch_args, "--accept-lang", resolved_accept_language)
    _upsert_arg(launch_args, "--timezone", resolved_timezone)
    if chrome_fp.platform:
        _upsert_arg(launch_args, "--fingerprint-platform", chrome_fp.platform)
    if hardware_concurrency:
        _upsert_arg(launch_args, "--fingerprint-hardware-concurrency", hardware_concurrency)
    if chrome_fp.disable_spoofing:
        _upsert_arg(launch_args, "--disable-spoofing", ",".join(chrome_fp.disable_spoofing))
    _upsert_arg(launch_args, "--window-size", profile.chrome.startup.window_size or "1200,800")
    enabled_extensions = _collect_enabled_chrome_extensions(profile, app_settings)
    if enabled_extensions:
        extension_arg = ",".join(enabled_extensions)
        _upsert_arg(launch_args, "--disable-extensions-except", extension_arg)
        _upsert_arg(launch_args, "--load-extension", extension_arg)

    proxy_bridge = None
    browser_proxy = proxy_config["server"] if proxy_config else None
    if proxy_config and proxy_config["username"] is not None:
        if proxy_config["scheme"] not in ("http", "https"):
            raise ValueError("Chrome 账号代理目前仅支持 http/https。")
        proxy_bridge = LocalHttpProxyBridge(proxy_config).start()
        browser_proxy = proxy_bridge.local_proxy

    if browser_proxy:
        _upsert_arg(launch_args, "--proxy-server", browser_proxy)
        proxy_bypass_list = _build_chrome_proxy_bypass_list(profile.proxy_bypass_rules)
        if proxy_bypass_list:
            _upsert_arg(launch_args, "--proxy-bypass-list", proxy_bypass_list)

    for raw_arg in profile.chrome.launch_args:
        raw_arg = str(raw_arg or "").strip()
        if not raw_arg:
            continue
        if raw_arg.startswith("--"):
            name, value = _split_arg(raw_arg)
            _upsert_arg(launch_args, name, value)
        else:
            launch_args.append(raw_arg)

    startup_urls = [item.strip() for item in profile.chrome.startup.open_urls if str(item).strip()]
    if startup_urls:
        launch_args.extend(startup_urls)

    user_data_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        launch_args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        cwd=str(executable_path.parent),
        env={
            **os.environ,
            "LANG": resolved_language,
            "LANGUAGE": resolved_accept_language,
        },
    )

    return {
        "process": process,
        "command": launch_args,
        "proxy_bridge": proxy_bridge,
        "proxy_bridge_url": proxy_bridge.local_proxy if proxy_bridge else None,
        "remote_debugging_port": remote_debugging_port,
        "geo_profile": geo_profile,
        "seed": seed,
    }


def _split_arg(raw_arg: str) -> tuple[str, str | None]:
    if "=" in raw_arg:
        name, value = raw_arg.split("=", 1)
        return name, value
    return raw_arg, None


def _build_chrome_proxy_bypass_list(values: list[str] | None) -> str:
    return build_chrome_proxy_bypass_list(values)


def _upsert_arg(args: list[str], name: str, value: Any | None = None) -> None:
    args[:] = [item for item in args if item != name and not item.startswith(f"{name}=")]
    if value is False or value is None or value == "":
        if value is None:
            args.append(name)
        return
    args.append(f"{name}={value}")


def _fallback_seed() -> int:
    return random.SystemRandom().randint(0, 2**32 - 1)


def _resolve_hardware_concurrency(mode: str | None, value: int | None) -> int | None:
    mode = str(mode or "random").lower()
    if mode == "manual":
        return int(value) if value else None
    if mode == "auto":
        return None
    return int(random.choice(DEFAULT_HARDWARE_CONCURRENCY))


def _normalize_language_value(language: str | None) -> str:
    raw = str(language or "").strip()
    if not raw:
        return "en-US"
    first = raw.split(",", 1)[0].strip()
    if ";q=" in first:
        first = first.split(";q=", 1)[0].strip()
    return first or "en-US"


def _resolve_accept_language(accept_language: str | None, language: str) -> str:
    requested_items = _parse_language_items(accept_language)
    primary = _normalize_language_value(language or (requested_items[0] if requested_items else ""))
    values: list[str] = [primary]

    for item in requested_items:
        if item.lower() != primary.lower():
            values.append(item)

    root = primary.split("-", 1)[0].strip()
    if root and root.lower() != primary.lower():
        values.append(root)
    if "en-us" not in {item.lower() for item in values}:
        values.append("en-US")

    unique_values: list[str] = []
    seen: set[str] = set()
    for item in values:
        lowered = item.lower()
        if item and lowered not in seen:
            unique_values.append(item)
            seen.add(lowered)

    return ",".join(unique_values)


def _parse_language_items(value: str | None) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw_item in str(value or "").split(","):
        item = raw_item.strip()
        if not item:
            continue
        if ";q=" in item:
            item = item.split(";q=", 1)[0].strip()
        lowered = item.lower()
        if not item or lowered in seen:
            continue
        items.append(item)
        seen.add(lowered)
    return items


def _prepare_chrome_language_preferences(user_data_dir: Path, language: str, accept_language: str) -> None:
    local_state_path = user_data_dir / "Local State"
    preferences_path = user_data_dir / "Default" / "Preferences"
    _merge_json_file(
        local_state_path,
        {
            "intl": {
                "app_locale": language,
                "accept_languages": accept_language,
            }
        },
    )
    _merge_json_file(
        preferences_path,
        {
            "intl": {
                "selected_languages": accept_language,
                "accept_languages": accept_language,
            }
        },
    )


def _merge_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current_data: dict[str, Any] = {}
    if path.exists():
        try:
            current_data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            current_data = {}
    merged = _deep_merge_dict(current_data, payload)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


def _deep_merge_dict(target: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(target)
    for key, value in payload.items():
        current_value = result.get(key)
        if isinstance(current_value, dict) and isinstance(value, dict):
            result[key] = _deep_merge_dict(current_value, value)
        else:
            result[key] = value
    return result


def _collect_enabled_chrome_extensions(profile: BrowserProfile, app_settings: AppSettings) -> list[str]:
    disabled_ids = set(profile.chrome.disabled_global_extension_ids or [])
    extension_paths: list[str] = []
    for extension in app_settings.managed_extensions:
        if extension.engine != "chrome" or not extension.enabled or extension.id in disabled_ids:
            continue
        candidate = Path(extension.unpacked_path or extension.stored_path)
        if candidate.exists():
            extension_paths.append(str(candidate))
    return extension_paths
