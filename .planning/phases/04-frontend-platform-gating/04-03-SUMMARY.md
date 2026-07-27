---
phase: 04-frontend-platform-gating
plan: 03
subsystem: ui
tags: [vue3, element-plus, capabilities-contract, platform-gating, node-test]

# Dependency graph
requires:
  - phase: 04-frontend-platform-gating (plan 01)
    provides: "frontend/src/lib/capabilitiesGating.js — isFirefoxEngineAvailable(capabilities) as the single D-00 gating source"
  - phase: 04-frontend-platform-gating (plan 02)
    provides: "platformLimits.windowsOnlyTag and platformLimits.startBlockedHint i18n leaf keys, bilingual and parity-guarded"
provides:
  - "ProfileList.vue's four gating consumption points (engine filter dropdown, row-level Windows-only tag, start-button disable + tooltip, batch-start filter) all funneling through the same firefoxEngineVisible computed / isProfileStartBlocked(row) predicate"
affects: [04-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "isProfileStartBlocked(row) as the single per-row start-eligibility predicate, consumed by the inline start button, handleStart's defensive early-return, handleBatchStart's filter chain, and the duplicate dropdown item — no independent re-derivation at any of the four call sites"
    - "el-tooltip wrapping a disabled el-button (Element Plus disabled buttons swallow pointer events, so the tooltip must wrap the button, not attach to it) — same shape already used in SyncManager.vue"

key-files:
  created: []
  modified:
    - frontend/src/components/ProfileList.vue

key-decisions:
  - "firefoxEngineVisible is a computed (not a plain function call) so bootstrap's late resolution of store.capabilities automatically re-renders the filter dropdown and row tags with no stale first-frame Firefox option — reactivity is free because store.capabilities is already a ref."
  - "isProfileStartBlocked(row) is a plain function (not memoized) since it is cheap and needs the current row argument; it delegates entirely to firefoxEngineVisible.value so there is exactly one place capabilities are read for start-eligibility."
  - "Duplicate is disabled for gated rows (duplicating a Firefox profile on macOS would create a new Firefox profile, directly re-opening the door SC1 closed for the create dialog) but delete and stop carry zero gating conditions — D-01's 'never hide, delete, or silently rewrite existing data' is honored literally: the row stays visible, its engine tag/icon are untouched, and the only new restriction is on actions that create new work for a kernel that cannot run here."

patterns-established:
  - "Any future component needing 'can this row's engine actually launch here' gating should reuse isFirefoxEngineAvailable(capabilities) directly (or a local wrapper following this file's isProfileStartBlocked shape) rather than re-deriving from row.engine and platform strings independently."

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "On a machine where capabilities.engines.firefox.available === false, the profile-list engine filter dropdown offers only Chrome; Chrome is never conditioned."
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "node --test frontend/src/lib/*.test.js (37/37 pass, includes capabilitiesGating.test.js which isFirefoxEngineAvailable's semantics are proven against)"
        status: pass
      - kind: other
        ref: "grep -c 'value=\"chrome\"' frontend/src/components/ProfileList.vue → 1, that line carries no v-if; grep -c 'firefoxEngineVisible' → 3 (computed decl + filter v-if + row tag condition)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A pre-existing engine=firefox profile (migrated from Windows) remains visible in the list on macOS, keeps its own engine tag/icon, gains a 'Windows only' badge, has its start button disabled with an explanatory tooltip, has duplicate disabled, and keeps delete/stop fully unconditioned."
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "grep 'command=\"delete\"' ProfileList.vue | grep -c disabled → 0; grep 'handleStop(row)' ProfileList.vue | grep -c isProfileStartBlocked → 0"
        status: pass
      - kind: automated_ui
        ref: "manual DOM/visual confirmation of the row-level Windows-only tag, disabled start button + tooltip content, and disabled duplicate item on a real macOS-rendered list with a firefox-engine row — not screenshot-captured in this session"
        status: unknown
    human_judgment: true
    rationale: "The data-layer guarantees (no disabled binding on delete, no gating on stop, isProfileStartBlocked wired at all required call sites) are grep/unit-verified, but the actual rendered DOM (tooltip appearing on hover, tag wrapping correctly at 160px width, duplicate item visually greyed) was not screenshot-verified in this session and needs a human pass, deferred to 04-06."
  - id: D3
    description: "Single-row start (inline button + handleStart) and batch start (handleBatchStart) share exactly one gating predicate, isProfileStartBlocked(row); batch start filters gated rows out of queuedIds instead of issuing a doomed backend request for each."
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "node --input-type=module inline script from PLAN.md verify block → 'start-gate wiring OK, refs = 6' (>= 5 required: function decl, inline :disabled, tooltip :disabled, handleStart early-return, handleBatchStart filter, duplicate :disabled)"
        status: pass
      - kind: other
        ref: "sed -n '/async function handleBatchStart/,/^}/p' ProfileList.vue | grep -c isProfileStartBlocked → 1"
        status: pass
    human_judgment: false
  - id: D4
    description: "No component-level platform derivation from navigator.platform/userAgent was introduced; the only signal source is store.capabilities via capabilitiesGating.js."
    verification:
      - kind: unit
        ref: "grep -rE 'navigator\\.(platform|userAgent)' frontend/src/components/ProfileList.vue | wc -l → 0"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-27
status: complete
---

# Phase 4 Plan 3: ProfileList Gating Consumption Summary

**Wired the D-00 gating module into ProfileList.vue's four consumption points — engine filter dropdown, row-level "Windows only" tag, start-button disable/tooltip, and batch-start filter — all sharing a single `firefoxEngineVisible` computed and `isProfileStartBlocked(row)` predicate so a legacy Windows-migrated Firefox profile stays fully visible and deletable on macOS while its start/duplicate actions are cleanly disabled.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-27
- **Tasks:** 2 (both auto)
- **Files modified:** 1

## Accomplishments
- `firefoxEngineVisible` computed added to `ProfileList.vue`, delegating to `capabilitiesGating.js`'s `isFirefoxEngineAvailable(store.capabilities)` — reactive by construction since `store.capabilities` is already a ref, so a late-resolving bootstrap never leaves a stale Firefox option in the first frame.
- Engine filter `el-select`: the Firefox `el-option` now carries `v-if="firefoxEngineVisible"`; the Chrome option is untouched and always present.
- Engine column: existing engine `el-tag` (name + color, e.g. "Firefox"/warning) is completely unmodified; a second conditional `el-tag` ("仅 Windows" / "Windows only", `type="info"`) appears only for `row.engine === 'firefox' && !firefoxEngineVisible`. Column widened from 110px to 160px with a flex-wrap container so both tags never get clipped on narrow viewports.
- New `isProfileStartBlocked(row)` function is the single per-row start-eligibility predicate, consumed at all required call sites: the inline start button's `:disabled` (plus an `el-tooltip` wrapper showing `platformLimits.startBlockedHint` only when blocked — Element Plus disabled buttons don't dispatch pointer events, so the tooltip wraps the button rather than attaching directly), `handleStart`'s defensive early-return, `handleBatchStart`'s filter chain (added after the existing status/starting filters), and the "duplicate" dropdown item's `:disabled` binding.
- Delete and stop remain completely unconditioned by platform gating — grep-verified zero `disabled` bindings anywhere near `command="delete"` and zero `isProfileStartBlocked` references near `handleStop(row)`.

## Task Commits

Each task was committed atomically:

1. **Task 1: 筛选下拉隐藏 Firefox,既有 Firefox 行加「仅 Windows」标记** - `f1abdd6` (feat)
2. **Task 2: 单行启动与批量启动共用同一套可启动性判定** - `7d04aab` (feat)

## Files Created/Modified
- `frontend/src/components/ProfileList.vue` - added `firefoxEngineVisible` computed and `isProfileStartBlocked(row)` function; gated the Firefox filter option, added the row-level Windows-only tag, wrapped the start button in a tooltip with a platform-blocked disable condition, added a defensive early-return in `handleStart`, filtered `handleBatchStart`'s `queuedIds`, and disabled the duplicate dropdown item for blocked rows. Delete, stop, edit, and the existing engine tag/icon are untouched.

## Capability Matrix — Legacy `engine=firefox` Profile on macOS (for 04-06 human UAT)

| Action | Behavior | Gated by |
|---|---|---|
| **Visible in list** | Yes — row renders identically to any other profile, no filtering of `store.filteredProfiles`/`pagedProfiles` | Not gated (by design — D-01) |
| **Engine tag/icon** | Yes — shows its own "Firefox" tag (warning color) and `firefoxIcon` in the profile column, exactly as before this plan | Not gated |
| **"Windows only" badge** | Appears as a second `info`-type tag next to the engine tag | `firefoxEngineVisible` (via `isFirefoxEngineAvailable`) |
| **Engine filter dropdown** | Does NOT offer "Firefox" as a filter choice (Chrome always offered) — this does not hide existing firefox rows from the unfiltered list, it only removes Firefox as a *filter criterion* | `firefoxEngineVisible` |
| **Start (inline button)** | Disabled; hovering shows a tooltip with `platformLimits.startBlockedHint` copy | `isProfileStartBlocked(row)` |
| **Start (batch "启动选中项")** | Row is silently excluded from `queuedIds` — no request is sent for it, no backend error surfaces, and the success toast's count reflects only the rows actually started | `isProfileStartBlocked(row)` in `handleBatchStart`'s filter chain |
| **Stop** | Always available, no gating — a running process must always be stoppable | Not gated |
| **Edit** | Always available — user can still change proxy/remark/etc.; the engine field itself was already locked read-only in `ProfileDialog.vue` by 04-01 | Not gated in this file |
| **Duplicate** | Disabled — duplicating would create a new Firefox profile on a platform where Firefox profiles cannot be created, directly reopening the door SC1 closed | `isProfileStartBlocked(row)` |
| **Delete** | Always available, unconditionally — the sole way a user is meant to remove this data, per D-01 | Not gated (verified via grep: `command="delete"` line carries no `disabled`) |

## Decisions Made
- `firefoxEngineVisible` is a `computed`, not a function call re-evaluated inline in the template on every access, so Vue's reactivity system automatically triggers a re-render of both the filter dropdown and every row's tag the moment `store.capabilities` resolves post-bootstrap — no manual watcher needed, and no risk of a stale first-paint Firefox option.
- `isProfileStartBlocked(row)` is deliberately a plain function (not a computed) since it needs the `row` argument and is cheap to evaluate on each table cell render; it delegates to `firefoxEngineVisible.value` so there remains exactly one code path reading platform capability for start-eligibility, per the plan's `key_links` requirement.
- Duplicate was disabled for gated rows (planner's explicit discretion point in the plan text) because duplicating a firefox-engine profile is functionally equivalent to creating a new one, which SC1 already forbids in the create dialog — leaving duplicate enabled would have been an inconsistent side door.
- Delete and stop were left completely untouched by any gating condition — this is not an oversight but the literal reading of D-01 ("existing user data must remain visible and deletable, never silently hidden or rewritten"), and is independently verified by two grep-based acceptance checks (no `disabled` near the delete dropdown item, no `isProfileStartBlocked` reference near `handleStop`).

## Deviations from Plan

None - plan executed exactly as written. Both tasks' automated verify commands and all listed acceptance-criteria grep/sed checks passed on the first implementation pass; no auto-fixes were needed.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four gating consumption points in `ProfileList.vue` now share the same two decision points (`firefoxEngineVisible`, `isProfileStartBlocked`) that 04-01 established as the D-00 single source of truth — no new gating logic or platform derivation was introduced in this file.
- `platformLimits.windowsOnlyTag` and `platformLimits.startBlockedHint` (both landed by 04-02) are now consumed verbatim; no new i18n keys were required or added by this plan.
- `python3 -m backend._g --mode build` exits 0 — the hash-locked `App.vue`/`openSourceNotice.js` anti-tamper assets were never touched; `git diff --name-only` for this plan's two commits contains only `frontend/src/components/ProfileList.vue`.
- Open item for 04-06's human UAT pass: the actual rendered DOM (tooltip-on-hover, tag wrapping at the new 160px column width, greyed-out duplicate item) was not screenshot-verified in this session — the Capability Matrix above gives 04-06 an exact per-action checklist to confirm visually against a real macOS-rendered list containing a migrated firefox profile.
- No blockers for 04-04/04-05, which consume different files (`SyncManager.vue`, `AppSettings.vue`, `App.vue`) and were not touched by this plan.

---
*Phase: 04-frontend-platform-gating*
*Completed: 2026-07-27*

## Self-Check: PASSED

`frontend/src/components/ProfileList.vue` and both task commit hashes (`f1abdd6`, `7d04aab`) verified present.
