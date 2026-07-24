---
phase: 01-backend-cross-platform
verified: 2026-07-24T22:10:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 01: Backend Cross-Platform Verification Report

**Phase Goal:** 后端在 macOS 上可以正常安装依赖、导入并启动(含纯后端模式),路径全部解析到 macOS 约定位置,同时 Windows 现行为字节级不变
**Verified:** 2026-07-24T22:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | macOS `pip install -r requirements.txt` 成功,不因 pywin32 等报错 | ✓ VERIFIED | `requirements.txt:14-15` carries `; sys_platform == "win32"` markers. Live run on macOS venv: `pip install --dry-run -r requirements.txt` → `Ignoring pywin32... Ignoring ruyipage...` |
| 2 | 后端在 macOS 可正常导入与启动;窗口排列 API 返回「仅 Windows 支持」错误 | ✓ VERIFIED | Live run: `python -c "import backend.main"` → `import-ok`. `backend/services/window_manager.py` wraps entire win32 implementation behind `if sys.platform == "win32":`; non-Windows `else:` branch exports identically-named/signed `list_monitors`/`show_windows`/`set_uniform_size`/`arrange_windows`, each raising `RuntimeError("窗口排列仅在 Windows 上可用")`. `tests/test_window_manager_posix.py` (6 tests, all pass) locks this in, including a concurrency backstop test. `backend/services/synchronizer.py:1395-1396` adds a matching gate (`RuntimeError("窗口同步仅在 Windows 上可用")`) at the top of `BrowserSynchronizer.start`, before any argument validation — closing the sync-API half of XPLAT-02. `tests/test_synchronizer_platform_gate.py` (3 tests, all pass) confirms gate precedes validation and win32 path is unaffected. `backend/main.py`'s existing `try/except → HTTPException(400)` wrapping (all synchronizer/window-arrangement routes) means these RuntimeErrors surface as 400s with no code changes needed to main.py (confirmed zero diff). |
| 3 | macOS 冻结态数据写入 `~/Library/Application Support/Open-Anti-Browser/`,Chrome 路径解析到 `Chromium.app/Contents/MacOS/Chromium` | ✓ VERIFIED | `backend/config.py:35-38` (`_writable_root`, darwin branch) returns `Path.home()/"Library"/"Application Support"/APP_NAME` unconditionally (portable markers ignored, D-07). `backend/config.py:86-92` locks `DEFAULT_CHROME_EXECUTABLE` to `ENGINES_DIR/chrome/Chromium.app/Contents/MacOS/Chromium`. `ENGINE_METADATA` retains both `chrome` and `firefox` keys with full field sets on macOS. `tests/test_config_platform.py` (8 tests, all pass) asserts all of the above plus a Pitfall-4 guard (darwin branch never uses `sys.executable`). |
| 4 | `--backend-only` 可在 macOS 派生、检活、停止;creationflags 平台条件化 | ✓ VERIFIED | `backend/runtime_control.py:143-147` builds `_POPEN_KWARGS` conditionally: POSIX → `start_new_session=True` (no creationflags), win32 → `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (unchanged value). `tests/test_runtime_control_posix.py` (3 tests, all pass) locks in both branches via mocked `subprocess.Popen`. **Live end-to-end integration run on this machine** (not just mocked): `start_backend_only()` → PID 20007 spawned, `psutil.Process(pid).is_running()` → `True`, `stop_backend_only()` → final `running: False`. This is a genuine behavioral proof of the state transition (spawn → alive → terminated), not just presence/wiring. |
| 5 | Windows 分支行为与既有 unittest 套件字节级不变 | ✓ VERIFIED | `git diff --ignore-all-space 65226da..HEAD -- backend/services/window_manager.py` shows only indentation/blank-line changes inside the `if sys.platform == "win32":` block — zero content diff. Same check on `backend/config.py` confirms the Windows executable-path constants are a verbatim migration into the `else:` branch. `backend/services/synchronizer.py` diff is exactly `+import sys` plus the 2-line gate inserted *before* all existing win32 logic — the CDP/Marionette forwarding path is untouched. `backend/browser_manager.py`, `backend/services/chrome.py`, `backend/services/firefox.py`, `backend/main.py` all show **zero diff** for the whole phase (`git diff --stat 65226da..HEAD`), confirming the prohibited-scope items (no new platform judgment in browser_manager.py/main.py, no changes to chrome.py/firefox.py creationflags) were honored. Full regression suite run live on macOS: 72 tests, 0 failures, 2 expected skips (1 Windows-only test, 1 file-existence guard for a gitignored packaging asset) — matches SUMMARY's claimed count exactly. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | PEP 508 markers on pywin32/ruyipage | ✓ VERIFIED | Lines 14-15 carry `; sys_platform == "win32"`, versions unchanged |
| `backend/services/window_manager.py` | Conditional import + macOS stubs | ✓ VERIFIED | `if sys.platform == "win32": ... else: ...` with 4 identically-signed stub functions |
| `backend/runtime_control.py` | Platform-conditional Popen kwargs | ✓ VERIFIED | `_POPEN_KWARGS` dict built conditionally before `Popen(**_POPEN_KWARGS, ...)` |
| `backend/config.py` | Platform-aware path constants | ✓ VERIFIED | `_writable_root` darwin branch + platform-conditional `SYSTEM_*`/`DEFAULT_*` executable constants |
| `backend/services/synchronizer.py` | Non-win32 gate in `BrowserSynchronizer.start` | ✓ VERIFIED | Gate is first executable statement of `start`, before all validation |
| `.github/workflows/ci-tests.yml` | Dual-runner (windows-latest/macos-latest) CI test workflow | ✓ VERIFIED | File exists, `windows-latest`/`macos-latest`/`unittest`/`pull_request` all present; `build-release.yml` confirmed untouched (`git status` clean, zero diff since before phase 1) |
| `tests/test_window_manager_posix.py` | New test file | ✓ VERIFIED | 6 tests (5 active + 1 win32-skip), all pass on macOS |
| `tests/test_runtime_control_posix.py` | New test file | ✓ VERIFIED | 3 tests, all pass |
| `tests/test_config_platform.py` | New test file | ✓ VERIFIED | 8 tests, all pass |
| `tests/test_synchronizer_platform_gate.py` | New test file | ✓ VERIFIED | 3 tests, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `browser_manager.py` named import | `window_manager.py` 4 stub functions | Named import at module load | ✓ WIRED | `browser_manager.py` has zero diff for the phase; `import backend.main` succeeds live, proving the named import resolves against the new stub functions without `ImportError` |
| `launch_app.main → run_backend_only` | `runtime_control.start_backend_only` Popen call | Function call | ✓ WIRED | Live integration run confirms spawn→alive→stop chain works end-to-end |
| `/api/synchronizer/start` route | `BrowserSynchronizer.start` | `browser_manager.start_synchronizer` → `self.synchronizer.start(...)` | ✓ WIRED | `main.py` try/except → `HTTPException(400)` wrapping confirmed unchanged (zero diff); RuntimeError from gate propagates automatically |
| `ENGINE_METADATA` | `SYSTEM_*`/`DEFAULT_*_EXECUTABLE` constants | Dict construction referencing platform-conditional constants | ✓ WIRED | Dict construction code itself has zero diff; only referenced constant values vary by platform (confirmed via `test_macos_engine_metadata_contains_chrome_and_firefox`) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| macOS pip skips Windows-only deps | `pip install --dry-run -r requirements.txt` | `Ignoring pywin32... Ignoring ruyipage...` | ✓ PASS |
| macOS import of backend.main | `python -c "import backend.main"` | `import-ok`, exit 0 | ✓ PASS |
| `--backend-only` spawn/alive/stop (state transition) | `runtime_control.start_backend_only()` → `psutil.Process(pid).is_running()` → `runtime_control.stop_backend_only()` | spawn PID 20007, alive `True`, final `running: False` | ✓ PASS |
| Full regression suite (single run) | `python -m unittest discover -s tests -v` | `Ran 72 tests ... OK (skipped=2)` | ✓ PASS |
| 4 new platform-branch test files | `python -m unittest tests.test_window_manager_posix tests.test_runtime_control_posix tests.test_config_platform tests.test_synchronizer_platform_gate -v` | `Ran 21 tests ... OK (skipped=1)` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| XPLAT-01 | 01-01, 01-04 | macOS `pip install` 成功,跳过 pywin32/ruyipage | ✓ SATISFIED | Live dry-run + real venv install confirmed |
| XPLAT-02 | 01-01, 01-03, 01-04 | 后端在 macOS 可导入与启动;窗口排列/同步 API 返回「仅 Windows」错误 | ✓ SATISFIED | `import backend.main` succeeds; both window_manager stubs and synchronizer gate confirmed live and via tests |
| XPLAT-03 | 01-02, 01-04 | config.py 平台分支;冻结态可写根/Chrome 路径解析正确 | ✓ SATISFIED | Unit tests + source inspection confirm exact target paths |
| XPLAT-04 | 01-01, 01-04 | `--backend-only` 在 macOS 派生/检活/停止;creationflags 平台条件化 | ✓ SATISFIED | Live end-to-end spawn/alive/stop run on this machine |

No orphaned requirements: REQUIREMENTS.md maps only XPLAT-01 through XPLAT-04 to Phase 1, and all four are claimed and satisfied across the four plans.

### Anti-Patterns Found

No blocker or warning-level anti-patterns (TBD/FIXME/XXX/TODO/HACK/placeholder/stub returns) found in any file modified by this phase.

Two **non-blocking** code-review findings from `01-REVIEW.md` (already produced during execution, cross-checked here and confirmed still open, not re-fixed):
- **WR-01** (info-level for this phase's scope): `config.py::_writable_root` silently falls through to `PROJECT_ROOT` if a frozen build somehow runs on a platform that is neither `win32` nor `darwin`. Out of scope for this milestone (only Windows + macOS are supported platforms per PROJECT.md/REQUIREMENTS.md); does not affect any of the 5 required truths.
- **WR-02** (info-level): `tests/test_config_platform.py::test_windows_frozen_writable_root_uses_local_appdata` exercises `Path(r"C:\...")` on a POSIX host, which resolves via `PosixPath` semantics rather than true Windows path semantics, so the assertion accidentally passes for a reason unrelated to what it claims to test. This is a **test-quality gap, not a functional gap** — the actual Windows-branch source code is separately proven byte-identical via `git diff --ignore-all-space` against the pre-phase state, and the real Windows CI runner (`windows-latest` job in `ci-tests.yml`) will exercise this code path with genuine `WindowsPath` semantics. Does not block phase-goal achievement; worth fixing in a follow-up but not gating.

### Human Verification Required

None. This phase is entirely backend infrastructure (dependency installation, module import, path resolution, process spawn/stop, platform gating) with fully programmatic, deterministic verification — no UI, visual, real-time, or external-service-dependent behavior requiring human judgment.

### Gaps Summary

No gaps found. All 5 roadmap success criteria are directly verified against the codebase (not just SUMMARY claims): live commands were re-run in this verification session (pip dry-run, `import backend.main`, full 72-test regression suite, and a genuine end-to-end `--backend-only` spawn→alive→stop cycle), and Windows-branch byte-identity was independently confirmed via whitespace-insensitive diffs against the pre-phase commit, not by trusting the SUMMARY's assertion. Prohibitions declared in all four plans' frontmatter (no changes to browser_manager.py/chrome.py/firefox.py/main.py, no requirements-build.txt split, no preexec_fn, no macOS kernel URLs added) were independently confirmed via `git diff --stat` showing zero diffs on the named files.

---

_Verified: 2026-07-24T22:10:00Z_
_Verifier: Claude (gsd-verifier)_
