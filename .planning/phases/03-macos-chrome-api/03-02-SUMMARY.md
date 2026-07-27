---
phase: 03-macos-chrome-api
plan: 02
subsystem: infra
tags: [psutil, process-termination, macos, zero-regression]

# Dependency graph
requires:
  - phase: 03-macos-chrome-api (plan 01)
    provides: BrowserManager.get_platform_capabilities() / capabilities API groundwork
provides:
  - "kill_process_tree() refactored to a single cross-platform SIGTERM -> wait_procs -> SIGKILL path (D-05/D-06)"
  - "DEFAULT_TERMINATION_GRACE_PERIOD constant (3.0s) governing the grace window"
  - "tests/test_process_termination_macos.py — Windows-safe (no pywin32) unit coverage of the terminate/kill sequence"
affects: [03-macos-chrome-api plan 03 (real-machine smoke: no residual Chrome processes / SingletonLock)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "kill_process_tree: terminate() whole tree -> psutil.wait_procs(timeout=grace_period) -> kill() survivors -> final wait_procs(timeout=5) cleanup, all per-process try/except psutil.Error swallowing (never a single tree-wide try/except)"
    - "New test files that must run without pywin32 import ONLY backend.services.network (or other pywin32-free modules), never backend.browser_manager/backend.main/launch_app"

key-files:
  created:
    - tests/test_process_termination_macos.py
  modified:
    - backend/services/network.py

key-decisions:
  - "grace_period is a keyword-defaulted parameter (default DEFAULT_TERMINATION_GRACE_PERIOD=3.0) so all existing kill_process_tree(pid) call sites in browser_manager.py remain unchanged"
  - "Single unified code path with no sys.platform branch (D-06) — psutil terminate()/kill() map to the same Windows API calls the old code used (TerminateProcess), so Windows behavior is unchanged by construction"

requirements-completed: [LAUNCH-03]

coverage:
  - id: D1
    description: "kill_process_tree sends SIGTERM to the whole process tree, waits up to grace_period, then SIGKILLs survivors (terminate -> wait_procs -> kill ordering, single cross-platform path)"
    requirement: "LAUNCH-03"
    verification:
      - kind: unit
        ref: "tests/test_process_termination_macos.py#test_sends_sigterm_before_sigkill"
        status: pass
      - kind: unit
        ref: "tests/test_process_termination_macos.py#test_sigkill_survivors_after_grace_period"
        status: pass
  - id: D2
    description: "Zero regression on the existing test suite after the kill_process_tree refactor (Windows behavior equivalence via psutil terminate()==TerminateProcess)"
    verification:
      - kind: unit
        ref: "python -m unittest discover -s tests -v"
        status: pass
    human_judgment: true
    rationale: "Final Windows zero-regression confirmation depends on the dual-runner CI (windows-latest) and a real Windows machine per D-11/D-12 — this plan's macOS-runner full-suite pass is necessary but not sufficient to declare Windows behavior unchanged."
  - id: D3
    description: "Real-machine 'no residual Chrome process / no SingletonLock corruption' after stop/quit on macOS"
    verification: []
    human_judgment: true
    rationale: "Requires a real macOS machine with the bundled Chromium engine running and stopping profiles — deferred to Plan 03's checkpoint:human-verify (pgrep -f Chromium empty after stop)."

# Metrics
duration: 15min
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 2: Graceful process-tree termination Summary

**kill_process_tree rewritten to a unified SIGTERM -> grace-period wait -> SIGKILL path (D-05/D-06), with a Windows-safe unit test suite and a full zero-regression pass of all 79 existing tests.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-27T17:40:00Z (approx)
- **Completed:** 2026-07-27T17:55:00Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- `kill_process_tree(pid, grace_period=DEFAULT_TERMINATION_GRACE_PERIOD)` now terminates the whole process tree gracefully, waits for the grace period, and only SIGKILLs survivors — a single cross-platform code path with no macOS-only branch
- Added `DEFAULT_TERMINATION_GRACE_PERIOD = 3.0` module constant
- New `tests/test_process_termination_macos.py` (2 tests, imports only `backend.services.network`) proves both the happy path (all processes exit within grace period, no kill() calls) and the survivor path (SIGKILL fires only on processes still alive after the grace window)
- Full existing suite (`python -m unittest discover -s tests`) confirmed at 79 tests, 0 failures/errors, 2 skips (both pre-existing Windows-only skips) — zero regression from the refactor

## Task Commits

Each task was committed atomically:

1. **Task 1: 改造 kill_process_tree 为优雅终止 + 新增跨平台单测** - `87fbf99` (feat)
2. **Task 2: Windows 零回归门禁 — 全量 unittest 套件绿灯** - no commit (verification-only task, no source changes; results recorded here)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `backend/services/network.py` - `kill_process_tree` refactored to terminate->wait_procs->kill; added `DEFAULT_TERMINATION_GRACE_PERIOD` constant
- `tests/test_process_termination_macos.py` - new Windows-safe unit tests for the graceful termination sequence

## Decisions Made
- Kept the exact target implementation from `03-PATTERNS.md` (psutil official `kill_proc_tree` recipe) verbatim — no deviation needed since the pattern was already fully specified and verified against the actual current code.
- Placed `DEFAULT_TERMINATION_GRACE_PERIOD` in the existing top-of-file constants block (alongside `DEFAULT_HTTP_TIMEOUT`, `PROXY_CONNECT_TIMEOUT`, etc.) rather than inline above the function, matching the file's existing convention.

## Deviations from Plan

None - plan executed exactly as written. Target code in `03-PATTERNS.md` matched the plan's `<action>` description precisely; no ambiguity or blocking issues encountered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Code-side LAUNCH-03 groundwork complete: graceful termination path in place, unit-tested, zero regression confirmed on macOS runner.
- Real-machine verification of "no residual Chrome process / no SingletonLock corruption" after stop/quit is deferred to Plan 03's `checkpoint:human-verify` step (per this plan's `<verification>` section) — no blocker, just the expected next confirmation point.
- Final Windows-side zero-regression confirmation rests on the dual-runner CI (windows-latest, per D-12) and/or a real Windows machine (D-11) — not verifiable from this macOS execution environment, but the refactor is designed (D-06 unified path, psutil `terminate()`==`TerminateProcess`) to require no Windows-specific changes.

---
*Phase: 03-macos-chrome-api*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: backend/services/network.py
- FOUND: tests/test_process_termination_macos.py
- FOUND: .planning/phases/03-macos-chrome-api/03-02-SUMMARY.md
- FOUND commit: 87fbf99
