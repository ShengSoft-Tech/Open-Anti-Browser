---
phase: 01-backend-cross-platform
reviewed: 2026-07-24T21:31:26Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - .github/workflows/ci-tests.yml
  - backend/config.py
  - backend/runtime_control.py
  - backend/services/synchronizer.py
  - backend/services/window_manager.py
  - requirements.txt
  - tests/test_config_platform.py
  - tests/test_runtime_control_posix.py
  - tests/test_sync_regressions.py
  - tests/test_synchronizer_platform_gate.py
  - tests/test_window_manager_posix.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-24T21:31:26Z
**Depth:** standard
**Files Reviewed:** 10 (in-scope diff against `e36341f^..HEAD`)
**Status:** issues_found

## Summary

This phase's actual diff is much narrower than the full file contents supplied for review: it adds `sys.platform` branching to `backend/config.py` (`_writable_root`, `SYSTEM_*`/`DEFAULT_*` executable paths), wraps all of `backend/services/window_manager.py` in a `if sys.platform == "win32": ... else: <stub raising RuntimeError>` block, adds a platform-conditional `Popen` kwargs branch in `backend/runtime_control.py::start_backend_only`, adds a two-line `sys.platform != "win32"` gate at the top of `BrowserSynchronizer.start`, adds PEP 508 markers to `pywin32`/`ruyipage` in `requirements.txt`, adds a new two-job (`windows-latest`/`macos-latest`) CI workflow, and adds/extends five test files.

I traced every diff hunk against the pre-phase code (not just the final file state) to confirm the Windows branches are byte-identical to before, and I independently reproduced the claimed macOS cross-platform-importability: installed `requirements.txt` in a clean macOS virtualenv and ran `python -m unittest discover -s tests -v` — all 72 tests pass (2 skipped as designed). No behavioral or security regressions were found. The two issues below are robustness/test-fragility gaps worth fixing, not functional blockers.

## Warnings

### WR-01: Packaged build on an unlisted platform silently falls back to the (likely unwritable) project source directory

**File:** `backend/config.py:23-39` (`_writable_root`)
**Issue:** The function only branches on `sys.platform == "win32"` and `sys.platform == "darwin"` inside the `_is_packaged()` (frozen) case. If a frozen build ever runs on any other platform (e.g. Linux, or an unexpected `sys.platform` value), control falls through both inner `if` blocks and reaches the final `return PROJECT_ROOT` — silently returning the (in a frozen/PyInstaller build) resource-extraction directory rather than a real writable, persistent user-data directory. No error is raised, so `DATA_DIR`, `DOWNLOADS_DIR`, `EXTENSIONS_DIR`, `DEFAULT_USER_DATA_ROOT`, and `runtime/backend-only.json` would all silently resolve into a location that may not be writable or may be deleted after the process exits (PyInstaller onefile `_MEIPASS` temp dir), leading to confusing runtime failures (e.g. `PermissionError` deep inside `JsonStorage`) instead of a clear "unsupported platform" error at startup.
**Fix:** Raise explicitly for the unsupported/packaged case instead of falling through:
```python
def _writable_root() -> Path:
    if _is_packaged():
        if sys.platform == "win32":
            ...
        if sys.platform == "darwin":
            ...
        raise RuntimeError(f"不支持在打包模式下运行于平台：{sys.platform}")
    return PROJECT_ROOT
```

### WR-02: New Windows-path test is silently non-representative (and latently flaky) when run on the new macOS CI job

**File:** `tests/test_config_platform.py:103-114` (`test_windows_frozen_writable_root_uses_local_appdata`)
**Issue:** This test patches `sys.executable` to a Windows-style raw string (`r"C:\Program Files\Open-Anti-Browser\Open-Anti-Browser.exe"`) to exercise the `win32` branch of `_writable_root()`. But `pathlib.Path(...)` dispatches to `PosixPath` vs `WindowsPath` based on the **real host OS**, not on the patched `sys.platform` value. On the phase's own new `test-macos` CI job (macOS runner), `Path(r"C:\...")` treats the entire backslash-laden string as one opaque path segment — verified empirically:
```python
>>> Path(r"C:\Program Files\Open-Anti-Browser\Open-Anti-Browser.exe").resolve()
PosixPath('/Users/.../Open-Anti-Browser/C:\\Program Files\\Open-Anti-Browser\\Open-Anti-Browser.exe')
>>> _.parent
PosixPath('/Users/.../Open-Anti-Browser')   # == PROJECT_ROOT, purely by cwd coincidence
```
The test currently passes only because `executable_dir` (now accidentally equal to `PROJECT_ROOT`) doesn't contain a `portable.mode` marker file, so execution falls through to the `LOCALAPPDATA`-based branch that the test actually asserts on. This means: (a) the test is not really validating Windows executable-directory path resolution when it runs on macOS CI — it's exercising an unrelated code path that happens to produce the same final answer; (b) it is latently flaky — if any local/CI checkout ever contains a stray `portable.mode` file at the repo root (the project's own portable-mode feature encourages exactly this kind of marker file), this test would fail on the macOS runner with a confusing, unrelated diff, even though the Windows code path itself is correct.
**Fix:** Either scope this specific assertion to Windows only (matching the existing pattern used in `tests/test_window_manager_posix.py`'s `WindowManagerWindowsBranchTests`):
```python
@unittest.skipUnless(sys.platform == "win32", "Windows 路径解析语义仅在真实 Windows 主机上有意义")
def test_windows_frozen_writable_root_uses_local_appdata(self) -> None:
    ...
```
or construct the expected `executable_dir` using `ntpath`/`PureWindowsPath` semantics explicitly and mock `Path` accordingly so the assertion is host-OS independent rather than accidentally correct.

## Info

### IN-01: Misleading naming for a local variable in `start_backend_only`

**File:** `backend/runtime_control.py:143`
**Issue:** `_POPEN_KWARGS: dict[str, Any] = {}` uses SCREAMING_SNAKE_CASE with a leading underscore — a convention normally reserved for module-level "private constant" bindings — for what is actually a local, per-call, mutable dict built fresh inside the function. This is confusing on read (looks like it might be a shared/global constant).
**Fix:** Rename to a conventional local variable, e.g. `popen_kwargs: dict[str, Any] = {}`.

### IN-02: CLAUDE.md's documented non-Windows test limitation is now stale

**File:** `CLAUDE.md` (测试环境 section — not itself part of this phase's file list, but directly contradicted by it)
**Issue:** CLAUDE.md states: "`backend/browser_manager.py` 顶层导入 `services/window_manager.py`（无条件 `import win32api`），所以凡是导入 `backend.browser_manager`、`backend.main` 或 `launch_app` 的测试在非 Windows 上无法运行。" This phase's `backend/services/window_manager.py` change makes that `import win32api` conditional on `sys.platform == "win32"`, which removes the described limitation. I verified this directly: in a clean macOS virtualenv, `import backend.browser_manager` succeeds and the *entire* test suite (including files that import `backend.browser_manager`/`launch_app`, e.g. `tests/test_sync_regressions.py`, `tests/test_api_docs_content.py`, `tests/test_firefox_extensions_and_selenium.py`, `tests/test_concurrent_profile_storage.py`) now runs and passes on macOS. The doc should be updated in a follow-up so future contributors don't avoid writing/running those tests on macOS under an outdated assumption.
**Fix:** Update the 测试环境 paragraph in CLAUDE.md to reflect that `backend.browser_manager`/`backend.main`/`launch_app` are now importable cross-platform as of this phase (only the Windows-only *runtime* features — window arrangement, browser sync — raise `RuntimeError` at call time on non-Windows).

---

_Reviewed: 2026-07-24T21:31:26Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
