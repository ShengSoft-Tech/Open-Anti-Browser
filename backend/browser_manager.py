from __future__ import annotations

import json
from pathlib import Path
import random
import urllib.request
import secrets
import shutil
import threading
import time
from typing import Any
from uuid import uuid4

import psutil

from .config import DOWNLOADS_DIR, ENGINE_METADATA, EXTENSIONS_DIR, bundled_engine_executable
from .models import AppSettings, BrowserProfile, ManagedExtension, ProxySettings, RuntimeSession, SavedProxy, utc_now_iso
from .services.chrome import launch_chrome_profile
from .services.downloads import DownloadRegistry
from .services.extensions import (
    FIREFOX_UPLOAD_SUFFIXES,
    CHROME_UPLOAD_SUFFIXES,
    persist_extension_folder,
    persist_uploaded_extension,
    remove_extension_storage,
)
from .services.firefox import launch_firefox_profile
from .services.network import (
    kill_process_tree,
    proxy_to_profile_proxy,
    resolve_geo_profile,
    slugify,
    test_proxy_connectivity,
)
from .services.synchronizer import BrowserSynchronizer, CdpPageClient
from .services.window_manager import arrange_windows, list_monitors, set_uniform_size, show_windows
from .storage import JsonStorage


def _fetch_ws_debugger_url(port: int, timeout: float = 10.0) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/json/version",
                headers={"User-Agent": "Open-Anti-Browser"},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                ws_url = data.get("webSocketDebuggerUrl")
                if ws_url:
                    return ws_url
        except Exception:
            pass
        time.sleep(0.5)
    return None


class BrowserManager:
    def __init__(self) -> None:
        self.storage = JsonStorage()
        self.downloads = DownloadRegistry()
        self.runtime_sessions: dict[str, dict[str, Any]] = {}
        self.pending_starts: set[str] = set()
        self._session_lock = threading.RLock()
        self.synchronizer = BrowserSynchronizer(self._resolve_runtime_session, self._resolve_profile_summary)

    def bootstrap(self) -> dict[str, Any]:
        return {
            "settings": self.get_settings().model_dump(mode="json"),
            "profiles": self.list_profiles(),
            "engines": self.get_engine_statuses(),
            "downloads": self.downloads.get_all(),
        }

    def get_settings(self) -> AppSettings:
        return self.storage.load_settings()

    def update_settings(self, payload: dict[str, Any]) -> AppSettings:
        if "saved_proxies" not in payload:
            payload = {
                **payload,
                "saved_proxies": [item.model_dump(mode="json") for item in self.get_settings().saved_proxies],
            }
        if "managed_extensions" not in payload:
            payload = {
                **payload,
                "managed_extensions": [item.model_dump(mode="json") for item in self.get_settings().managed_extensions],
            }
        settings = AppSettings.model_validate(payload)
        if not str(settings.api_access.api_key or "").strip():
            settings.api_access.api_key = secrets.token_urlsafe(32)
        if not settings.api_access.backend_only_port:
            settings.api_access.backend_only_port = 18000
        Path(settings.user_data_root).mkdir(parents=True, exist_ok=True)
        EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
        settings.chrome.executable_path = str(bundled_engine_executable("chrome"))
        settings.firefox.executable_path = str(bundled_engine_executable("firefox"))
        settings.chrome.download_path = str(DOWNLOADS_DIR / ENGINE_METADATA["chrome"]["download_name"])
        settings.firefox.download_path = str(DOWNLOADS_DIR / ENGINE_METADATA["firefox"]["download_name"])
        Path(settings.chrome.download_path).parent.mkdir(parents=True, exist_ok=True)
        Path(settings.firefox.download_path).parent.mkdir(parents=True, exist_ok=True)
        return self.storage.save_settings(settings)

    def list_profiles(self) -> list[dict[str, Any]]:
        self._refresh_runtime_sessions()
        profiles = self.storage.load_profiles()
        result: list[dict[str, Any]] = []
        for profile in profiles:
            item = profile.model_dump(mode="json")
            session = self._get_runtime_session(profile.id)
            item["runtime"] = session["session"].model_dump(mode="json") if session else None
            item["status"] = self._get_profile_status(profile.id, session=session)
            result.append(item)
        return result

    def get_profile(self, profile_id: str) -> BrowserProfile:
        profiles = self.storage.load_profiles()
        profile = next((item for item in profiles if item.id == profile_id), None)
        if not profile:
            raise KeyError("配置不存在")
        return profile

    def save_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = BrowserProfile.model_validate(payload)
        profile.updated_at = utc_now_iso()

        def updater(profiles: list[BrowserProfile]) -> tuple[list[BrowserProfile], BrowserProfile]:
            existing = next((item for item in profiles if item.id == profile.id), None)
            if existing:
                profile.created_at = existing.created_at
                profile.last_used = existing.last_used
            if profile.engine == "chrome" and profile.chrome.fingerprint.seed is None:
                profile.chrome.fingerprint.seed = self._new_chrome_seed()
            profile.name = self._ensure_sequence_name(profile.name, (item.name for item in profiles if item.id != profile.id))

            replaced = False
            updated_profiles: list[BrowserProfile] = []
            for item in profiles:
                if item.id == profile.id:
                    updated_profiles.append(profile)
                    replaced = True
                else:
                    updated_profiles.append(item)
            if not replaced:
                updated_profiles.append(profile)
            return updated_profiles, profile

        saved_profile = self.storage.update_profiles(updater)
        return self._profile_response(saved_profile)

    def delete_profile(self, profile_id: str) -> None:
        profile = self.get_profile(profile_id)
        settings = self.get_settings()
        self.stop_profile(profile_id, quiet=True)
        self._delete_profile_user_data_dirs(profile, settings)
        self.storage.delete_profile(profile_id)

    def delete_profile_by_name(self, name: str) -> None:
        # 按名称删除第一个匹配的 profile，调用方需保证名称唯一
        profiles = self.storage.load_profiles()
        match = next((p for p in profiles if p.name == name), None)
        if not match:
            raise KeyError(f"找不到名称为 {name!r} 的配置")
        self.delete_profile(match.id)

    def duplicate_profile(self, profile_id: str) -> dict[str, Any]:
        profile = self.storage.duplicate_profile(profile_id)
        if not profile:
            raise KeyError("配置不存在")
        return self._profile_response(profile)

    def start_profile(self, profile_id: str) -> dict[str, Any]:
        self._refresh_runtime_sessions()
        with self._session_lock:
            session = self.runtime_sessions.get(profile_id)
            if session:
                return self._profile_response(self.get_profile(profile_id))
            if profile_id in self.pending_starts:
                raise RuntimeError("浏览器正在启动中，请稍等")
            self.pending_starts.add(profile_id)

        try:
            profile = self.get_profile(profile_id)
            if profile.engine == "chrome" and profile.chrome.fingerprint.seed is None:
                profile.chrome.fingerprint.seed = self._new_chrome_seed()
                profile.updated_at = utc_now_iso()
                self.storage.upsert_profile(profile)
            settings = self.get_settings()
            user_data_dir = self._resolve_user_data_dir(profile, settings)

            if profile.engine == "chrome":
                launch_info = launch_chrome_profile(profile, settings, user_data_dir)
            elif profile.engine == "firefox":
                launch_info = launch_firefox_profile(profile, settings, user_data_dir)
            else:
                raise ValueError("不支持的内核类型")

            executable_path = bundled_engine_executable(profile.engine)

            runtime = RuntimeSession(
                profile_id=profile.id,
                engine=profile.engine,
                pid=launch_info["process"].pid,
                user_data_dir=str(user_data_dir),
                executable_path=str(executable_path),
                command=launch_info["command"],
                remote_debugging_port=launch_info.get("remote_debugging_port"),
                marionette_port=launch_info.get("marionette_port"),
                proxy_bridge_url=launch_info.get("proxy_bridge_url"),
                resolved_ip=launch_info["geo_profile"].get("ip"),
                resolved_timezone=launch_info["geo_profile"].get("timezone"),
                resolved_language=launch_info["geo_profile"].get("language"),
            )
            with self._session_lock:
                self.runtime_sessions[profile.id] = {
                    "session": runtime,
                    "process": launch_info["process"],
                    "proxy_bridge": launch_info.get("proxy_bridge"),
                }
            profile.last_used = utc_now_iso()
            profile.updated_at = profile.last_used
            self.storage.upsert_profile(profile)
            return self._profile_response(self.get_profile(profile_id))
        finally:
            with self._session_lock:
                self.pending_starts.discard(profile_id)

    def create_and_start_profile(self, task_id: str, proxy: str = "", engine: str = "chrome") -> dict[str, Any]:
        task_id = task_id.strip()
        proxy = (proxy or "").strip()
        profiles = self.storage.load_profiles()
        if any(p.name == task_id for p in profiles):
            raise RuntimeError(f"task_id {task_id!r} 已存在")
        payload: dict[str, Any] = {"name": task_id, "engine": engine}
        if proxy:
            payload["proxy"] = proxy
        saved = self.save_profile(payload)
        result = self.start_profile(saved["id"])
        port = result.get("port")
        if port:
            result["debug_url"] = _fetch_ws_debugger_url(port) or result.get("debug_url")
        return result

    def stop_profile(self, profile_id: str, quiet: bool = False) -> dict[str, Any] | None:
        self._refresh_runtime_sessions()
        with self._session_lock:
            active = self.runtime_sessions.pop(profile_id, None)
            self.pending_starts.discard(profile_id)
        if not active:
            if quiet:
                return None
            return self._profile_response(self.get_profile(profile_id))

        try:
            kill_process_tree(active["session"].pid)
        finally:
            proxy_bridge = active.get("proxy_bridge")
            if proxy_bridge:
                try:
                    proxy_bridge.stop()
                except Exception:
                    pass
        self.synchronizer.status()
        if quiet:
            return None
        return self._profile_response(self.get_profile(profile_id))

    def start_group(self, group_name: str) -> list[dict[str, Any]]:
        profiles = self.storage.load_profiles()
        result = []
        for profile in profiles:
            if (profile.group or "").strip() == group_name:
                result.append(self.start_profile(profile.id))
        return result

    def stop_group(self, group_name: str) -> list[dict[str, Any]]:
        profiles = self.storage.load_profiles()
        result = []
        for profile in profiles:
            if (profile.group or "").strip() == group_name:
                payload = self.stop_profile(profile.id)
                if payload:
                    result.append(payload)
        return result

    def test_proxy(self, payload: dict[str, Any]) -> dict[str, Any]:
        proxy_config = proxy_to_profile_proxy(payload)
        connect_result = test_proxy_connectivity(proxy_config)
        if not connect_result["ok"]:
            return {
                "ok": False,
                "message": connect_result["message"],
                "data": dict(connect_result),
            }

        return {
            "ok": True,
            "message": "连接成功",
            "data": connect_result,
        }

    def get_synchronizer_status(self) -> dict[str, Any]:
        return self.synchronizer.status()

    def start_synchronizer(self, payload: dict[str, Any]) -> dict[str, Any]:
        master_profile_id = payload.get("master_profile_id")
        follower_profile_ids = payload.get("follower_profile_ids") or []
        options = payload.get("options") or {}
        return self.synchronizer.start(master_profile_id, follower_profile_ids, options)

    def stop_synchronizer(self) -> dict[str, Any]:
        return self.synchronizer.stop()

    def navigate_synchronizer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.synchronizer.navigate(
            payload.get("url"),
            include_master=bool(payload.get("include_master", True)),
        )

    def sync_master_url_to_followers(self) -> dict[str, Any]:
        return self.synchronizer.sync_master_url()

    def list_sync_monitors(self) -> list[dict[str, Any]]:
        return list_monitors()

    def show_sync_windows(self, profile_ids: list[str]) -> dict[str, Any]:
        targets = self._normalize_running_profile_ids(profile_ids)
        return show_windows(self._resolve_runtime_session, targets)

    def uniform_sync_windows(self, profile_ids: list[str]) -> dict[str, Any]:
        targets = self._normalize_running_profile_ids(profile_ids)
        return set_uniform_size(self._resolve_runtime_session, targets)

    def arrange_sync_windows(self, payload: dict[str, Any]) -> dict[str, Any]:
        targets = self._normalize_running_profile_ids(payload.get("profile_ids") or [])
        return arrange_windows(
            self._resolve_runtime_session,
            targets,
            monitor_id=str(payload.get("monitor_id") or "").strip() or None,
            arrange_mode=str(payload.get("arrange_mode") or "grid").strip().lower() or "grid",
        )

    def run_sync_text_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        targets = self._normalize_running_profile_ids(payload.get("profile_ids") or [])
        action = str(payload.get("action") or "").strip().lower()
        if action not in {"clear", "same", "random", "designated"}:
            raise ValueError("不支持的文本操作")

        values = self._build_text_action_values(action, targets, payload)
        updated = 0
        clients = self._open_cdp_clients(targets)
        try:
            for profile_id, client in clients:
                value = values.get(profile_id, "")
                client.evaluate(_build_active_text_expression(action, value))
                updated += 1
        finally:
            for _, client in clients:
                client.close()
        return {"ok": True, "count": updated, "action": action}

    def run_sync_tab_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        targets = self._normalize_running_profile_ids(payload.get("profile_ids") or [])
        action = str(payload.get("action") or "").strip().lower()
        if action not in {"open_urls", "close_blank", "close_current", "close_others", "unify_tabs"}:
            raise ValueError("不支持的标签页操作")

        clients = self._open_cdp_clients(targets)
        updated = 0
        try:
            if action == "open_urls":
                urls = [item for item in (payload.get("urls") or []) if str(item or "").strip()]
                if not urls:
                    raise ValueError("请至少填写一个网址")
                first_in_current = bool(payload.get("first_in_current", True))
                for _, client in clients:
                    if first_in_current:
                        client.navigate(urls[0])
                        for url in urls[1:]:
                            client.create_target(url)
                    else:
                        for url in urls:
                            client.create_target(url)
                    updated += 1
            elif action == "unify_tabs":
                master_id = str(payload.get("master_profile_id") or "").strip() or targets[0]
                master_client = next((client for profile_id, client in clients if profile_id == master_id), None)
                if not master_client:
                    raise ValueError("没有找到可用的主窗口")
                master_url = master_client.get_location()
                for profile_id, client in clients:
                    if profile_id == master_id:
                        continue
                    client.navigate(master_url)
                    updated += 1
            else:
                for _, client in clients:
                    updated += self._apply_tab_cleanup_action(client, action)
        finally:
            for _, client in clients:
                client.close()
        return {"ok": True, "count": updated, "action": action}

    def list_saved_proxies(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.get_settings().saved_proxies]

    def save_saved_proxy(self, payload: dict[str, Any]) -> dict[str, Any]:
        proxy = SavedProxy.model_validate(payload)
        if not str(proxy.id or "").strip():
            proxy.id = uuid4().hex
        settings = self.get_settings()
        proxy.name = self._ensure_sequence_name(proxy.name, (item.name for item in settings.saved_proxies if item.id != proxy.id))

        replaced = False
        updated_proxies: list[SavedProxy] = []
        for item in settings.saved_proxies:
            if item.id == proxy.id:
                updated_proxies.append(proxy)
                replaced = True
            else:
                updated_proxies.append(item)
        if not replaced:
            updated_proxies.append(proxy)
        settings.saved_proxies = updated_proxies
        self.storage.save_settings(settings)
        return proxy.model_dump(mode="json")

    def regenerate_api_key(self) -> dict[str, Any]:
        settings = self.get_settings()
        settings.api_access.api_key = secrets.token_urlsafe(32)
        self.storage.save_settings(settings)
        return settings.api_access.model_dump(mode="json")

    def delete_saved_proxy(self, proxy_id: str) -> None:
        settings = self.get_settings()
        settings.saved_proxies = [item for item in settings.saved_proxies if item.id != proxy_id]
        self.storage.save_settings(settings)

    def assign_saved_proxy(self, proxy_id: str, profile_ids: list[str]) -> list[dict[str, Any]]:
        profile_ids = [str(item) for item in profile_ids if str(item).strip()]
        if not profile_ids:
            return []

        saved_proxy = next((item for item in self.get_settings().saved_proxies if item.id == proxy_id), None)
        if not saved_proxy:
            raise KeyError("代理不存在")

        profiles = self.storage.load_profiles()
        saved_proxy_payload = ProxySettings.model_validate(saved_proxy.model_dump(mode="json"))
        updated_profiles: list[BrowserProfile] = []
        result: list[dict[str, Any]] = []
        target_ids = set(profile_ids)
        for profile in profiles:
            if profile.id in target_ids:
                profile.proxy = ProxySettings.model_validate(saved_proxy_payload.model_dump(mode="json"))
                profile.updated_at = utc_now_iso()
                result.append(self._profile_response(profile))
            updated_profiles.append(profile)
        self.storage.save_profiles(updated_profiles)
        return result

    def list_managed_extensions(self, engine: str | None = None) -> list[dict[str, Any]]:
        target_engine = str(engine or "").strip().lower()
        extensions = self.get_settings().managed_extensions
        result: list[dict[str, Any]] = []
        for extension in extensions:
            if target_engine and extension.engine != target_engine:
                continue
            payload = extension.model_dump(mode="json")
            effective_path = extension.unpacked_path if extension.engine == "chrome" else extension.stored_path
            payload["effective_path"] = effective_path
            payload["exists"] = Path(effective_path or extension.stored_path).exists()
            result.append(payload)
        result.sort(key=lambda item: (item.get("engine", ""), item.get("created_at", "")))
        return result

    def save_managed_extension(
        self,
        engine: str,
        filename: str,
        content: bytes,
        name: str | None = None,
    ) -> dict[str, Any]:
        engine = self._normalize_extension_engine(engine)
        filename = Path(str(filename or "extension")).name
        suffix = Path(filename).suffix.lower()
        if engine == "chrome" and suffix not in CHROME_UPLOAD_SUFFIXES:
            raise ValueError("Chrome 扩展请上传 zip 或 crx 文件")
        if engine == "firefox" and suffix not in FIREFOX_UPLOAD_SUFFIXES:
            raise ValueError("Firefox 扩展请上传 xpi 或 zip 文件")
        if not content:
            raise ValueError("扩展文件为空")

        extension_id = uuid4().hex
        stored_path, unpacked_path = persist_uploaded_extension(
            EXTENSIONS_DIR,
            engine,
            extension_id,
            filename,
            content,
        )
        display_name = str(name or "").strip() or Path(filename).stem or extension_id
        extension = ManagedExtension(
            id=extension_id,
            engine=engine,
            name=display_name,
            file_name=filename,
            stored_path=stored_path,
            unpacked_path=unpacked_path,
            enabled=True,
        )
        settings = self.get_settings()
        settings.managed_extensions.append(extension)
        self.storage.save_settings(settings)
        return extension.model_dump(mode="json")

    def import_managed_extension_folder(
        self,
        engine: str,
        folder_path: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        engine = self._normalize_extension_engine(engine)
        raw_folder_path = str(folder_path or "").strip()
        if not raw_folder_path:
            raise ValueError("扩展文件夹路径不能为空")

        extension_id = uuid4().hex
        stored_path, unpacked_path, folder_name = persist_extension_folder(
            EXTENSIONS_DIR,
            engine,
            extension_id,
            raw_folder_path,
        )
        display_name = str(name or "").strip() or folder_name or extension_id
        extension = ManagedExtension(
            id=extension_id,
            engine=engine,
            name=display_name,
            file_name=folder_name,
            stored_path=stored_path,
            unpacked_path=unpacked_path,
            enabled=True,
        )
        settings = self.get_settings()
        settings.managed_extensions.append(extension)
        self.storage.save_settings(settings)
        return extension.model_dump(mode="json")

    def update_managed_extension(self, extension_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self.get_settings()
        updated: ManagedExtension | None = None
        next_extensions: list[ManagedExtension] = []
        for extension in settings.managed_extensions:
            if extension.id != extension_id:
                next_extensions.append(extension)
                continue
            if "enabled" in payload:
                extension.enabled = bool(payload.get("enabled"))
            if "name" in payload:
                name = str(payload.get("name") or "").strip()
                if name:
                    extension.name = name
            extension.updated_at = utc_now_iso()
            updated = extension
            next_extensions.append(extension)
        if not updated:
            raise KeyError("扩展不存在")
        settings.managed_extensions = next_extensions
        self.storage.save_settings(settings)
        return updated.model_dump(mode="json")

    def delete_managed_extension(self, extension_id: str) -> None:
        settings = self.get_settings()
        extension = next((item for item in settings.managed_extensions if item.id == extension_id), None)
        if not extension:
            raise KeyError("扩展不存在")
        settings.managed_extensions = [item for item in settings.managed_extensions if item.id != extension_id]
        self.storage.save_settings(settings)
        remove_extension_storage(EXTENSIONS_DIR, extension.engine, extension.id)

        profiles = self.storage.load_profiles()
        for profile in profiles:
            profile.chrome.disabled_global_extension_ids = [
                item for item in profile.chrome.disabled_global_extension_ids if item != extension_id
            ]
            profile.firefox.disabled_global_extension_ids = [
                item for item in profile.firefox.disabled_global_extension_ids if item != extension_id
            ]
        self.storage.save_profiles(profiles)

    def get_engine_statuses(self) -> dict[str, Any]:
        settings = self.get_settings()
        chrome_path = bundled_engine_executable("chrome")
        firefox_path = bundled_engine_executable("firefox")
        return {
            "chrome": {
                **ENGINE_METADATA["chrome"],
                "configured_path": str(chrome_path),
                "download_path": settings.chrome.download_path,
                "installed": chrome_path.exists(),
                "capability_ok": chrome_path.exists(),
                "bundled": True,
            },
            "firefox": {
                **ENGINE_METADATA["firefox"],
                "configured_path": str(firefox_path),
                "download_path": settings.firefox.download_path,
                "installed": firefox_path.exists(),
                "capability_ok": firefox_path.exists(),
                "bundled": True,
            },
        }

    def start_download(self, engine: str) -> dict[str, Any]:
        settings = self.get_settings()
        if engine == "chrome":
            return self.downloads.start("chrome", settings.chrome.installer_url, settings.chrome.download_path)
        if engine == "firefox":
            return self.downloads.start("firefox", settings.firefox.installer_url, settings.firefox.download_path)
        raise ValueError("未知内核")

    def import_profiles(self, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        existing_profiles = {item.id: item for item in self.storage.load_profiles()}
        for raw in payload:
            profile = BrowserProfile.model_validate(raw)
            profile.updated_at = utc_now_iso()
            if profile.id in existing_profiles:
                profile.id = f"{profile.id}-{slugify(profile.name, 'copy')}"
            profile.name = self._ensure_sequence_name(profile.name, (item.name for item in existing_profiles.values() if item.id != profile.id))
            existing_profiles[profile.id] = profile
            imported.append(self._profile_response(profile))
        self.storage.save_profiles(list(existing_profiles.values()))
        return imported

    def export_profiles(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.storage.load_profiles()]

    def _profile_response(self, profile: BrowserProfile) -> dict[str, Any]:
        self._refresh_runtime_sessions()
        payload = profile.model_dump(mode="json")
        session = self._get_runtime_session(profile.id)
        payload["runtime"] = session["session"].model_dump(mode="json") if session else None
        payload["status"] = self._get_profile_status(profile.id, session=session)
        runtime_payload = payload.get("runtime") or {}
        port = runtime_payload.get("remote_debugging_port")
        marionette_port = runtime_payload.get("marionette_port")
        payload["port"] = port
        payload["debug_port"] = port
        payload["debug_url"] = f"http://127.0.0.1:{port}" if port else None
        payload["marionette_port"] = marionette_port
        payload["selenium_port"] = marionette_port
        return payload

    def _resolve_user_data_dir(self, profile: BrowserProfile, settings: AppSettings, ensure_exists: bool = True) -> Path:
        root = profile.storage.root_dir.strip() if profile.storage.root_dir else settings.user_data_root
        base_root = Path(root).expanduser().resolve()
        engine_dir = base_root / profile.engine
        profile_dir_name = f"{slugify(profile.name, profile.id[:8])}-{profile.id[:8]}"
        resolved = engine_dir / profile_dir_name
        if ensure_exists:
            resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def _delete_profile_user_data_dirs(self, profile: BrowserProfile, settings: AppSettings) -> None:
        root = (profile.storage.root_dir.strip() if profile.storage.root_dir else settings.user_data_root or "").strip()
        if not root:
            return

        base_root = Path(root).expanduser().resolve()
        engine_dir = (base_root / profile.engine).resolve()
        short_id = profile.id[:8].lower()
        candidates: list[Path] = [self._resolve_user_data_dir(profile, settings, ensure_exists=False)]

        if engine_dir.exists():
            try:
                candidates.extend(
                    item.resolve()
                    for item in engine_dir.iterdir()
                    if item.is_dir() and item.name.lower().endswith(f"-{short_id}")
                )
            except OSError:
                pass

        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            self._safe_remove_profile_dir(candidate, engine_dir)

    @staticmethod
    def _safe_remove_profile_dir(profile_dir: Path, engine_dir: Path) -> None:
        try:
            profile_dir = profile_dir.resolve()
            engine_dir = engine_dir.resolve()
        except OSError:
            return

        if profile_dir == engine_dir or engine_dir not in profile_dir.parents:
            return
        if not profile_dir.exists() or not profile_dir.is_dir():
            return

        for attempt in range(5):
            try:
                shutil.rmtree(profile_dir)
                return
            except FileNotFoundError:
                return
            except PermissionError:
                time.sleep(0.25 * (attempt + 1))
            except OSError:
                time.sleep(0.25 * (attempt + 1))

        shutil.rmtree(profile_dir, ignore_errors=True)

    def _normalize_running_profile_ids(self, profile_ids: list[str]) -> list[str]:
        targets: list[str] = []
        for item in profile_ids:
            profile_id = str(item or "").strip()
            if not profile_id or profile_id in targets:
                continue
            runtime = self._resolve_runtime_session(profile_id)
            if runtime and runtime.get("remote_debugging_port"):
                targets.append(profile_id)
        if not targets:
            raise ValueError("请至少选择一个已启动的浏览器")
        return targets

    def _open_cdp_clients(self, profile_ids: list[str]) -> list[tuple[str, CdpPageClient]]:
        clients: list[tuple[str, CdpPageClient]] = []
        for profile_id in profile_ids:
            runtime = self._resolve_runtime_session(profile_id)
            if not runtime or not runtime.get("remote_debugging_port"):
                continue
            client = CdpPageClient(profile_id, int(runtime["remote_debugging_port"]))
            client.connect()
            clients.append((profile_id, client))
        if not clients:
            raise RuntimeError("没有可用的调试连接")
        return clients

    def _build_text_action_values(self, action: str, profile_ids: list[str], payload: dict[str, Any]) -> dict[str, str]:
        if action == "clear":
            return {profile_id: "" for profile_id in profile_ids}
        if action == "same":
            value = str(payload.get("text") or "")
            return {profile_id: value for profile_id in profile_ids}
        if action == "random":
            start = float(payload.get("range_start") or 0)
            end = float(payload.get("range_end") or 0)
            minimum = min(start, end)
            maximum = max(start, end)
            precision = int(payload.get("precision") or 3)
            return {
                profile_id: f"{random.uniform(minimum, maximum):.{precision}f}"
                for profile_id in profile_ids
            }

        groups = payload.get("groups") or []
        lines: list[str] = []
        for item in groups:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "")
            group_lines = [line for line in (value.strip() for value in content.splitlines()) if line]
            lines.extend(group_lines)
        if not lines:
            raise ValueError("请先填写指定文本内容")
        mode = str(payload.get("designated_mode") or "sequential").strip().lower()
        if mode == "random":
            return {profile_id: random.choice(lines) for profile_id in profile_ids}
        if mode == "fixed":
            fixed_value = str(payload.get("fixed_text") or "").strip() or lines[0]
            return {profile_id: fixed_value for profile_id in profile_ids}
        return {
            profile_id: lines[index % len(lines)]
            for index, profile_id in enumerate(profile_ids)
        }

    @staticmethod
    def _apply_tab_cleanup_action(client: CdpPageClient, action: str) -> int:
        targets = [
            item
            for item in client.list_targets()
            if isinstance(item, dict)
            and str(item.get("type") or "").lower() in {"page", "tab"}
            and item.get("id")
        ]
        if not targets:
            return 0

        current_id = client.current_target_id()
        close_ids: list[str] = []
        if action == "close_blank":
            for item in targets:
                url = str(item.get("url") or "")
                if url in {"about:blank", "chrome://newtab/", "chrome://new-tab-page/", "about:newtab"}:
                    close_ids.append(str(item["id"]))
        elif action == "close_current":
            if current_id:
                close_ids.append(current_id)
        elif action == "close_others":
            for item in targets:
                target_id = str(item["id"])
                if target_id != current_id:
                    close_ids.append(target_id)

        closed = 0
        for target_id in close_ids:
            try:
                client.close_target(target_id)
                closed += 1
            except Exception:
                continue
        return closed

    def _refresh_runtime_sessions(self) -> None:
        stale_ids = []
        with self._session_lock:
            items = list(self.runtime_sessions.items())
        for profile_id, payload in items:
            pid = payload["session"].pid
            if not psutil.pid_exists(pid):
                stale_ids.append(profile_id)
                continue
            try:
                process = psutil.Process(pid)
                if process.status() == psutil.STATUS_ZOMBIE:
                    stale_ids.append(profile_id)
            except psutil.Error:
                stale_ids.append(profile_id)
        for profile_id in stale_ids:
            with self._session_lock:
                payload = self.runtime_sessions.pop(profile_id, None)
            if not payload:
                continue
            proxy_bridge = payload.get("proxy_bridge")
            if proxy_bridge:
                try:
                    proxy_bridge.stop()
                except Exception:
                    pass

    def _get_runtime_session(self, profile_id: str) -> dict[str, Any] | None:
        with self._session_lock:
            return self.runtime_sessions.get(profile_id)

    def _resolve_runtime_session(self, profile_id: str) -> dict[str, Any] | None:
        self._refresh_runtime_sessions()
        payload = self._get_runtime_session(profile_id)
        if not payload:
            return None
        return payload["session"].model_dump(mode="json")

    def get_profile_cdp_ws_url(self, profile_id: str) -> str | None:
        session = self._resolve_runtime_session(profile_id)
        if not session:
            return None
        port = session.get("remote_debugging_port")
        if not port:
            return None
        return _fetch_ws_debugger_url(int(port), timeout=3.0)

    def _resolve_profile_summary(self, profile_id: str) -> dict[str, Any] | None:
        try:
            profile = self.get_profile(profile_id)
        except KeyError:
            return None
        payload = profile.model_dump(mode="json")
        payload["status"] = self._get_profile_status(profile_id)
        return payload

    def _get_profile_status(self, profile_id: str, session: dict[str, Any] | None = None) -> str:
        active_session = session or self._get_runtime_session(profile_id)
        if active_session:
            return "running"
        with self._session_lock:
            if profile_id in self.pending_starts:
                return "starting"
        return "stopped"

    @staticmethod
    def _ensure_sequence_name(raw_name: str, existing_names) -> str:
        name = str(raw_name or "").strip()
        if name:
            return name

        used_numbers = set()
        for item in existing_names:
            text = str(item or "").strip()
            if text.isdigit():
                used_numbers.add(int(text))

        next_number = 1
        while next_number in used_numbers:
            next_number += 1
        return str(next_number)

    @staticmethod
    def _new_chrome_seed() -> int:
        return random.SystemRandom().randint(0, 2**32 - 1)

    @staticmethod
    def _normalize_extension_engine(engine: str) -> str:
        value = str(engine or "").strip().lower()
        if value not in {"chrome", "firefox"}:
            raise ValueError("扩展内核必须是 chrome 或 firefox")
        return value


def _build_active_text_expression(action: str, value: str) -> str:
    action_json = json.dumps(str(action or ""), ensure_ascii=False)
    value_json = json.dumps(str(value or ""), ensure_ascii=False)
    return f"""
(() => {{
  const action = {action_json};
  const value = {value_json};
  const pickTarget = () => {{
    const active = document.activeElement;
    if (active && (active.matches?.('input, textarea, select') || active.isContentEditable)) {{
      return active;
    }}
    return document.querySelector('input, textarea, [contenteditable="true"], select');
  }};
  const target = pickTarget();
  if (!target) return false;
  target.focus?.();
  if (action === 'clear') {{
    if (target.isContentEditable) {{
      target.innerText = '';
    }} else if ('value' in target) {{
      target.value = '';
    }}
  }} else if (target.isContentEditable) {{
    target.innerText = value;
  }} else if ('value' in target) {{
    target.value = value;
  }} else {{
    return false;
  }}
  target.dispatchEvent(new Event('input', {{ bubbles: true }}));
  target.dispatchEvent(new Event('change', {{ bubbles: true }}));
  return true;
}})()
"""
