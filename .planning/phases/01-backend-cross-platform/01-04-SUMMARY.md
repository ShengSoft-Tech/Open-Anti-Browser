---
phase: 01-backend-cross-platform
plan: 04
subsystem: testing
tags: [ci, github-actions, unittest, macos, windows, cross-platform]

# Dependency graph
requires:
  - phase: 01-backend-cross-platform (01-01, 01-02, 01-03)
    provides: "macOS-importable backend.main / backend.browser_manager, platform-aware config.py, window_manager posix stubs, synchronizer Windows-only start gate, and four new platform-branch test files (test_window_manager_posix, test_runtime_control_posix, test_config_platform, test_synchronizer_platform_gate)"
provides:
  - "push/PR-triggered CI workflow (.github/workflows/ci-tests.yml) running the full unittest suite on windows-latest and macos-latest"
  - "Documented macOS test-range conclusion: full suite runs clean on macOS (72 tests, 0 failures, 2 skips)"
  - "Fix for a cross-platform-breaking test (installer .iss content assertion) that would have failed on both CI runners"
affects: [phase-05-ci-packaging-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CI test workflow separate from release workflow (build-release.yml unchanged), triggered on push/pull_request instead of v* tags"
    - "unittest.TestCase.skipTest() as a runtime file-existence guard for tests that assert on gitignored packaging config"

key-files:
  created:
    - .github/workflows/ci-tests.yml
  modified:
    - tests/test_sync_regressions.py

key-decisions:
  - "D-12: new independent ci-tests.yml (push/pull_request/workflow_dispatch), build-release.yml (v* tag release) untouched"
  - "D-11 continuation: windows-latest job runs the full unittest suite unconditionally (persists the one-off manual Windows verification as a permanent CI gate)"
  - "macOS CI range = full suite (not a subset): actual run on macOS produced 72/72 tests passing after the installer-test guard fix, so no skip list was needed"
  - "Deviation (Rule 3, blocking): test_installer_closes_existing_desktop_app_before_install skipped via file-existence check rather than platform check, because installer/ is gitignored on ANY platform/checkout, not just macOS — without this fix both windows-latest and macos-latest CI jobs would fail"

patterns-established:
  - "New CI test workflow triggers: on: [push, pull_request, workflow_dispatch], permissions: contents: read (no write permission needed, no secrets)"

requirements-completed: [XPLAT-01, XPLAT-02, XPLAT-03, XPLAT-04]

coverage:
  - id: D1
    description: "macOS-only test run of the full unittest suite recorded and used to determine CI test range"
    requirement: XPLAT-01
    verification:
      - kind: unit
        ref: "python -m unittest discover -s tests -v (run locally on macOS, this session)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ci-tests.yml added with windows-latest (full suite) and macos-latest (full suite) jobs, triggered on push/pull_request, independent of build-release.yml"
    requirement: XPLAT-02
    verification:
      - kind: other
        ref: "grep-based structure check: windows-latest / macos / unittest / pull_request keywords present in .github/workflows/ci-tests.yml"
        status: pass
    human_judgment: true
    rationale: "Workflow correctness on actual GitHub Actions runners (windows-latest, macos-latest) can only be confirmed by a real push/PR triggering the workflow — not locally verifiable in this session."
  - id: D3
    description: "Four platform-branch test files (test_window_manager_posix, test_runtime_control_posix, test_config_platform, test_synchronizer_platform_gate) confirmed passing on macOS, making them CI-verifiable"
    requirement: XPLAT-03
    verification:
      - kind: unit
        ref: "python -m unittest discover -s tests -v — all 4 files, all cases pass on macOS"
        status: pass
    human_judgment: false
  - id: D4
    description: "build-release.yml (release workflow) left untouched; new workflow is a fully independent file"
    requirement: XPLAT-04
    verification:
      - kind: unit
        ref: "git diff --stat .github/workflows/build-release.yml (empty diff, verified this session)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-24
status: complete
---

# Phase 01 Plan 04: CI cross-platform test workflow Summary

**Added push/PR-triggered `.github/workflows/ci-tests.yml` running the full unittest suite on windows-latest and macos-latest, and fixed one test that would have broken both CI runners on any fresh checkout.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-07-24T21:22:43Z
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Ran `python -m unittest discover -s tests -v` on macOS (this machine) and recorded the full result: 72 tests, 0 real failures, 2 skips (1 pre-existing Windows-only guard, 1 newly-added file-existence guard) — confirming the macOS CI job can run the **full suite**, no subset/skip list needed.
- Confirmed all four new Wave 1-2 platform-branch test files pass cleanly on macOS: `test_window_manager_posix`, `test_runtime_control_posix`, `test_config_platform`, `test_synchronizer_platform_gate`.
- Discovered and fixed a cross-platform CI blocker: `test_installer_closes_existing_desktop_app_before_install` reads `installer/Open-Anti-Browser.iss`, which is gitignored per CLAUDE.md ("打包脚本已 gitignore"). This fails on ANY fresh checkout on ANY platform — meaning it would have broken both the new macos-latest job and the windows-latest job. Guarded with `skipTest()` on file absence rather than a platform check, since the root cause is repo hygiene, not OS.
- Created `.github/workflows/ci-tests.yml`: two parallel jobs (`test-windows` on `windows-latest`, `test-macos` on `macos-latest`), both triggered on `push`/`pull_request`/`workflow_dispatch`, both running `pip install -r requirements.txt` (asserting pywin32/ruyipage install on Windows, skip-success on macOS) followed by the full `python -m unittest discover -s tests -v`.
- Verified `.github/workflows/build-release.yml` (the existing v*-tag release workflow) has zero diff — completely untouched, as required.

## Task Commits

Each task was committed atomically:

1. **Task 1: 实测圈定 macOS 可运行测试范围** - `1bd5607` (fix) — includes the installer-test file-existence guard, which was the direct, necessary output of the macOS test-range analysis (documented as a Rule 3 deviation below)
2. **Task 2: 编写双 runner CI 测试 workflow (D-12)** - `8cf8180` (feat)

**Plan metadata:** (this commit) `docs: complete 01-04 plan`

## Files Created/Modified

- `.github/workflows/ci-tests.yml` - New CI workflow: `test-windows` (windows-latest, full unittest) + `test-macos` (macos-latest, full unittest), triggered on push/PR, `permissions: contents: read`, no secrets, no engine downloads or packaging steps
- `tests/test_sync_regressions.py` - `test_installer_closes_existing_desktop_app_before_install` now skips (via `self.skipTest`) when `installer/Open-Anti-Browser.iss` doesn't exist on disk, instead of erroring with `FileNotFoundError`

## Decisions Made

- macOS CI job runs the **full** `python -m unittest discover -s tests -v` (not a subset). The actual macOS run produced zero platform-specific failures once the installer-test fix landed, so no skip list was required — simpler than maintaining a curated subset.
- Both CI jobs pin `python-version: '3.11'`, matching `build-release.yml`'s existing convention.
- `permissions: contents: read` declared explicitly (stricter than "rely on repo default"), consistent with the threat model's T-01-05 mitigation (no write permission needed for a read-only test workflow).
- The installer-test fix is scoped as a file-existence check (`installer_script.exists()`), not a `sys.platform == "win32"` check — because the failure is caused by the file never being committed to git (any platform, any checkout), not by an OS difference. A platform check would have been the wrong fix and would still fail on windows-latest CI.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Guarded `test_installer_closes_existing_desktop_app_before_install` against missing `installer/` directory**
- **Found during:** Task 1 (实测圈定 macOS 可运行测试范围)
- **Issue:** The test unconditionally reads `installer/Open-Anti-Browser.iss` via `Path.read_text()`. That path is gitignored (per CLAUDE.md, packaging scripts are intentionally excluded from the repo), so on any fresh checkout — this machine, windows-latest CI, macos-latest CI — the file doesn't exist and the test errors with `FileNotFoundError` rather than a normal assertion failure. This is not specific to macOS; it would have broken the windows-latest job too, defeating the whole purpose of this plan (a CI workflow that's supposed to go green).
- **Fix:** Added `if not installer_script.exists(): self.skipTest(...)` before the read, with a message explaining the file is intentionally gitignored per CLAUDE.md. No assertion logic was changed — if the file exists (e.g. a future local checkout with installer configs present), the original `assertIn` checks still run unmodified.
- **Files modified:** `tests/test_sync_regressions.py`
- **Verification:** `python -m unittest discover -s tests -v` — went from `FAILED (errors=1, skipped=1)` to `OK (skipped=2)`, 72/72 tests passing or intentionally skipped.
- **Committed in:** `1bd5607`

The plan's Task 1 `<action>` text says "不修改任何测试文件的断言逻辑(如需补 skipUnless 属既有测试的最小平台守卫,记录清单,不改断言)" — the fix above adds a *guard*, not a change to any `assertIn` assertion, so it stays within that constraint. This is also explicitly pre-authorized in this session's wave-context brief as an acceptable documented deviation given the alternative (leaving CI red on every push/PR) would defeat the plan's entire purpose.

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking issue)
**Impact on plan:** Necessary for CI correctness on both runners; no scope creep — the plan's own Task 1 acceptance criteria explicitly anticipated needing to record/apply a skip guard for tests failing for non-platform reasons.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required. `ci-tests.yml` needs no secrets (GitHub Actions provides the ambient `GITHUB_TOKEN` automatically; this workflow doesn't even use it since `permissions: contents: read` is the default checkout-only need).

## Next Phase Readiness

- Phase 01 (backend-cross-platform) is now fully executed: all 4 plans complete (01-01 tracer slice, 01-02 config.py path resolution, 01-03 synchronizer platform gate, 01-04 CI workflow).
- The next push or PR against this repo will exercise `ci-tests.yml` on real GitHub-hosted `windows-latest` and `macos-latest` runners — this is the first real-world confirmation that the workflow YAML is valid and both jobs go green (only locally verified in this session via structure grep + local macOS test run, not an actual Actions run).
- Phase 2 (macOS kernel build) can proceed; it does not depend on anything in this plan beyond the fact that the backend is now macOS-importable/testable, which Plans 01-03 already delivered.
- Phase 5 (CI packaging/release) will likely reuse the pattern established here (independent workflow file, python-version 3.11 pin) when it eventually adds a macOS packaging job to `build-release.yml`.

---
*Phase: 01-backend-cross-platform*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: .github/workflows/ci-tests.yml
- FOUND: tests/test_sync_regressions.py
- FOUND: commit 1bd5607
- FOUND: commit 8cf8180
