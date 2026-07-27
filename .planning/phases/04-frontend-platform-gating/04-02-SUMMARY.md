---
phase: 04-frontend-platform-gating
plan: 02
subsystem: ui
tags: [i18n, vue-i18n, node-test, macos, gatekeeper, localStorage]

# Dependency graph
requires:
  - phase: 04-frontend-platform-gating (plan 01)
    provides: "capabilitiesGating.js D-00 gating module + established platformLimits i18n namespace, node --test frontend/src/lib/*.test.js as the corrected test command"
provides:
  - "frontend/src/lib/i18n-parity.test.js — automated zh-CN/en-US key-set parity guard (recursive, order-insensitive) plus a Phase 4 required-keys assertion consumed by every downstream wave-3/4 plan"
  - "24 new bilingual i18n leaf keys (platformLimits x10, syncer x2, gatekeeper x11, engineLockedHint already existed) — the single, final key surface for 04-03/04-04/04-05 to consume verbatim"
  - "frontend/src/lib/macosGatekeeperNotice.js — independent first-run Gatekeeper gate + pure HTML builder, consumed by 04-04 (settings re-view button) and 04-05 (App.vue first-run modal)"
affects: [04-03, 04-04, 04-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "i18n-parity.test.js: flatten-to-dotted-path + Set-diff comparison, order-insensitive, prints exact missing paths on failure"
    - "macosGatekeeperNotice.js: same 'independent localStorage key + pure gate functions' shape as openSourceNotice.js, but plain readable code (no base64 obfuscation — that mechanism exists solely for _g.py's anti-tamper lock, not a general pattern)"
    - "TDD RED/GREEN commit pairs for both i18n required-keys assertion and the new logic module, matching 04-01's established convention"

key-files:
  created:
    - frontend/src/lib/i18n-parity.test.js
    - frontend/src/lib/macosGatekeeperNotice.js
    - frontend/src/lib/macosGatekeeperNotice.test.js
  modified:
    - frontend/src/i18n/zh-CN.js
    - frontend/src/i18n/en-US.js

key-decisions:
  - "GATEKEEPER_XATTR_COMMAND is a module constant (not an i18n string) so zh-CN and en-US always render byte-identical, unit-asserted terminal syntax: 'xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app' — targets exactly one .app bundle, contains no sudo/spctl, matches backend/config.py's APP_NAME."
  - "shouldShowGatekeeperNotice(capabilities) checks platform === 'darwin' (not !== 'win32') — mirrors 04-01's isFirefoxEngineAvailable 'not-equal-false' pre-bootstrap-safe idiom but inverted: an undefined/pre-bootstrap platform must never trigger a macOS-only modal, so darwin is the single positive trigger, never inferred from navigator/user-agent (D-00)."
  - "Gatekeeper copy follows the post-Sequoia flow only (System Settings -> Privacy & Security -> Open Anyway), not the deprecated right-click-to-open instruction, per 04-RESEARCH.md's State of the Art citation."
  - "24 required-key list is centralized as a single array inside i18n-parity.test.js (not duplicated per-consumer) so any future locale edit that silently drops one of these keys fails loudly with the missing dotted path."

patterns-established:
  - "Pure-logic-module-with-localStorage-gate pattern (macosGatekeeperNotice.js) is now the second instance in frontend/src/lib/ after capabilitiesGating.js — future first-run/gate modules should follow the same 'no Vue/UI-library import, named exports, try/catch around all storage access' shape."

requirements-completed: [UI-03, UI-04]

coverage:
  - id: D1
    description: "Automated i18n parity guard: zh-CN and en-US recursive key sets are mutual subsets, every leaf is a non-empty string, and leaf counts match — any locale drift fails with the exact dotted-path key printed."
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/i18n-parity.test.js#zh-CN and en-US locale key sets are mutual subsets (parity)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/i18n-parity.test.js#every leaf value in both locales is a non-empty trimmed string"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/i18n-parity.test.js#zh-CN and en-US have the same non-zero number of leaf keys"
        status: pass
      - kind: unit
        ref: "manual repro: temporarily removed platformLimits.engineLockedHint from en-US.js, reran the parity test, observed failure message containing the exact missing dotted path, then restored the file (git diff confirmed zero)"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 24 Phase 4 i18n leaf keys (platformLimits x10 new + engineLockedHint from 04-01, syncer x2, gatekeeper x11) exist as non-empty strings in both locales, structurally 1:1, with zero regressions to the pre-existing 350 leaves."
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/i18n-parity.test.js#Phase 4 required i18n keys exist as non-empty strings in both locales"
        status: pass
      - kind: other
        ref: "node --input-type=module inline script from PLAN.md verify block -> printed 'all 24 keys present; total leaves 374'"
        status: pass
      - kind: other
        ref: "git diff --stat frontend/src/i18n/{zh-CN,en-US}.js -> 25/25 insertions; git diff -U0 ... | grep '^-' | wc -l -> 0 for both files (no existing copy altered)"
        status: pass
    human_judgment: false
  - id: D3
    description: "macosGatekeeperNotice.js provides an independent localStorage-gated first-run check (hasSeenGatekeeperNotice/markGatekeeperNoticeSeen/shouldShowGatekeeperNotice) that degrades silently on any storage exception and never derives platform from navigator/user-agent."
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/macosGatekeeperNotice.test.js (11 cases: empty storage, empty-string-as-unseen, idempotent mark, throwing-storage degrade for all three storage functions, darwin/win32/{}/undefined/null gating, key identity vs. openSourceNotice.js's key)"
        status: pass
    human_judgment: false
  - id: D4
    description: "buildGatekeeperNoticeHtml(t) is a pure function assembling only developer-authored i18n copy plus the GATEKEEPER_XATTR_COMMAND constant — no API/user/store-sourced dynamic value enters the dangerouslyUseHTMLString payload (T-04-04 mitigation), and the command itself is scoped to a single .app bundle with no sudo/spctl (T-04-06 mitigation)."
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/macosGatekeeperNotice.test.js#buildGatekeeperNoticeHtml includes the verbatim xattr command and references all four step keys"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/macosGatekeeperNotice.test.js#GATEKEEPER_XATTR_COMMAND targets a single .app bundle without sudo or spctl"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/macosGatekeeperNotice.test.js#buildGatekeeperNoticeHtml is pure: repeated calls return the same string with no storage side effects"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-27
status: complete
---

# Phase 4 Plan 2: i18n Parity Guard, Bilingual Copy, and Gatekeeper Notice Module Summary

**Added an automated zh-CN/en-US parity test (order-insensitive, recursive, prints exact missing paths), landed all 24 bilingual leaf keys the rest of Phase 4 will consume, and shipped `macosGatekeeperNotice.js` — an independent, exception-hardened first-run Gatekeeper gate with a pure HTML builder limited to a single `.app` bundle's `xattr` command.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-27
- **Tasks:** 3 (1 auto + 2 TDD)
- **Files modified:** 5 (3 new, 2 modified)

## Accomplishments
- `frontend/src/lib/i18n-parity.test.js` recursively flattens both locale dictionaries to dotted-path key sets, asserts mutual-subset parity (both directions), non-empty-string leaves, and equal non-zero leaf counts — verified to fail loudly with the exact missing path when a key is removed from either file, then restored to a zero-diff state.
- 24 new bilingual leaf keys landed 1:1 across `zh-CN.js`/`en-US.js`: 10 new `platformLimits.*` leaves (title/desc/tags/item descriptions/reopen button/kernel badge), 2 new `syncer.*` leaves (macOS-unavailable banner), and an entirely new `gatekeeper.*` section (11 leaves) describing the post-Sequoia System Settings -> Privacy & Security -> Open Anyway flow — none of the pre-existing 350 leaves were altered (`git diff -U0 | grep '^-'` returns 0 for both files).
- `frontend/src/lib/macosGatekeeperNotice.js` ships a fully independent first-run gate: its own localStorage key (`oab:macos-gatekeeper-notice:v1`, distinct from `openSourceNotice.js`'s `oab:first-use-notice:v2`), three storage functions all wrapped in try/catch (silent degrade, verified against a "throws on every call" stub), a `darwin`-only positive-trigger gate function, and a pure `buildGatekeeperNoticeHtml(t)` that assembles only `t()`-sourced copy plus the module's own `GATEKEEPER_XATTR_COMMAND` constant.
- Real end-to-end proof: `python3 -m backend._g --mode build` exits 0 and `git status --porcelain` on both `frontend/src/lib/openSourceNotice.js` and `frontend/src/App.vue` is empty — the hash-locked anti-tamper assets were never touched by this plan.

## Task Commits

Each task was committed atomically:

1. **Task 1: 建立 i18n 中英 parity 自动守护** - `ae0e40a` (test)
2. **Task 2: 一次性补齐本 phase 全部中英双语文案 (TDD)** - `cb8402e` (test, RED) → `40b615c` (feat, GREEN)
3. **Task 3: Gatekeeper 首启提示的纯逻辑模块 (TDD)** - `14294f1` (test, RED) → `1221965` (feat, GREEN)

## Files Created/Modified
- `frontend/src/lib/i18n-parity.test.js` - recursive flatten helpers + 4 test cases (base parity/non-empty/leaf-count trio from Task 1, plus the Phase-4 required-keys assertion added in Task 2)
- `frontend/src/i18n/zh-CN.js` / `frontend/src/i18n/en-US.js` - 10 `platformLimits.*` + 2 `syncer.*` + new 11-leaf `gatekeeper.*` section, all bilingual, structurally identical between files
- `frontend/src/lib/macosGatekeeperNotice.js` - `GATEKEEPER_NOTICE_KEY`, `GATEKEEPER_XATTR_COMMAND`, `hasSeenGatekeeperNotice()`, `markGatekeeperNoticeSeen()`, `shouldShowGatekeeperNotice(capabilities)`, `buildGatekeeperNoticeHtml(t)`
- `frontend/src/lib/macosGatekeeperNotice.test.js` - 11 node:test cases covering empty/idempotent/throwing-storage/gating/purity behaviors

## macosGatekeeperNotice.js — Full Exported API (for 04-04/04-05)

- **`GATEKEEPER_NOTICE_KEY`** = `'oab:macos-gatekeeper-notice:v1'` — independent from `openSourceNotice.js`'s `oab:first-use-notice:v2`; verified distinct by unit test.
- **`GATEKEEPER_XATTR_COMMAND`** = `'xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app'` — the exact, verbatim, unit-asserted string every consumer must render inside a `<code>` element. Targets a single installed `.app` bundle path (matches `backend/config.py`'s `APP_NAME = "Open-Anti-Browser"`); does not contain `sudo` or `spctl`; does not reference any broad directory.
- **`hasSeenGatekeeperNotice()`** → `boolean`. Reads `localStorage.getItem(GATEKEEPER_NOTICE_KEY) === '1'`; any read exception or an empty-string value both return `false` (treated as "not seen").
- **`markGatekeeperNoticeSeen()`** → `void`. Writes `'1'`; any write exception is swallowed silently (never propagates, never blocks `App.vue`'s `onMounted`). Idempotent — repeated calls leave a single key with an unchanged value.
- **`shouldShowGatekeeperNotice(capabilities)`** → `boolean`. `capabilities?.platform === 'darwin' && !hasSeenGatekeeperNotice()`. Uses the positive `=== 'darwin'` check (not `!== 'win32'`) so an undefined/pre-bootstrap `capabilities` object never triggers a macOS-only modal — mirrors 04-01's fail-open idiom but inverted for a modal that must default to *not showing*. Never derives platform from `navigator`/user-agent (D-00). `undefined`/`null`/`{}`/`{platform:'win32'}` all return `false`, never throw.
- **`buildGatekeeperNoticeHtml(t)`** → `string`. Assembles `gatekeeper.intro` → `gatekeeper.stepsTitle` → `gatekeeper.step1..4` (ordered list) → `gatekeeper.commandTitle` → `GATEKEEPER_XATTR_COMMAND` (inside `<code>`) → `gatekeeper.commandHint` → `gatekeeper.settingsHint`. Pure: no localStorage access, no side effects, deterministic output for a given `t`. Consumers pass `vue-i18n`'s `t` function; the resulting string is intended for `ElMessageBox.alert(html, title, { dangerouslyUseHTMLString: true, ... })`, matching the shape of the existing (untouched) `_0x31ab()` first-use-notice flow in `App.vue`.

## The 24 Required i18n Key Paths (04-03/04-04/04-05 must consume these verbatim, not introduce new ones)

```
platformLimits.engineLockedHint   (already existed, from 04-01)
platformLimits.title
platformLimits.desc
platformLimits.windowsOnlyTag
platformLimits.windowsOnlyFallback
platformLimits.firefoxItem
platformLimits.windowItem
platformLimits.gatekeeperItem
platformLimits.startBlockedHint
platformLimits.reopenGatekeeper
platformLimits.kernelWindowsOnly
syncer.platformBannerTitle
syncer.platformBannerHint
gatekeeper.title
gatekeeper.intro
gatekeeper.stepsTitle
gatekeeper.step1
gatekeeper.step2
gatekeeper.step3
gatekeeper.step4
gatekeeper.commandTitle
gatekeeper.commandHint
gatekeeper.settingsHint
gatekeeper.confirm
```

Total locale leaf count after this plan: **374** (350 pre-existing + 24 above).

## Decisions Made
- `GATEKEEPER_XATTR_COMMAND` is a hardcoded module constant rather than an i18n string, specifically so both locales render the identical, unit-tested terminal command — i18n keys only carry the surrounding title/hint prose (per plan's explicit red line against putting the command itself in i18n copy).
- The Gatekeeper copy (`gatekeeper.step2`/`step3`) describes the current macOS Sequoia-era flow (System Settings → Privacy & Security → Open Anyway) rather than the deprecated right-click-to-open shortcut, per `04-RESEARCH.md`'s State-of-the-Art citation — this avoids shipping instructions that read as broken on any Mac running Sequoia or later.
- `shouldShowGatekeeperNotice` gates on `capabilities?.platform === 'darwin'` (a positive check), not `!== 'win32'` — an undefined/pre-bootstrap `capabilities` value must never trigger a macOS-specific modal; this is a deliberate asymmetry versus `capabilitiesGating.js`'s fail-open engine-visibility checks (which default to *available* for undefined capabilities), because a modal is not "hidden" if it never fires, and firing a wrong-platform modal is the greater regression risk.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded a code comment in `macosGatekeeperNotice.js` that literally contained the string "element-plus", false-positiving the plan's own acceptance-criteria grep guard (`grep -c "element-plus" ... → 0`)**
- **Found during:** Task 3 acceptance-criteria check
- **Issue:** The module's header comment explaining "this module does not import element-plus" contained the literal substring `element-plus`, which the plan's own verification grep (`grep -c "element-plus" frontend/src/lib/macosGatekeeperNotice.js` expected `0`) matched against, even though no code actually imports the package. Identical class of self-inflicted false positive documented in 04-01's SUMMARY for the `navigator.platform` grep guard.
- **Fix:** Reworded the comment to describe the constraint (no UI component library / Vue runtime dependency) without using the literal package name.
- **Files modified:** `frontend/src/lib/macosGatekeeperNotice.js`
- **Verification:** `grep -c "element-plus" frontend/src/lib/macosGatekeeperNotice.js` → `0`
- **Committed in:** `1221965` (Task 3 GREEN commit)

**2. [Rule 1 - Bug] Fixed an over-specified test assertion for the throwing-localStorage-stub case**
- **Found during:** Task 3 GREEN run (initial test failure after implementing the module)
- **Issue:** The RED-phase test for "all storage functions degrade silently when localStorage throws on every call" asserted `shouldShowGatekeeperNotice({ platform: 'darwin' })` returns `false` under a throwing storage stub. The plan's `<behavior>` block only specifies this call must not throw ("不抛") for the throwing-stub case — it does not pin a specific return value. Since `hasSeenGatekeeperNotice()` correctly degrades to `false` ("not seen") when storage throws, `shouldShowGatekeeperNotice` correctly evaluates to `true` for a darwin capabilities object in that scenario — the test's return-value assertion contradicted the plan's own stated behavior, not the implementation.
- **Fix:** Changed the assertion to only verify the call does not throw, matching the plan's `<behavior>` wording exactly; removed the incorrect return-value pin.
- **Files modified:** `frontend/src/lib/macosGatekeeperNotice.test.js`
- **Verification:** `node --test frontend/src/lib/macosGatekeeperNotice.test.js` → 11/11 pass
- **Committed in:** `1221965` (Task 3 GREEN commit)

---

**Total deviations:** 2 auto-fixed (2 bugs — both self-inflicted test/comment authoring issues caught before the plan's own acceptance criteria were run; zero deviations in production module logic or i18n content).
**Impact on plan:** Cosmetic/test-authoring only. No behavior change to the shipped module API, no scope creep, no change to i18n copy content.

## Issues Encountered
None beyond the two auto-fixed items above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `macosGatekeeperNotice.js`'s full API is ready for 04-04 (AppSettings.vue re-view button, calling `markGatekeeperNoticeSeen()`/`buildGatekeeperNoticeHtml(t)` to re-show the guide on demand) and 04-05 (App.vue `onMounted`, gating on `shouldShowGatekeeperNotice(store.capabilities)` immediately after the existing, untouched `_0x31ab()` open-source notice call).
- All 24 required i18n keys are locked in and parity-guarded — 04-03 (ProfileList Firefox-disabled hint), 04-04 (SyncManager banner + AppSettings platform-limits card), and 04-05 (App.vue nav gating + first-run modal mount) should consume these exact dotted paths, not introduce new ones.
- `i18n-parity.test.js` will now catch any future locale drift automatically as part of `node --test frontend/src/lib/*.test.js` — no manual bilingual diffing required going forward.
- No blockers. `App.vue` and `openSourceNotice.js` remain completely unmodified by this plan; the `_g.py` SHA-256 lock is verified still satisfied (`python3 -m backend._g --mode build` exits 0).

---
*Phase: 04-frontend-platform-gating*
*Completed: 2026-07-27*

## Self-Check: PASSED

All 3 created files and all 5 task commit hashes (`ae0e40a`, `cb8402e`, `40b615c`, `14294f1`, `1221965`) verified present.
