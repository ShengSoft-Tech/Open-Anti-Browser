# Architecture Research: macOS Support Integration

**Domain:** Cross-platform desktop app retrofit (Windows-only → Windows + macOS), Chrome-only on macOS
**Researched:** 2026-07-23
**Confidence:** HIGH for backend/CI integration points (read directly from repo code), MEDIUM for macOS packaging specifics (verified against current PyInstaller docs + macOS Gatekeeper behavior, not yet tested against this repo's actual build)

## Standard Architecture

### System Overview (current, from code)

```
┌──────────────────────────────────────────────────────────────────────┐
│  launch_app.py (entry point)                                         │
│  - main() → backend._g._7("runtime") integrity check                  │
│  - run_desktop(): PySide6 QWebEngineView shell (Qt, win-agnostic)     │
│  - run_backend_only(): headless uvicorn, used by runtime_control.py  │
├──────────────────────────────────────────────────────────────────────┤
│  backend/config.py  — SINGLE SOURCE OF PATH TRUTH                    │
│  RESOURCE_ROOT (frozen: sys._MEIPASS / dev: PROJECT_ROOT)             │
│  APP_ROOT (frozen: LOCALAPPDATA\Open-Anti-Browser / dev: PROJECT_ROOT)│
│  ENGINES_DIR = RESOURCE_ROOT/engines                                 │
│  DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR/chrome/chrome.exe  ← Windows-only literal
├──────────────────────────────────────────────────────────────────────┤
│  backend/browser_manager.py (BrowserManager facade)                  │
│  imports services/window_manager.py UNCONDITIONALLY at module scope  │
│    → window_manager.py does `import win32api/win32con/win32gui/win32process`
│    → this import alone crashes the whole backend on macOS            │
├──────────────────────────────────────────────────────────────────────┤
│  services/chrome.py   services/firefox.py   services/window_manager.py│
│  (launch cmd builder)  (launch cmd builder)  (win32 only, no macOS)   │
├──────────────────────────────────────────────────────────────────────┤
│  backend/runtime_control.py — backend-only child process spawner     │
│  DETACHED_PROCESS = getattr(subprocess,"DETACHED_PROCESS", 0x8)       │
│    fallback literal 0x8 has NO meaning to POSIX Popen — passed        │
│    unconditionally into creationflags= on all platforms today          │
├──────────────────────────────────────────────────────────────────────┤
│  .github/workflows/build-release.yml — windows-latest only            │
│  fetch engines zip (URL from backend.config) → PyInstaller --onedir  │
│  --add-data "engines;engines" (Windows path-list separator ';')       │
│  → Inno Setup → GitHub Release                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (existing, confirmed by reading the files)

| Component | File | Responsibility | macOS impact |
|-----------|------|-----------------|---------------|
| Path resolution | `backend/config.py` | Single source of truth for all paths, engine metadata, install/download URLs | Needs `sys.platform` branch for exe suffix, writable root, and macOS-specific engine metadata |
| Core facade | `backend/browser_manager.py` | Profile CRUD, launch orchestration, imports `services.window_manager` at line 36 (module top) | Top-level `from .services.window_manager import ...` must become conditional/guarded |
| Chrome launcher | `backend/services/chrome.py` | Builds fingerprint-chromium CLI args, `subprocess.Popen(..., creationflags=CREATE_NEW_PROCESS_GROUP, ...)` (line 22, 124) | `CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)` already degrades safely to `0` on POSIX — **no change needed**, this file is already portable |
| Window manager | `backend/services/window_manager.py` | win32-only window enumeration/arrangement, imports `win32api/win32con/win32gui/win32process` unconditionally (lines 6-9) | Entire module is Windows-only; needs a macOS no-op sibling module, selected at import time |
| Backend-only spawner | `backend/runtime_control.py` | Spawns detached `--backend-only` child process | `DETACHED_PROCESS \| CREATE_NEW_PROCESS_GROUP` passed unconditionally to `subprocess.Popen(creationflags=...)` (line 149) — **this will raise `ValueError` on macOS/POSIX** (Popen only accepts `creationflags` on Windows; non-zero value on POSIX raises `ValueError: creationflags is only supported on Windows platforms`) |
| Desktop shell | `launch_app.py` | Qt WebEngine window, calls `_0x2f("runtime")` integrity check at `main()` (line 364) | Framework-agnostic (Qt/PySide6 ships macOS wheels); no blocking issue found, but desktop-only Chromium flags (`QTWEBENGINE_CHROMIUM_FLAGS`) are harmless no-ops on macOS |
| CI/release | `.github/workflows/build-release.yml` | Windows-only job: fetch engines → PyInstaller onedir → Inno Setup → GH Release | Needs a parallel macOS job (see Section 5) |

## Answering the Five Questions

### 1. Exact seams for platform branching

**A. `backend/config.py` — executable paths and default `ENGINES_DIR` layout**

Current Windows-only literals (confirmed):
```python
# config.py:81-86
SYSTEM_CHROME_EXECUTABLE = Path(fr"C:\Users\{USERNAME}\AppData\Local\Chromium\Application\chrome.exe")
SYSTEM_FIREFOX_EXECUTABLE = Path(r"C:\Program Files\Mozilla Firefox\firefox.exe")
DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"
DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox.exe"
```
On macOS, fingerprint-chromium does not produce a bare `chrome` executable — it produces a `.app` bundle (`Chromium.app` per the sibling `../fingerprint-chromium` repo's `flags.macos.gn` referenced in PROJECT.md). The real Mach-O binary lives at `Chromium.app/Contents/MacOS/Chromium`. So the seam is:

```python
# NEW seam in config.py, near line 13 (_is_packaged) — add a platform predicate
IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

# NEW: macOS-specific bundled executable path (replaces the single
# DEFAULT_CHROME_EXECUTABLE literal with a platform branch)
if IS_MACOS:
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
else:
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"
```
`ENGINE_METADATA["chrome"]["bundle_dir"]` (line 120, `str(ENGINES_DIR / "chrome")`) stays the same — it's the *containing* directory either way; only `default_executable` differs. `bundled_engine_executable()` (line 134) needs no change since it just reads `ENGINE_METADATA[engine]["default_executable"]`.

`SYSTEM_CHROME_EXECUTABLE` / `SYSTEM_FIREFOX_EXECUTABLE` are used only as a "system install" fallback hint; on macOS these become e.g. `/Applications/Chromium.app/Contents/MacOS/Chromium` — low priority since macOS scope bundles the kernel in the dmg and never relies on a system install (per PROJECT.md: "内核打包进 dmg（非首启下载）").

Firefox has **no macOS build** (Out of Scope). `DEFAULT_FIREFOX_EXECUTABLE` / `ENGINE_METADATA["firefox"]` can stay as literal Windows paths — they simply won't resolve (`.exists()` → False) on macOS, and `get_engine_statuses()` (`browser_manager.py:602`) already reports `installed`/`capability_ok` per-engine via `.exists()`, which is the exact mechanism the frontend already uses to gray out an engine (`App.vue:432`, `t('engine.needFingerprintBuild')`). This is the reason a real `/api/capabilities` platform gate is still needed in addition — see Q3, because "not installed" and "not supported on this OS" are different UI messages, and window-sync/arrange features have no per-engine `capability_ok` flag today.

**B. `_writable_root()` — `~/Library/Application Support` on frozen macOS**

```python
# config.py:23-34, current
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
```
Two macOS-specific issues to solve here, not just one:
1. `Path(sys.executable).resolve().parent` — on a frozen macOS onedir `.app`, `sys.executable` resolves to `.../Open-Anti-Browser.app/Contents/MacOS/Open-Anti-Browser`, so `executable_dir` is `Contents/MacOS/`. A portable-mode marker file at that path is *inside the read-only, code-signed-in-spirit bundle* — writing there is possible only because we're unsigned, but it's still the wrong semantic location (should never write inside `.app` on macOS; Gatekeeper/notarization-adjacent tooling and future signing would break). Portable mode should be considered **out of scope for macOS** (dmg install to `/Applications` is the only supported flow per PROJECT.md), so the marker-file / `OPEN_ANTI_BROWSER_PORTABLE` branch can simply be skipped when `IS_MACOS`.
2. The actual writable root: add an `elif IS_MACOS:` branch returning `Path.home() / "Library" / "Application Support" / APP_NAME`.

```python
def _writable_root() -> Path:
    if _is_packaged():
        if IS_MACOS:
            return Path.home() / "Library" / "Application Support" / APP_NAME
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
```
Everything downstream (`APP_ROOT`, `DATA_DIR`, `DOWNLOADS_DIR`, `EXTENSIONS_DIR`, `DEFAULT_USER_DATA_ROOT`, `RUNTIME_DIR` in `runtime_control.py:20`) derives from `APP_ROOT` and needs zero further changes — this is exactly why `config.py` is described as "the single source of truth" in CLAUDE.md; one function edit fixes the whole tree.

**C. `_resource_root()` on frozen macOS**

```python
# config.py:17-20, current — already platform-safe as written
def _resource_root() -> Path:
    if _is_packaged():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return PROJECT_ROOT
```
`sys._MEIPASS` exists identically on macOS PyInstaller onedir builds (it's the temp-extraction dir for onefile, or the bundle's Resources-symlinked root for onedir — see Q2). **No platform branch needed here** — this is the one config.py function that Just Works, because PyInstaller normalizes `_MEIPASS` across platforms. Confirm this holds once Q2's `--add-data` colon-vs-semicolon fix is made (the separator, not this function, is what's Windows-specific in the current CI).

**D. `_current_username()` / `BIND_HOST` / `_resolve_bind_host()`**

`os.getlogin()` (config.py:75) and `os.environ.get("USERNAME")` (Windows env var) already have a POSIX-compatible fallback to `os.environ.get("USER")` (line 77) — **no change needed**, already portable. `_resolve_bind_host()` reads `bind-host.txt` next to the executable (`_exe_dir()`); on macOS onedir this is `Contents/MacOS/bind-host.txt`, which is writable-at-install-time only if the installer (dmg) drops it there — for macOS this marker file is unnecessary since there is no Windows-style Inno Setup "choose bind host" install step; default `"127.0.0.1"` is correct and requires no macOS-specific code, just confirm the dmg does not attempt to write into the bundle.

**E. `window_manager.py` conditional import that keeps Windows byte-identical**

The requirement "keeps Windows behavior byte-identical" means: **do not touch `services/window_manager.py`'s Windows code path at all.** The correct seam is a facade/dispatch layer, not conditional imports *inside* the existing file:

```
backend/services/
├── window_manager.py           # UNCHANGED — still unconditionally imports win32api etc.
├── window_manager_macos.py     # NEW — no-op/unsupported stubs, same function signatures
└── window_manager_stub.py      # (optional) shared "unsupported" raiser, or fold into _macos file
```
And in `backend/browser_manager.py:36` — the single import line that currently crashes macOS at module load:
```python
# CURRENT (browser_manager.py:36) — breaks macOS unconditionally
from .services.window_manager import arrange_windows, list_monitors, set_uniform_size, show_windows
```
becomes a conditional import resolved once at module load:
```python
# NEW
import sys as _sys
if _sys.platform == "win32":
    from .services.window_manager import arrange_windows, list_monitors, set_uniform_size, show_windows
else:
    from .services.window_manager_macos import arrange_windows, list_monitors, set_uniform_size, show_windows
```
This satisfies "byte-identical Windows behavior" exactly: on `win32`, the imported names are the literal same functions from the literal same file, unmodified. On macOS, `window_manager_macos.py` provides same-signature functions that return a `{"ok": False, "count": 0, "error": "窗口排列/同步仅支持 Windows"}`-shaped payload (matching the existing return shape of `show_windows`/`set_uniform_size`/`arrange_windows`, e.g. `browser_manager.py:72` `{"ok": True, "count": shown}`) rather than raising, so `browser_manager.py`'s `show_sync_windows`/`uniform_sync_windows`/`arrange_sync_windows` (lines 336-351) don't need try/except changes. `list_monitors()` returns `[]` on macOS.

Same pattern applies to `services/synchronizer.py`'s CDP-based `BrowserSynchronizer` — it is *not* win32-dependent per se (CDP is Chrome-only and cross-platform), but PROJECT.md explicitly puts window sync out of scope for macOS this milestone ("窗口排列/窗口同步在 macOS 禁用"). Rather than editing `synchronizer.py` internals, gate it at the API layer (Q3) so the whole feature is hidden/rejected on macOS without touching the synchronizer's Windows-tested code path at all.

### 2. Where the bundled Chromium.app lives inside the PyInstaller `.app`, and how `ENGINES_DIR` maps to it

PyInstaller macOS onedir builds relocate all *binaries* into `Contents/Frameworks/` and all *data* into `Contents/Resources/`, then **cross-link the two directories with symlinks** so the app sees one unified tree at runtime (this is standard PyInstaller ≥6 behavior, done to satisfy Apple code-signing path rules while preserving the "everything is under one root" assumption most bundled code relies on). `--add-data` on macOS uses colon as the source:dest separator (`source:dest_dir`), not semicolon — **this is a required CI diff**, not optional: the existing Windows job uses `--add-data "engines;engines"` (build-release.yml:83); the macOS job must use `--add-data "engines:engines"` or the build will silently mis-place/ignore the argument.

Because `engines/chrome/Chromium.app` is itself a **nested `.app` bundle** (a directory tree with an `Info.plist`, `Contents/MacOS/Chromium` Mach-O executable, `Contents/Frameworks/*.framework`, etc.) rather than a flat set of files like the Windows `chrome.exe` + DLLs, it is data-as-a-whole-directory from PyInstaller's point of view — treat `engines/` as one `--add-data "engines:engines"` tree exactly like Windows does, and let the nested bundle round-trip as opaque directory content into `Contents/Resources/engines/chrome/Chromium.app/...`. At runtime, `sys._MEIPASS` resolves to `Contents/Resources` (via the cross-link) on onedir macOS builds, so `RESOURCE_ROOT/engines/chrome/Chromium.app/Contents/MacOS/Chromium` is a valid, stable path — **this is exactly what config.py's `IS_MACOS` branch in Q1.A should compute**, no different from how `RESOURCE_ROOT / "engines" / "chrome" / "chrome.exe"` works today on Windows.

Two concrete build-time risks specific to nesting a `.app` inside another `.app`, to flag for the CI/implementation phase (MEDIUM confidence — verify empirically once a macOS build is attempted):
- **Executable bit / symlink preservation**: PyInstaller's data collection must preserve the nested bundle's executable permissions and any internal symlinks (e.g. `Chromium.app/Contents/MacOS/Chromium` mode bits, framework version symlinks). If the local-Mac-built kernel zip is unzipped and copied with a tool that doesn't preserve permissions (e.g. some zip libraries strip the executable bit), the launch will fail with "permission denied" even though the path resolves. Recommend the macOS CI fetch step uses `ditto` (Apple's official archive tool, preserves resource forks/permissions/extended attributes) rather than Python's `zipfile` or generic `unzip`, mirroring how the Windows job uses `Expand-Archive` (PowerShell-native, no permission-bit concept on Windows so this wasn't a problem there).
- **Ad-hoc signing side effects**: PyInstaller ad-hoc-signs the final top-level `.app`'s own Mach-O binaries by default on macOS (a `codesign --sign -` pass). This targets the outer bundle's own executable and collected shared libraries — the nested `Chromium.app`'s own (already-signed-or-unsigned, per the local Mac build) binaries are unlikely to be re-signed by PyInstaller since they sit inside a foreign bundle at a data path, not a PyInstaller-collected binary path — but this should be explicitly verified during the first macOS CI run since a broken inner signature silently produces a Gatekeeper "damaged and can't be opened" error at first-launch time, which is easy to misattribute to something else.

`ENGINES_DIR` mapping summary (both platforms use the identical `RESOURCE_ROOT / "engines"` formula in `config.py:44` — **no change needed to that line itself**, only to what's *under* it and how the executable path is computed per-platform, per Q1.A):

| Platform | `ENGINES_DIR` | `bundled_engine_executable("chrome")` |
|---|---|---|
| Windows (unchanged) | `<install>/engines` | `engines/chrome/chrome.exe` |
| macOS (new) | `<App>.app/Contents/Resources/engines` (via `_MEIPASS` cross-link) | `engines/chrome/Chromium.app/Contents/MacOS/Chromium` |

### 3. How the frontend/API should expose platform capabilities

Add a new, additive-only endpoint rather than overloading `/api/bootstrap` or `/api/engines` (both of which report per-*engine* install status, not per-*OS* feature availability — conflating the two would make `get_engine_statuses()` do double duty and complicate the Firefox-not-installed-vs-Firefox-not-supported distinction called out in Q1.A):

- **New file:** none required — add directly to `backend/main.py` near the existing `@app.get("/api/engines")` (main.py:403) and `manager.get_engine_statuses()` call site in `backend/browser_manager.py`.
- **New endpoint:** `GET /api/capabilities` → new `BrowserManager.get_platform_capabilities()` method in `browser_manager.py`, something like:
```python
def get_platform_capabilities(self) -> dict[str, Any]:
    return {
        "platform": sys.platform,          # "win32" | "darwin"
        "supports_firefox": sys.platform == "win32",
        "supports_window_sync": sys.platform == "win32",
        "supports_window_arrange": sys.platform == "win32",
    }
```
  This mirrors the existing thin-facade pattern already used for `get_engine_statuses()` (`browser_manager.py:602`) and `get_synchronizer_status()` (`browser_manager.py:312`) — no new architectural pattern introduced, just a new read-only capability query alongside them.
- **Frontend:** add `capabilities` to the `bootstrap()` payload (`browser_manager.py:68-74`, `main.py:84-86`) so `frontend/src/stores/profile.js` (`bootstrap()` at line 180-186, which already destructures `data.engines`) picks it up in the same round-trip with zero extra network calls, then gate:
  - `App.vue`'s Firefox engine tag (lines 73-74, 432, 439 — currently keyed only on `capability_ok`) to also hide/disable when `!capabilities.supports_firefox`, with a distinct i18n string (e.g. `engine.macOSUnsupported`) instead of reusing `engine.needFingerprintBuild` (which implies "just build it," misleading on macOS where it's structurally unsupported).
  - Window sync / arrange UI controls (wherever they're rendered — same `App.vue` region as the engine tags, and any sync-specific view/component under `frontend/src/`) behind `capabilities.supports_window_sync`.
  - This is additive to `i18n/zh-CN.js` and `i18n/en-US.js` per CLAUDE.md's existing convention ("新增用户可见文案必须同时更新...").
- This keeps the *backend* the single source of truth for "what can this OS do," consistent with `config.py` already being the single source of truth for "where do things live" — the frontend never needs its own `navigator.platform`/user-agent sniffing, avoiding a second, driftable source of platform truth.

### 4. What the macOS CI job mirrors vs. diverges from the Windows job

Reading `.github/workflows/build-release.yml` job-by-job:

| Step | Windows (existing) | macOS (new) — mirrors | macOS (new) — diverges |
|---|---|---|---|
| Runner | `windows-latest` | — | New: matrix `[macos-14 (arm64), macos-13 (x64)]` — GitHub-hosted `macos-14`+ runners are Apple Silicon; `macos-13` is the last Intel-hosted runner generation. Two separate matrix legs produce two separate dmgs, matching PROJECT.md's "arm64 + x64 分开构建、分开出 dmg" decision (no `universal2`) |
| Python/Node setup | `actions/setup-python@v5`, `actions/setup-node@v4` | Identical action, identical versions — no divergence | none |
| `pip install -r requirements.txt` | same | same, **conditional on `pywin32` being marked `sys_platform == 'win32'`** in requirements.txt (currently unconditional at requirements.txt:14 — this is a prerequisite fix, not CI-only; see build order below) | none once requirements.txt is fixed |
| Frontend build | `npm install && npm run build` (also runs `backend._g` integrity check via pre/postbuild hooks per CLAUDE.md) | identical steps | none — integrity check is platform-agnostic Python, runs the same |
| Engine fetch | PowerShell function `Fetch-Engine`, `curl.exe`, `Expand-Archive`, reads `CHROME_ENGINE_ZIP_URL` from `backend.config` (build-release.yml:44-65) | **Same single-source-of-truth pattern**: `python -c "from backend.config import CHROME_ENGINE_ZIP_URL; print(...)"` — mirrors exactly, per PROJECT.md's explicit instruction ("macOS job 沿用此模式") | Needs a **new** `CHROME_ENGINE_ZIP_URL_MACOS_ARM64` / `..._X64` (or a platform-keyed dict) in `config.py`, since the existing single `CHROME_ENGINE_ZIP_URL` constant is Windows-x64-specific; extraction uses `ditto` (permission/xattr-preserving) instead of `Expand-Archive`, written as a bash step, not PowerShell; only Chrome is fetched (no Firefox fetch step at all on macOS, since Firefox is Out of Scope) |
| PyInstaller | `--onedir --windowed --add-data "frontend/dist;frontend/dist" --add-data "assets;assets" --add-data "engines;engines"` + Windows-only hidden-imports (`ruyipage`, `websockets.legacy*`) | `--onedir --windowed` same intent | **Separator changes `;` → `:`** for all `--add-data` args (see Q2); **drop** `--hidden-import "ruyipage"` (Firefox-only, not installed on macOS since `ruyipage` is a `pywin32`-adjacent Windows package per requirements.txt context) and re-verify `--icon` uses a macOS `.icns` rather than `.ico` (`assets/app.ico` → need an `assets/app.icns`, new asset) |
| Installer/packaging | `choco install innosetup`, `ISCC.exe /DMyAppVersion=... .github/installer.iss` → `installer_out/*.exe` | conceptually mirrors "package the onedir output into a distributable" | **Entirely different toolchain**: macOS uses `hdiutil create` (built into every macOS runner, no install step) or a small wrapper like `create-dmg` to wrap the `.app` into a `.dmg`; no `.iss` script — needs a new, much smaller packaging step/script (e.g. `.github/build-dmg.sh` or inline `hdiutil` calls), not a port of `installer.iss` |
| Artifact naming | `Open-Anti-Browser-Setup.exe` | same `actions/upload-artifact@v4` + `softprops/action-gh-release@v2` pattern | Two artifacts per release: `Open-Anti-Browser-arm64.dmg` and `Open-Anti-Browser-x64.dmg` (matrix-produced, both attached via `files:` glob in the same release step, or two separate release-upload steps if matrix jobs can't share one release step cleanly — confirm `action-gh-release` supports matrix-fan-in via `if: always()` + artifact download, or just let each matrix leg upload directly since `softprops/action-gh-release@v2` appends rather than replaces release assets by default) |
| Trigger | `push: tags: v*` / `workflow_dispatch` | same trigger block, shared or duplicated at file top | Could be the **same workflow file with a second `build-macos` job** (recommended — keeps the "on: push tags" trigger single-sourced) or a fully separate `.github/workflows/build-release-macos.yml`. Given CLAUDE.md's emphasis on single-source-of-truth patterns already established for `CHROME_ENGINE_ZIP_URL`, prefer **one workflow file, two jobs** (`build-windows`, `build-macos` with its own `strategy.matrix`), not a second file, to avoid trigger/version-string logic drifting between two files |

**Unsigned distribution note (real gotcha, not just a CI checkbox):** per the quarantine research above, macOS applies `com.apple.quarantine` recursively to everything inside a downloaded dmg's `.app`, and a single right-click-"Open" on the top-level `.app` only registers a SystemPolicy exception for *that specific bundle path* — it does **not** clear the quarantine xattr on nested executables like the inner `Chromium.app/Contents/MacOS/Chromium`, which is launched directly via `subprocess.Popen` (bypassing Finder/`open`, so it never gets its own "right-click" moment). This means "right-click open once" (the release-notes plan per PROJECT.md's Out of Scope section) **may not be sufficient** for the bundled Chromium kernel specifically. The release notes should instruct users to run `xattr -cr /Applications/Open-Anti-Browser.app` (recursive quarantine strip) after installing, not merely "right-click → Open," or the first `start_profile()` call will fail to launch the inner Chromium binary with an opaque Gatekeeper rejection that never surfaces as a Python exception (the OS kills the process before or during exec).

### 5. Suggested build order (Windows stays green at every step)

Ordered so every intermediate commit still produces a working, unmodified Windows build (verifiable via the existing Windows CI job untouched until the very last step):

1. **`requirements.txt`** — mark `pywin32>=308; sys_platform == "win32"` and `ruyipage>=1.0.0; sys_platform == "win32"` with environment markers. Zero behavior change on Windows; makes `pip install -r requirements.txt` succeed on macOS for the first time. This is a pure prerequisite and unblocks everything else (including running Python tests locally on the dev's Mac, per CLAUDE.md's existing test-environment caveat about `pywin32`).
2. **`backend/config.py`** — add `IS_MACOS`/`IS_WINDOWS` predicates and the `_writable_root()` / `DEFAULT_CHROME_EXECUTABLE` platform branches (Q1.A, Q1.B). Windows branch is the untouched `else`, so behavior is byte-identical on `win32`.
3. **`backend/services/window_manager_macos.py`** (new file) + the conditional-import edit in `backend/browser_manager.py:36` (Q1.E). This is the change that actually lets the backend *import* on macOS at all today; sequence it after config.py since `window_manager_macos.py`'s stubs don't need config, but logically this is the "unblock macOS boot" milestone.
4. **`backend/runtime_control.py`** — guard `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (line 149) behind `if sys.platform == "win32": kwargs["creationflags"] = ...` (both constants already default to `0` via `getattr` fallback on line 18-19, but passing `creationflags=0` explicitly to `Popen` on POSIX still raises `ValueError` per Python's subprocess docs — the *keyword itself* must be omitted on non-Windows, not just zeroed). Test: `python -m unittest tests.test_sync_regressions` equivalent for backend-only mode continues to pass unmodified on Windows.
5. **`backend/main.py` + `browser_manager.py`** — add `get_platform_capabilities()` + `/api/capabilities` (Q3), additive to `bootstrap()`. Zero risk to Windows since it's a pure addition.
6. **Frontend** — consume `capabilities` in `stores/profile.js` bootstrap, gate Firefox tag / window-sync UI in `App.vue`, add i18n strings. Windows UI unaffected since `capabilities.supports_firefox === true` there.
7. **`.github/workflows/build-release.yml`** — add the new `CHROME_ENGINE_ZIP_URL_MACOS_*` constants to `config.py` first (small addendum to step 2, or its own commit), then add the `build-macos` job with its own matrix, `ditto`-based engine fetch, `--add-data ...:...` PyInstaller invocation, and `hdiutil`/`create-dmg` packaging step. Since this is an **additive new job** in the same workflow file (not an edit to the existing `build` job), the existing Windows job's YAML is untouched — verify by diffing the PR against only additions, no deletions/edits inside the current `build:` job block.
8. **Local macOS kernel build** (out of this repo's CI, per PROJECT.md) — build arm64 + x64 `Chromium.app` from `../fingerprint-chromium`, upload to the `kernel-149.0.7827.114` GitHub release as new assets, matching the existing kernel-release single-source-of-truth pattern `config.py` already uses for Windows.
9. **Release notes** — document the `xattr -cr` unquarantine step (Q4 gotcha), not just "right-click open."

This order front-loads the changes with the highest "does the backend even start" risk (steps 1-4) before the lower-risk additive changes (steps 5-9), and defers all CI/packaging work (which has no way to be verified without an actual macOS runner run) to the end, after the Python-level logic has already been exercised via local `python -m unittest discover -s tests` runs on a Mac dev machine per CLAUDE.md's test-environment notes.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Editing `window_manager.py` in place with `if sys.platform` branches inside its functions
**What people do:** Add `if sys.platform == "win32": ... else: return {...}` inside each of `list_monitors`/`show_windows`/`set_uniform_size`/`arrange_windows`.
**Why it's wrong:** The module still does `import win32api` etc. at module scope (lines 6-9), so it crashes on import on macOS regardless of what the function bodies do — the crash happens before any function is ever called. It also violates "keeps Windows behavior byte-identical" less cleanly than a separate file, since every future win32 tweak now has to thread through platform-neutral scaffolding.
**Instead:** New sibling module (`window_manager_macos.py`) + conditional import at the single `browser_manager.py:36` call site, per Q1.E.

### Anti-Pattern 2: Making `/api/engines`'/`get_engine_statuses()` the platform gate for Firefox
**What people do:** Reuse `capability_ok` (already `False` when the exe is missing) to also mean "not supported on this OS."
**Why it's wrong:** Conflates two different failure modes with two different remediations — "download the engine" vs. "this OS can never run this engine" — and the frontend already has a specific string (`engine.needFingerprintBuild`) tied to the former that would be actively misleading for the latter.
**Instead:** New, separate `/api/capabilities` endpoint (Q3) as the single source of platform truth, independent of per-engine install state.

### Anti-Pattern 3: Building a macOS `universal2` binary "since PyInstaller supports it"
**What people do:** Since PyInstaller can build `universal2` PyInstaller apps, try to bundle both arm64 and x64 `Chromium.app` kernels into one universal app to simplify distribution.
**Why it's wrong:** Explicitly out of scope per PROJECT.md ("universal binary（单包双架构）— Chromium universal 构建复杂，采用 arm64/x64 分开出包") — the underlying Chromium kernel build itself isn't universal, only the wrapper Python app could be, which would still need two separately-bundled kernels selected at runtime, adding complexity for no shipped benefit this milestone.
**Instead:** Two full separate PyInstaller builds (one per matrix leg), each with its own single-arch kernel bundled, each producing its own dmg.

## Integration Points

### Internal Boundaries (new/modified components, explicit)

| Boundary | File | Status | Notes |
|----------|------|--------|-------|
| Path resolution | `backend/config.py` | **Modified** | Add `IS_MACOS`/`IS_WINDOWS`, branch `_writable_root()`, branch `DEFAULT_CHROME_EXECUTABLE`, add macOS kernel zip URL constant(s) |
| Window manager (Windows) | `backend/services/window_manager.py` | **Unmodified** | Must stay byte-identical per requirement |
| Window manager (macOS) | `backend/services/window_manager_macos.py` | **New** | Same function signatures, no-op/"unsupported" return payloads matching existing shape |
| Core facade import | `backend/browser_manager.py` line 36 | **Modified** | Conditional import based on `sys.platform` |
| Chrome launcher | `backend/services/chrome.py` | **Unmodified** | Already portable (`getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)`) |
| Backend-only spawner | `backend/runtime_control.py` line 149 | **Modified** | Must not pass `creationflags` kwarg at all on non-Windows |
| Capabilities API | `backend/main.py` (new route near line 403), `backend/browser_manager.py` (new method) | **New** | `GET /api/capabilities`, folded into `bootstrap()` |
| Frontend capability gating | `frontend/src/stores/profile.js`, `frontend/src/App.vue`, `frontend/src/i18n/zh-CN.js`, `frontend/src/i18n/en-US.js` | **Modified** | Consume `capabilities`, hide Firefox tag + window-sync UI on macOS |
| CI | `.github/workflows/build-release.yml` | **Modified (additive job)** | New `build-macos` job with matrix `[arm64, x64]`, existing `build` (Windows) job untouched |
| Dependency markers | `requirements.txt` | **Modified** | `pywin32`, `ruyipage` gain `sys_platform == "win32"` markers |
| Kernel assets | `../fingerprint-chromium` (sibling repo, out of this repo) + `kernel-149.0.7827.114` GitHub release | **New assets** | Local Mac build, uploaded manually, mirrors existing Windows kernel-release pattern |
| dmg packaging | `.github/build-dmg.sh` (or inline workflow step) | **New** | Replaces Inno Setup's role for macOS only |
| macOS icon asset | `assets/app.icns` | **New** | PyInstaller `--icon` on macOS requires `.icns`, not the existing `.ico` |

## Sources

- [PyInstaller: Using PyInstaller (stable docs) — macOS bundle structure, `--add-data` syntax](https://pyinstaller.org/en/stable/usage.html)
- [PyInstaller changelog — Contents/Frameworks vs Contents/Resources cross-linking on macOS onedir builds](https://pyinstaller.org/en/v6.0.0/CHANGES.html)
- [Handling macOS Gatekeeper as an unsigned indie dev — quarantine xattr / recursive strip](https://dev.to/hiyoyok/handling-macos-gatekeeper-as-an-unsigned-indie-dev-the-xattr-struggle-1028)
- [Eclectic Light Co. — Quarantine and the quarantine flag (per-bundle SystemPolicy exception scope)](https://eclecticlight.co/2020/10/29/quarantine-and-the-quarantine-flag/)
- Direct reading of this repository: `backend/config.py`, `backend/browser_manager.py`, `backend/runtime_control.py`, `backend/services/chrome.py`, `backend/services/window_manager.py`, `launch_app.py`, `backend/main.py`, `requirements.txt`, `.github/workflows/build-release.yml`, `.planning/PROJECT.md` (HIGH confidence — line numbers cited throughout are from the current repo state as of 2026-07-23)

---
*Architecture research for: macOS support integration (Open-Anti-Browser v0.2 milestone)*
*Researched: 2026-07-23*
