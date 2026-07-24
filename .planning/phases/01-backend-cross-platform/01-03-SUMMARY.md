---
phase: 01-backend-cross-platform
plan: 03
subsystem: backend
tags: [synchronizer, cross-platform, sys.platform, unittest]

# Dependency graph
requires:
  - phase: 01-backend-cross-platform (plan 01)
    provides: window_manager.py sys.platform branching pattern; import backend.main succeeds on macOS
provides:
  - "BrowserSynchronizer.start platform gate: non-win32 raises RuntimeError('窗口同步仅在 Windows 上可用') before any argument validation"
  - "D-04 verified/closed: main.py open_system_url already cross-platform (os.startfile on nt, webbrowser.open_new_tab otherwise) — zero code change"
affects: [phase-02-macos-kernel, phase-03-desktop-shell-macos]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Service-layer platform gate: RuntimeError raised as the first statement inside the sole execution entrypoint (BrowserSynchronizer.start), so every caller (API route, future callers) is protected without route-layer platform checks"

key-files:
  created:
    - tests/test_synchronizer_platform_gate.py
  modified:
    - backend/services/synchronizer.py

key-decisions:
  - "D-03: Synchronizer start gate lives inside BrowserSynchronizer.start (not in main.py route or browser_manager) — same convention as window_manager.py's per-function win32 gate"
  - "D-04: main.py open_system_url is already cross-platform (verified via git blame — cross-platform branch present since commit 8afdce3, initial open source release); no code change made, closed as a verification-only task"

patterns-established:
  - "Platform gate placement: first executable statement of the platform-dependent entrypoint, before any other validation, ensures no half-available state and consistent error propagation via existing HTTPException(400) wrapping in main.py"

requirements-completed: [XPLAT-02]

coverage:
  - id: D1
    description: "macOS(非 win32)上 BrowserSynchronizer.start 在任何参数校验之前抛 RuntimeError,消息为「窗口同步仅在 Windows 上可用」"
    requirement: "XPLAT-02"
    verification:
      - kind: unit
        ref: "tests/test_synchronizer_platform_gate.py#SynchronizerPlatformGateTests.test_start_raises_runtime_error_on_non_windows"
        status: pass
      - kind: unit
        ref: "tests/test_synchronizer_platform_gate.py#SynchronizerPlatformGateTests.test_start_gate_precedes_argument_validation"
        status: pass
    human_judgment: false
  - id: D2
    description: "win32 上 BrowserSynchronizer.start 保持原有校验与启动逻辑不变(门禁只在非 win32 触发)"
    requirement: "XPLAT-02"
    verification:
      - kind: unit
        ref: "tests/test_synchronizer_platform_gate.py#SynchronizerPlatformGateTests.test_start_on_windows_is_not_gated"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-04 核销:main.py open_system_url 端点已是跨平台实现(os.startfile / webbrowser.open_new_tab),macOS 上冒烟验证通过,main.py 零改动"
    requirement: "XPLAT-02"
    verification:
      - kind: unit
        ref: "python -c \"assert 'webbrowser.open_new_tab' in src and 'os.startfile' in src\" (plan's <verify> command)"
        status: pass
      - kind: integration
        ref: "manual invocation of backend.main.open_system_url with webbrowser.open_new_tab/os.startfile mocked — confirmed non-Windows branch is taken, no exception"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-24
status: complete
---

# Phase 01 Plan 03: Synchronizer Platform Gate + D-04 Closure Summary

**Gated BrowserSynchronizer.start to Windows-only via a single RuntimeError check ahead of all argument validation, and verified (without modifying) that main.py's open_system_url endpoint is already cross-platform.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-24T21:20:00Z
- **Completed:** 2026-07-24T21:32:00Z
- **Tasks:** 2 completed
- **Files modified:** 2 (1 modified, 1 created); main.py verified with zero diff

## Accomplishments
- `BrowserSynchronizer.start` now raises `RuntimeError("窗口同步仅在 Windows 上可用")` as its first statement on any non-`win32` platform, before `master_profile_id` validation — closing the last gap in XPLAT-02 (the four window-arrangement endpoints were already gated by Plan 01's `window_manager.py` stubs; synchronizer start had no natural gate point until now)
- Added `tests/test_synchronizer_platform_gate.py` with 3 unit tests: darwin gate fires, gate precedes existing `ValueError` validation, win32 path is completely unaffected (still raises the pre-existing `ValueError("请选择主浏览器")` on empty master)
- Verified D-04 is already resolved in the codebase: `backend/main.py`'s `open_system_url` branches on `os.name == "nt"` (→ `os.startfile`) vs. else (→ `webbrowser.open_new_tab`), present since the initial open-source commit (`8afdce3`) — no code change made or needed

## Task Commits

Each task was committed atomically:

1. **Task 1: 同步器启动平台门禁(D-03)+ 门禁单元测试** - `97afbae` (feat)
2. **Task 2: 核销 D-04 —— 验证 main.py open_system_url 已跨平台** - no commit (pure verification, zero code diff as required by the plan; see Deviations)

**Plan metadata:** (this commit, pending)

## Files Created/Modified
- `backend/services/synchronizer.py` - Added `import sys` to top-level imports; inserted a `sys.platform != "win32"` gate as the first statement of `BrowserSynchronizer.start`, raising `RuntimeError("窗口同步仅在 Windows 上可用")`. No other logic touched — win32 CDP/Marionette forwarding path is byte-identical apart from the new leading gate.
- `tests/test_synchronizer_platform_gate.py` (new) - `SynchronizerPlatformGateTests`: 3 tests patching `backend.services.synchronizer.sys.platform` to assert gate behavior on darwin vs. win32.
- `backend/main.py` - **Not modified.** Task 2 is a verification-only task per the plan; `git diff --stat backend/main.py` is empty, confirming zero changes.

## Decisions Made
- Gate placed inside `BrowserSynchronizer.start` (service layer), not in `main.py`'s route handler or `browser_manager.py`, matching the existing `window_manager.py` convention of per-function win32 gates and satisfying D-03's requirement that the whole synchronizer subsystem fail uniformly with no half-available state.
- D-04 confirmed as already closed by prior work — RESEARCH's Pitfall 1 warning (do not "fix" already-cross-platform code) was heeded; no code was touched.

## Deviations from Plan

None - plan executed exactly as written. Task 2 intentionally produced zero code changes per its `<action>` and `<acceptance_criteria>` ("本 plan 的 git diff 中 backend/main.py 无任何改动(纯验证,零 diff)"), so no commit was created for Task 2 — there is nothing to commit. This is expected behavior per the plan, not a deviation.

## Issues Encountered

None. Both the plan's `<automated>` verify commands ran clean:
- `python -m unittest tests.test_synchronizer_platform_gate -v` → 3/3 pass
- `python -c "...assert 'webbrowser.open_new_tab' in src and 'os.startfile' in src..."` → `D-04 verified: cross-platform branch present`

Full regression suite (`python -m unittest discover -s tests -v`) run for sanity: 72 tests, 1 error (the pre-existing, already-logged `test_installer_closes_existing_desktop_app_before_install` failure caused by the gitignored `installer/` directory — not introduced by this plan, documented in `.planning/phases/01-backend-cross-platform/deferred-items.md`), 1 skip (Windows-only branch test, expected on macOS). No new failures.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- XPLAT-02 is now fully addressed: all five macOS-unsupported endpoints (four window-arrangement endpoints via Plan 01's `window_manager.py` stubs, plus `/api/synchronizer/start` via this plan's gate) return `400` with a Chinese "Windows only" message and produce no half-available state.
- Remaining plan in this phase (01-04) can proceed; no blockers introduced by this plan.
- Future CDP-only cross-platform sync work (SYNC-01, out of scope for v0.2) can remove the single `sys.platform != "win32"` check in `BrowserSynchronizer.start` with no migration cost, per the plan's reversibility note.

---
*Phase: 01-backend-cross-platform*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: backend/services/synchronizer.py
- FOUND: tests/test_synchronizer_platform_gate.py
- FOUND: .planning/phases/01-backend-cross-platform/01-03-SUMMARY.md
- FOUND: 97afbae (Task 1 commit)
