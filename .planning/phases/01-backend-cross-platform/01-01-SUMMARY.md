---
phase: 01-backend-cross-platform
plan: 01
subsystem: infra
tags: [python, cross-platform, pep508, subprocess, packaging]

# Dependency graph
requires: []
provides:
  - "requirements.txt with PEP 508 sys_platform == \"win32\" markers on pywin32/ruyipage"
  - "backend/services/window_manager.py conditional import + macOS stub functions (list_monitors/show_windows/set_uniform_size/arrange_windows all raise RuntimeError on non-Windows)"
  - "backend/runtime_control.py platform-conditional Popen kwargs (start_new_session on POSIX, creationflags on win32) for --backend-only spawn"
affects: [01-02, 01-03, 01-04, config.py cross-platform work, synchronizer platform gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.platform == \"win32\" top-level if/else gating a whole module's Windows-only implementation, non-Windows branch exports identically-named/signed stub functions that raise RuntimeError"
    - "Local _POPEN_KWARGS dict built conditionally right before subprocess.Popen(**_POPEN_KWARGS, ...) call, keeping the Windows call site byte-identical minus the flag"

key-files:
  created:
    - tests/test_window_manager_posix.py
    - tests/test_runtime_control_posix.py
    - .planning/phases/01-backend-cross-platform/deferred-items.md
  modified:
    - requirements.txt
    - backend/services/window_manager.py
    - backend/runtime_control.py

key-decisions:
  - "D-01: window_manager.py Windows branch code moved verbatim (indentation-only diff) into if sys.platform == \"win32\": block; browser_manager.py needed zero changes since stub functions share exact name/signature"
  - "D-09: pywin32/ruyipage got '; sys_platform == \"win32\"' PEP 508 markers, version pins unchanged"
  - "D-10: no requirements-build.txt split — pyinstaller etc. stay in the single requirements.txt"
  - "Tracer gate (Task 1) verified via automated <verify> commands only (pip dry-run, import, unittest) — no interactive checkpoint needed since the plan defines zero checkpoint tasks and all verification is automated; proceeded straight to Task 2 per Pattern A (fully autonomous)"

patterns-established:
  - "Platform-stub pattern for future window_manager-like modules: top-level if/else, identical exported names/signatures in both branches, else branch raises RuntimeError with user-facing Chinese message"

requirements-completed: [XPLAT-01, XPLAT-02, XPLAT-04]

coverage:
  - id: D1
    description: "pip install skips pywin32/ruyipage on macOS via PEP 508 sys_platform markers"
    requirement: "XPLAT-01"
    verification:
      - kind: other
        ref: "pip install --dry-run -r requirements.txt (macOS) -> 'Ignoring pywin32... Ignoring ruyipage...'"
        status: pass
    human_judgment: false
  - id: D2
    description: "backend.main imports successfully on macOS; four window-arrangement functions raise RuntimeError('窗口排列仅在 Windows 上可用') with identical names/signatures to the Windows implementation"
    requirement: "XPLAT-02"
    verification:
      - kind: unit
        ref: "tests/test_window_manager_posix.py#WindowManagerPosixTests (4 tests) + WindowManagerConcurrencyTests"
        status: pass
      - kind: other
        ref: "python -c \"import backend.main\" (macOS venv) -> exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "--backend-only spawns via subprocess.Popen with start_new_session=True (no creationflags) on POSIX, and creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP on win32; verified end-to-end spawn/psutil-alive/stop on macOS"
    requirement: "XPLAT-04"
    verification:
      - kind: unit
        ref: "tests/test_runtime_control_posix.py#RuntimeControlPosixTests (3 tests, mocked Popen for both platform branches)"
        status: pass
      - kind: integration
        ref: "python -c \"from backend import runtime_control as r; s=r.start_backend_only(); ...; r.stop_backend_only()\" -> final output 'False'"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-24
status: complete
---

# Phase 01 Plan 01: macOS Backend Tracer Slice Summary

**Cross-platform tracer: PEP 508 platform markers unblock pip install, `window_manager.py` gains a Windows/non-Windows conditional split with byte-identical Windows branch, and `runtime_control.py`'s `--backend-only` spawn uses `start_new_session=True` on POSIX instead of the previously-crashing nonzero `creationflags`.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-24T21:09:36Z
- **Tasks:** 2 (Task 1 tracer, Task 2 auto)
- **Files modified:** 3 (requirements.txt, backend/services/window_manager.py, backend/runtime_control.py)
- **Files created:** 2 tests + 1 deferred-items log

## Accomplishments
- macOS `pip install -r requirements.txt` (and `--dry-run`) now skips `pywin32`/`ruyipage` cleanly via PEP 508 `sys_platform == "win32"` markers, both pinned versions unchanged.
- `backend/services/window_manager.py` no longer crashes `import backend.main` on macOS — the entire Windows implementation (238 lines, byte-identical minus indentation) now lives behind `if sys.platform == "win32":`, with a new `else:` branch exporting the same four function names/signatures (`list_monitors`, `show_windows`, `set_uniform_size`, `arrange_windows`) that each raise `RuntimeError("窗口排列仅在 Windows 上可用")`. `browser_manager.py`'s named import required zero changes (D-01).
- `backend/runtime_control.py`'s `start_backend_only` Popen call is now platform-conditional: POSIX gets `start_new_session=True` (no `creationflags`), win32 keeps the exact prior `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`. Verified end-to-end on macOS: spawn → psutil-alive check → stop, final output `False`.
- Two new test files (`tests/test_window_manager_posix.py`, `tests/test_runtime_control_posix.py`) lock in this behavior, including an XPLAT-02 concurrency backstop test (8 threads calling the stub concurrently, each independently raises the same `RuntimeError`, no shared mutable state).

## Task Commits

Each task was committed atomically:

1. **Task 1: macOS 可安装 + 可导入纵切 (requirements 标记 + window_manager 条件导入)** - `e36341f` (feat, tracer)
2. **Task 2: 纯后端模式跨平台派生 (runtime_control creationflags 条件化)** - `bcec3af` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `requirements.txt` - Appended `; sys_platform == "win32"` markers to pywin32 and ruyipage lines
- `backend/services/window_manager.py` - Windows implementation moved into `if sys.platform == "win32":` (verbatim, indentation-only); new `else:` branch with 4 identically-named/signed stub functions raising `RuntimeError`
- `backend/runtime_control.py` - `start_backend_only`'s `subprocess.Popen` call now builds `_POPEN_KWARGS` conditionally (win32: `creationflags`; POSIX: `start_new_session=True`) instead of hardcoding `creationflags`
- `tests/test_window_manager_posix.py` (new) - `WindowManagerPosixTests`, `WindowManagerConcurrencyTests`, `WindowManagerWindowsBranchTests` (skip-unless win32)
- `tests/test_runtime_control_posix.py` (new) - `RuntimeControlPosixTests` (POSIX branch, win32 branch, constants-still-defined)
- `.planning/phases/01-backend-cross-platform/deferred-items.md` (new) - logs one pre-existing, out-of-scope test failure (see Issues Encountered)

## Decisions Made
- Kept `from typing import Any, Callable` at module top level (outside the `if/else`) in `window_manager.py` since both the Windows implementation and the non-Windows stubs need these types for identical function signatures — this is a necessary consequence of D-01's "stub functions must match signatures exactly" requirement, not a deviation from it.
- Verified the plan's tracer feedback gate (Task 1) via its three `<automated>` verify commands (pip dry-run, `import backend.main`, unittest) rather than an interactive `checkpoint:human-verify`, since the plan defines zero `checkpoint:*` tasks (Pattern A: fully autonomous) and all Task 1 verification is scriptable/automated — there is no human-visual-only step to gate on.
- Used a scratch venv (outside the repo, in the session scratchpad) to install `requirements.txt` for verification, since the system Homebrew Python is externally managed (PEP 668) and no project `.venv` exists yet. Did not modify the repo or global Python environment.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>` specs were followed literally; all `<acceptance_criteria>` and `<verify>` commands pass.

## Issues Encountered

- `tests.test_sync_regressions.SynchronizerRegressionTests.test_installer_closes_existing_desktop_app_before_install` fails with `FileNotFoundError: installer/Open-Anti-Browser.iss` when running the full `python -m unittest discover -s tests -v` regression pass. This is a pre-existing, out-of-scope failure: `installer/` is gitignored per CLAUDE.md ("打包脚本已 gitignore"), so the referenced `.iss` file is simply absent from any fresh checkout on any platform — unrelated to this plan's `window_manager.py`/`runtime_control.py`/`requirements.txt` changes. Logged in `deferred-items.md`, not fixed (out of scope per executor scope-boundary rules).
- No project virtualenv exists yet and the system Python is PEP 668 externally-managed, so a scratch venv was created outside the repo purely for verification; this does not affect the repo state and is not part of the deliverable (a `requirements.txt`-based venv/setup step is expected to land in a later phase/plan, if not already covered).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The tracer spine ("`sys.platform` branching makes the backend runnable on macOS") is proven end-to-end: pip installs cleanly, `import backend.main` succeeds, and `--backend-only` spawns/checks/stops correctly on macOS.
- Plans 01-02/01-03/01-04 (config.py path branching, synchronizer platform gate, CI matrix per PATTERNS.md) can now build on a macOS-importable backend without re-deriving this foundation.
- No blockers identified for subsequent phase-01 plans.

---
*Phase: 01-backend-cross-platform*
*Completed: 2026-07-24*

## Self-Check: PASSED

All created/modified files verified present on disk; both task commits (`e36341f`, `bcec3af`) verified present in git log.
