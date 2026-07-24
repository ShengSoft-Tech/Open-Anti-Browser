---
phase: 01-backend-cross-platform
plan: 02
subsystem: infra
tags: [config, cross-platform, macos, pathlib, unittest]

# Dependency graph
requires:
  - phase: 01-backend-cross-platform (plan 01)
    provides: sys.platform branching pattern for window_manager.py/runtime_control.py; backend.main importable on macOS
provides:
  - "backend/config.py path resolution is platform-aware (win32 vs darwin) with Windows values byte-identical to pre-change state"
  - "macOS frozen writable root resolves to ~/Library/Application Support/Open-Anti-Browser, ignoring portable markers/env vars"
  - "macOS DEFAULT_CHROME_EXECUTABLE resolves into the .app bundle binary (Chromium.app/Contents/MacOS/Chromium)"
  - "ENGINE_METADATA keeps both chrome and firefox entries on macOS (firefox naturally unavailable via missing file, not deleted)"
affects: [02-macos-kernel-build, 03-macos-core-features, 05-ci-macos-packaging]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.platform branching for module-level path constants, with importlib.reload(config) in tests to re-evaluate module-level branches"

key-files:
  created: [tests/test_config_platform.py]
  modified: [backend/config.py]

key-decisions:
  - "D-05/D-06/D-07/D-08 implemented per plan skeleton: config.py path constants branch on sys.platform, macOS ignores portable mode entirely (data always in user-level Application Support, never inside .app bundle), ENGINE_METADATA dict construction untouched"
  - "SYSTEM_CHROME_EXECUTABLE/SYSTEM_FIREFOX_EXECUTABLE macOS values (/Applications/Chromium.app/..., /Applications/Firefox.app/...) used Claude's Discretion per RESEARCH.md Open Question 2 — not acceptance-locked, only ENGINES_DIR-relative DEFAULT_* paths are locked by XPLAT-03"

patterns-established:
  - "Platform-conditional module-level constants: wrap in `if sys.platform == \"darwin\": ... else: ...` with the else branch as a verbatim migration of prior Windows-only code (zero regression via byte-identical string literals)"

requirements-completed: [XPLAT-03]

coverage:
  - id: D1
    description: "macOS frozen APP_ROOT resolves to ~/Library/Application Support/Open-Anti-Browser, ignoring OPEN_ANTI_BROWSER_PORTABLE env var and portable.mode marker"
    requirement: "XPLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_macos_frozen_app_root_is_application_support"
        status: pass
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_macos_frozen_portable_env_var_is_ignored"
        status: pass
    human_judgment: false
  - id: D2
    description: "macOS DEFAULT_CHROME_EXECUTABLE resolves into the .app bundle binary path"
    requirement: "XPLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_macos_default_chrome_executable_points_into_app_bundle"
        status: pass
    human_judgment: false
  - id: D3
    description: "ENGINE_METADATA retains both chrome and firefox entries (with full field set) on macOS"
    requirement: "XPLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_macos_engine_metadata_contains_chrome_and_firefox"
        status: pass
    human_judgment: false
  - id: D4
    description: "Windows path constants (_writable_root LOCALAPPDATA logic, SYSTEM_CHROME_EXECUTABLE, SYSTEM_FIREFOX_EXECUTABLE, DEFAULT_CHROME_EXECUTABLE, DEFAULT_FIREFOX_EXECUTABLE) are byte-identical to pre-change values — zero regression"
    requirement: "XPLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_windows_frozen_writable_root_uses_local_appdata"
        status: pass
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_windows_system_and_default_executable_values_unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "Dev mode (sys.frozen false) _writable_root returns PROJECT_ROOT on both platforms"
    requirement: "XPLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_dev_mode_writable_root_is_project_root_on_both_platforms"
        status: pass
    human_judgment: false
  - id: D6
    description: "macOS darwin branch of config.py does not use any sys.executable-based path derivation (Pitfall 4 guard)"
    requirement: "XPLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_config_platform.py#ConfigPlatformTests.test_macos_darwin_branch_does_not_use_sys_executable"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-24
status: complete
---

# Phase 01 Plan 02: config.py Platform-Aware Path Resolution Summary

**backend/config.py path constants branch on sys.platform (win32/darwin) with macOS writable root locked to `~/Library/Application Support/Open-Anti-Browser` and Chrome path locked into the `.app` bundle binary, Windows values byte-identical to pre-change state.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-07-24T21:04:00Z (approx.)
- **Completed:** 2026-07-24T21:16:05Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- `_writable_root()` now branches on `sys.platform`: the `win32` branch is a verbatim migration of the prior LOCALAPPDATA/portable-marker logic; a new `darwin` branch returns `Path.home() / "Library" / "Application Support" / APP_NAME` unconditionally, ignoring `OPEN_ANTI_BROWSER_PORTABLE` and `portable.mode` (D-07); dev mode (`sys.frozen` false) still returns `PROJECT_ROOT` on both platforms.
- `SYSTEM_CHROME_EXECUTABLE` / `SYSTEM_FIREFOX_EXECUTABLE` / `DEFAULT_CHROME_EXECUTABLE` / `DEFAULT_FIREFOX_EXECUTABLE` wrapped in `if sys.platform == "darwin": ... else: ...`. macOS `DEFAULT_CHROME_EXECUTABLE` resolves to `ENGINES_DIR/chrome/Chromium.app/Contents/MacOS/Chromium`; macOS `DEFAULT_FIREFOX_EXECUTABLE` points at a path that has no backing file (naturally unavailable, D-08). The `else` (Windows) branch is a verbatim copy of the original four constant definitions — zero regression.
- `ENGINE_METADATA` dict construction untouched: both `chrome` and `firefox` keys remain with identical field names on both platforms (D-08); only the referenced path constants differ by platform.
- New `tests/test_config_platform.py` (8 tests, pure `unittest.TestCase` + `unittest.mock.patch` + `importlib.reload(config)`, matching the existing `test_window_manager_posix.py`/`test_runtime_control_posix.py` style): macOS frozen `APP_ROOT` assertion, portable-ignored assertion, Chrome `.app` bundle path assertion, `ENGINE_METADATA` chrome+firefox structure assertion, dev-mode `PROJECT_ROOT` assertion for both platforms, Windows verbatim regression assertions for all four executable constants, and a guard asserting the darwin-specific constant block contains no `sys.executable` usage (Pitfall 4).

## Task Commits

Each task was committed atomically:

1. **Task 1: config.py 平台感知路径解析 + 两平台路径锁定测试** - `4a166f8` (feat)

**Plan metadata:** _pending — see final commit below_

## Files Created/Modified
- `backend/config.py` - `_writable_root()` gained a `darwin` branch (Application Support, portable-ignored); `SYSTEM_*_EXECUTABLE`/`DEFAULT_*_EXECUTABLE` wrapped in platform conditional, Windows branch verbatim
- `tests/test_config_platform.py` - New test module: `ConfigPlatformTests` (8 test methods covering macOS frozen paths, portable-ignore, ENGINE_METADATA structure, dev-mode behavior, Windows zero-regression, and the Pitfall 4 sys.executable guard)

## Decisions Made
- Followed the plan's exact skeleton from 01-PATTERNS.md / 01-RESEARCH.md Code Examples verbatim: `_writable_root()` nests `win32`/`darwin` branches inside the `_is_packaged()` guard; the four executable constants use a top-level `if sys.platform == "darwin": ... else: ...` block.
- `SYSTEM_CHROME_EXECUTABLE`/`SYSTEM_FIREFOX_EXECUTABLE` macOS values (`/Applications/Chromium.app/...`, `/Applications/Firefox.app/...`) chosen per "Claude's Discretion" flagged in RESEARCH.md Open Question 2 — these are system-installed-browser detection paths, not part of the XPLAT-03 acceptance-locked values (which are the `ENGINES_DIR`-relative `DEFAULT_*` paths). Left with an inline comment noting Phase 2/3 calibration if needed.
- `CHROME_ENGINE_ZIP_URL`/`CHROME_INSTALLER_URL`/`FIREFOX_INSTALLER_URL` left unchanged (still Windows-only kernel URLs) — plan explicitly scopes real macOS kernel URLs to Phase 2, after kernel release assets exist.

## Deviations from Plan

None - plan executed exactly as written. One self-correction during test authoring: an early draft of the Pitfall-4 guard test (`test_macos_darwin_branch_does_not_use_sys_executable`) matched too broad a source-code window and tripped on the Chinese explanatory comment text itself (which mentions "sys.executable" as prose, not code). Narrowed the scanned window to the `USERNAME = _current_username()` → `DEFAULT_USER_DATA_ROOT = APP_ROOT` block before committing — this was test-authoring iteration, not a deviation from the plan's implementation instructions, and no separate commit was needed since it was fixed before the task's single commit.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `backend/config.py` now exposes a fully platform-conditional set of path constants; Phase 2 (macOS kernel build) can rely on `ENGINES_DIR/chrome/Chromium.app/Contents/MacOS/Chromium` as the target install location for the macOS Chromium bundle.
- `ENGINE_METADATA["firefox"]` remains structurally intact on macOS for Phase 3's capabilities API / Phase 4's frontend hiding logic to consume without special-casing missing dict keys.
- No blockers for Plan 03/04 of this phase.

---
*Phase: 01-backend-cross-platform*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: backend/config.py
- FOUND: tests/test_config_platform.py
- FOUND: .planning/phases/01-backend-cross-platform/01-02-SUMMARY.md
- FOUND commit: 4a166f8
