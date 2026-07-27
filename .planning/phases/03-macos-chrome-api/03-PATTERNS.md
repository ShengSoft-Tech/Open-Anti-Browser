# Phase 3: macOS Chrome 启动与能力 API - Pattern Map

**Mapped:** 2026-07-27
**Files analyzed:** 7 (5 modifications + 2 new test files)
**Analogs found:** 7 / 7 (this phase modifies mostly itself — "analog" = the current code in the same file/its neighbor)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `backend/services/network.py` (`kill_process_tree`) | utility (process lifecycle) | event-driven (signal/terminate) | itself (current impl, network.py:839-854) | exact — modify in place |
| `backend/browser_manager.py` (`get_engine_statuses`, `bootstrap`, new `get_platform_capabilities`) | service (facade/aggregator) | CRUD / request-response | itself (current impl, :602-623, :68-74) | exact — modify in place |
| `backend/main.py` (`GET /api/capabilities`) | route/controller | request-response | `GET /api/engines` (main.py:403-405) | exact — same shape (thin delegation to manager) |
| `backend/services/chrome.py` (`launch_chrome_profile`, defensive quarantine hook) | service (process launch) | event-driven (subprocess spawn) | itself (current impl, chrome.py:26-142) | exact — insert hook, don't rewrite |
| `backend/config.py` (`bundled_engine_executable`) | config/utility | request-response (path resolution) | itself (config.py:155-157) | exact — potential landing hook site |
| `tests/test_process_termination_macos.py` (new) | test | unit (mock psutil) | `tests/test_launch_geo_fallback.py` (mock Popen/subprocess pattern) + `tests/test_sync_regressions.py` (mock.patch style, no browser_manager import) | role-match |
| `tests/test_capabilities_api.py` (new) | test | unit (direct method call / route) | `tests/test_launch_geo_fallback.py` (settings fixture builder `_settings()`) | role-match |

## Pattern Assignments

### `backend/services/network.py` — `kill_process_tree` (utility, event-driven)

**Analog:** current implementation, same file, lines 839-854 — this is a **modification**, not a copy-from-elsewhere.

**Current code (to be replaced):**
```python
def kill_process_tree(pid: int) -> None:
    try:
        parent = psutil.Process(pid)
    except psutil.Error:
        return
    children = parent.children(recursive=True)
    for process in reversed(children):
        try:
            process.kill()
        except psutil.Error:
            continue
    try:
        parent.kill()
    except psutil.Error:
        pass
    psutil.wait_procs(children + [parent], timeout=5)
```

**Target pattern (from RESEARCH.md Pattern 1, psutil official `kill_proc_tree` recipe)** — unified cross-platform, no `if sys.platform` branch:
```python
def kill_process_tree(pid: int, grace_period: float = 3.0) -> None:
    try:
        parent = psutil.Process(pid)
    except psutil.Error:
        return
    children = parent.children(recursive=True)
    procs = children + [parent]

    for process in procs:
        try:
            process.terminate()
        except psutil.Error:
            continue

    gone, alive = psutil.wait_procs(procs, timeout=grace_period)

    for process in alive:
        try:
            process.kill()
        except psutil.Error:
            continue
    psutil.wait_procs(alive, timeout=5)
```
Keep the same function signature callers rely on (`kill_process_tree(pid)`); add `grace_period` as a keyword-defaulted param so no call site needs updating. Callers: `backend/browser_manager.py` (`stop_profile`, `_refresh_runtime_sessions` area around :173-283, :831-856) — grep confirms `kill_process_tree` import at browser_manager.py:29 and no other call-site signature dependency beyond `pid`.

**Error handling pattern:** every psutil call wrapped in `try/except psutil.Error: continue/pass` — preserve this exact granularity (per-process, not blanket try/except around the whole tree) so one dead process doesn't abort the sweep for its siblings.

---

### `backend/browser_manager.py` — `get_engine_statuses()` / `bootstrap()` / new `get_platform_capabilities()` (service, CRUD)

**Analog:** current implementations, same file.

**Current `bootstrap()` (lines 68-74):**
```python
def bootstrap(self) -> dict[str, Any]:
    return {
        "settings": self.get_settings().model_dump(mode="json"),
        "profiles": self.list_profiles(),
        "engines": self.get_engine_statuses(),
        "downloads": self.downloads.get_all(),
    }
```
D-01 change: add `"capabilities": self.get_platform_capabilities(),` as a new key — same flat-dict-of-method-calls pattern, no new abstraction needed.

**Current `get_engine_statuses()` (lines 602-623):**
```python
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
```
D-02 note: `installed`/`capability_ok` here mean "kernel path exists on disk" — **do not overload these fields with `available`**. `available` (platform-level support) is a *separate*, new key added to each engine's dict, e.g. `"available": True` for chrome, `"available": sys.platform == "win32"` for firefox — this can be added directly inside this same method's returned dicts, OR sourced from the new `get_platform_capabilities()` and merged in. Either placement is planner's call; the field name/semantics (D-02) are locked.

**New method to add (per RESEARCH.md Pattern 2, place adjacent to `get_engine_statuses()` at :602):**
```python
def get_platform_capabilities(self) -> dict[str, Any]:
    is_windows = sys.platform == "win32"
    window_reason = None if is_windows else "窗口排列仅在 Windows 上可用"
    sync_reason = None if is_windows else "窗口同步仅在 Windows 上可用"
    return {
        "platform": sys.platform,
        "engines": {
            "chrome": {"available": True},
            "firefox": {"available": is_windows},
        },
        "window": {
            "arrange": {"available": is_windows, "reason": window_reason},
            "sync": {"available": is_windows, "reason": sync_reason},
        },
    }
```
Note: `browser_manager.py` currently has no top-level `import sys` (checked lines 1-38) — needs adding to the import block alongside existing stdlib imports (`json`, `random`, `urllib.request`, `secrets`, `shutil`, `threading`, `time`).

**Imports block for reference (lines 1-38):**
```python
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
...
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
```

---

### `backend/main.py` — new `GET /api/capabilities` (route, request-response)

**Analog:** `GET /api/engines` (main.py:403-405) — the adjacent, structurally-identical route:
```python
@app.get("/api/engines")
def get_engines() -> dict:
    return manager.get_engine_statuses()
```
New route follows the exact same one-liner delegation shape, placed adjacent (main.py currently ends its engines section at line 405):
```python
@app.get("/api/capabilities")
def get_capabilities() -> dict:
    return manager.get_platform_capabilities()
```
**Auth pattern:** none — confirmed by reading main.py:79-91: `/api/health`, `/api/bootstrap`, `/api/settings` all have no auth decorator/dependency; this whole `app` (local UI surface, as opposed to `open_api`) is unauthenticated per CLAUDE.md architecture notes. No auth wrapper needed for `/api/capabilities`.

**Error handling pattern:** simple routes like `/api/health`, `/api/bootstrap`, `/api/engines` have **no try/except** — they return dict literals or delegate directly with no expected failure mode. Only routes that parse/validate user input (`update_settings`, `delete_extension`, `start_engine_download`) wrap in try/except and raise `HTTPException`. Since `get_platform_capabilities()` has no failure mode (pure `sys.platform` read), no try/except needed — follow the `/api/engines` no-error-handling precedent, not the mutating-route precedent.

---

### `backend/services/chrome.py` — `launch_chrome_profile` defensive quarantine hook (service, event-driven)

**Analog:** current implementation, same file, lines 26-142 — insertion point only, not a rewrite.

**Current flow (relevant excerpt, lines 26-34):**
```python
def launch_chrome_profile(
    profile: BrowserProfile,
    app_settings: AppSettings,
    user_data_dir: Path,
) -> dict[str, Any]:
    executable_path = bundled_engine_executable("chrome")
    if not executable_path.exists():
        raise FileNotFoundError(f"Chrome 内核不存在：{executable_path}")

    proxy_config = proxy_to_profile_proxy(profile.proxy.model_dump(mode="json"))
    ...
```
**Slot for D-07 defensive xattr strip:** immediately after the `executable_path.exists()` check (line 33), before any proxy/geo work — e.g.:
```python
    executable_path = bundled_engine_executable("chrome")
    if not executable_path.exists():
        raise FileNotFoundError(f"Chrome 内核不存在：{executable_path}")
    if sys.platform == "darwin":
        _strip_quarantine_if_present(executable_path)  # defensive, best-effort, no-op if already clean
    ...
```
Per RESEARCH.md "Don't Hand-Roll" table: implement `_strip_quarantine_if_present` via `subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(path)], ...)`, wrapped in try/except so failure never blocks launch (best-effort only). `chrome.py` currently imports `subprocess` already (line 6) — no new import needed for the xattr call itself, but `sys` is not yet imported (checked lines 1-19) and would need adding if gating by platform.

**Subprocess spawn pattern (lines 118-132) — for reference, unchanged by this phase:**
```python
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
```

---

### `backend/config.py` — `bundled_engine_executable` (config/utility, request-response)

**Current implementation (lines 155-157):**
```python
def bundled_engine_executable(engine: str) -> Path:
    meta = ENGINE_METADATA[str(engine)]
    return Path(meta["default_executable"])
```
This is the single call site if planner chooses **install-time/landing-time** xattr strip (D-07 alternative to launch-path defensive strip) — e.g. wrapping the returned path with a one-time strip when the kernel is first detected as present. Note this function is a pure path lookup with no I/O side effects today; adding a strip call here would change it from read-only to having a side effect, so the planner should weigh this against doing the strip in `chrome.py` at launch time (recommended default per RESEARCH.md D-07, since it's naturally idempotent/no-op-safe there).

**Platform-branch precedent in same file (lines 25-38, for style reference — ternary `if sys.platform ==` pattern used throughout config.py):**
```python
        if sys.platform == "win32":
            executable_dir = Path(sys.executable).resolve().parent
            if os.environ.get("OPEN_ANTI_BROWSER_PORTABLE") == "1":
                return executable_dir
...
        if sys.platform == "darwin":
            # macOS：忽略 portable 标记与环境变量（D-07），固定写用户级 Application Support，
            # 不使用任何基于 sys.executable 的路径推导（Pitfall 4：.app bundle 内部结构不适用）。
            return Path.home() / "Library" / "Application Support" / APP_NAME
```

---

### `tests/test_process_termination_macos.py` (new test file)

**Analog:** `tests/test_sync_regressions.py` (mock.patch style) for the *import discipline* constraint, and `tests/test_launch_geo_fallback.py` (mock Popen/subprocess style) for the *fixture/mock construction* pattern.

**Critical constraint (from CLAUDE.md and CONTEXT.md):** must import only `backend.services.network`, NOT `backend.browser_manager`/`backend.main`, so the test runs on Windows without pywin32.

**Concrete skeleton (from RESEARCH.md Code Examples, verified against actual `kill_process_tree` signature at network.py:839):**
```python
import unittest
from unittest.mock import MagicMock, patch

from backend.services import network


class KillProcessTreeGracefulTests(unittest.TestCase):
    @patch("backend.services.network.psutil.wait_procs")
    @patch("backend.services.network.psutil.Process")
    def test_sends_sigterm_before_sigkill(self, mock_process_cls, mock_wait_procs):
        parent = MagicMock()
        child = MagicMock()
        parent.children.return_value = [child]
        mock_process_cls.return_value = parent
        mock_wait_procs.return_value = ([parent, child], [])

        network.kill_process_tree(1234)

        parent.terminate.assert_called_once()
        child.terminate.assert_called_once()
        parent.kill.assert_not_called()
        child.kill.assert_not_called()

    @patch("backend.services.network.psutil.wait_procs")
    @patch("backend.services.network.psutil.Process")
    def test_sigkill_survivors_after_grace_period(self, mock_process_cls, mock_wait_procs):
        parent = MagicMock()
        mock_process_cls.return_value = parent
        parent.children.return_value = []
        mock_wait_procs.side_effect = [([], [parent]), ([parent], [])]

        network.kill_process_tree(1234)

        parent.terminate.assert_called_once()
        parent.kill.assert_called_once()
```

**Analog import-discipline example (`tests/test_sync_regressions.py`, lines 1-8) — shows the project's mock.patch + minimal-import convention:**
```python
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services import synchronizer
import launch_app
```
(Note: `test_sync_regressions.py` itself imports `launch_app`, which does pull in the full desktop stack — it is NOT itself Windows-safe. The relevant precedent for the NEW test file is its `unittest.mock.patch` usage style, not its import list. Follow `network`-only import discipline instead, per the explicit CLAUDE.md constraint.)

**Analog fixture-construction pattern (`tests/test_launch_geo_fallback.py`, lines 20-38) — shows temp-dir + Mock(pid=...) + multi-patch context-manager style used elsewhere in this test suite:**
```python
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
```
This file (`test_launch_geo_fallback.py`) DOES import `backend.services.chrome`, which is macOS/Windows-safe (no pywin32 pulled in transitively — confirmed only `subprocess`, `os`, `random`, `json` at chrome.py:1-19). If the D-07 quarantine defensive-strip hook is added to `chrome.py`, extend this existing file with a new test case (patch `subprocess.run` for the xattr call) rather than creating a third test file — matches "Wave 0 Gaps" guidance in RESEARCH.md which only calls out two new files.

---

### `tests/test_capabilities_api.py` (new, or new cases in existing file)

**Analog:** no direct FastAPI-route-testing analog exists yet in the current test suite (all 11 existing files test service/model layer directly, not via FastAPI TestClient — confirmed by directory listing: `test_api_docs_content.py`, `test_concurrent_profile_storage.py`, `test_config_platform.py`, `test_firefox_extensions_and_selenium.py`, `test_geo_resolution.py`, `test_launch_geo_fallback.py`, `test_proxy_bypass_domains.py`, `test_runtime_control_posix.py`, `test_sync_regressions.py`, `test_synchronizer_platform_gate.py`, `test_window_manager_posix.py` — none use `TestClient`).

**Recommended approach (per RESEARCH.md Validation Architecture table):** call `manager.get_platform_capabilities()` directly (unittest instantiating `BrowserManager()` or a lighter-weight direct import), rather than introducing FastAPI `TestClient` as a new test infra pattern — this keeps the new test file consistent with the existing "test methods directly" convention and avoids `backend.main`'s heavier import surface (imports `browser_manager`, which is fine per CLAUDE.md but adds no value if the route is a one-line delegation already covered by testing `get_platform_capabilities()` and the `/api/engines` precedent).

**Closest structural analog for module-level fixture style:** `tests/test_config_platform.py` (title suggests it already tests `sys.platform`-gated config.py behavior — same category of platform-conditional-dict assertions needed for capabilities). Use `unittest.mock.patch("sys.platform", "darwin")` / `"win32"` to assert both branches of `get_platform_capabilities()` deterministically without needing to run on both OSes.

---

## Shared Patterns

### Platform-branch idiom
**Source:** `backend/config.py:25`, `:35`, `:86`; `backend/services/window_manager.py:6`
**Apply to:** `get_platform_capabilities()`, chrome.py quarantine hook
```python
if sys.platform == "win32":
    ...
if sys.platform == "darwin":
    ...
```
Project convention is direct `sys.platform ==` string comparison, not a wrapper/enum. Follow this literally rather than introducing an abstraction.

### psutil per-process error swallowing
**Source:** `backend/services/network.py:839-854` (current `kill_process_tree`)
**Apply to:** the rewritten `kill_process_tree`
```python
try:
    process.terminate()  # or .kill()
except psutil.Error:
    continue  # or pass
```
Never let one dead/zombie process's exception abort the loop over the rest of the tree.

### Route delegation (thin controller)
**Source:** `backend/main.py:403-405` (`/api/engines`), `:84-86` (`/api/bootstrap`)
**Apply to:** new `/api/capabilities` route
```python
@app.get("/api/engines")
def get_engines() -> dict:
    return manager.get_engine_statuses()
```
Routes on the local `app` (not `open_api`) are one-liners with no auth, no try/except unless the route mutates state or parses user input.

### Test mock.patch target path convention
**Source:** `tests/test_launch_geo_fallback.py:28-32`, `tests/test_sync_regressions.py`
**Apply to:** both new test files
```python
patch("backend.services.chrome.bundled_engine_executable", ...)
patch("backend.services.network.psutil.wait_procs")
```
Always patch at the *importing module's* namespace (`backend.services.network.psutil.X`), not the source module (`psutil.X`) — matches how `psutil` etc. are imported at module level and referenced unqualified within functions.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| N/A | — | — | This phase is entirely modifications-in-place to existing files plus new test files with strong analogs found; no net-new production module lacks a pattern source. |

## Metadata

**Analog search scope:** `backend/services/network.py`, `backend/browser_manager.py`, `backend/main.py`, `backend/services/chrome.py`, `backend/config.py`, `backend/services/window_manager.py`, `tests/*.py` (all 11 existing test files enumerated)
**Files scanned:** 7 production files (read in full or targeted ranges) + 11 test files (listed, 2 read in detail)
**Pattern extraction date:** 2026-07-27
