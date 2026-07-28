---
phase: 04-frontend-platform-gating
reviewed: 2026-07-28T01:58:55Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - backend/_g.py
  - frontend/src/App.vue
  - frontend/src/assets/global.css
  - frontend/src/components/AppSettings.vue
  - frontend/src/components/GroupManager.vue
  - frontend/src/components/ProfileDialog.vue
  - frontend/src/components/ProfileList.vue
  - frontend/src/components/SyncManager.vue
  - frontend/src/i18n/en-US.js
  - frontend/src/i18n/zh-CN.js
  - frontend/src/lib/capabilitiesGating.js
  - frontend/src/lib/capabilitiesGating.test.js
  - frontend/src/lib/i18n-parity.test.js
  - frontend/src/lib/macosGatekeeperNotice.js
  - frontend/src/lib/macosGatekeeperNotice.test.js
  - frontend/src/stores/profile.js
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-07-28T01:58:55Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Reviewed the frontend platform-gating changes scoped to diff base `c11cf058`. The gating
helpers in `capabilitiesGating.js` are correctly fail-open (verified against the unit tests
and by manual trace: `undefined`/`null`/`{}` capabilities always resolve to "available"/"not
disabled"), no component reads `navigator.platform`/`navigator.userAgent` (single source of
truth via `capabilitiesGating.js` is respected), backend `reason` strings are always rendered
verbatim and never routed through `t()`, the `backend/_g.py` SHA-256 lock for `App.vue` was
correctly recomputed and matches the current file content byte-for-byte (verified locally),
`openSourceNotice.js` and its hash entry were untouched, the new Gatekeeper notice HTML
builder is a provably pure function with no dynamic/user-controlled interpolation (safe
against XSS despite `dangerouslyUseHTMLString`), and the Gatekeeper guidance command is
correctly scoped to a single `.app` bundle with no `sudo`/`spctl`/global-disable instructions.
Legacy Firefox profiles remain visible and deletable, and the engine selector is form-disabled
(`el-segmented :disabled`) whenever a locked Firefox profile is being edited, preventing the
`engine` field from being silently rewritten to `chrome` on save.

Two real defects were found, both in the newly-added nav/onboarding wiring in `App.vue`, plus
two minor quality nits in `SyncManager.vue`. None of these touch the invariants graded
Critical in the phase brief (fail-open gating, single source of truth, verbatim reasons, the
integrity lock, legacy data reachability, or Gatekeeper command safety), so nothing here is
classified as a blocker — but WR-01 and WR-02 are genuine, provable behavioral bugs that should
be fixed.

## Warnings

### WR-01: "Disabled" sidebar nav item is purely cosmetic — click still navigates

**File:** `frontend/src/App.vue:24-32` (also `:369-377` for `isNavDisabled`, `:365-370` for `setActiveNav`)
**Issue:** The Syncer nav item is now wrapped in an `el-tooltip` and gets a `disabled` CSS
class (`opacity: 0.45; cursor: not-allowed;`, see `frontend/src/assets/global.css:209-217`)
when `getWindowFeatureGate(store.capabilities, 'sync').disabled` is true. However, the
`@click="setActiveNav(item.key)"` handler on the underlying `<div class="nav-item">` is
unchanged and `setActiveNav` never checks `isNavDisabled`:
```js
function setActiveNav(nextNav) {
  if (!validNavKeys.has(nextNav) || activeNav.value === nextNav) {
    return
  }
  activeNav.value = nextNav
}
```
Nothing in the click path (and no `pointer-events: none` in CSS) actually blocks the
navigation — the nav item merely *looks* unclickable (dimmed, "not-allowed" cursor) while
still fully functioning as a normal nav item. This is a real, user-visible mismatch between
the presented affordance and the actual behavior: a user sees a "not-allowed" cursor and a
tooltip explaining the feature is unavailable, clicks anyway (as many users do to see what
happens), and lands on the Syncer view exactly as if nothing were disabled.
**Fix:** Either make the click genuinely inert (preferred, to match the visual signal):
```js
function setActiveNav(nextNav) {
  if (!validNavKeys.has(nextNav) || activeNav.value === nextNav || isNavDisabled(nextNav)) {
    return
  }
  activeNav.value = nextNav
}
```
or, if click-through-to-explanation is the intended UX (SyncManager itself shows a banner
with the same reason), drop the `not-allowed` cursor/opacity treatment so the affordance
doesn't promise something the code doesn't deliver.

### WR-02: New Gatekeeper first-run notice can be silently skipped by an unrelated unguarded `localStorage` call ahead of it

**File:** `frontend/src/App.vue:293-332` (`onMounted`), `:488-518` (`_0x31ab`), `:520-533` (`maybeShowGatekeeperNotice`)
**Issue:** `onMounted` wraps the whole startup sequence in a single `try/catch`:
```js
onMounted(async () => {
  try {
    ...
    await store.bootstrap()
    await store.getBackendModeStatus()
    await _0x31ab()                      // pre-existing open-source notice, unguarded localStorage
    await maybeShowGatekeeperNotice()     // NEW: macOS Gatekeeper notice
    profileRefreshTimer = window.setInterval(...)   // NEW-adjacent: polling setup
    backendStatusTimer = window.setInterval(...)
  } catch (error) {
    ElMessage.error(error.message || t('common.loadFailed'))
  }
})
```
`_0x31ab()` calls `localStorage.getItem(_0x5c10)` / `localStorage.setItem(_0x5c10, '1')`
directly, with no try/catch of its own (unlike the new `macosGatekeeperNotice.js` helpers,
which correctly guard every `localStorage` call and are unit-tested for the throwing case —
see `macosGatekeeperNotice.test.js`). If `localStorage` throws in a restricted context (e.g. a
sandboxed WebView, Safari-style private mode, or a quota/permission failure — plausible on a
newly-supported macOS target where the runtime shell differs from Windows), the exception
propagates out of `_0x31ab()`, is caught by the outer `catch`, and **every statement after it
in the `try` block never runs**: the new `maybeShowGatekeeperNotice()` call is skipped (so
macOS users in that situation never see the Gatekeeper guidance the phase exists to add), and
`profileRefreshTimer`/`backendStatusTimer` are never set up, degrading the whole app (no
auto-refresh of profile status, no backend-mode polling) with only a generic "加载失败" toast
as feedback.
**Fix:** Guard `_0x31ab()`'s storage access the same way `macosGatekeeperNotice.js` does, and/or
give each startup step its own try/catch so one non-critical failure can't cascade and skip
unrelated initialization:
```js
async function _0x31ab() {
  let alreadySeen = false
  try {
    alreadySeen = localStorage.getItem(_0x5c10) === '1'
  } catch {
    return // localStorage unavailable: don't block subsequent startup steps
  }
  if (alreadySeen) return
  ...
  try {
    localStorage.setItem(_0x5c10, '1')
  } catch {
    // degrade silently, same pattern as markGatekeeperNoticeSeen()
  }
}
```

## Info

### IN-01: Row-level "显示窗口" button tooltip doesn't surface the backend gate reason like every other gated control

**File:** `frontend/src/components/SyncManager.vue:242` (row actions column)
**Issue:** Every other window-arrange/sync control added in this phase wraps its `el-button`
in an `el-tooltip` whose `:content` shows `arrangeGate.reason || t('platformLimits.windowsOnlyFallback')`
(or the `sync` equivalent) when disabled. The single-row "显示窗口" action is disabled the same
way (`:disabled="arrangeGate.disabled"`) but keeps its original static tooltip:
```html
<el-tooltip content="显示窗口">
  <el-button circle text class="row-action" :disabled="arrangeGate.disabled" @click="showWindows([row.id])">
```
so a user hovering this specific disabled icon button sees only "显示窗口" (its label) instead
of the reason it's greyed out, unlike the identical action available elsewhere on the page.
**Fix:**
```html
<el-tooltip :content="arrangeGate.disabled ? (arrangeGate.reason || t('platformLimits.windowsOnlyFallback')) : '显示窗口'">
```

### IN-02: New `.platform-banner` / `.platform-banner-hint` classes have no CSS rules

**File:** `frontend/src/components/SyncManager.vue:5,13`
**Issue:** The new platform-limits `el-alert` banner and its hint `<p>` are given
`class="platform-banner"` / `class="platform-banner-hint"`, but neither selector is defined
anywhere — not in `SyncManager.vue`'s own `<style scoped>` block, nor in `global.css`. The
banner still renders correctly today only because `.sync-page`'s flex layout happens to
provide spacing between children; the classes themselves are currently dead selectors that
give the impression styling was intended but not finished.
**Fix:** Either add the intended spacing/typography rules under `.sync-page :deep(.platform-banner)`
in the component's `<style>` block, or drop the unused class names if the default `el-alert`
spacing is sufficient.

---

_Reviewed: 2026-07-28T01:58:55Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
