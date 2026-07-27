---
phase: 03-macos-chrome-api
plan: 01
subsystem: api
tags: [capabilities, platform-gating, fastapi, sys.platform, macos]

# Dependency graph
requires:
  - phase: 01-backend-cross-platform
    provides: "window_manager.py sys.platform == \"win32\" gate (the fact source for window.arrange/sync.available); ENGINE_METADATA retains firefox entry on macOS (D-08)"
provides:
  - "get_platform_capabilities() on BrowserManager — single backend source of truth for platform-level feature support"
  - "GET /api/capabilities — independent read-only endpoint"
  - "bootstrap().capabilities — same contract folded into the existing bootstrap aggregate"
  - "Locked JSON contract (option-a nested shape) for Phase 4 frontend gating to consume verbatim"
affects: [04-frontend-macos-gating]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Platform capability facts computed once in backend, exposed as explicit booleans (`available`) — never left to frontend UA-sniffing"
    - "`available` (platform-level support) kept strictly orthogonal to `installed`/`capability_ok` (kernel-path-exists) — two different fields, two different UI treatments (hide vs. install-prompt)"

key-files:
  created:
    - tests/test_capabilities_api.py
  modified:
    - backend/browser_manager.py
    - backend/main.py

key-decisions:
  - "Task 1 (blocking checkpoint:decision) resolved by user prior to execution start: option-a (nested shape) selected over option-b (flat prefixed keys) — see 'Locked Contract' section below"
  - "capabilities NOT exposed on /open-api this plan (03-RESEARCH Open Question 2) — minimal-diff default, ROADMAP SC4 only requires the /api/capabilities endpoint to exist"

patterns-established:
  - "New orthogonal capability dimensions are added as new keys/methods, never overloaded onto existing installed/capability_ok fields"

requirements-completed: [XPLAT-05]

coverage:
  - id: D1
    description: "GET /api/capabilities returns 200 JSON with engines.chrome.available==true and engines.firefox.available==false on macOS"
    requirement: "XPLAT-05"
    verification:
      - kind: unit
        ref: "tests/test_capabilities_api.py#PlatformCapabilitiesTests.test_darwin_capabilities"
        status: pass
      - kind: manual_procedural
        ref: "curl http://127.0.0.1:18099/api/capabilities on live macOS uvicorn — returned exact locked contract"
        status: pass
    human_judgment: false
  - id: D2
    description: "window.arrange and window.sync each expose available boolean + reason text (non-empty on macOS, None on Windows)"
    requirement: "XPLAT-05"
    verification:
      - kind: unit
        ref: "tests/test_capabilities_api.py#PlatformCapabilitiesTests.test_darwin_capabilities"
        status: pass
      - kind: unit
        ref: "tests/test_capabilities_api.py#PlatformCapabilitiesTests.test_win32_capabilities"
        status: pass
    human_judgment: false
  - id: D3
    description: "bootstrap() returns dict containing new key 'capabilities' with structure identical to the standalone endpoint"
    requirement: "XPLAT-05"
    verification:
      - kind: unit
        ref: "tests/test_capabilities_api.py#PlatformCapabilitiesTests.test_bootstrap_includes_capabilities_key"
        status: pass
    human_judgment: false
  - id: D4
    description: "get_platform_capabilities().engines.*.available is orthogonal to get_engine_statuses() installed/capability_ok — neither overwrites the other"
    requirement: "XPLAT-05"
    verification:
      - kind: unit
        ref: "grep -c 'capability_ok' backend/browser_manager.py (unchanged count, 2, before/after)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 1: Platform Capabilities API Summary

**Backend `GET /api/capabilities` + `bootstrap().capabilities` exposing per-engine `available` and window-feature `available`/`reason`, sourced from a single `sys.platform` check — locks the Phase 3→4 hard interface for frontend gating.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-27T17:51:51Z
- **Tasks:** 2 (Task 1 decision — pre-resolved before spawn; Task 2 tracer implementation)
- **Files modified:** 3 (2 modified, 1 created)

## Locked Contract (Task 1 — option-a, resolved before execution)

Task 1 was a `checkpoint:decision` (`gate="blocking"`). **The user resolved this decision before this executor was spawned** (per orchestrator instruction) — no pause occurred, no re-ask happened. The selection was **option-a (nested shape)**, RESEARCH.md Pattern 2's recommended shape, driven by a single platform source `is_windows = (sys.platform == "win32")`.

This is the exact, final, Phase-4-consumable JSON contract, verified byte-for-byte via live `curl` against a running macOS backend in this plan (see Deviations/Issues — none):

```json
{
  "platform": "darwin",
  "engines": {
    "chrome":  { "available": true },
    "firefox": { "available": false }
  },
  "window": {
    "arrange": { "available": false, "reason": "窗口排列仅在 Windows 上可用" },
    "sync":    { "available": false, "reason": "窗口同步仅在 Windows 上可用" }
  }
}
```

On `win32`: `engines.firefox.available == true`, `window.arrange.available == true` with `reason == null`, `window.sync.available == true` with `reason == null`.

**Phase 4 consumption contract (hard interface):**
- UI-01 (hide Firefox entirely on macOS) → read `capabilities.engines.firefox.available`
- UI-02 (grey out + tooltip window features) → read `capabilities.window.arrange.available` / `capabilities.window.sync.available` and their `.reason` strings

**Field semantics locked (D-02, unchanged by Task 1):** `available` = "does this platform structurally support this feature" — strictly orthogonal to the pre-existing `installed`/`capability_ok` fields on `get_engine_statuses()`, which mean "is the kernel binary present on disk". Example: Chrome on macOS is `available=true` regardless of whether the kernel zip has been downloaded (`installed` tracks that separately).

## Accomplishments
- Added `get_platform_capabilities()` instance method to `BrowserManager` (backend/browser_manager.py), placed adjacent to `get_engine_statuses()`, single platform source `sys.platform`
- Added top-level `import sys` to browser_manager.py's stdlib import block (previously absent)
- Folded the same capabilities dict into `bootstrap()` as a new `"capabilities"` key (one-line addition, consistent with bootstrap's existing flat-dict-of-method-calls shape)
- Added `GET /api/capabilities` route to backend/main.py — one-line thin delegation matching the `/api/engines` precedent exactly (no auth, no try/except, since the method has no failure mode)
- Created `tests/test_capabilities_api.py` — 3 unittest cases covering the darwin branch, the win32 branch (via `mock.patch("backend.browser_manager.sys.platform", ...)`), and bootstrap aggregation
- Live-verified the exact JSON output via a real uvicorn process on this macOS machine (`curl http://127.0.0.1:18099/api/capabilities` and `/api/bootstrap`) — output matches the locked contract exactly

## Task Commits

Task 1 (checkpoint:decision) required no code changes — resolved via user pre-approval before spawn, recorded above; no commit for Task 1 itself (nothing to commit).

1. **Task 2: 端到端实现 capabilities（方法 → 路由 → bootstrap → 单测）** - `c1f6a6d` (feat)

**Plan metadata:** (this commit, following SUMMARY write)

## Files Created/Modified
- `backend/browser_manager.py` - added `import sys`; new `get_platform_capabilities()` method; `bootstrap()` gained `"capabilities"` key
- `backend/main.py` - new `GET /api/capabilities` route, adjacent to `/api/engines`
- `tests/test_capabilities_api.py` - new file, 3 test cases (darwin branch, win32 branch, bootstrap aggregation)

## Decisions Made
- Task 1's blocking decision (option-a nested shape) was resolved by the user prior to this executor's spawn per orchestrator instruction — recorded verbatim above for Phase 4 traceability.
- `capabilities` not exposed on `/open-api` this plan — deferred per 03-RESEARCH Open Question 2 (no signal of automation-consumer need; ROADMAP SC4 only requires the `/api/capabilities` endpoint on the local `app`).

## Deviations from Plan

None — plan executed exactly as written (Task 2 implemented to the locked option-a contract verbatim; `get_engine_statuses()`'s `installed`/`capability_ok` fields untouched, confirmed via `grep -c 'capability_ok'` returning 2 both before and after).

## Issues Encountered
None.

## Known Stubs
None.

## Threat Flags
None — `GET /api/capabilities` matches the plan's `<threat_model>` T-3-01 disposition exactly (read-only, no request params, no sensitive data, no new auth surface); no new surface introduced beyond what the threat model already accounted for.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The Phase 3→4 hard interface (`capabilities.engines.*.available`, `capabilities.window.*.available`/`.reason`) is now live and locked. Phase 4 (frontend macOS gating) can consume `bootstrap().capabilities` or `GET /api/capabilities` directly with the exact field names documented in "Locked Contract" above.
- No blockers for the remaining plans in Phase 03 (LAUNCH-01/02/03 process termination and launch-path work, plan 02+).

---
*Phase: 03-macos-chrome-api*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: backend/browser_manager.py
- FOUND: backend/main.py
- FOUND: tests/test_capabilities_api.py
- FOUND: .planning/phases/03-macos-chrome-api/03-01-SUMMARY.md
- FOUND: commit c1f6a6d
