---
phase: 02-macos
plan: 02
subsystem: backend-config
tags: [config, macos, kernel-url, unittest, ssot]

# Dependency graph
requires:
  - phase: 01-backend-cross-platform
    provides: config.py platform-aware path resolution, existing _CHROME_KERNEL_BASE/CHROME_ENGINE_ZIP_URL Windows pattern to extend
provides:
  - "backend.config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64 and CHROME_ENGINE_ZIP_URL_MACOS_X64 — module-level, platform-agnostic constants reusing _CHROME_KERNEL_BASE, -1.3 revision, macOS arm64/x64 filenames"
  - "tests/test_config_platform.py assertions locking the two constants' shape (startswith base, contains -1.3, contains arch tag, ends .zip, full string equality)"
affects: [02-01-verify-upload-script, 02-03-arm64-real-upload, 02-04-x64-real-upload, phase-5-ci-macos-job]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New platform-specific URL constants stay outside any if sys.platform branch when the value itself is a static string with no platform-dependent computation — only path resolution that differs by OS needs the branch"

key-files:
  created: []
  modified:
    - backend/config.py
    - tests/test_config_platform.py

key-decisions:
  - "Followed plan's explicit direction (Open Question 3): two independent named constants per arch, no platform.machine() runtime branching — keeps CI/installer consumption a plain static import"
  - "-1.3 revision chosen precisely as specified (D-08) to distinguish macOS kernel builds from Windows -1.2, avoiding any ambiguity in the shared _CHROME_KERNEL_BASE release directory"

requirements-completed: [KERNEL-01, KERNEL-02]

coverage:
  - id: D1
    description: "CHROME_ENGINE_ZIP_URL_MACOS_ARM64 == f'{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip'"
    requirement: KERNEL-01
    verification:
      - kind: automated_test
        ref: "python -m unittest tests.test_config_platform.ConfigPlatformTests.test_macos_arm64_kernel_url -v"
        status: pass
    human_judgment: false
  - id: D2
    description: "CHROME_ENGINE_ZIP_URL_MACOS_X64 == f'{_CHROME_KERNEL_BASE}/ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip'"
    requirement: KERNEL-02
    verification:
      - kind: automated_test
        ref: "python -m unittest tests.test_config_platform.ConfigPlatformTests.test_macos_x64_kernel_url -v"
        status: pass
    human_judgment: false
  - id: D3
    description: "Windows existing constants (CHROME_ENGINE_ZIP_URL -1.2, _CHROME_KERNEL_BASE) unmodified; full test_config_platform suite zero regression"
    requirement: KERNEL-01
    verification:
      - kind: automated_test
        ref: "python -m unittest tests.test_config_platform -v (10/10 pass); git diff backend/config.py shows no changes to CHROME_ENGINE_ZIP_URL or _CHROME_KERNEL_BASE lines"
        status: pass
    human_judgment: false

# Metrics
duration: 8min
completed: 2026-07-24
status: complete
---

# Phase 2 Plan 2: macOS Kernel URL Config Backfill Summary

**Backfilled `backend/config.py` with `CHROME_ENGINE_ZIP_URL_MACOS_ARM64`/`_X64` (reusing `_CHROME_KERNEL_BASE`, `-1.3` revision) plus two matching unit tests — zero Windows regression, single source of truth ready for 02-03/02-04 uploads and the Phase 5 CI macOS job.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-07-24T16:49:13-07:00
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added two module-level constants to `backend/config.py` immediately after `CHROME_ENGINE_ZIP_URL` and before `FIREFOX_INSTALLER_URL`: `CHROME_ENGINE_ZIP_URL_MACOS_ARM64` and `CHROME_ENGINE_ZIP_URL_MACOS_X64`, both f-string built from `_CHROME_KERNEL_BASE` with filenames `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` / `..._macos_x64.zip`.
- Constants are platform-agnostic static strings — not wrapped in any `if sys.platform` branch, per the plan's Open Question 3 guidance (explicit named constants over `platform.machine()` runtime dispatch).
- Added a short Chinese-language rationale comment directly above the new constants explaining the macOS asset purpose and the `-1.3` vs Windows `-1.2` revision distinction, matching the file's existing house style.
- Added `test_macos_arm64_kernel_url` and `test_macos_x64_kernel_url` to `ConfigPlatformTests`, asserting `startswith(_CHROME_KERNEL_BASE)`, `-1.3` substring, correct arch tag substring, `.zip` suffix, and full string equality — no `patch.object(sys, "platform", ...)` needed since the constants don't vary by platform.
- Full `test_config_platform` suite: 10/10 pass, including the existing `test_windows_system_and_default_executable_values_unchanged` guard (zero Windows regression).

## Task Commits

Each task was committed atomically:

1. **Task 1: config.py 回填 macOS arm64/x64 内核 URL 常量** - `093abf5` (feat)
2. **Task 2: test_config_platform 补 macOS URL 断言** - `4c773c3` (test)

## Files Created/Modified

- `backend/config.py` - Added `CHROME_ENGINE_ZIP_URL_MACOS_ARM64` and `CHROME_ENGINE_ZIP_URL_MACOS_X64` constants (8 lines) between the existing `CHROME_ENGINE_ZIP_URL` and `FIREFOX_INSTALLER_URL` definitions. No other lines touched.
- `tests/test_config_platform.py` - Added `test_macos_arm64_kernel_url` and `test_macos_x64_kernel_url` methods to `ConfigPlatformTests` (24 lines). No existing method bodies changed.

## Decisions Made

- Followed the plan's explicit direction to use two independent named constants per architecture rather than a `platform.machine()` runtime branch — this keeps the constants trivially importable as static strings for both the Phase 5 CI macOS job and the runtime installer download path, matching how `.github/workflows/build-release.yml` already reads `CHROME_ENGINE_ZIP_URL`.
- Used the exact `-1.3` revision and filename pattern specified in the plan's `must_haves.truths` (D-07/D-08) with no deviation.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their `<action>` and `<acceptance_criteria>` blocks precisely; no auto-fixes, no architectural questions, no auth gates.

## Issues Encountered

None. The broader `python -m unittest discover -s tests -v` run in this environment shows 9 pre-existing import errors (`ModuleNotFoundError` for `pydantic`, `psutil`, `websocket`) because `requirements.txt` is not installed in this sandbox — this is a pre-existing environment condition unrelated to this plan's changes (per CLAUDE.md's documented test-environment constraints) and out of scope per the deviation rules' scope boundary. `tests.test_config_platform` itself — the only test module this plan touches — is fully green with zero import errors.

## User Setup Required

None.

## Next Phase Readiness

- 02-03 (arm64 real upload, human-gated checkpoint) and 02-04 (x64 real upload) can now run `scripts/release/verify_and_upload_macos_kernel.sh` without `--dry-run`; the script's `gh release upload` step resolves the asset filename from `backend.config` at runtime, and both `CHROME_ENGINE_ZIP_URL_MACOS_ARM64`/`_X64` now exist and match the exact filenames the sibling-repo build will produce.
- Phase 5's CI macOS job can read these two constants the same way `build-release.yml:62` already reads `CHROME_ENGINE_ZIP_URL` for Windows.

---
*Phase: 02-macos*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: backend/config.py
- FOUND: tests/test_config_platform.py
- FOUND: .planning/phases/02-macos/02-02-SUMMARY.md
- FOUND commit: 093abf5
- FOUND commit: 4c773c3
