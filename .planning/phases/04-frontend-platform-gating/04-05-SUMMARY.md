---
phase: 04-frontend-platform-gating
plan: 05
subsystem: ui
tags: [vue3, i18n, capabilities-contract, platform-gating, integrity-lock, element-plus]

# Dependency graph
requires:
  - phase: 04-frontend-platform-gating (plan 01)
    provides: "capabilitiesGating.js — isFirefoxEngineAvailable, getWindowFeatureGate as the D-00 single source of truth"
  - phase: 04-frontend-platform-gating (plan 02)
    provides: "macosGatekeeperNotice.js (shouldShowGatekeeperNotice/markGatekeeperNoticeSeen/buildGatekeeperNoticeHtml) and gatekeeper.*/platformLimits.windowsOnlyFallback i18n keys"
  - phase: 04-frontend-platform-gating (plan 04)
    provides: "SyncManager.vue banner + disabled controls the greyed nav item routes into"
provides:
  - "App.vue: sidebar Firefox status row hidden via firefoxEngineVisible; syncer nav item greyed (el-tooltip + .nav-item.disabled) via isNavDisabled/navDisabledReason, click handler left unconditional"
  - "App.vue: maybeShowGatekeeperNotice() mounted in onMounted immediately after the existing open-source first-use notice, gated by shouldShowGatekeeperNotice(store.capabilities)"
  - "backend/_g.py: App.vue's SHA-256 digest recomputed to match its final byte content post-edit; integrity mechanism otherwise untouched"
affects: [04-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "App.vue's nav v-for wrapped one level deeper in el-tooltip (v-for/:key moved up), :disabled bound to !isNavDisabled so only gated items show a bubble — same shape as SyncManager.vue's per-button tooltips from 04-04"
    - "backend/_g.py relock procedure: recompute App.vue's SHA-256 only after all App.vue edits are final, replace exactly one dict value, verify with --mode build then a full npm run build (covers --mode runtime's build-artifact marker scan)"

key-files:
  created: []
  modified:
    - frontend/src/App.vue
    - frontend/src/assets/global.css
    - backend/_g.py

key-decisions:
  - "GroupManager.vue's per-group Firefox profile-count column (line ~36) is deliberately NOT hidden — D-01's three enumerated hiding points don't include it, it reports the true composition of existing configs, and hiding it would make group totals not add up (contradicts D-01's 'never hide/delete/silently drop existing data'). It is not a Firefox-creation entry point, so SC1 is unaffected."
  - "isNavDisabled/navDisabledReason are generic-by-key functions (only 'syncer' currently gates) rather than a single hardcoded boolean, matching capabilitiesGating.js's per-feature getWindowFeatureGate shape so a future gated nav item is a one-line addition"
  - "Gatekeeper modal is awaited strictly after _0x31ab() (the open-source notice) inside the same onMounted try block — sequencing preserves T-04-12's anti-repudiation intent (open-source notice must never be skipped, delayed, or replaced) while letting macosGatekeeperNotice.js's own localStorage try/catch handle storage failures without a second try/catch"
  - "npm run build's prebuild/postbuild hooks invoke a literal 'python' binary; this sandbox only has python3 on PATH. Per the plan's explicit prohibition on touching frontend/package.json's hooks, no repo file was changed — a throwaway 'python -> python3' symlink was created in the session scratchpad directory and prepended to PATH for the single npm run build invocation only. Zero footprint on the repository or the user's machine-wide environment."

patterns-established:
  - "Nav-item disabled state pattern (el-tooltip wrapper + .nav-item.disabled CSS + reason bound verbatim from backend, i18n fallback only for empty reason) is now the third instance of D-02's 'grey, don't hide' contract after SyncManager.vue's button-level tooltips and AppSettings.vue's platform-limits card — any future gated nav entry should follow the same isNavDisabled(key)/navDisabledReason(key) dispatch shape."

requirements-completed: [UI-01, UI-02, UI-04]

coverage:
  - id: D1
    description: "On a machine where capabilities.engines.firefox.available === false, the sidebar kernel-status card shows only the Chrome row; the Firefox row is conditionally rendered out via firefoxEngineVisible, Chrome's row carries no condition."
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "grep -c 'firefoxEngineVisible' frontend/src/App.vue -> 2 (computed declaration + v-if); grep -n '<span>Chrome</span>' -> line has no v-if on its status-row"
        status: pass
    human_judgment: true
    rationale: "Visual confirmation on a real macOS run (only Chrome row visible, no layout gap) was not screenshot-verified in this non-interactive session; the conditional-rendering wiring and firefoxEngineVisible -> isFirefoxEngineAvailable(store.capabilities) data path are grep/unit-verified."
  - id: D2
    description: "On a machine where capabilities.window.sync.available === false, the sidebar 'syncer' nav item renders greyed (.nav-item.disabled, ~0.45 opacity, not-allowed cursor) with an el-tooltip showing the backend's verbatim reason (or platformLimits.windowsOnlyFallback when reason is empty), while @click=\"setActiveNav(item.key)\" remains completely unconditional so the synchronizer view stays reachable."
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "node --input-type=module inline check from PLAN.md Task 1 verify block — printed 'App shell gating OK'"
        status: pass
      - kind: unit
        ref: "grep checks: isNavDisabled/navDisabledReason each declared exactly once; setActiveNav(item.key) present unconditionally; no @click attribute references isNavDisabled; navigator.platform/userAgent grep across frontend/src/App.vue -> 0"
        status: pass
    human_judgment: true
    rationale: "The plan's own acceptance criteria call for a macOS-machine visual/interaction pass (nav item visibly faded, cursor not-allowed, tooltip bubble on hover, click still reaching the SyncManager view with its 04-04 banner) — not screenshot-verified in this non-interactive session; the underlying template/computed wiring and D-02 'click stays unconditional' invariant are grep-asserted."
  - id: D3
    description: "On macOS first run, immediately after the existing open-source first-use notice is dismissed, a Gatekeeper release-instruction modal appears exactly once (gated by its own independent oab:macos-gatekeeper-notice:v1 localStorage key), rendering the verbatim xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app command inside a selectable, wrap-safe <code> element; it never appears on Windows or before capabilities resolves, and marking it seen prevents recurrence."
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "node --input-type=module inline checks from PLAN.md Task 2 verify block — printed 'gatekeeper mount OK' and 'command literal OK: xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app'"
        status: pass
      - kind: unit
        ref: "index-of check: 'await _0x31ab()' occurs before 'await maybeShowGatekeeperNotice()' inside onMounted; grep confirms _0x31ab appears exactly twice (declaration + call), oab:first-use-notice:v2 and first-use-notice-box markers both still present exactly once"
        status: pass
    human_judgment: true
    rationale: "The plan's acceptance criteria require an actual macOS browser pass: delete the gatekeeper localStorage key, reload, confirm the open-source notice fires first and the gatekeeper modal fires second, confirm the command renders character-for-character selectable/copyable in both zh-CN and en-US, and confirm it does not reappear after confirming. This is a rendering/interaction check not performed in this non-interactive session; the sequencing, gating, and command-literal invariants are unit/grep-verified."
  - id: D4
    description: "backend/_g.py's App.vue SHA-256 digest matches the file's final post-edit bytes; both --mode build and --mode runtime (via a full npm run build) pass; the integrity table still holds exactly 2 entries, the build-artifact marker table still holds 6 markers, and _5/_7's verification logic is unchanged (10/5 source lines respectively)."
    verification:
      - kind: unit
        ref: "python3 -m backend._g --mode build -> exit 0; python3 inline integrity-table self-check script -> printed 'integrity table OK: [...App.vue, ...openSourceNotice.js]'; cd frontend && npm run build -> exit 0 (prebuild --mode build + vite build + postbuild --mode runtime all succeeded)"
        status: pass
      - kind: unit
        ref: "git diff -U0 backend/_g.py | grep -cE '^[+-][^+-]' -> 2 (exactly one delete + one add); openSourceNotice.js status/package.json status both git status --porcelain empty; _5/_7 source line counts unchanged at 10/5"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-27
status: complete
---

# Phase 4 Plan 5: App Shell Gating and Integrity Relock Summary

**App.vue's sidebar now hides the Firefox kernel-status row and greys the syncer nav item (tooltip + click still reachable) on capability-gated machines, mounts a one-time macOS Gatekeeper release-instruction modal sequenced strictly after the existing open-source notice, and backend/_g.py's App.vue SHA-256 lock was recomputed to the file's final bytes with the anti-tamper mechanism otherwise untouched.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-27
- **Tasks:** 3 (all `type="auto"`)
- **Files modified:** 3 (`frontend/src/App.vue`, `frontend/src/assets/global.css`, `backend/_g.py`)

## Accomplishments
- `App.vue`: imported `isFirefoxEngineAvailable`/`getWindowFeatureGate` from `capabilitiesGating.js`; added `firefoxEngineVisible` computed gating the sidebar's Firefox status row (`v-if`), Chrome's row left unconditional.
- `App.vue`: nav `v-for` wrapped in `el-tooltip` (per-item, `:disabled="!isNavDisabled(item.key)"`, `:content="navDisabledReason(item.key)"`, `placement="right"`); added `isNavDisabled(key)`/`navDisabledReason(key)` dispatch functions gating only `'syncer'` via `getWindowFeatureGate(store.capabilities, 'sync')`; `@click="setActiveNav(item.key)"` left completely unconditional so the synchronizer view stays reachable (D-02).
- `frontend/src/assets/global.css`: added `.nav-item.disabled` (opacity 0.45, `cursor: not-allowed`) and a `.nav-item.disabled:hover` reset so a greyed item never looks hover-highlighted; the three pre-existing `.nav-item*` rules are untouched (verified via diff).
- `App.vue`: imported `shouldShowGatekeeperNotice`/`markGatekeeperNoticeSeen`/`buildGatekeeperNoticeHtml` from `macosGatekeeperNotice.js`; added `async function maybeShowGatekeeperNotice()` (no dynamic interpolation, reuses 04-02's builder verbatim) and awaited it in `onMounted` immediately after `await _0x31ab()` (the existing open-source notice) and before both `setInterval` calls — sequencing is source-order-verified.
- `frontend/src/assets/global.css`: added `.gatekeeper-notice-box`/`.gatekeeper-notice` styling with a monospace, selectable, wrap-safe `<code>` rule so the `xattr` command renders character-for-character and is fully copyable; `.first-use-notice-box`/`.first-use-notice` rules untouched.
- `backend/_g.py`: recomputed `frontend/src/App.vue`'s SHA-256 (`31871ec3656874a435c4744b7ce807669089f6596481325805c1c9fadc320f7d`, replacing `cfa6427a0c0f17357a41888128ed7d391c2efde62214304d9654027250886104`) as the single changed line, after both App.vue edits landed. `python3 -m backend._g --mode build` and a full `npm run build` (prebuild `--mode build` + `vite build` + postbuild `--mode runtime`) all pass; the integrity table still holds exactly 2 entries, the build-artifact marker table still holds 6 markers, and `openSourceNotice.js`'s entry/`frontend/package.json` are both `git status --porcelain`-clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: 侧栏 Firefox 状态行隐藏 + 同步器导航项置灰(入口不屏蔽)** - `59cad68` (feat)
2. **Task 2: macOS 首次运行的 Gatekeeper 放行指引弹窗** - `9c96040` (feat)
3. **Task 3: 重算 App.vue 摘要写回完整性校验表** - `caefdcf` (chore)

## Files Created/Modified
- `frontend/src/App.vue` - `firefoxEngineVisible` computed + `v-if` on Firefox status row; nav `el-tooltip` wrapper + `isNavDisabled`/`navDisabledReason`; `maybeShowGatekeeperNotice()` mounted after the existing open-source notice
- `frontend/src/assets/global.css` - `.nav-item.disabled` + hover-reset rule; `.gatekeeper-notice-box`/`.gatekeeper-notice`/`code` styling
- `backend/_g.py` - single App.vue digest value updated in the `_1` integrity table

## The final App.vue SHA-256 and its commit

- **New digest:** `31871ec3656874a435c4744b7ce807669089f6596481325805c1c9fadc320f7d`
- **Computed from:** `frontend/src/App.vue` as it exists after commit `9c96040` (Task 2's final edit) — Task 3 (`caefdcf`) writes this exact value into `backend/_g.py`'s `_1` dict and makes no further App.vue edits.

## First-run modal sequencing (final order)

1. `await store.bootstrap()` → `await store.getBackendModeStatus()`
2. `await _0x31ab()` — existing open-source first-use notice (`oab:first-use-notice:v2`, untouched, must always fire first per T-04-12)
3. `await maybeShowGatekeeperNotice()` — new Gatekeeper release-instruction modal (`oab:macos-gatekeeper-notice:v1`), only on `capabilities.platform === 'darwin'` and only if not previously seen
4. The two `setInterval` polling timers start

Both awaits share the single pre-existing `onMounted` `try`/`catch` — no new try/catch block was added (see Deviations for a plan-assertion discrepancy on the exact `try {` count).

## Decisions Made
- **GroupManager.vue Firefox count column (planning discretion, carried over from plan text):** the per-group Firefox profile-count column at `GroupManager.vue` line ~36 is **not** hidden. D-01 enumerates exactly three hiding points for this phase and this column is not one of them; it reports the true composition of already-existing profiles, and hiding it would make group totals not reconcile with the underlying data — directly contradicting D-01's "never hide/delete/silently drop existing data" rule. It is not a Firefox-profile-creation entry point, so it does not affect SC1 ("new-profile flows never offer Firefox on unsupported machines").
- `isNavDisabled`/`navDisabledReason` are written as key-dispatch functions (`if (key === 'syncer') { ... } return false/''`) rather than a single inlined boolean expression on the `syncer` nav item, so any future gated nav entry in this phase or later is a one-line branch addition, matching `capabilitiesGating.js`'s per-feature `getWindowFeatureGate` shape.
- `maybeShowGatekeeperNotice()` deliberately reuses the existing `onMounted` `try` block (no second `try`/`catch`) — `macosGatekeeperNotice.js`'s own storage functions already degrade silently on any `localStorage` exception (unit-tested in 04-02), so a second try/catch here would be redundant defensive layering, not a correctness requirement.
- The npm `python` vs `python3` PATH gap (see below) was worked around with a session-scratchpad-only symlink prepended to `PATH` for a single command invocation, specifically to honor the plan's explicit prohibition on touching `frontend/package.json`'s `prebuild`/`postbuild` hooks. No repository file and no persistent machine-level configuration was changed.

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1/2/3 code fixes were needed; both edits and the digest relock followed the plan's action blocks directly.

### Environment workaround (not a code deviation)

**1. `npm run build`'s prebuild/postbuild hooks invoke `python`, this sandbox only has `python3`**
- **Found during:** Task 3 verification (`cd frontend && npm run build`)
- **Issue:** `frontend/package.json`'s `prebuild`/`postbuild` scripts run `python -m backend._g --mode {build,runtime}`. This execution sandbox's `PATH` contains only `python3` (Homebrew-installed), no bare `python` symlink, so a direct `npm run build` failed at the prebuild step with `sh: python: command not found` — before any code from this plan ever ran.
- **Fix:** The plan explicitly prohibits touching `frontend/package.json`'s prebuild/postbuild hooks (a change to those hooks is listed among the operations that would weaken the integrity mechanism's blast-radius guarantee), so no repository file was modified. Instead, a throwaway `python -> python3` symlink was created inside this session's scratchpad directory (`/private/tmp/claude-501/.../scratchpad/bin/python`) and prepended to `PATH` for the single `npm run build` invocation only. This is a per-command shell-level shim with zero footprint on the repository and no lasting change to the user's machine environment.
- **Files modified:** None (workaround is entirely outside the repository).
- **Verification:** `PATH="$SCRATCH/bin:$PATH" npm run build` — prebuild (`--mode build`), `vite build`, and postbuild (`--mode runtime`) all completed successfully; `git status --porcelain` on `frontend/package.json` and every other repo file remained clean throughout.
- **Committed in:** N/A — no commit, as no repository file changed.

### Plan-assertion discrepancies (verified equivalent by more precise checks)

**1. Task 2's `sed ... | grep -c 'try {'` acceptance criterion expects `1`, actual count is `3`**
- **Found during:** Task 2 acceptance-criteria check
- **Issue:** The plan's acceptance criteria assert `sed -n '/^onMounted/,/^})/p' frontend/src/App.vue | grep -c 'try {'` outputs `1` ("no independent try/catch was added"). The `onMounted` body already contained 3 occurrences of `try {` *before* this plan touched the file: the outer `try` plus one `try` inside each of the two pre-existing `setInterval` polling callbacks (`profileRefreshTimer`, `backendStatusTimer`). Confirmed via `git show HEAD~3:frontend/src/App.vue | sed ... | grep -c 'try {'` → `3` (pre-plan baseline).
- **Resolution:** This is a discrepancy in the plan's own acceptance-criteria assertion (it did not account for the two nested interval-callback `try` blocks), not an execution error. The actual invariant the criterion is meant to protect — "this task adds zero new `try`/`catch` blocks" — holds exactly: the count is 3 both before and after this plan's edits, and `await maybeShowGatekeeperNotice()` was added to the single existing outer `try` block, not wrapped in a new one.
- **Verification:** `git diff 47b5c62 HEAD -- frontend/src/App.vue` shows only additive lines for `maybeShowGatekeeperNotice` itself and its `onMounted` call site — no `try`/`catch` keyword appears in the diff's added lines.

**2. Task 3's `git diff backend/_g.py | grep -c '2a766e...'` acceptance criterion expects `0`, actual count is `1`**
- **Found during:** Task 3 acceptance-criteria check
- **Issue:** The plan asserts the `openSourceNotice.js` digest string must not appear anywhere in `git diff backend/_g.py`'s output. Because that digest sits on the line immediately above the changed App.vue digest line, `git diff`'s default 3-line context window includes it as an unchanged context line (prefixed with a space, not `+`/`-`).
- **Resolution:** Not a real omission — the more precise check already specified elsewhere in the same task's acceptance criteria, `git diff -U0 backend/_g.py | grep -cE '^[+-][^+-]'` → `2` (exactly one deletion + one addition, both on the App.vue line only), proves the `openSourceNotice.js` entry was never part of the actual change. Re-ran with `-U0` (no context) and confirmed the digest string does not appear in any `+`/`-` line.
- **Verification:** `git diff -U0 backend/_g.py` shows exactly 2 changed lines, both for the App.vue key.

---

**Total deviations:** 0 code auto-fixes; 1 environment-only workaround (no repo footprint); 2 plan-assertion discrepancies resolved by cross-checking with a more precise command already present in the same task's own acceptance criteria.
**Impact on plan:** None on shipped behavior or the integrity mechanism. All plan prohibitions (no `package.json` hook edits, no `openSourceNotice.js` edits, no `_1`/`_2`/`_5`/`_7` logic changes) were honored exactly.

## Issues Encountered
See "Environment workaround" and "Plan-assertion discrepancies" above — both fully resolved within this session, no open follow-up required.

## User Setup Required
None - no external service configuration required. (Note: this sandbox's `PATH` lacking a `python` alias is a pre-existing local-machine condition unrelated to this plan; a real macOS deployment target already has `python` resolving correctly per this repo's other phases' verified CI runs.)

## Next Phase Readiness
- All three of this phase's remaining UI gating requirements (UI-01, UI-02, UI-04) are now wired end-to-end in the app shell; `04-06` (if it exists) can proceed to any remaining human-facing wording/visual pass.
- `backend/_g.py`'s integrity lock is fully relocked to `App.vue`'s current bytes; any *future* plan touching `App.vue` again must rerun Task 3's exact procedure (recompute digest, single-line replace, `--mode build` + full `npm run build`) before that plan can close.
- Four coverage items in this SUMMARY (D1-D3, all requiring a real macOS interactive browser pass) are marked `human_judgment: true` — a human should visually confirm: (1) only the Chrome kernel row shows in the sidebar, (2) the syncer nav item is visibly greyed with a working tooltip and still navigable, and (3) the Gatekeeper modal fires once, in the correct order relative to the open-source notice, with a byte-perfect copyable command, in both zh-CN and en-US.
- No blockers for downstream work. `openSourceNotice.js` and `frontend/package.json` remain byte-for-byte untouched across this entire plan.

---
*Phase: 04-frontend-platform-gating*
*Completed: 2026-07-27*

## Self-Check: PASSED

SUMMARY.md and all 3 task commit hashes (`59cad68`, `9c96040`, `caefdcf`) verified present.
