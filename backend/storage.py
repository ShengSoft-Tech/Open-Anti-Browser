from __future__ import annotations

import json
import secrets
import threading
from copy import deepcopy
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from .config import DATA_DIR, DOWNLOADS_DIR, ENGINE_METADATA, DEFAULT_USER_DATA_ROOT
from .models import ApiAccessSettings, AppSettings, BrowserProfile, EngineSettings, utc_now_iso

T = TypeVar("T")


class JsonStorage:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.data_dir = DATA_DIR
        self.downloads_dir = DOWNLOADS_DIR
        self.settings_file = self.data_dir / "settings.json"
        self.profiles_file = self.data_dir / "profiles.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def load_settings(self) -> AppSettings:
        with self._lock:
            if not self.settings_file.exists():
                settings = self._default_settings()
                self.save_settings(settings)
                return settings
            raw = self._read_json(self.settings_file, {})
            try:
                settings = AppSettings.model_validate(raw)
                changed = False
                if settings.chrome.executable_path != ENGINE_METADATA["chrome"]["default_executable"]:
                    settings.chrome.executable_path = ENGINE_METADATA["chrome"]["default_executable"]
                    changed = True
                if settings.firefox.executable_path != ENGINE_METADATA["firefox"]["default_executable"]:
                    settings.firefox.executable_path = ENGINE_METADATA["firefox"]["default_executable"]
                    changed = True
                chrome_download = str(self.downloads_dir / ENGINE_METADATA["chrome"]["download_name"])
                firefox_download = str(self.downloads_dir / ENGINE_METADATA["firefox"]["download_name"])
                if settings.chrome.download_path != chrome_download:
                    settings.chrome.download_path = chrome_download
                    changed = True
                if settings.firefox.download_path != firefox_download:
                    settings.firefox.download_path = firefox_download
                    changed = True
                if not str(settings.api_access.api_key or "").strip():
                    settings.api_access.api_key = secrets.token_urlsafe(32)
                    changed = True
                if not settings.api_access.backend_only_port:
                    settings.api_access.backend_only_port = 18000
                    changed = True
                for proxy in settings.saved_proxies:
                    if not str(proxy.id or "").strip():
                        proxy.id = uuid4().hex
                        changed = True
                    if not str(proxy.name or "").strip():
                        proxy.name = self._next_sequence_name(settings.saved_proxies, proxy.id)
                        changed = True
                for extension in settings.managed_extensions:
                    if not str(extension.id or "").strip():
                        extension.id = uuid4().hex
                        changed = True
                    if not str(extension.name or "").strip():
                        extension.name = Path(extension.file_name or extension.stored_path or extension.id).stem or extension.id
                        changed = True
                if changed:
                    self.save_settings(settings)
                return settings
            except Exception:
                settings = self._default_settings()
                self.save_settings(settings)
                return settings

    def save_settings(self, settings: AppSettings) -> AppSettings:
        with self._lock:
            payload = settings.model_dump(mode="json")
            self._write_json(self.settings_file, payload)
            return settings

    def load_profiles(self) -> list[BrowserProfile]:
        with self._lock:
            return self._load_profiles_unlocked()

    def save_profiles(self, profiles: list[BrowserProfile]) -> list[BrowserProfile]:
        with self._lock:
            return self._save_profiles_unlocked(profiles)

    def upsert_profile(self, profile: BrowserProfile) -> BrowserProfile:
        with self._lock:
            profiles = self._load_profiles_unlocked()
            replaced = False
            for index, item in enumerate(profiles):
                if item.id == profile.id:
                    profiles[index] = profile
                    replaced = True
                    break
            if not replaced:
                profiles.append(profile)
            self._save_profiles_unlocked(profiles)
            return profile

    def delete_profile(self, profile_id: str) -> None:
        with self._lock:
            profiles = [item for item in self._load_profiles_unlocked() if item.id != profile_id]
            self._save_profiles_unlocked(profiles)

    def duplicate_profile(self, profile_id: str) -> BrowserProfile | None:
        with self._lock:
            profiles = self._load_profiles_unlocked()
            source = next((item for item in profiles if item.id == profile_id), None)
            if not source:
                return None
            payload = deepcopy(source.model_dump(mode="json"))
            payload["id"] = uuid4().hex
            payload["name"] = f'{source.name or "未命名配置"} 副本'
            payload["created_at"] = utc_now_iso()
            payload["updated_at"] = payload["created_at"]
            payload["last_used"] = None
            if payload.get("engine") == "chrome":
                payload.setdefault("chrome", {}).setdefault("fingerprint", {})["seed"] = None
            copy_profile = BrowserProfile.model_validate(payload)
            profiles.append(copy_profile)
            self._save_profiles_unlocked(profiles)
            return copy_profile

    def update_profiles(self, updater: Callable[[list[BrowserProfile]], tuple[list[BrowserProfile], T]]) -> T:
        with self._lock:
            profiles = self._load_profiles_unlocked()
            updated_profiles, result = updater(profiles)
            self._save_profiles_unlocked(updated_profiles)
            return result

    def _load_profiles_unlocked(self) -> list[BrowserProfile]:
        raw_items = self._read_json(self.profiles_file, [])
        profiles: list[BrowserProfile] = []
        for item in raw_items if isinstance(raw_items, list) else []:
            try:
                profiles.append(BrowserProfile.model_validate(item))
            except Exception:
                continue
        profiles.sort(key=lambda item: item.created_at)
        return profiles

    def _save_profiles_unlocked(self, profiles: list[BrowserProfile]) -> list[BrowserProfile]:
        profiles = list(profiles)
        payload = [item.model_dump(mode="json") for item in profiles]
        self._write_json(self.profiles_file, payload)
        return profiles

    def _default_settings(self) -> AppSettings:
        chrome_meta = ENGINE_METADATA["chrome"]
        firefox_meta = ENGINE_METADATA["firefox"]
        return AppSettings(
            language="zh-CN",
            theme_mode="system",
            user_data_root=str(DEFAULT_USER_DATA_ROOT),
            chrome=EngineSettings(
                executable_path=chrome_meta["default_executable"],
                installer_url=chrome_meta["installer_url"],
                download_path=str(self.downloads_dir / chrome_meta["download_name"]),
                keep_installer=True,
            ),
            firefox=EngineSettings(
                executable_path=firefox_meta["default_executable"],
                installer_url=firefox_meta["installer_url"],
                download_path=str(self.downloads_dir / firefox_meta["download_name"]),
                keep_installer=True,
            ),
            api_access=ApiAccessSettings(
                enabled=True,
                api_key=secrets.token_urlsafe(32),
                backend_only_port=18000,
            ),
        )

    @staticmethod
    def _next_sequence_name(proxies: list, current_id: str) -> str:
        used_numbers = set()
        for item in proxies:
            if getattr(item, "id", "") == current_id:
                continue
            name = str(getattr(item, "name", "") or "").strip()
            if name.isdigit():
                used_numbers.add(int(name))
        next_number = 1
        while next_number in used_numbers:
            next_number += 1
        return str(next_number)

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.parent / f".{path.name}.{uuid4().hex}.tmp"
        try:
            temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
