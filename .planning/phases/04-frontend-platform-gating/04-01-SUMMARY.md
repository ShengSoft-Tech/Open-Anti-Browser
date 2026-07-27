---
phase: 04-frontend-platform-gating
plan: 01
subsystem: ui
tags: [vue3, pinia, capabilities-contract, platform-gating, node-test]

# Dependency graph
requires:
  - phase: 03-platform-capabilities-contract
    provides: "backend GET /api/bootstrap → data.capabilities contract (BrowserManager.get_platform_capabilities()), independently verified in Phase 3"
provides:
  - "frontend/src/lib/capabilitiesGating.js — the single source of truth (D-00) for all platform gating in Phase 4: isFirefoxEngineAvailable, visibleEngineOptions, isEngineSelectorLocked, getWindowFeatureGate"
  - "stores/profile.js capabilities ref populated from bootstrap()"
  - "ProfileDialog.vue engine selector gated + locked on edit of existing firefox profiles"
  - "corrected, actually-runnable frontend test command in CLAUDE.md"
affects: [04-02, 04-03, 04-04, 04-05, 04-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Platform gating funnels exclusively through capabilitiesGating.js pure functions reading store.capabilities — no component may read navigator.platform/userAgent"
    - "node:test + node:assert/strict, plain ESM import of lib/*.js modules (matches existing proxyBypass.test.js convention)"
    - "fail-open gating: undefined/null/{} capabilities (pre-bootstrap) never hides an engine/feature — only an explicit available === false disables"

key-files:
  created:
    - frontend/src/lib/capabilitiesGating.js
    - frontend/src/lib/capabilitiesGating.test.js
  modified:
    - CLAUDE.md
    - frontend/src/stores/profile.js
    - frontend/src/components/ProfileDialog.vue
    - frontend/src/i18n/zh-CN.js
    - frontend/src/i18n/en-US.js

key-decisions:
  - "capabilitiesGating.js exports four named pure functions (export function xxx( form, matching project convention) — isFirefoxEngineAvailable, visibleEngineOptions, isEngineSelectorLocked, getWindowFeatureGate — all reading only from the capabilities object, never from browser platform APIs"
  - "visibleEngineOptions retains the firefox option when currentEngine === 'firefox' even if firefox is unavailable, specifically so the edit-existing-profile case never produces an empty selected value or a silent engine rewrite; isEngineSelectorLocked then disables the whole control in that case"
  - "getWindowFeatureGate reads window.sync / window.arrange independently and passes the backend reason string through verbatim (no client-side translation/templating), reserved for wave 3 (SyncManager) and wave 4 (App.vue) to import directly so two parallel plans don't redeclare the same symbol"
  - "Fixed CLAUDE.md's frontend test command from the directory form (MODULE_NOT_FOUND on Node 22) to node --test frontend/src/lib/*.test.js — this was the plan's Task 1 first step, required so every subsequent plan's automated verify actually runs"

patterns-established:
  - "capabilitiesGating.js is the only allowed platform-gating entry point for the rest of Phase 4 (UI-02 consumers in wave 3/4 import getWindowFeatureGate directly)"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "macOS (or any capabilities.engines.firefox.available === false machine) new-profile dialog engine selector offers only Chrome"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/capabilitiesGating.test.js#visibleEngineOptions removes firefox but keeps chrome when firefox is unavailable"
        status: pass
      - kind: integration
        ref: "node --input-type=module -e (real backend get_platform_capabilities() piped through visibleEngineOptions) — printed 'E2E OK on darwin'"
        status: pass
    human_judgment: false
  - id: D2
    description: "capabilities ref exposed on the Pinia profile store, populated defensively from bootstrap() data.capabilities"
    verification:
      - kind: unit
        ref: "grep -c 'capabilities' frontend/src/stores/profile.js → 3 (ref declaration, bootstrap assignment, store export)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Editing an existing engine=firefox profile on a machine without Firefox shows the selector locked (disabled, current value retained, no empty selection) with a bilingual hint, and save never rewrites form.engine"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/capabilitiesGating.test.js#isEngineSelectorLocked is true when editing an existing firefox profile on a machine without firefox"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/capabilitiesGating.test.js#visibleEngineOptions keeps the firefox option when currentEngine is firefox even if unavailable"
        status: pass
    human_judgment: true
    rationale: "Visual/interaction confirmation (segmented control renders disabled with Firefox highlighted, hint text shows, no flash of empty selection) requires a human looking at the running dialog; the underlying data-layer guarantee is unit-tested but the actual DOM rendering was not screenshot-verified in this session."
  - id: D4
    description: "getWindowFeatureGate(capabilities, feature) available for wave 3/4 window sync/arrange gating consumers"
    verification:
      - kind: unit
        ref: "frontend/src/lib/capabilitiesGating.test.js (6 getWindowFeatureGate test cases, all pass)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-27
status: complete
---

# Phase 4 Plan 1: Capabilities Gating Foundation Summary

**Wired the Phase 3 capabilities contract into a single-source-of-truth gating module (`capabilitiesGating.js`) consumed by the Pinia store and ProfileDialog, proving end-to-end that macOS hides the Firefox engine option in the new-profile dialog while never corrupting existing Windows-migrated firefox profiles.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-27
- **Tasks:** 3 (1 tracer + 2 TDD)
- **Files modified:** 7 (2 new, 5 modified)

## Accomplishments
- `frontend/src/lib/capabilitiesGating.js` created as the phase's single gating source (D-00): `isFirefoxEngineAvailable`, `visibleEngineOptions`, `isEngineSelectorLocked`, `getWindowFeatureGate` — all pure, all fail-open on undefined/null/`{}` capabilities.
- `stores/profile.js` exposes a reactive `capabilities` ref populated by `bootstrap()` with the same defensive-default pattern already used for `downloads`.
- `ProfileDialog.vue`'s engine selector is now a `computed` filtered through `visibleEngineOptions`; editing an existing `engine=firefox` profile on a machine without Firefox locks the control (`isEngineSelectorLocked`) instead of producing an empty selection or silently rewriting `form.engine`.
- `CLAUDE.md`'s documented frontend test command corrected from the directory form (throws `MODULE_NOT_FOUND` on Node 22) to `node --test frontend/src/lib/*.test.js`, unblocking every subsequent plan's automated verify.
- Real end-to-end proof on this machine: real backend `BrowserManager().get_platform_capabilities()` output piped through `visibleEngineOptions` produces a Chrome-only option list (`E2E OK on darwin`).

## Task Commits

Each task was committed atomically:

1. **Task 1: 端到端「macOS 上新建配置看不到 Firefox」(tracer)** - `f61c11a` (feat)
2. **Task 2: 编辑既有 Firefox 配置时锁定引擎选择器 (TDD)** - `1388b78` (test, RED) → `484a704` (feat, GREEN)
3. **Task 3: 补齐窗口能力门控函数 getWindowFeatureGate (TDD)** - `2a8313c` (test, RED) → `05d23da` (feat, GREEN)

_No REFACTOR commits were needed — GREEN implementations were minimal and required no cleanup._

## Files Created/Modified
- `frontend/src/lib/capabilitiesGating.js` - single-source gating module: `isFirefoxEngineAvailable`, `visibleEngineOptions`, `isEngineSelectorLocked`, `getWindowFeatureGate`
- `frontend/src/lib/capabilitiesGating.test.js` - 22 node:test cases (16 new plus the 2 pre-existing `proxyBypass.test.js` cases run alongside via the glob)
- `frontend/src/stores/profile.js` - added `capabilities` ref, `bootstrap()` assignment, store export
- `frontend/src/components/ProfileDialog.vue` - `engineOptions` converted to computed via `visibleEngineOptions`; added `engineSelectorLocked` computed bound to `:disabled` + a `form-tip` hint
- `frontend/src/i18n/zh-CN.js` / `frontend/src/i18n/en-US.js` - new `platformLimits.engineLockedHint` key (bilingual, non-empty, distinct wording)
- `CLAUDE.md` - corrected frontend test command from directory form to glob form

## capabilitiesGating.js — Full Exported API (for downstream plans)

- **`isFirefoxEngineAvailable(capabilities)`** → `boolean`. Returns `capabilities?.engines?.firefox?.available !== false`. Uses "not-equal-false" (not "equal-true") specifically so undefined/pre-bootstrap capabilities default to available=true — this is the Windows/first-frame zero-regression guarantee.
- **`visibleEngineOptions(baseOptions, capabilities, currentEngine)`** → new array, same shape as `baseOptions` (`{label, value}`). Returns a fresh copy of `baseOptions` unmodified when Firefox is available. When unavailable, filters out `value === 'firefox'` **unless** `currentEngine === 'firefox'` (retains it so an edit-in-progress profile never loses its bound value). Pure — never mutates `baseOptions` or `capabilities`; relative order of surviving options is preserved (filter, not rebuild).
- **`isEngineSelectorLocked(capabilities, currentEngine)`** → `boolean`. `true` only when `currentEngine === 'firefox'` AND `isFirefoxEngineAvailable(capabilities)` is false. Undefined/null capabilities never lock (unknown platform is not locked). Consumed by `ProfileDialog.vue`'s `:disabled` binding on the engine `el-segmented`.
- **`getWindowFeatureGate(capabilities, feature)`** → `{ disabled, reason }` (fresh object). `feature` is `'sync'` or `'arrange'`. `disabled` is `true` only on an explicit `available === false` (undefined defaults to not-disabled). `reason` passes the backend string through verbatim with **no translation or templating** — empty/missing reason returns `''` so consumers fall back to local i18n copy. `sync` and `arrange` are read independently with no cross-fallback. Not yet consumed by any component — reserved for wave 3 (`SyncManager.vue`) and wave 4 (`App.vue`).

## Decisions Made
- Edit-mode reconciliation with SC1 ("create/edit dialogs never show Firefox"): for a **new** profile (`mode === 'create'`, engine defaults to chrome) Firefox is fully absent, satisfying SC1 literally. For **editing** a profile that already has `engine: 'firefox'` (e.g. migrated from Windows), the selector displays that existing value, locked/disabled — it is not offered as a *choice*, it is the profile's *existing state* being shown non-destructively. This is the deliberate reconciliation of D-01 (never hide/delete/silently rewrite existing user data) with SC1, and is why `visibleEngineOptions` special-cases `currentEngine === 'firefox'`.
- CLAUDE.md test-command fix: the documented `node --test frontend/src/lib/` form treats the directory as a module entrypoint and Node 22 throws `MODULE_NOT_FOUND` (reproduced on this machine, v22.18.0). The corrected `node --test frontend/src/lib/*.test.js` form relies on shell glob expansion and works on both Node 20 and 22. This was Task 1's first step because every other plan in this phase depends on this command actually running (otherwise their automated `<verify>` steps would be silently green-by-failure).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded a code comment that false-positived the anti-navigator-hardcoding grep guard**
- **Found during:** Task 1 acceptance-criteria check
- **Issue:** The initial explanatory comment at the top of `capabilitiesGating.js` literally contained the substring `navigator.platform`, which matched the plan's own guard command `grep -rE "navigator\.(platform|userAgent)" frontend/src/` (expected to output `0`), even though no code actually read `navigator.platform`.
- **Fix:** Reworded the comment to describe the constraint without using the literal dotted API name.
- **Files modified:** `frontend/src/lib/capabilitiesGating.js`
- **Verification:** `grep -rE "navigator\.(platform|userAgent)" frontend/src/ | wc -l` → `0`
- **Committed in:** `f61c11a` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — self-inflicted grep false positive, caught before commit)
**Impact on plan:** Cosmetic only; no behavior change, no scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `capabilitiesGating.js`'s full API (all four functions) is ready for the remaining Phase 4 plans: `04-02` through `04-06` can import `getWindowFeatureGate`, and any new component-level gating needs must route through this module (D-00 contract).
- The `platformLimits` i18n namespace has been established in both `zh-CN.js` and `en-US.js` at the correct insertion point (after `settings`, before `apiAccess`) — `04-02` will continue adding keys to the same namespace.
- Open item for a future plan/human pass: visual/DOM confirmation of the locked-selector UX (D3 in coverage above) was not screenshot-verified in this session; unit tests fully cover the underlying data contract.

---
*Phase: 04-frontend-platform-gating*
*Completed: 2026-07-27*

## Self-Check: PASSED

All created files and all 5 task commit hashes (`f61c11a`, `1388b78`, `484a704`, `2a8313c`, `05d23da`) verified present.
