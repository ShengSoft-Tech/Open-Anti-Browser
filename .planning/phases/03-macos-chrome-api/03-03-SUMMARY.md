---
phase: 03-macos-chrome-api
plan: 03
subsystem: launch
tags: [launch, quarantine, gatekeeper, amfi, macos, real-machine-verify]

# Dependency graph
requires:
  - phase: 03-macos-chrome-api (plan 01)
    provides: GET /api/capabilities — real-machine XPLAT-05 spot-check
  - phase: 03-macos-chrome-api (plan 02)
    provides: graceful kill_process_tree — real-machine LAUNCH-03 no-residue confirmation
provides:
  - "backend/services/chrome.py: darwin-only best-effort quarantine strip on the kernel .app bundle before Popen launch"
  - "_strip_quarantine_if_present(path) — recursive xattr -dr com.apple.quarantine, best-effort (never blocks launch)"
  - "D-07 empirical conclusion: freshly browser-downloaded ad-hoc kernel is AMFI-killed (exit 137) unless the WHOLE .app bundle is de-quarantined"
affects: [phase 05 (CI dmg packaging — kernel carries quarantine on browser download; needs whole-bundle strip or notarization), phase 06 (docs — Gatekeeper/quarantine guidance)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "macOS kernel launch hardening: walk up executable_path.parents to the .app bundle root, xattr -dr com.apple.quarantine on the bundle (framework dylib + helpers all carry quarantine; stripping only the main binary is insufficient — AMFI SIGKILLs on framework load)"
    - "quarantine strip target stays scoped to the backend-resolved kernel .app bundle (no wildcard, no user input — T-3-03 EoP mitigation preserved)"

key-files:
  created: []
  modified:
    - backend/services/chrome.py
    - tests/test_launch_geo_fallback.py

key-decisions:
  - "D-07 RESOLVED ON REAL HARDWARE (contradicts research MEDIUM-confidence assumption): a freshly browser-downloaded, ad-hoc-signed arm64 149 kernel launched via raw nested-binary Popen is SIGKILLed at launch (exit 137, AMFI/code-signing layer — NOT a Gatekeeper prompt). Stripping com.apple.quarantine makes it launch. The strip hook is therefore LOAD-BEARING for macOS launch, not merely defensive."
  - "BUG FOUND + FIXED (fbac808): the original hook (Task 1, commit 8cf3e13) stripped quarantine from the main binary only; the Chromium Framework dylib + helper binaries (all 452 bundle files carry quarantine after ditto) stayed quarantined, so AMFI still killed the process when the stripped binary loaded the quarantined framework. Fix: resolve the .app bundle root from executable_path and strip recursively."
  - "Sub-finding: an already-assessed quarantined app (system Chromium 148 at /Applications, quarantine flag 01c1) launches fine via raw exec — the AMFI kill is specific to FRESH/unassessed downloads (flag 0081). Confirms the hook must run on the user's just-downloaded kernel."
  - "Extension-visibility sub-item of LAUNCH-02 was NOT re-verified this session (user elected to wrap up); low risk — extension install code is cross-platform and unchanged this phase."

requirements-completed: [LAUNCH-01, LAUNCH-02, LAUNCH-03]

coverage:
  - id: D1
    description: "chrome.py strips com.apple.quarantine from the kernel .app bundle (darwin only, best-effort, scoped to backend-resolved path) before Popen launch"
    requirement: "LAUNCH-01"
    verification:
      - kind: unit
        ref: "tests/test_launch_geo_fallback.py#test_chrome_launch_strips_quarantine_from_app_bundle_root_on_darwin"
        status: pass
      - kind: unit
        ref: "tests/test_launch_geo_fallback.py#test_chrome_launch_skips_quarantine_strip_on_non_darwin"
        status: pass
      - kind: unit
        ref: "tests/test_launch_geo_fallback.py#test_chrome_launch_continues_when_quarantine_strip_raises"
        status: pass
  - id: D2
    description: "D-07 empirical probe: fresh browser-downloaded ad-hoc kernel is AMFI-killed (exit 137) while quarantined; de-quarantining the whole bundle makes it launch (CDP responds)"
    requirement: "LAUNCH-01"
    verification:
      - kind: real-machine
        ref: "arm64 real-machine probe: quarantined raw exec -> exit 137; strip whole .app bundle -> Chrome/149.0.7827.114 CDP up. Binary-only strip -> still exit 137 (framework dylib quarantine)."
        status: pass
    human_judgment: true
    rationale: "Required real arm64 hardware + a browser-downloaded (LSQuarantine) kernel — done this session on the developer's arm64 Mac."
  - id: D3
    description: "LAUNCH-01 one-click launch: fingerprint Chrome launches via app, CDP port up, session tracked, isolated user_data_dir, fingerprint params effective"
    requirement: "LAUNCH-01"
    verification:
      - kind: real-machine
        ref: "App start -> status running, CDP Chrome/149.0.7827.114; Playwright over CDP: timezone/language/UA(Windows on macOS)/platform(Win32)/hardwareConcurrency(spoofed, masks real 10)/webdriver=false all match fingerprint flags"
        status: pass
    human_judgment: true
  - id: D4
    description: "LAUNCH-02 proxy + geo match: account proxy via LocalHttpProxyBridge, browser egress IP = proxy egress, timezone/language track the egress geo"
    requirement: "LAUNCH-02"
    verification:
      - kind: real-machine
        ref: "AU account proxy -> bridge http://127.0.0.1; Playwright egress ipinfo = 115.128.181.113 Sydney AU (== app resolved_ip); JS timezone Australia/Sydney, language en-AU — all consistent, no leak"
        status: pass
    human_judgment: true
  - id: D5
    description: "LAUNCH-02 batch 2-3 isolation: concurrent profiles have distinct user_data_dir / CDP port / pid / fingerprint seed"
    requirement: "LAUNCH-02"
    verification:
      - kind: real-machine
        ref: "3 concurrent profiles: distinct user_data_dir, ports (61073/50556/50560), pids, fingerprint seeds (2097861730/53485006/533033547)"
        status: pass
    human_judgment: true
  - id: D6
    description: "LAUNCH-02 extension visibility"
    requirement: "LAUNCH-02"
    verification: []
    human_judgment: true
    rationale: "NOT re-verified this session — user elected to wrap up before installing a test extension. Low risk: extension install is cross-platform code, unchanged this phase. Follow-up: install a real extension and confirm it loads (chrome://extensions / CDP service-worker target)."
  - id: D7
    description: "LAUNCH-03 no residue after stop (single + batch), graceful termination"
    requirement: "LAUNCH-03"
    verification:
      - kind: real-machine
        ref: "stop single + batch(3) -> pgrep -f Chromium empty; ~1-2s transient helper teardown clears cleanly (Plan 02 SIGTERM->grace->SIGKILL)"
        status: pass
    human_judgment: true
  - id: D8
    description: "XPLAT-05 spot-check: GET /api/capabilities on macOS returns engines.firefox.available=false, engines.chrome.available=true"
    requirement: "XPLAT-05"
    verification:
      - kind: real-machine
        ref: "curl /api/capabilities -> platform darwin, engines.firefox.available=false, chrome=true, window.arrange/sync unavailable with reasons"
        status: pass

# Metrics
duration: real-machine-session
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 3: macOS Chrome launch finalization + arm64 real-machine acceptance Summary

**Added a darwin-only best-effort quarantine strip to the Chrome launch path and ran full arm64 real-machine acceptance. The real-machine probe overturned the research's "probably not blocked" assumption: a fresh browser-downloaded ad-hoc kernel is AMFI-killed (exit 137) while quarantined — and exposed a real bug (the hook stripped only the main binary, leaving the framework dylib quarantined, still killed). Fixed to strip the whole .app bundle. All of LAUNCH-01/02/03 + XPLAT-05 verified on real hardware (extension-visibility sub-item deferred).**

## Accomplishments
- **Task 1 (`8cf3e13`)**: `import sys` + `_strip_quarantine_if_present()` best-effort helper + darwin gate in `launch_chrome_profile` before Popen; 3 new unit cases in `test_launch_geo_fallback.py`.
- **Fix (`fbac808`)**: real-machine verification found binary-only stripping insufficient — recurse from `executable_path` up to the `.app` bundle root and strip the whole bundle (framework dylib + helpers carry quarantine too). +1 unit case; target stays scoped to the backend-resolved kernel path (T-3-03 unchanged).
- **D-07 empirically resolved** on the developer's arm64 Mac (see below).
- **LAUNCH-01/02/03 + XPLAT-05** verified end-to-end on real hardware with the real fingerprint 149 kernel, using Playwright-over-CDP for objective fingerprint/geo checks.
- Full suite green: **83 tests, 0 failures, 2 skips** (`.venv/bin/python -m unittest discover -s tests`).

## D-07 quarantine / Gatekeeper empirical conclusion (recorded for Phase 5/6 dmg distribution)
- **(a)** A kernel zip downloaded **via browser** carries `com.apple.quarantine` (flag `0081`, fresh/unassessed).
- **(b)** `ditto` extraction **propagates** quarantine to **all 452 bundle files** — main binary, `Chromium Framework` dylib, and every Helper.
- **(c)** Launching the quarantined, ad-hoc-signed kernel via **raw nested-binary Popen** (not `open -a`) → **SIGKILL, exit 137** (AMFI/code-signing layer — NOT a Gatekeeper prompt; `syspolicyd` logs nothing). The process never comes up (CDP unreachable).
- **Diagnostic**: stripping `com.apple.quarantine` → the same kernel launches, CDP returns `Chrome/149.0.7827.114`. Therefore the strip hook is **load-bearing**, not merely defensive.
- **Bug**: stripping only the main binary is **insufficient** — the still-quarantined `Chromium Framework` dylib triggers the same AMFI kill when the (stripped) binary loads it. Must strip the **whole `.app` bundle** (fixed in `fbac808`).
- **Sub-finding**: an already-*assessed* quarantined app (system Chromium 148, flag `01c1`) launches fine via raw exec — the kill is specific to **fresh/unassessed** downloads, i.e. exactly the user-download-then-launch scenario the hook targets.
- **Phase 5/6 implication**: a dmg-distributed kernel will be quarantined on the user's browser download; the whole-bundle strip hook is required (or proper notarization/stapling).

## Real-machine acceptance results
| Requirement | Check | Result |
|-------------|-------|--------|
| LAUNCH-01 | App-launch 149 kernel → CDP `Chrome/149.0.7827.114`, session tracked, isolated user_data_dir | ✅ |
| LAUNCH-01 (fingerprint) | Playwright/CDP: tz America/Vancouver→Australia/Sydney, lang en-CA→en-AU, UA **Windows on macOS**, platform Win32, hwConcurrency spoofed (masks real 10), webdriver=false | ✅ |
| LAUNCH-02 (proxy) | AU account proxy via LocalHttpProxyBridge | ✅ |
| LAUNCH-02 (geo match) | Browser egress `115.128.181.113` Sydney AU == app resolved_ip; tz/lang track egress | ✅ |
| LAUNCH-02 (batch isolation) | 3 concurrent profiles: distinct user_data_dir / port / pid / fingerprint seed | ✅ |
| LAUNCH-02 (extension) | not re-verified this session (user wrapped up) | ⏳ deferred |
| LAUNCH-03 (no residue) | stop single + batch → `pgrep -f Chromium` empty (graceful termination) | ✅ |
| XPLAT-05 | `/api/capabilities`: engines.firefox.available=false, chrome=true | ✅ |

## Task Commits
1. **Task 1: quarantine 防御性剥离钩子** — `8cf3e13` (feat)
2. **Task 2: arm64 真机端到端冒烟 + D-07 实证** — checkpoint:human-verify, resolved this session (results above)
3. **Fix from real-machine finding: strip whole .app bundle** — `fbac808` (fix)

## Deviations from Plan
- **Real-machine-driven fix (`fbac808`)**: Task 1's hook stripped only the kernel binary (the plan's literal `bundled_engine_executable("chrome")` path). Real-machine D-07 proved this insufficient — the framework dylib's quarantine still triggers the AMFI kill. Corrected to strip the `.app` bundle root (still scoped to the backend-resolved path, T-3-03 intact). This is the intended behavior of the plan's `xattr -dr` (recursive) — the original target path was the defect.

## Issues Encountered
- Initial hook was insufficient (binary-only strip) — found and fixed on real hardware; see Deviations.
- Extension-visibility sub-item of LAUNCH-02 left unverified per user decision to wrap up.

## User Setup Required
- macOS kernel is NOT auto-downloaded by the backend; it must be placed at `engines/chrome/Chromium.app` (download the arm64 zip from the `kernel-149.0.7827.114` release and `ditto`-extract). In production this is bundled into the dmg (Phase 5).

## Next Phase Readiness
- LAUNCH-01/02/03 + XPLAT-05 confirmed on arm64 real hardware; the quarantine strip is proven load-bearing and correct for the whole-bundle case.
- **Phase 5 (CI dmg)** must ensure the bundled kernel launches despite quarantine — the whole-bundle strip hook covers it, but notarization/stapling should be considered.
- Extension real-machine visibility remains an open manual-verification item (low risk).

---
*Phase: 03-macos-chrome-api*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: backend/services/chrome.py (_strip_quarantine_if_present + .app-bundle-root strip)
- FOUND: tests/test_launch_geo_fallback.py (6 tests incl. .app-bundle-root case)
- FOUND: .planning/phases/03-macos-chrome-api/03-03-SUMMARY.md
- FOUND commit: 8cf3e13 (Task 1)
- FOUND commit: fbac808 (real-machine fix)
