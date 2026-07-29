---
phase: 05-ci
plan: 02-gap-fix-2
subsystem: infra
tags: [pyside6, qt, macos, cmd-q, ci, github-actions, bash, event-loop, applescript]

# Dependency graph
requires:
  - phase: 05-ci
    provides: "05-02-GAP-FIX (installEventFilter SIGSEGV fix) and its 05-06 real-machine re-run, which found the app now launches fine but Cmd+Q spins the process forever instead of exiting"
provides:
  - "launch_app.py: DesktopApplication.event() now always forwards the delivered event to super().event(e) after running the macOS Quit shutdown side effect, instead of `return True`-swallowing it -- restoring QCoreApplication's own default Quit handling (the thing that actually stops the event loop)"
  - "launch_app.py: DesktopMainWindow.force_exit() gained a `_closing` idempotency guard so a re-entrant Quit event can't re-showNormal() a window mid-shutdown"
  - "AST structural guard (MacQuitEventLoopConvergenceTests) pinning both of the above shapes so this exact regression cannot silently return"
  - "build-macos GUI smoke gate gained a second dimension: after the existing 18s crash-survival dwell, sends a real Quit request (osascript, same Apple Event path as Cmd+Q) and asserts the process exits within a bounded 12s timeout with no residual process -- empirically proven to FAIL on the pre-fix shape and PASS on the fix"
affects: [05-06-real-machine-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QCoreApplication::event()'s default handling of QEvent.Type.Quit is what actually calls quit() to stop the event loop -- an override that does side effects then `return True`s bypasses it entirely and nothing else in the call chain substitutes for it correctly on macOS."
    - "On macOS, calling QApplication.quit()/exit() asynchronously (e.g. via QTimer.singleShot(0, ...)) outside the direct synchronous handling of a currently-pending Cocoa termination query re-triggers Cocoa's applicationShouldTerminate: protocol from scratch, posting another QEvent.Quit rather than completing the pending one -- the fix is to let quit() happen synchronously inside the same event() call that received the Quit event, not deferred."
    - "CI GUI-lifecycle gates need two independent dimensions for this bug class: process-survives-a-dwell (catches crash-too-early) and process-exits-after-a-real-quit-request (catches spins-forever-too-well); the first one provably cannot catch the second failure mode, and vice versa."
    - "osascript's own exit code is not a reliable signal that an Apple Event failed to reach a running unregistered/adhoc-signed app -- confirmed empirically that `tell application \"X\" to quit` can return a reply-timeout error (`User canceled (-128)`) while the event was in fact delivered and processed; the only trustworthy pass/fail signal is the observed process state (kill -0 polling), not the sender's exit code."

key-files:
  created:
    - .planning/phases/05-ci/05-02-GAP-FIX-2-SUMMARY.md
  modified:
    - launch_app.py
    - tests/test_macos_desktop_runtime.py
    - .github/workflows/build-release.yml

key-decisions:
  - "Fix shape: DesktopApplication.event() no longer gates a `return True` on handle_macos_quit_request(...)'s return value. It always runs the shutdown side effect (still via the single existing handle_macos_quit_request() -> window.force_exit() path, no parallel shutdown logic invented) and then unconditionally forwards the event to super().event(e), letting Qt's own default Quit handling run synchronously in the call stack that's actually processing the pending Cocoa termination query."
  - "force_exit() got a `_closing` idempotency guard (skip showNormal()/close() if shutdown() already ran) because the pre-existing closeEvent() QTimer.singleShot(0, quit) can still cause a second Quit event to reach event() asynchronously; without the guard that second pass would re-show a window mid-shutdown."
  - "CI gate quit mechanism: `osascript -e 'tell application \"Open-Anti-Browser\" to quit'`, chosen because it sends the same kAEQuitApplication Apple Event that a user's Cmd+Q or Dock-menu Quit takes -- not a POSIX signal, which Qt never translates into QEvent.Quit and so could not exercise this bug class at all. Verified this pragmatically by first reproducing the exact bug signature locally against the already-installed buggy .app before writing the CI step, then confirming the same signature (process survives, doesn't crash, spins at high CPU, backend port releases) on the real GitHub-hosted runner."
  - "The gate deliberately does NOT use osascript's own exit code as the pass/fail signal -- empirically, on both the local machine and the CI runner, osascript returned a nonzero 'User canceled' reply-timeout error even when the Apple Event was demonstrably delivered and processed (CPU jumped, port released). The only trustworthy signal is polling the target process's actual liveness."

requirements-completed: []

coverage:
  - id: D1
    description: "launch_app.py: DesktopApplication.event() always forwards to super().event(e) after the macOS Quit shutdown side effect, instead of swallowing the event with an early `return True`; force_exit() gained a `_closing` idempotency guard against re-entrant Quit events"
    requirement: "PKG-02"
    verification:
      - kind: unit
        ref: "tests/test_macos_desktop_runtime.py#MacQuitEventLoopConvergenceTests (new, 2 tests) -- AST structural guard, proven to FAIL against the pre-fix source shape and PASS against the fix (verified by temporarily swapping launch_app.py for the pre-fix version and back)"
        status: pass
      - kind: e2e
        ref: "workflow_dispatch run 30418547844 (main, commit acfcc9a) -- GUI launch smoke test step PASSED: 18s crash-survival dwell held, Quit request delivered, process exited cleanly (exit code 0) within 2s, zero residual processes"
        status: pass
    human_judgment: true
    rationale: "Same rationale as the first 05-02 gap-fix: this defect class was discovered by a real macOS machine, not CI or unit tests, and the correct closure is the user re-running the actual 05-06 real-machine checkpoint (feel of Cmd+Q, no lingering process in Activity Monitor) against the fresh dmg this run produced."
  - id: D2
    description: "build-macos GUI smoke gate extended with a second dimension: after the existing 18s survival dwell, send a real Quit request and assert the process exits within a bounded 12s timeout with no residual process -- proven, with real workflow_dispatch evidence, to FAIL on the pre-fix code and PASS on the fix"
    requirement: "PKG-02"
    verification:
      - kind: e2e
        ref: "workflow_dispatch run 30418065169 (scratch/verify-cmdq-exit-gate, pre-fix launch_app.py restored) -- GUI launch smoke test step FAILED: 18s dwell survived (not a crash), Quit request sent, process still alive after full 12s timeout at 113.7% CPU, step correctly failed with the Cmd+Q-infinite-loop diagnostic message, process force-killed for runner cleanup, exit code 137"
        status: pass
      - kind: e2e
        ref: "workflow_dispatch run 30418547844 (main, commit acfcc9a, post-fix code) -- GUI launch smoke test step PASSED: 18s dwell survived, Quit request sent, process exited cleanly within 2s (exit code 0), zero residual processes, full success message printed"
        status: pass
      - kind: other
        ref: "Local, non-CI reproduction on this dev machine's already-installed buggy .app (built from the first 05-02 gap-fix, predates this second fix): sent the exact same osascript quit command used in the CI step; CPU jumped from ~1% to 60.2%, TCP port 8000 released (backend genuinely shut down), process still alive 8s later. Confirms the mechanism reproduces the real bug before spending CI minutes on it."
        status: pass
    human_judgment: false
  - id: D3
    description: "Full local test suite (118 Python unittest cases, 2 skipped as Windows-only -- 2 more than the first gap-fix's 116, from the new MacQuitEventLoopConvergenceTests) and full frontend test suite (43 node:test cases) still pass after the fix"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m unittest discover -s tests"
        status: pass
      - kind: unit
        ref: "node --test frontend/src/lib/*.test.js"
        status: pass
    human_judgment: false

# Metrics
duration: ~55min (diagnosis was pre-supplied; fix + tests + CI gate + two real workflow_dispatch validation runs)
completed: 2026-07-29
status: complete
---

# Phase 5 Plan 02 Gap-Fix 2: macOS Cmd+Q Infinite Quit Loop Summary

**Fixed the second defect in D-07's Cmd+Q feature -- surfaced by the 05-06 real-machine checkpoint re-run after the first gap-fix's crash was already resolved -- where `DesktopApplication.event()` swallowed the Quit event with an early `return True`, starving `QCoreApplication`'s own default Quit handling (the thing that actually stops the event loop) and leaving the process spinning at ~60% CPU forever instead of exiting. Extended the CI GUI smoke gate with a second dimension (real Quit request -> bounded-timeout exit assertion) that the crash-survival-only gate provably could not catch, and validated both the fix and the new gate with real `workflow_dispatch` runs against buggy and fixed code.**

## Performance

- **Duration:** ~55 min total (diagnosis pre-supplied by the task, not re-derived) -- fix + AST tests: ~20 min; CI gate script + local bash-3.2 syntax/pattern validation: ~15 min; two real `workflow_dispatch` CI validation runs (buggy-branch FAIL proof + main PASS proof): ~20 min wall-clock (parallel-ish polling, each run ~10-13 min)
- **Completed:** 2026-07-29
- **Commits:** 3
- **Files modified:** 3 (`launch_app.py`, `tests/test_macos_desktop_runtime.py`, `.github/workflows/build-release.yml`)

## Diagnosis Recap (pre-supplied by the task, not re-derived)

`DesktopApplication.event()` (from the first 05-02 gap-fix) did:
```python
def event(self, e) -> bool:
    if (
        e.type() == QEvent.Type.Quit
        and self.target_window is not None
        and handle_macos_quit_request(self.target_window)  # unconditionally returns True
    ):
        return True          # super().event(e) NEVER runs
    return super().event(e)
```
`QCoreApplication::event()`'s default handling of `QEvent::Quit` is what actually calls `quit()` to terminate the event loop -- by always `return True`-ing first, that path was never reached, not once. The observed symptom: Cmd+Q closed the window, hid the tray icon, and genuinely stopped the backend (port 8000 released -- `shutdown()` ran), but the process itself never exited, spinning at ~60% CPU indefinitely (`sample` showed 100% of samples in `QCoreApplicationPrivate::sendPostedEvents`). `closeEvent()`'s own `QTimer.singleShot(0, QApplication.instance().quit)` called `quit()` asynchronously, which on macOS re-triggers Cocoa's termination protocol from scratch (posts a new `QEvent::Quit`) rather than completing the already-pending one -- that new event was swallowed by the same buggy `event()`, forever.

Critically: this was **not a regression introduced by the first gap-fix**. The original `installEventFilter` implementation had the identical logical flaw (an event filter returning `True` also blocks delivery to `QApplication`), so D-07's Cmd+Q feature has never actually worked in any shipped form -- the launch crash simply prevented anyone from ever getting far enough to press Cmd+Q and discover it.

## Accomplishments

- **The fix (`launch_app.py`):** `DesktopApplication.event()` now always calls `super().event(e)` after running the shutdown side effect via `handle_macos_quit_request(...)` (still the single existing `force_exit()` path -- no second shutdown mechanism was invented). This lets Qt's own default Quit handling run synchronously inside the same call stack that's processing the pending Cocoa termination query, which is what actually stops the event loop for real. `DesktopMainWindow.force_exit()` also gained a `_closing` idempotency guard, since the pre-existing `QTimer.singleShot(0, quit)` in `closeEvent()` can still cause a second Quit event to reach `event()` asynchronously (shared by the tray "退出程序" and API exit paths too) -- without the guard, that second pass would call `showNormal()` on a window that's already mid-shutdown.
- **AST structural guard (`tests/test_macos_desktop_runtime.py`):** `MacQuitEventLoopConvergenceTests` (2 new tests) statically pins both shapes: `event()` must have exactly one `return` in its entire body (walking the full subtree, not just top-level statements -- a naive top-level-only count is vacuous for this exact bug, since the buggy `if ...: return True` / trailing `return super().event(e)` shape produces exactly one top-level `Return` node), and that return must be an unconditional `return super().event(e)`; `force_exit()` must open with `if self._closing: return`. Verified both tests genuinely FAIL against the restored pre-fix source and PASS against the fix.
- **CI GUI smoke gate, second dimension (`.github/workflows/build-release.yml`):** After the existing 18s crash-survival dwell (unchanged, still catches the first gap-fix's crash class), the gate now sends a real Quit request via `osascript -e 'tell application "Open-Anti-Browser" to quit'` -- the same `kAEQuitApplication` Apple Event path Cmd+Q and the Dock-menu Quit item take, not a POSIX signal (which Qt never translates into `QEvent.Quit` and so could never exercise this bug class) -- then polls for the process to disappear within a bounded 12s timeout, and separately asserts no residual process remains afterward.
- **Empirical, not assumed, validation of the new gate dimension** -- see Evidence below, including proof the gate genuinely fails on buggy code (not a false pass from an unrelated mechanism).

## Task Commits

1. `4ae6539` — **fix(05-02):** stop Cmd+Q infinite quit loop by always forwarding to super().event()
2. `dd8e372` — **test(05-02):** AST guard against the Cmd+Q infinite quit loop regressing
3. `acfcc9a` — **ci(05-02):** extend GUI smoke gate to assert Cmd+Q actually exits the process

All commits pushed directly to `origin/main` per pre-authorization.

## Files Created/Modified

- `launch_app.py` — `DesktopApplication.event()` unconditional `super().event(e)` forward; `DesktopMainWindow.force_exit()` `_closing` idempotency guard
- `tests/test_macos_desktop_runtime.py` — new `MacQuitEventLoopConvergenceTests` class (2 tests), AST-based structural guard
- `.github/workflows/build-release.yml` — extended `GUI launch smoke test` step in `build-macos` (renamed to reflect both crash and exit dimensions) with the quit-and-verify-exit + residual-process-assertion logic

## Decisions Made

See `key-decisions` in frontmatter. The most consequential one: the CI gate's quit mechanism (`osascript ... to quit`) was chosen and *validated locally against the already-installed buggy build* before writing a single line of the CI step, specifically to avoid shipping a gate whose "quit trigger" turned out to be a no-op or a signal-based kill that would pass even on buggy code. That local check also surfaced a real gotcha carried into the CI script: `osascript`'s own exit code is not a trustworthy pass/fail signal (it returned `User canceled (-128)` on both the local machine and the CI runner even when the Apple Event was demonstrably delivered and processed) -- so the gate's actual pass/fail logic is driven entirely by polling the target process's liveness, not by `osascript`'s exit status.

## Deviations from Plan

None. No auto-fixes were needed beyond the fix itself -- the CI gate script passed `bash -n` syntax checks against the real macOS system bash 3.2 on the first attempt (the first gap-fix's bash-3.2/`set -e` lessons were applied proactively this time, not discovered mid-validation), and both real `workflow_dispatch` runs produced clean, unambiguous evidence on the first attempt for each branch.

## Evidence (Honesty Requirement — Layer 2 CI Gate Extension)

**What the gate's new dimension uses:** `osascript -e 'tell application "Open-Anti-Browser" to quit'`, sent to the real, running `.app` process on GitHub's `macos-15` hosted runner (same real cocoa/WindowServer session the first gap-fix's crash-survival dimension already relies on, `QT_QPA_PLATFORM` still deliberately left unset).

**Local pre-CI sanity check (against this dev machine's already-installed buggy `.app`, built from the first 05-02 gap-fix, predates this fix):**
- Launched `/Applications/Open-Anti-Browser.app`, confirmed PID alive, port 8000 listening (`lsof -i :8000` showed `LISTEN`).
- Ran the exact same osascript command: returned `execution error: ... User canceled. (-128)`, exit code 1.
- 8 seconds later: process still alive, CPU jumped from ~1.3% to **60.2%**, port 8000 **released** (`lsof -i :8000` empty) -- this is the exact bug signature from the diagnosis (backend genuinely shuts down, process itself never exits). Confirms the mechanism reliably delivers a real Quit event and reproduces the bug, before spending any CI minutes on it.
- Cleaned up with `pkill -9 -f Open-Anti-Browser`.

**Buggy-code CI run (`scratch/verify-cmdq-exit-gate`, pre-fix `launch_app.py` restored on top of the new CI gate, run `30418065169`):**
- `02:55:56` step started, GUI process launched (PID 10311).
- `02:56:16` — survived the full 18s dwell (`存活满 18s，未观察到进程提前退出(未崩溃)`) -- proving the *first* dimension alone would have falsely PASSED this buggy code, exactly the gap this extension closes.
- `02:56:16` — Quit request sent (`osascript` exit code 1, same reply-timeout as the local check).
- `02:56:30` — 12s timeout expired, process still alive: `ps -p 10311` showed **113.7% CPU**, `00:34` elapsed since Quit was sent.
- Step correctly FAILED with the diagnostic: `进程在收到 Quit 请求后 12s 内仍未退出 —— 这正是 05-06 二次 real-machine checkpoint 抓到的 Cmd+Q 无限循环缺陷...`.
- Process force-killed (`kill -9`) for runner cleanup; final `wait` exit code `137`; residual-process assertion afterward correctly found nothing (cleanup succeeded).
- Overall run conclusion: `failure` (as required). Scratch branch deleted after the run completed (both local and `origin`).

**Fixed-code CI run (`main`, commit `acfcc9a`, run `30418547844`):**
- `03:06:44` step started, GUI process launched (PID 14652).
- `03:07:04` — survived the full 18s dwell.
- `03:07:04` — Quit request sent (`osascript` exit code 1, same expected reply-timeout, correctly not treated as a failure signal).
- `03:07:06` — process exited **2 seconds** after the Quit request, exit code **0** (a clean, non-signal exit -- notably better than the crash-survival dimension's old `kill -TERM` cleanup path, which always exits via SIGTERM/143).
- Residual-process assertion: `断言通过: 未检测到残留进程`.
- Final message: `GUI 冒烟测试通过: 进程在真实 cocoa 事件循环下存活 18s 且期间无新增崩溃报告，随后收到 Quit 请求(与 Cmd+Q 同路径)后 2s 内干净退出，无残留进程`.
- Overall run conclusion: `success` (`build` and `build-macos` both `success`, `release` correctly `skipped` for a non-tag `workflow_dispatch`, per D-04).

**What this gate DOES cover (both dimensions together):** The exact two defect classes the 05-06 real-machine checkpoint has now found in this feature across two gap-fixes -- (1) a process-wide SIGSEGV during/shortly after main-window show (first gap-fix, unchanged), and (2) the process surviving a real Cmd+Q-equivalent Quit request without ever actually terminating (this gap-fix). Both proven, with real CI evidence, to catch the corresponding buggy code and pass cleanly on the corresponding fix.

**What this gate does NOT cover (stated plainly, not overclaimed):**
- It still does not assert the web page finished loading, that the UI is visually correct, or that user interactions work -- same limitation as the first gap-fix's dimension, now also true of the second.
- It does not distinguish *why* a Quit request was accepted quickly (e.g. it would not catch a hypothetical future regression where Cmd+Q exits "too fast" by skipping `shutdown()`'s real cleanup work entirely) -- it only proves the process eventually disappears and the backend port is not the process's own concern to re-verify here (the crash-survival dimension's diagnostic log capture would still surface an obviously broken shutdown, but there's no explicit port-8000-released assertion in the gate itself; this was checked manually in the local pre-CI sanity check and in the 05-06 checkpoint's original diagnosis, not asserted in CI).
- The tray "退出程序" and API-triggered exit paths are not independently exercised by this gate -- only the Cmd+Q-equivalent Apple Event path is. Per the fix's design, both routes converge on the same `force_exit()` -> `closeEvent()` -> `shutdown()` chain, so a regression there would likely also surface in this gate's dimension, but that inference is not itself proven by a dedicated CI step; the 05-06 real-machine checkpoint's task list already covers the tray-menu path with a human verification step.
- 12s was chosen as a timeout comfortably larger than the observed 2s clean-exit time (fixed code) while still clearly distinguishing a real hang (buggy code was still spinning well past 12s, unbounded) from a slow-but-legitimate shutdown; it is not a proof that no future regression could introduce, say, a 15s legitimate shutdown delay that would false-positive this gate -- if `shutdown()`'s server-thread join timeout (currently 8s) is ever increased, this gate's 12s window should be revisited accordingly.

## Local Reproduction (Additional, Non-CI Evidence)

Covered above under "Local pre-CI sanity check" -- performed *before* writing the CI script (not after, unlike the first gap-fix's pattern of debugging the gate against real CI runs) specifically to front-load the "does this quit mechanism even work" question the task's honesty requirement calls out, rather than discovering a worthless gate only after spending CI minutes on it.

## Issues Encountered

None. Both real `workflow_dispatch` validation runs produced the expected result on the first attempt; no CI-script debugging cycles were needed this time (unlike the first 05-02 gap-fix, which needed 3 rounds against bash 3.2 / GitHub Actions `-e` semantics / ReportCrash timing -- those lessons were applied proactively here: `set +e -uo pipefail` was used from the start, and no unbraced `$VAR` was placed adjacent to non-ASCII text anywhere in the new script, verified with a dedicated regex scan against the actual system bash 3.2 before the first CI run).

## User Setup Required

None. All fixes are code/CI changes; no external service configuration needed.

## Fresh dmg for Re-Verification

- **Source run:** `workflow_dispatch` run `30418547844` on `main` at commit `acfcc9a`, `build-macos` job `success`, artifact `Open-Anti-Browser-macos-dmg` (artifact id `8711137405`, 371,040,420 bytes)
- **Not yet downloaded to this machine** -- unlike the first gap-fix, this summary does not include a local `~/Downloads` copy; the user should `gh run download 30418547844 -n Open-Anti-Browser-macos-dmg` (or via the Actions UI) to fetch it, then apply the same synthetic quarantine xattr protocol from the 05-06 plan's Task 1 if downloading via `gh` rather than a browser.
- **Windows installer artifact** from the same run: `Open-Anti-Browser-Setup` (artifact id `8711188867`, 399,424,782 bytes) — Windows job was untouched by this gap-fix (out of scope per the task), included here only because it's part of the same green run.

## Next Phase Readiness

- The 05-06 real-machine checkpoint (`.planning/phases/05-ci/05-06-PLAN.md`) can now be re-run against this fresh dmg, specifically re-covering section C's three exit paths (Cmd+Q / red-X / tray "退出程序"). Cmd+Q should now genuinely terminate the process (window gone, tray icon gone, Dock entry gone, `ps` shows no residual process) instead of spinning.
- No blockers.

---
*Phase: 05-ci*
*Completed: 2026-07-29*

## Self-Check: PASSED

- FOUND: `launch_app.py` — `DesktopApplication.event()` has exactly one `return super().event(e)`, no early `return True`; `force_exit()` opens with `if self._closing: return`
- FOUND: `tests/test_macos_desktop_runtime.py` — `MacQuitEventLoopConvergenceTests` present, 118 tests total, all passing
- FOUND: `.github/workflows/build-release.yml` — extended `GUI launch smoke test (real Cocoa event loop — crash + Cmd+Q exit regression gate)` step present in `build-macos`
- FOUND: commit `4ae6539` (fix)
- FOUND: commit `dd8e372` (test)
- FOUND: commit `acfcc9a` (ci)
- FOUND: workflow run `30418065169` (scratch branch, buggy code) — conclusion `failure`, correct dimension (Cmd+Q exit timeout), scratch branch deleted after use
- FOUND: workflow run `30418547844` (main, fixed code) — conclusion `success`
