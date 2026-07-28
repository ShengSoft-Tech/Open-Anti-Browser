---
phase: 05-ci
plan: 02
subsystem: infra
tags: [pyside6, qt, macos, quarantine, gatekeeper, launch_app]

# Dependency graph
requires:
  - phase: 04-frontend-platform-gating
    provides: "frontend/src/lib/macosGatekeeperNotice.js GATEKEEPER_XATTR_COMMAND constant (Python-side wording must align verbatim)"
provides:
  - "should_intercept_quit_event()/handle_macos_quit_request() — macOS Cmd+Q routed into existing force_exit() -> closeEvent shutdown path (D-07)"
  - "maybe_strip_quarantine() and its helpers — frozen-runtime first-launch quarantine self-strip with D-12a fallback notice, cross-language parity-locked against macosGatekeeperNotice.js"
affects: [05-03-app-bundle, 05-06-real-machine-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "launch_app.py module-level pure functions for macOS-only branches (should_intercept_quit_event, handle_macos_quit_request, is_macos_frozen_runtime, resolve_app_bundle_root, is_translocated_path, strip_quarantine_from_bundle, quarantine_command_target, build_quarantine_failure_message, maybe_strip_quarantine) so tests/test_macos_desktop_runtime.py can `import launch_app` directly on both CI runners with no platform skip guard"

key-files:
  created:
    - tests/test_macos_desktop_runtime.py
  modified:
    - launch_app.py

key-decisions:
  - "Cmd+Q interception implemented as a QObject event filter installed on qt_app (parented to qt_app to avoid GC), filtering QEvent.Type.Quit and delegating to the existing force_exit() — no parallel shutdown logic (D-07)."
  - "Quarantine self-strip failure message is worded as an expected first-launch phenomenon (QMessageBox.information, not critical) per D-12a's 2026-07-28 revision, since the scenario that triggers self-strip (App Translocation) is exactly the scenario where it is guaranteed to fail."
  - "backend/config.py was not modified — RESEARCH Pattern 1 already confirmed the PyInstaller macOS layout resolves correctly with existing config.py logic; this plan's guardrail against touching config.py was not triggered."

requirements-completed: [PKG-02, PKG-03]

coverage:
  - id: D1
    description: "macOS Cmd+Q intercepted and routed into the existing force_exit() -> closeEvent shutdown -> uvicorn stop path; Windows tray/closeEvent/force_exit/shutdown bodies unchanged"
    requirement: "PKG-02"
    verification:
      - kind: unit
        ref: "tests/test_macos_desktop_runtime.py#MacQuitInterceptionTests"
        status: pass
    human_judgment: true
    rationale: "Real Cmd+Q keyboard-driven behavior on macOS (menu bar icon retained, actual process exit) can only be confirmed on a real Mac — deferred to the 05-06 real-machine checkpoint per the plan's own note (\"真机手感留待 05-06 checkpoint 确认\")."
  - id: D2
    description: "Frozen-runtime first-launch quarantine self-strip with D-12a fallback notice; command text verbatim-matches frontend GATEKEEPER_XATTR_COMMAND and targets the canonical /Applications install path when translocated"
    requirement: "PKG-03"
    verification:
      - kind: unit
        ref: "tests/test_macos_desktop_runtime.py#BuildQuarantineFailureMessageTests, StripQuarantineFromBundleTests, MaybeStripQuarantineTests, QuarantineCommandTargetTests, BundleRootResolutionTests, TranslocationDetectionTests"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-28
status: complete
---

# Phase 05 Plan 02: macOS Cmd+Q Interception and Quarantine Self-Strip Summary

**launch_app.py gains a macOS Cmd+Q event filter routed into existing force_exit(), plus a frozen-runtime quarantine self-strip with a D-12a "expected first-launch" fallback notice that is cross-language parity-locked against frontend/src/lib/macosGatekeeperNotice.js.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-28T17:32:27Z
- **Completed:** 2026-07-28T17:38:35Z
- **Tasks:** 2
- **Files modified:** 2 (`launch_app.py`, `tests/test_macos_desktop_runtime.py`)

## Accomplishments
- Added `should_intercept_quit_event()` / `handle_macos_quit_request(window)` module-level pure functions; wired a `QObject` event filter (parented to `qt_app`) into `run_desktop()` that intercepts `QEvent.Type.Quit` on macOS only and delegates to the window's existing `force_exit()` — Windows tray/closeEvent/force_exit/shutdown behavior is byte-for-byte unchanged (D-07).
- Added `is_macos_frozen_runtime()`, `resolve_app_bundle_root()`, `is_translocated_path()`, `strip_quarantine_from_bundle()`, `quarantine_command_target()`, `build_quarantine_failure_message()`, `maybe_strip_quarantine()`. Wired `maybe_strip_quarantine()` into `run_desktop()` right after the single-instance guard, showing a `QMessageBox.information` (not `critical`) when it returns a message — per D-12a this is the expected first-launch main path, not an error branch (D-12/D-12a).
- Created `tests/test_macos_desktop_runtime.py` (21 tests, no platform skip guard) covering both tasks' behavior, including a cross-language parity test that reads `frontend/src/lib/macosGatekeeperNotice.js`, regex-extracts `GATEKEEPER_XATTR_COMMAND`, and asserts it is verbatim-identical to the Python-side translocated-scenario command.

## Task Commits

Each task was committed atomically:

1. **Task 1: macOS Cmd+Q 接管到既有 force_exit 路径 (D-07)** - `b7fb6cc` (feat)
2. **Task 2: 冻结态首启 quarantine 自剥离 + D-12a 兜底提示** - `e4d1c9f` (feat)

**Plan metadata:** (this commit) — `docs(05-02): complete plan`

## Files Created/Modified
- `launch_app.py` — module-level macOS runtime-branch functions (Cmd+Q interception, quarantine self-strip) + minimal wiring in `run_desktop()`
- `tests/test_macos_desktop_runtime.py` — 21 unit tests covering both tasks, no platform skip guard, importable on windows-latest and macos CI runners

## Decisions Made
- Cmd+Q interception uses a `QObject` event filter (`MacQuitEventFilter`) installed via `qt_app.installEventFilter(...)` rather than overriding `QApplication.event()` or connecting to `aboutToQuit` — matches the plan's suggested `QEvent.Quit` reload approach and keeps all shutdown logic inside the existing `force_exit()` chain.
- The quarantine command target always resolves to `CANONICAL_INSTALL_BUNDLE` (`/Applications/Open-Anti-Browser.app`) whenever the bundle is `None` or under `/AppTranslocation/`, so the printed command is always something the user can actually run (RESEARCH Pitfall 4 / D-12a).

## Deviations from Plan

None - plan executed exactly as written.

**`backend/config.py` modification-required declaration (per plan's explicit ask):** Not triggered. The plan's guardrail required a stop-and-declare if config.py needed changes; `git diff backend/config.py` is empty for this plan, confirming RESEARCH Pattern 1's finding that the existing `_resource_root()`/`ENGINES_DIR`/`FRONTEND_DIST_DIR` resolution is already compatible with the PyInstaller macOS `.app` layout.

## Issues Encountered

None. One self-correction during execution: the first implementation pass wrote both tasks' code into `launch_app.py` in a single edit for efficiency, then had to be split back into two separate diffs (temporarily removing Task 2's additions, committing Task 1, then re-adding Task 2's code) to preserve the required per-task atomic commit structure. Final commits are clean single-task diffs as verified by `git diff HEAD~2 -- launch_app.py` showing no changes to `closeEvent`/`force_exit`/`shutdown`/`_create_tray_icon` function bodies.

## `force_exit` / `QMessageBox.critical` grep baselines (plan-mandated tracking)

- `grep -c 'force_exit' launch_app.py`: **7 (before) → 8 (after)** — exactly +1, the single new call site in `handle_macos_quit_request`.
- `grep -c 'QMessageBox.critical' launch_app.py`: **3 (before) → 3 (after)** — unchanged; the new quarantine notice uses `QMessageBox.information`.

## `build_quarantine_failure_message(None)` verbatim output

```
首次打开 Open-Anti-Browser 时出现这个提示是正常现象，不代表应用损坏或出错。

macOS 会给刚安装的应用加上一次性的隔离标记，需要手动清除一次才能正常启动内置的浏览器内核。请打开“终端”（Terminal），完整复制粘贴以下命令并回车：

xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app

若你把应用安装在了别的位置，请把命令末尾的路径换成实际安装位置。
```

## Parity with `GATEKEEPER_XATTR_COMMAND`

`frontend/src/lib/macosGatekeeperNotice.js:11` defines:
```js
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app'
```

The translocated-scenario Python command embedded in `build_quarantine_failure_message(None)` above is **`xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app`** — verbatim identical, character for character. Locked by `tests/test_macos_desktop_runtime.py::BuildQuarantineFailureMessageTests::test_translocated_scenario_matches_frontend_constant`, which reads the JS source file at test time (not a hardcoded string), regex-extracts the constant, and asserts equality — so any future drift in either file fails CI immediately.

## `backend/config.py` modification declaration

**Not modified. Not required.** `git diff backend/config.py` is empty. No implementation friction encountered that would have required touching it.

## Next Phase Readiness

- `launch_app.py`'s macOS runtime branches (Cmd+Q, quarantine self-strip) are complete and unit-tested; ready for 05-03 (`.app` bundle build via PyInstaller + icns) to package this code into a real bundle.
- Real Cmd+Q keyboard behavior and the actual quarantine self-strip / fallback-notice flow on a genuine downloaded-from-dmg `.app` still need the 05-06 real-machine checkpoint per D-15 — this plan only proves the pure-function logic, not the end-to-end Qt/AMFI interaction.
- No blockers.

---
*Phase: 05-ci*
*Completed: 2026-07-28*

## Self-Check: PASSED

- FOUND: `launch_app.py`
- FOUND: `tests/test_macos_desktop_runtime.py`
- FOUND: commit `b7fb6cc` (Task 1)
- FOUND: commit `e4d1c9f` (Task 2)
