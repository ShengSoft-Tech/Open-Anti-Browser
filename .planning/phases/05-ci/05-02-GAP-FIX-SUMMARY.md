---
phase: 05-ci
plan: 02-gap-fix
subsystem: infra
tags: [pyside6, qt, macos, crash, ci, github-actions, bash, event-filter]

# Dependency graph
requires:
  - phase: 05-ci
    provides: "05-02 macOS Cmd+Q interception (installEventFilter anti-pattern origin) and the 05-06 real-machine checkpoint crash report that discovered the blocking defect"
provides:
  - "launch_app.py: DesktopApplication (QApplication subclass overriding event()) replacing the app-wide installEventFilter(...) that caused a 100%-reproducible ~2s post-launch SIGSEGV on macOS"
  - "AST structural guard test pinning the anti-pattern so installEventFilter cannot silently return to launch_app.py"
  - "build-macos CI job gains a real-cocoa GUI-launch smoke gate that empirically reproduces and catches this exact crash class on every future build"
affects: [05-06-real-machine-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QApplication subclass overriding event() instead of a QObject event filter installed via installEventFilter(qt_app) — avoids Qt's app-wide QObject-wrapper-construction storm that PySide cannot always survive"
    - "GitHub Actions shell: bash always wraps run: blocks in `bash -e -o pipefail`; a script-local `set -uo pipefail` does NOT turn off that inherited -e — multi-signal diagnostic steps that must run to completion regardless of an early nonzero need an explicit `set +e -uo pipefail`"

key-files:
  created:
    - .planning/phases/05-ci/05-02-GAP-FIX-SUMMARY.md
  modified:
    - launch_app.py
    - tests/test_macos_desktop_runtime.py
    - .github/workflows/build-release.yml

key-decisions:
  - "Root-cause fix matches the task's suggested shape exactly: DesktopApplication(QApplication) overriding event() for QEvent.Type.Quit, replacing MacQuitEventFilter(QObject) + qt_app.installEventFilter(...). Cmd+Q still converges on the single existing handle_macos_quit_request() -> window.force_exit() path; no second shutdown path was introduced (D-07 constraint preserved)."
  - "CI GUI-launch smoke gate deliberately does NOT set QT_QPA_PLATFORM=offscreen — the crash goes through -[NSWindow makeKeyAndOrderFront:], which offscreen skips. Verified empirically (not assumed) that GitHub's macos-15 hosted runner has a real logged-in cocoa/WindowServer session capable of reproducing this exact bug."
  - "Iterated the CI gate script itself against real workflow_dispatch runs three times before it produced trustworthy evidence: (1) a bash-3.2 locale bug where a variable immediately adjacent to a non-ASCII character raised a spurious 'unbound variable' error, (2) GitHub Actions' inherited `bash -e` aborting the script before it could print its own diagnostic summary (this bug would have made the gate falsely FAIL even on correctly-fixed code, via the SIGTERM path also returning nonzero from `wait`), (3) a crash-report-file race with macOS's asynchronous ReportCrash daemon. All three are documented below with real run IDs."

requirements-completed: []

coverage:
  - id: D1
    description: "launch_app.py no longer installs an app-wide QObject event filter on QApplication; Cmd+Q still routes through handle_macos_quit_request() -> window.force_exit(); Windows/Linux code paths byte-for-byte unchanged (should_intercept_quit_event() gate untouched)"
    requirement: "PKG-02"
    verification:
      - kind: unit
        ref: "tests/test_macos_desktop_runtime.py#MacQuitInterceptionTests (pre-existing, unmodified, still passing)"
        status: pass
      - kind: e2e
        ref: "workflow_dispatch run 30408816656, build-macos job, step 'GUI launch smoke test' — real .app binary launched under real cocoa session, survived full 18s dwell, clean SIGTERM exit (143), zero new crash reports"
        status: pass
    human_judgment: true
    rationale: "The blocking defect this gap-fix addresses was discovered by a REAL macOS machine, not by CI or unit tests — CI's prior --backend-only smoke test never entered the GUI code path that crashed. The correct closure for this specific defect class is the user re-running the actual 05-06 real-machine checkpoint (Cmd+Q feel, window focus, full app lifecycle) against the fresh dmg this run produced, not a second layer of automated self-certification."
  - id: D2
    description: "AST structural guard added to tests/test_macos_desktop_runtime.py: fails if launch_app.py ever calls installEventFilter again, and asserts a QApplication subclass overrides event()"
    requirement: "PKG-02"
    verification:
      - kind: unit
        ref: "tests/test_macos_desktop_runtime.py#QApplicationEventFilterGuardTests::test_no_install_event_filter_call_anywhere_in_launch_app"
        status: pass
      - kind: unit
        ref: "tests/test_macos_desktop_runtime.py#QApplicationEventFilterGuardTests::test_desktop_application_subclass_overrides_event_not_install_filter"
        status: pass
      - kind: other
        ref: "Manually validated the guard FAILS against pre-fix source (git show 580b269:launch_app.py, AST-scanned directly — found the installEventFilter call at line 436) before being validated to pass against the fixed source"
        status: pass
    human_judgment: false
  - id: D3
    description: "CI GUI-launch smoke gate added to build-macos: launches the real built .app binary under the runner's real cocoa session, watches an 18s dwell window, asserts the process survives and no new .ips crash report appears, then cleanly terminates it"
    requirement: "PKG-02"
    verification:
      - kind: e2e
        ref: "workflow_dispatch run 30408617294 (scratch/verify-gui-crash-gate, pre-fix code) — GUI launch smoke test step FAILED: 'Segmentation fault: 11', exit code 139, detected at 4s (well inside the 18s dwell), full custom diagnostic summary printed"
        status: pass
      - kind: e2e
        ref: "workflow_dispatch run 30408816656 (main, post-fix code) — GUI launch smoke test step PASSED: survived full 18s dwell, terminated via SIGTERM (exit 143, non-crash), zero new crash reports, 'GUI 冒烟测试通过' printed"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full local test suite (116 Python unittest cases, 2 skipped as Windows-only) and full frontend test suite (43 node:test cases) still pass after the fix"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m unittest discover -s tests"
        status: pass
      - kind: unit
        ref: "node --test frontend/src/lib/*.test.js"
        status: pass
    human_judgment: false

# Metrics
duration: 34min (code) + ~40min (CI validation cycles, 4 real workflow_dispatch runs)
completed: 2026-07-28
status: complete
---

# Phase 5 Plan 02 Gap-Fix: macOS App-Wide Event Filter Crash Summary

**Replaced `qt_app.installEventFilter(...)` with a `QApplication` subclass overriding `event()`, fixing a 100%-reproducible ~2s post-launch SIGSEGV on macOS discovered by the 05-06 real-machine checkpoint, and added a two-layer regression gate (AST structural guard + real-cocoa CI GUI-launch smoke test) empirically proven to catch this exact crash class.**

## Performance

- **Duration:** ~34 min writing the fix + tests + CI gate; ~40 min of real `workflow_dispatch` CI validation across 4 runs (3 needed to debug the gate script itself against bash 3.2 / GH Actions `-e` semantics / ReportCrash timing, before it produced trustworthy evidence)
- **Started:** 2026-07-28T23:22:26Z (first commit)
- **Completed:** 2026-07-28T23:56:13Z
- **Commits:** 6
- **Files modified:** 3 (`launch_app.py`, `tests/test_macos_desktop_runtime.py`, `.github/workflows/build-release.yml`)

## Diagnosis Recap (not re-derived — provided by the task)

`launch_app.py`'s `run_desktop()` installed a Python-implemented `QObject` event filter directly on the `QApplication` instance (`qt_app.installEventFilter(mac_quit_filter)`) to route macOS Cmd+Q into the existing `force_exit()` shutdown path (D-07, from plan 05-02). Qt gives filters installed on `QCoreApplication::instance()` special semantics: they receive events for **every** `QObject` in the thread, forcing PySide to construct a Python wrapper for every event target app-wide. During main-window show, Cocoa's `-[NSWindow makeKeyAndOrderFront:]` drives QtWebEngineView's internal QtQuick-based compositor's focus delivery, which sends events through `QObject`s PySide cannot safely wrap — a null-pointer dereference (`SIGSEGV`, `EXC_BAD_ACCESS` at `0x8`, stack top `PySide::typeName`). This crashed the shipped `.app` 100% reproducibly ~2s after launch. Three identical crash reports on the user's real Mac (arm64, macOS 15.7) surfaced this during the 05-06 checkpoint; CI's `--backend-only` smoke test never entered `run_desktop()`'s GUI path, so nothing caught it before shipping.

## Accomplishments

- **The fix (`launch_app.py`):** `MacQuitEventFilter(QObject)` + `qt_app.installEventFilter(...)` replaced by `DesktopApplication(QApplication)` overriding `event()`. This subclass receives only events delivered to the application object itself — no app-wide wrapper-construction storm. Cmd+Q still converges on the single existing `handle_macos_quit_request(window) -> window.force_exit()` path (module-level pure functions and their unit tests untouched); `should_intercept_quit_event()`'s darwin-only gate is unchanged, so Windows/Linux behavior is byte-for-byte identical (`target_window` stays `None` off darwin).
- **Layer 1 — AST structural guard (`tests/test_macos_desktop_runtime.py`):** `QApplicationEventFilterGuardTests` statically scans `launch_app.py`'s AST and fails if `installEventFilter` is ever called anywhere in the file, and separately asserts a `QApplication` subclass overrides `event()`. Manually validated against the pre-fix commit (`580b269`) — the scan correctly flagged the `installEventFilter` call at line 436 — before being validated to pass against the fix.
- **Layer 2 — CI GUI-launch smoke gate (`.github/workflows/build-release.yml`):** New step in `build-macos`, after the existing `--backend-only` smoke test and before dmg creation. Launches the real built `.app` binary (not `--backend-only`) under the runner's actual cocoa session (`QT_QPA_PLATFORM` deliberately left unset), watches it for an 18s dwell window, then terminates it and asserts both that it survived the full dwell and that no new `.ips` crash report appeared under `~/Library/Logs/DiagnosticReports`.
- **Empirical, not assumed, validation of both layers** — see Evidence below.

## Task Commits

1. `66b91d9` — **fix(05-02):** stop crashing ~2s after launch on macOS by removing app-wide event filter
2. `11ea28f` — **test(05-02):** add structural guard against reintroducing QApplication-wide event filter
3. `3f061a5` — **ci(05-02):** add GUI-launch smoke gate to build-macos for the 05-06 crash class
4. `4281df7` — **fix(05-02):** avoid bash 3.2 unbound-variable bug in GUI smoke test step
5. `995e6a3` — **fix(05-02):** explicitly disable inherited `-e` in GUI smoke test so full diagnostics run
6. `26190e7` — **fix(05-02):** give ReportCrash time to flush `.ips` before comparing crash reports

All commits pushed directly to `origin/main` per pre-authorization.

## Files Created/Modified

- `launch_app.py` — `DesktopApplication(QApplication)` subclass overriding `event()`, replacing `MacQuitEventFilter(QObject)` + `installEventFilter`
- `tests/test_macos_desktop_runtime.py` — new `QApplicationEventFilterGuardTests` class (2 tests), AST-based structural guard
- `.github/workflows/build-release.yml` — new `GUI launch smoke test (real Cocoa event loop — 05-06 crash regression gate)` step in `build-macos`

## Decisions Made

See `key-decisions` in frontmatter. The most consequential one: the CI gate script needed three rounds of real-CI-driven debugging before it was trustworthy, and one of those bugs (`bash -e` inherited from GitHub Actions' shell wrapper) would have made the gate **falsely fail even on the fix** — every non-crash termination path (`kill -TERM` + `wait`) returns a nonzero exit status from the signal, which `errexit` treats as a script-ending failure just as readily as a real crash's `139`. This was caught and fixed *before* validating the fix on `main`, avoiding a misleading false-negative CI run.

## Deviations from Plan

### Auto-fixed Issues (Rule 3 — blocking, discovered mid-implementation of the CI gate itself)

**1. [Rule 3 - Blocking] bash 3.2 unbound-variable bug on `$VAR` adjacent to non-ASCII text**
- **Found during:** First real `workflow_dispatch` validation run (`30408031397`) against the buggy-code scratch branch
- **Issue:** macOS ships an ancient GPLv2 `/bin/bash` 3.2 (Apple can't upgrade past GPLv2 for licensing reasons); this build has a known parser bug where `$VAR` immediately followed by a multi-byte UTF-8 character (no ASCII separator) under `set -u` misparses the variable-name boundary and raises a spurious `unbound variable` error. `"$APP_PID，持续观察"` (fullwidth comma directly after the variable) tripped this, aborting the step before it could even launch the app.
- **Fix:** Inserted an ASCII space/parenthesis: `"$APP_PID (持续观察 ...)"`.
- **Files modified:** `.github/workflows/build-release.yml`
- **Verification:** Reproduced and confirmed locally against the same system bash 3.2 build (`bash --version` → `GNU bash, version 3.2.57(1)-release`); confirmed the exact same source pattern is not present anywhere else in the file (regex-scanned).
- **Committed in:** `4281df7`

**2. [Rule 3 - Blocking] GitHub Actions' inherited `bash -e` aborting the script before diagnostics print**
- **Found during:** Second real validation run (`30408314357`) — the gate correctly failed (exit 139 from the segfault) but printed none of its own custom diagnostic summary
- **Issue:** `shell: bash` wraps the entire `run:` block in `bash -e -o pipefail`. A script-local `set -uo pipefail` does **not** turn off that inherited `-e`. When `wait "$APP_PID"` returned a nonzero exit status (139 for the crash, but *also* 143 for an intentional `kill -TERM` on the healthy/PASS path), `errexit` aborted the script immediately — before reaching the crash-report comparison or the FAIL/PASS summary. This would have made the gate **falsely fail on correctly-fixed code too**, since the graceful-termination path also returns nonzero from `wait`.
- **Fix:** Changed `set -uo pipefail` to `set +e -uo pipefail`, explicitly overriding the inherited `-e`.
- **Files modified:** `.github/workflows/build-release.yml`
- **Verification:** Reproduced locally with `bash -e -o pipefail script.sh` on both a simulated crash and a simulated healthy-terminate scenario — without the fix, both prematurely aborted before reaching the summary; the healthy-terminate case even exited nonzero (143), which would have been a false-positive gate failure. With the fix, both reach the full summary and exit with the intended, controlled code.
- **Committed in:** `995e6a3`

**3. [Rule 1 - Bug] Crash-report file comparison raced against the ReportCrash daemon**
- **Found during:** Third validation run (`30408617294`) — the gate correctly failed via the primary signal (process died at 4s, exit 139), but the secondary "new crash report" comparison found nothing even though the process demonstrably segfaulted
- **Issue:** macOS's `ReportCrash` daemon writes the `.ips` file asynchronously after the process dies; comparing the crash-report directory immediately after detecting process death is a race that can (and did) miss the report.
- **Fix:** Added a 3s settle `sleep` before the crash-report comparison. Does not affect the FAIL determination (already correctly fires off the `SURVIVED` flag + signal-specific exit code, proven reliable across all three buggy-code runs); this only makes the secondary diagnostic more likely to also carry evidence.
- **Files modified:** `.github/workflows/build-release.yml`
- **Committed in:** `26190e7`
- **Note:** This fix was applied to `main` directly without a fourth dedicated buggy-branch validation cycle — it only adds a delay and touches no FAIL/PASS branching logic that hadn't already been proven correct in the prior two runs. Documented here for full transparency rather than re-spending CI time to re-prove a change that cannot affect the gate's pass/fail outcome.

---

**Total deviations:** 3 auto-fixed (all Rule 3/Rule 1, all in the CI gate script itself — the `launch_app.py` fix and the AST guard test needed no deviations)
**Impact on plan:** All three were necessary to get the CI gate to a trustworthy state; #2 in particular was caught before it could produce a misleading false-negative "PASS" run against buggy code disguised as a script bug, or a false "FAIL" against the actual fix. No scope creep — all changes stayed within `.github/workflows/build-release.yml`'s new step.

## Evidence (Honesty Requirement — Layer 2 CI Gate)

**What the gate uses:** The real `cocoa` Qt platform plugin (`QT_QPA_PLATFORM` intentionally left unset) on GitHub's `macos-15` hosted runner, launching the actual signed, dmg-ready `.app` binary — not `--backend-only`, not `offscreen`. This was an empirical choice, not an assumption: the runner does have a real logged-in cocoa/WindowServer session capable of creating, showing, and focusing real `NSWindow`s, confirmed by the fact that the exact crash reproduced on it.

**Buggy-code runs (pre-fix commit, scratch branch, 2 runs after the script itself was fixed):**
- Run `30408314357`: launched at `23:34:41.13`, `Segmentation fault: 11` at `23:34:44.43` (~3.3s), `SURVIVED=0` detected at second 4, step exit code `139`.
- Run `30408617294` (final, with all script fixes): launched at `23:40:49.585`, `Segmentation fault: 11` at `23:40:52.946` (~3.36s — closely matching the diagnosed "~2s" real-machine timing plus CI overhead), full diagnostic summary printed: `错误: GUI 进程未能存活满 18s(第 4s 时已消失)` → `错误: GUI 冒烟测试失败 —— 这正是 05-06 real-machine checkpoint 抓到的「双击后 ~2s 内 SIGSEGV」崩溃路径`. Step correctly failed.
- (A first attempt, run `30408031397`, also failed the step, but on the bash-3.2 script bug rather than the intended crash-detection logic — see Deviation #1. Not counted as gate evidence; documented for transparency.)

**Fixed-code run (`main`, commit `26190e7`, run `30408816656`):**
- Launched at `23:45:17.716`, survived the full 18s dwell with **zero** early-exit detection, then intentionally terminated via `kill -TERM` (`存活满 18s，未观察到进程提前退出，主动终止(SIGTERM，非崩溃信号)`), exit code `143` (a signal-terminated but non-crash exit), zero new crash reports found, final line: `GUI 冒烟测试通过: 进程在真实 cocoa 事件循环下存活 18s，期间无新增崩溃报告`. `build-macos` job: all 21 steps succeeded. Overall workflow run: **green** (`build` and `build-macos` both `success`; `release` correctly `skipped` since this was `workflow_dispatch` on a branch, not a tag push, per D-04).

**What this gate DOES cover:** The exact crash class this gap-fix addresses — a process-wide SIGSEGV during/shortly after main-window `show()`/`activateWindow()` on macOS, driven by real Cocoa window-focus delivery. Proven to both catch the bug on buggy code (2/2 real runs) and pass cleanly on the fix (1/1 real run, 18s full survival).

**What this gate does NOT cover (stated plainly, not overclaimed):**
- It is a **crash gate**, not a functional/behavioral test — it does not assert the web page actually finished loading, that the UI is visually correct, or that user interactions (clicks, typing) work. It only proves the process doesn't die unexpectedly during the dwell window.
- The **secondary** "new crash report" signal has a known async-write race with macOS's `ReportCrash` daemon (Deviation #3); a 3s settle delay was added but this secondary channel was never independently proven reliable — the **primary** signal (process-survival + signal-specific exit code from `wait`) is the one empirically proven reliable across all validation runs, and is sufficient on its own to fail the step.
- It does not touch quarantine/Gatekeeper/App-Translocation behavior — that remains the domain of the separate 05-06 real-machine checkpoint (D-12a), which this gap-fix does not re-litigate per the task's explicit scope boundary.
- CI runner cocoa sessions may differ from a physical user's Mac in ways not yet characterized (no attached display, virtualized GPU); the fact that this specific bug reproduced identically in both environments is evidence the CI environment is representative *for this bug class*, not a general guarantee for all GUI bugs.
- 18s was chosen as a dwell time comfortably larger than the observed ~2-3.4s crash window (both real-machine and CI-observed); it is not a proof that no crash could occur later, only that this specific, already-diagnosed crash pattern (which occurs during/immediately after window show) is caught.

## Local Reproduction (Additional, Non-CI Evidence)

Independent of the CI runs above, the previously-installed buggy `.app` (from an earlier CI build, still present at `/Applications/Open-Anti-Browser.app` on this development machine) was launched directly:
- Crash-report count went from 3 → 4 after `open /Applications/Open-Anti-Browser.app` + 6s wait; `ps` confirmed no process remained.
- The new crash report's thread-0 (`CrBrowserMain`) stack matched the diagnosed pattern exactly: `PySide::typeName(QObject const*)` → `PySide::getWrapperForQObject` → `QObjectWrapper::sbk_o_eventFilter` → `QObjectWrapper::eventFilter` → `QCoreApplicationPrivate::sendThroughApplicationEventFilters`.
- The AST structural guard test was independently run against `git show 580b269:launch_app.py` (the pre-fix source) and correctly flagged the `installEventFilter` call.

## Issues Encountered

None beyond the three CI-gate-script deviations documented above, all resolved. `.venv/bin/python -m unittest discover -s tests` (116 tests, 2 skipped) and `node --test frontend/src/lib/*.test.js` (43 tests) both pass with no regressions.

## User Setup Required

None. All fixes are code/CI changes; no external service configuration needed.

## Fresh dmg for Re-Verification

- **Location:** `~/Downloads/Open-Anti-Browser-0.1.16-arm64.dmg` (the previous, buggy dmg used in the original 05-06 checkpoint session was moved to `~/Downloads/old-buggy-dmg-05-06-checkpoint/` and renamed with a `-BUGGY-crashes-on-launch` suffix so it's unambiguous which is which)
- **Source run:** `workflow_dispatch` run `30408816656` on `main` at commit `26190e7`, `build-macos` job `success`, artifact `Open-Anti-Browser-macos-dmg`
- **Quarantine:** Manually tagged with a synthetic `com.apple.quarantine` xattr (`0083;<timestamp>;Chrome;<uuid>`) to simulate a real browser download, matching the 05-06 plan's Task 1 protocol, since this was downloaded via `gh run download` (which does not set quarantine) rather than a browser
- **SHA-256:** `5a2cc5764fe981b3cf802167439df47e51331ca189fc63989df65e4b6736d3be`

## Next Phase Readiness

- The 05-06 real-machine checkpoint (`.planning/phases/05-ci/05-06-PLAN.md`) can now be re-run against this fresh dmg. Everything in that plan's checkpoint task remains valid and unmodified by this gap-fix — this gap-fix only fixed the blocking crash defect and added regression coverage for it; it did not touch quarantine/D-12a logic, dmg packaging, icon/background assets, or any of the other things 05-06 verifies.
- No blockers.

---
*Phase: 05-ci*
*Completed: 2026-07-28*

## Self-Check: PASSED

- FOUND: `launch_app.py` — `DesktopApplication` class present, `installEventFilter` absent
- FOUND: `tests/test_macos_desktop_runtime.py` — `QApplicationEventFilterGuardTests` present, 23 tests total, all passing
- FOUND: `.github/workflows/build-release.yml` — `GUI launch smoke test` step present in `build-macos`
- FOUND: commit `66b91d9` (fix)
- FOUND: commit `11ea28f` (test)
- FOUND: commit `3f061a5` (ci)
- FOUND: commit `4281df7` (fix)
- FOUND: commit `995e6a3` (fix)
- FOUND: commit `26190e7` (fix)
- FOUND: `~/Downloads/Open-Anti-Browser-0.1.16-arm64.dmg` (fresh, quarantined, from run 30408816656)
- FOUND: workflow run `30408816656` — conclusion `success`
