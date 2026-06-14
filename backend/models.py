from __future__ import annotations

from datetime import datetime, timezone
import secrets
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProfileEngine = Literal["chrome", "firefox"]
ProxyType = Literal["none", "http", "https", "socks5"]
ModeChoice = Literal["auto", "manual", "random"]
ThemeMode = Literal["system", "light", "dark"]
ProxyBypassMatchMode = Literal["exact", "subdomains"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProxySettings(ModelBase):
    type: ProxyType = "none"
    host: str = ""
    port: int | None = None
    username: str = ""
    password: str = ""


class ProxyBypassRule(ModelBase):
    domain: str = ""
    match_mode: ProxyBypassMatchMode = "subdomains"

    @field_validator("domain", mode="before")
    @classmethod
    def _normalize_domain(cls, value: str) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return ""
        raw = raw.removeprefix("*.").removeprefix(".")
        if "://" in raw:
            from urllib.parse import urlparse

            parsed = urlparse(raw)
            raw = parsed.hostname or ""
        raw = raw.split("/", 1)[0]
        if raw.count(":") == 1 and not raw.startswith("["):
            raw = raw.rsplit(":", 1)[0]
        return raw.strip().strip(".")


class SavedProxy(ProxySettings):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = ""
    remark: str = ""


class StorageSettings(ModelBase):
    root_dir: str = ""


class StartupSettings(ModelBase):
    open_urls: list[str] = Field(default_factory=list)
    window_size: str = ""


class ChromeFingerprintSettings(ModelBase):
    seed: int | None = None
    auto_timezone: bool = True
    language: str = ""
    accept_language: str = ""
    timezone: str = ""
    platform: str = "windows"
    platform_version: str = ""
    brand: str = "Google Chrome"
    brand_version: str = ""
    hardware_concurrency_mode: ModeChoice = "random"
    hardware_concurrency: int | None = None
    disable_spoofing: list[str] = Field(default_factory=list)


class ChromeSettings(ModelBase):
    executable_path: str = ""
    fingerprint: ChromeFingerprintSettings = Field(default_factory=ChromeFingerprintSettings)
    launch_args: list[str] = Field(default_factory=list)
    startup: StartupSettings = Field(default_factory=StartupSettings)
    disabled_global_extension_ids: list[str] = Field(default_factory=list)


class ScreenFingerprintSettings(ModelBase):
    mode: ModeChoice = "auto"
    width: int | None = None
    height: int | None = None


class WebGLFingerprintSettings(ModelBase):
    mode: ModeChoice = "random"
    vendor: str = ""
    renderer: str = ""
    version: str = ""
    glsl_version: str = ""
    unmasked_vendor: str = ""
    unmasked_renderer: str = ""
    max_texture_size: int | None = None
    max_cube_map_texture_size: int | None = None
    max_texture_image_units: int | None = None
    max_vertex_attribs: int | None = None
    aliased_point_size_max: int | None = None
    max_viewport_dim: int | None = None


class WebRTCFingerprintSettings(ModelBase):
    mode: ModeChoice = "random"
    local_ip: str = ""
    public_ip: str = ""


class ExtraFingerprintField(ModelBase):
    key: str = ""
    value: str = ""


class FirefoxFingerprintSettings(ModelBase):
    auto_timezone: bool = True
    language: str = ""
    timezone: str = ""
    font_system: str = "windows"
    screen: ScreenFingerprintSettings = Field(default_factory=ScreenFingerprintSettings)
    webgl: WebGLFingerprintSettings = Field(default_factory=WebGLFingerprintSettings)
    hardware_concurrency_mode: ModeChoice = "random"
    hardware_concurrency: int | None = None
    webrtc: WebRTCFingerprintSettings = Field(default_factory=WebRTCFingerprintSettings)
    load_webrtc_block_extension: bool = False
    extra_fields: list[ExtraFingerprintField] = Field(default_factory=list)


class FirefoxSettings(ModelBase):
    executable_path: str = ""
    fingerprint_file_path: str = ""
    extension_paths: list[str] = Field(default_factory=list)
    launch_args: list[str] = Field(default_factory=list)
    startup: StartupSettings = Field(default_factory=StartupSettings)
    fingerprint: FirefoxFingerprintSettings = Field(default_factory=FirefoxFingerprintSettings)
    disabled_global_extension_ids: list[str] = Field(default_factory=list)


class BrowserProfile(ModelBase):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = ""
    group: str = ""
    remark: str = ""
    engine: ProfileEngine = "chrome"
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    proxy_bypass_rules: list[ProxyBypassRule] = Field(default_factory=list)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    chrome: ChromeSettings = Field(default_factory=ChromeSettings)
    firefox: FirefoxSettings = Field(default_factory=FirefoxSettings)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    last_used: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_proxy_bypass_rules(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        proxy = payload.get("proxy")
        if isinstance(proxy, str):
            if proxy.strip():
                from .services.network import normalize_proxy_config
                config = normalize_proxy_config(proxy.strip())
                if config:
                    payload["proxy"] = {
                        "type": config["scheme"],
                        "host": config["host"] or "",
                        "port": config["port"],
                        "username": config["username"] or "",
                        "password": config["password"] or "",
                    }
            else:
                # 空字符串视为不使用代理，交给默认值（type=none）
                payload.pop("proxy", None)
        current_rules = payload.get("proxy_bypass_rules")
        legacy_domains = payload.get("proxy_bypass_domains")
        if current_rules:
            return payload
        if not legacy_domains:
            return payload
        payload["proxy_bypass_rules"] = [
            {"domain": item, "match_mode": "subdomains"}
            for item in legacy_domains
            if str(item or "").strip()
        ]
        return payload


class EngineSettings(ModelBase):
    executable_path: str
    installer_url: str
    download_path: str
    keep_installer: bool = True


class ApiAccessSettings(ModelBase):
    enabled: bool = True
    api_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    backend_only_port: int = 18000


class ManagedExtension(ModelBase):
    id: str = Field(default_factory=lambda: uuid4().hex)
    engine: ProfileEngine
    name: str = ""
    file_name: str = ""
    stored_path: str = ""
    unpacked_path: str = ""
    enabled: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class AppSettings(ModelBase):
    language: str = "zh-CN"
    theme_mode: ThemeMode = "system"
    user_data_root: str
    chrome: EngineSettings
    firefox: EngineSettings
    api_access: ApiAccessSettings = Field(default_factory=ApiAccessSettings)
    saved_proxies: list[SavedProxy] = Field(default_factory=list)
    managed_extensions: list[ManagedExtension] = Field(default_factory=list)


class RuntimeSession(ModelBase):
    profile_id: str
    engine: ProfileEngine
    pid: int
    launched_at: str = Field(default_factory=utc_now_iso)
    user_data_dir: str
    executable_path: str
    command: list[str]
    remote_debugging_port: int | None = None
    marionette_port: int | None = None
    proxy_bridge_url: str | None = None
    resolved_ip: str | None = None
    resolved_timezone: str | None = None
    resolved_language: str | None = None
