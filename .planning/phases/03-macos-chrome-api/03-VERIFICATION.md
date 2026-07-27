---
phase: 03-macos-chrome-api
verified: 2026-07-27T20:09:03Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification_resolved:
  - test: "Install a real Chrome extension on a macOS profile and confirm it loads/is visible"
    resolved: "2026-07-27 — verified this session. A minimal MV3 extension was imported via POST /api/extensions/import-folder (enabled=true), enabled on the P3 profile, and launched: the launch command carried --load-extension / --disable-extensions-except pointing at the unpacked extension; Playwright-over-CDP confirmed the content script injected data-p3-ext=loaded on a real page (example.com through the AU proxy). MV3 service worker is dormant/lazy (0 CDP targets) — content-script injection is the definitive active-load proof."
---

# Phase 3: macOS Chrome 启动与能力 API Verification Report

**Phase Goal:** macOS 用户可以完整走通"创建配置 → 启动指纹 Chrome → 使用代理/扩展/批量启动 → 停止"的核心链路,后端同时暴露平台能力供前端消费。
**Verified:** 2026-07-27T20:09:03Z
**Status:** passed
**Re-verification:** No — initial verification (extension sub-item resolved same session, see Truth 10 / Human Verification)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `GET /api/capabilities` returns 200 JSON with `engines.chrome.available==true` / `engines.firefox.available==false` on macOS (XPLAT-05) | ✓ VERIFIED | `backend/main.py:408-410` delegates to `BrowserManager.get_platform_capabilities()` (`backend/browser_manager.py:627-641`); `tests.test_capabilities_api.PlatformCapabilitiesTests.test_darwin_capabilities` passes; 03-01-SUMMARY records a live `curl` against a running macOS uvicorn matching the locked contract byte-for-byte; 03-03-SUMMARY records a second real-machine spot-check with the same result |
| 2 | `window.arrange`/`window.sync` each expose `available` bool + `reason` text (non-empty on macOS, `None` on Windows) | ✓ VERIFIED | `backend/browser_manager.py:628-640` — `arrange_reason`/`sync_reason` computed from single `is_windows` source; `test_darwin_capabilities` and `test_win32_capabilities` both pass |
| 3 | `bootstrap()` returns dict containing `capabilities` key, identical structure to standalone endpoint | ✓ VERIFIED | `backend/browser_manager.py:75` — `"capabilities": self.get_platform_capabilities()`; `test_bootstrap_includes_capabilities_key` passes |
| 4 | `get_platform_capabilities().engines.*.available` orthogonal to `get_engine_statuses().installed`/`capability_ok` — neither overwrites the other | ✓ VERIFIED | `get_engine_statuses()` (`backend/browser_manager.py:604-625`) unchanged; `capability_ok` still appears exactly 2×, both inside `get_engine_statuses`, none inside `get_platform_capabilities` |
| 5 | `kill_process_tree` sends SIGTERM to whole tree, waits `grace_period`, then SIGKILLs only survivors — terminate → wait_procs → kill ordering, single cross-platform path (LAUNCH-03) | ✓ VERIFIED | `backend/services/network.py:840-861` — code matches exactly: `terminate()` loop (848-852) → `psutil.wait_procs(procs, timeout=grace_period)` (854) → `kill()` loop on `alive` (856-860); no `sys.platform` branch anywhere in the function; `tests.test_process_termination_macos` both cases pass |
| 6 | `kill_process_tree(pid)` old single-arg call signature still works (no call-site changes needed) | ✓ VERIFIED | Signature is `kill_process_tree(pid: int, grace_period: float = DEFAULT_TERMINATION_GRACE_PERIOD)`; sole call site `backend/browser_manager.py:267` still calls with one positional arg |
| 7 | Stopping a profile / quitting the app leaves no residual Chrome process on macOS, no SingletonLock corruption (LAUNCH-03, real-machine) | ✓ VERIFIED (real-machine, this session) | Code basis for truth 5/6 confirmed above; 03-03-SUMMARY.md D7 records real-hardware confirmation this session: stop single + batch(3) → `pgrep -f Chromium` empty, graceful SIGTERM→grace→SIGKILL teardown clears in ~1-2s |
| 8 | macOS user can one-click launch a fingerprinted Chrome profile: fingerprint params, isolated `user_data_dir`, CDP port, psutil session tracking all work — direct `Popen` of the nested `.app` binary, not `open -a` (LAUNCH-01, real-machine) | ✓ VERIFIED (real-machine, this session) | `backend/services/chrome.py:32` resolves `executable_path` via `bundled_engine_executable("chrome")`; line 83 places `str(executable_path)` as `launch_args[0]`; `subprocess.Popen(launch_args, ...)` at line 131 — no `open -a` anywhere in the file. 03-03-SUMMARY.md D3 records real arm64 hardware confirmation: CDP `Chrome/149.0.7827.114`, session tracked, isolated `user_data_dir`, Playwright-over-CDP confirmed fingerprint spoof (tz/lang/UA/platform/hwConcurrency/webdriver=false) |
| 9 | Proxy (incl. `LocalHttpProxyBridge`), geo resolution (tz/lang track egress IP), and 2-3 profile batch isolation work on macOS Chrome (LAUNCH-02, real-machine) | ✓ VERIFIED (real-machine, this session) | 03-03-SUMMARY.md D4/D5: AU account proxy via bridge, browser egress IP == app `resolved_ip` (Sydney AU), tz/lang matched; 3 concurrent profiles had distinct `user_data_dir`/port/pid/fingerprint seed |
| 10 | Extension install/visibility works on macOS Chrome (LAUNCH-02 sub-item) | ✓ VERIFIED (real-machine, this session) | Resolved same session: minimal MV3 extension imported via `/api/extensions/import-folder` (enabled), enabled on P3 profile; launch command carried `--load-extension`/`--disable-extensions-except`; Playwright-over-CDP confirmed the content script injected `data-p3-ext=loaded` on example.com (through the AU proxy). MV3 SW dormant (0 CDP targets, normal lazy behavior) — content-script injection is the active-load proof. |
| 11 | `chrome.py`'s quarantine strip only fires on `sys.platform=='darwin'`, best-effort (try/except), failure never blocks launch | ✓ VERIFIED | `backend/services/chrome.py:35-45` gates on `sys.platform == "darwin"`; `_strip_quarantine_if_present` (157-174) wraps `subprocess.run` in try/except swallowing all exceptions; `tests.test_launch_geo_fallback` covers all 3 behaviors (darwin strips, non-darwin skips, strip-raises doesn't block launch) — all pass |
| 12 | Quarantine strip targets the whole `.app` bundle root (not just the kernel binary) — real-machine-discovered fix (D-07) | ✓ VERIFIED | `backend/services/chrome.py:40-44` walks `executable_path.parents` up to the first `.app`-suffixed ancestor and strips that; `test_chrome_launch_strips_quarantine_from_app_bundle_root_on_darwin` passes; matches 03-03-SUMMARY.md's documented `fbac808` fix and D-07 real-machine finding (binary-only strip still hit AMFI exit 137; whole-bundle strip fixed it) |

**Score:** 12/12 truths verified (the extension sub-item was resolved the same session via Playwright content-script confirmation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/browser_manager.py:get_platform_capabilities()` | New method, dual sys.platform branches | ✓ VERIFIED | Lines 627-641, matches locked contract exactly |
| `backend/browser_manager.py:bootstrap()` | New `capabilities` key | ✓ VERIFIED | Line 75 |
| `backend/main.py:GET /api/capabilities` | New route | ✓ VERIFIED | Lines 408-410, thin delegation, unauthenticated on `app` (not on `open_api`) matching `/api/engines` precedent |
| `tests/test_capabilities_api.py` | New test file | ✓ VERIFIED | 3 tests, all pass |
| `backend/services/network.py:kill_process_tree` | Terminate→wait→kill refactor | ✓ VERIFIED | Lines 840-861 |
| `backend/services/network.py:DEFAULT_TERMINATION_GRACE_PERIOD` | New constant | ✓ VERIFIED | Line 32, value 3.0, referenced as default at line 840 (2 occurrences as required) |
| `tests/test_process_termination_macos.py` | New test file, network-only import | ✓ VERIFIED | Imports only `unittest`, `unittest.mock`, `backend.services.network` — no pywin32-dependent modules |
| `backend/services/chrome.py:_strip_quarantine_if_present` | New best-effort helper | ✓ VERIFIED | Lines 157-174 |
| `backend/services/chrome.py` launch-path quarantine call + `import sys` | Darwin-gated call site | ✓ VERIFIED | Line 7 `import sys`; lines 35-45 gated call, walks to `.app` bundle root |
| `tests/test_launch_geo_fallback.py` quarantine cases | New test cases in existing file | ✓ VERIFIED | 4 quarantine-related test names present (incl. the app-bundle-root case), all pass |
| Real-machine verification execution record | D-07 conclusion + LAUNCH-01/02/03 real-machine results | ✓ VERIFIED | 03-03-SUMMARY.md contains detailed D-07 findings table and per-requirement real-machine results table |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `get_platform_capabilities()` | `GET /api/capabilities` route | direct method call | ✓ WIRED | `backend/main.py:410` |
| `get_platform_capabilities()` | `bootstrap()` `capabilities` key | direct method call | ✓ WIRED | `backend/browser_manager.py:75` |
| `bundled_engine_executable("chrome")` resolved path | `_strip_quarantine_if_present` | scoped `.app`-root path variable, not user input | ✓ WIRED | `backend/services/chrome.py:32-45` — path derivation is fully backend-controlled, matches T-3-03 mitigation as designed |
| `kill_process_tree` | `browser_manager.stop_profile` call site | single positional-arg call, unaffected by new keyword param | ✓ WIRED | `backend/browser_manager.py:267` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full existing suite green (zero regression) | `.venv/bin/python -m unittest discover -s tests` | `Ran 83 tests ... OK (skipped=2)` | ✓ PASS — matches stated baseline exactly |
| capabilities API unit tests | `.venv/bin/python -m unittest tests.test_capabilities_api -v` | 3/3 pass | ✓ PASS |
| process termination unit tests | `.venv/bin/python -m unittest tests.test_process_termination_macos -v` | 2/2 pass | ✓ PASS |
| chrome launch quarantine unit tests | `.venv/bin/python -m unittest tests.test_launch_geo_fallback -v` | 6/6 pass (incl. 4 quarantine-specific cases) | ✓ PASS |
| Commit hashes referenced in SUMMARYs exist | `git log --oneline -1 <hash>` for c1f6a6d, 87fbf99, 8cf3e13, fbac808 | All 4 resolve to the described commits | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| XPLAT-05 | 03-01 | 后端暴露平台能力信息 | ✓ SATISFIED | Truths 1-4 above; live-curl + unit tests |
| LAUNCH-03 | 03-02, 03-03 | 停止/退出正确终止进程树、无残留 | ✓ SATISFIED | Truths 5-7; code + unit tests + real-machine confirmation this session |
| LAUNCH-01 | 03-03 | 一键启动指纹 Chrome | ✓ SATISFIED | Truth 8; code (direct Popen, no `open -a`) + real-machine confirmation this session |
| LAUNCH-02 | 03-03 | 代理/扩展/geo/批量启动可用 | ✓ SATISFIED | Truth 9 (proxy/geo/batch) + Truth 10 (extension load) all confirmed real-machine this session |

No orphaned requirements: all four phase requirement IDs (LAUNCH-01, LAUNCH-02, LAUNCH-03, XPLAT-05) are declared across the three plans' frontmatter and map to phase's ROADMAP.md requirements list with no unclaimed remainder.

**Documentation note (non-blocking):** `.planning/REQUIREMENTS.md` still shows `LAUNCH-01` and `LAUNCH-02` as `[ ]` (unchecked/"Pending" in the traceability table at the bottom of the file), while `LAUNCH-03` and `XPLAT-05` are already checked `[x]`/"Complete". This appears to be a checklist-update lag — the last commit touching REQUIREMENTS.md predates the 03-03 plan (which is where LAUNCH-01/LAUNCH-02 evidence was produced) — rather than a code gap. Recommend updating the checkboxes as part of phase closure.

### Anti-Patterns Found

None. Scanned all 7 files touched across the three plans (`backend/browser_manager.py`, `backend/main.py`, `backend/services/network.py`, `backend/services/chrome.py`, `tests/test_capabilities_api.py`, `tests/test_process_termination_macos.py`, `tests/test_launch_geo_fallback.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented" markers — zero matches.

### Human Verification — RESOLVED (this session)

### 1. LAUNCH-02 extension visibility on macOS Chrome — ✓ RESOLVED

**Test:** Install a real browser extension on a macOS Chrome profile and launch that profile.
**Result (2026-07-27, this session):** A minimal MV3 extension was imported via `POST /api/extensions/import-folder` (returned `enabled=true`), enabled on the P3 profile, and launched. The launch command carried `--load-extension=…/extensions/chrome/<id>/unpacked` and `--disable-extensions-except=…`. Playwright-over-CDP navigated a real page (example.com, through the AU proxy) and confirmed the extension's content script injected `data-p3-ext=loaded` into the DOM — proving the extension is loaded and actively running on the macOS Chrome kernel. (The MV3 service worker showed 0 CDP targets, which is expected dormant/lazy behavior, not a failure.) Extension then removed to restore a clean state.

### Gaps Summary

No blocking gaps. All code-level must-haves (capabilities API contract, graceful process termination, quarantine strip hook including the real-machine-discovered whole-bundle fix) are present, substantively implemented, wired correctly, and covered by passing unit tests with zero regression (83/83 pass, 2 pre-existing skips, matching the stated baseline exactly). Commit hashes referenced in all three SUMMARYs resolve to the described changes.

The phase's real-machine backstop truths (LAUNCH-01, most of LAUNCH-02, LAUNCH-03) were genuinely exercised on arm64 hardware this session per 03-03-SUMMARY.md's detailed, specific evidence (exact CDP version strings, egress IPs, pids, ports, fingerprint seeds) — this is credible first-hand evidence, not a restated claim, and is accepted per this verification's real-machine-context instructions.

The previously-open item (LAUNCH-02 extension visibility) was **resolved the same session** via a real-machine Playwright content-script confirmation (see Truth 10 / Human Verification RESOLVED). All 12 must-haves are now verified; no open items remain. Phase passes.

---

_Verified: 2026-07-27T20:09:03Z_
_Verifier: Claude (gsd-verifier)_
