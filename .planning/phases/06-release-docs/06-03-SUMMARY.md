---
phase: 06-release-docs
plan: 03
subsystem: docs
tags: [i18n, gatekeeper, dmg, node-test, macos]

# Dependency graph
requires:
  - phase: 06-release-docs
    provides: ".github/RELEASE_NOTES_TEMPLATE.md (06-01) as the canonical bilingual 放行 wording, and the quoted GATEKEEPER_XATTR_COMMAND single-source-of-truth (06-01/D-04) this plan must not duplicate"
provides:
  - "gatekeeper.step1-step4 in both zh-CN.js and en-US.js rewritten so step1 is the measured double-click-again path and step2 is the System-Settings fallback"
  - "frontend/src/lib/gatekeeperCopyParity.test.js — a standing node:test lock on the step ordering plus a forbidden-fragment gate over the whole gatekeeper block in both locales"
  - "Regenerated assets/dmg-background.png and assets/dmg-background@2x.png whose footer describes the same double-click-again flow instead of the never-exercised right-click route"
affects: [06-04, 06-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "gatekeeperCopyParity.test.js follows i18n-parity.test.js's direct-import-both-locales pattern rather than DOM rendering, keeping the assertion at the string-content level where the copy actually lives"
    - "Forbidden-fragment audit is now enforced twice at two different layers: once as a standing node:test over the shipped i18n strings (gatekeeperCopyParity.test.js), and once as a one-time manual grep over the ephemeral dmg-background scratch HTML before it is deleted (05-01's precedent, repeated verbatim here)"

key-files:
  created:
    - frontend/src/lib/gatekeeperCopyParity.test.js
  modified:
    - frontend/src/i18n/zh-CN.js
    - frontend/src/i18n/en-US.js
    - assets/dmg-background.png
    - assets/dmg-background@2x.png

key-decisions:
  - "step4's new wording ('如果以上都不行，再使用下方的终端命令作为最后手段' / 'If none of that works, use the terminal command below as the last resort.') deliberately does not restate GATEKEEPER_XATTR_COMMAND, preserving 06-01's single-source-of-truth lock — buildGatekeeperNoticeHtml still renders the command from the module constant immediately below the <ol>"
  - "dmg background footer kept to exactly two short lines (Chinese, then English) rather than reproducing the full three-step progressive disclosure the in-app notice and release notes carry — the dmg window is a signpost pointing at the Release notes for the full walkthrough, consistent with 05-01's original scoping decision"
  - "New composition re-derived at the same 600x400/1200x800 geometry and (150,190)/(450,190) slot centers create-dmg already depends on — no coordinate change, only the footer text"

patterns-established: []

requirements-completed: [DOCS-01]

coverage:
  - id: D1
    description: "gatekeeper.step1 in both zh-CN.js and en-US.js describes double-clicking the app a second time as the primary, usually-sufficient action, with System Settings demoted to step2's fallback"
    requirement: "DOCS-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/gatekeeperCopyParity.test.js#gatekeeper.step1 describes double-clicking the app again as the primary action (both locales)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/gatekeeperCopyParity.test.js#gatekeeper.step1 does not mention the System Settings fallback in either locale"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/gatekeeperCopyParity.test.js#gatekeeper.step2 is the System Settings -> Privacy & Security fallback (both locales)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/i18n-parity.test.js#Phase 4 required i18n keys exist as non-empty strings in both locales"
        status: pass
    human_judgment: false
  - id: D2
    description: "No value in either locale's gatekeeper block contains a privilege-escalation fragment (sudo, spctl, --master-disable, csrutil, ~/Downloads), and step4 does not duplicate GATEKEEPER_XATTR_COMMAND"
    requirement: "DOCS-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/gatekeeperCopyParity.test.js#neither locale's gatekeeper block contains a forbidden privilege-escalation fragment"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/gatekeeperCopyParity.test.js#gatekeeper.step4 leads into the command block without restating GATEKEEPER_XATTR_COMMAND"
        status: pass
    human_judgment: false
  - id: D3
    description: "assets/dmg-background.png (600x400) and assets/dmg-background@2x.png (1200x800) regenerated with a bilingual footer describing the double-click-again flow, at the exact dimensions and icon-slot geometry create-dmg depends on"
    requirement: "DOCS-01"
    verification:
      - kind: other
        ref: "sips -g pixelWidth -g pixelHeight (600x400 and 1200x800 confirmed) + tiffutil -cathidpicheck (2 images written) — both executed and passed during this run"
        status: pass
    human_judgment: true
    rationale: "Automated checks confirm dimensions, TIFF composability, and the absence of forbidden phrases in the generating HTML, but whether the placeholder slots visually align under Finder's real icon overlay and whether the footer text reads well in an actual mounted dmg window can only be fully confirmed once a real create-dmg run is inspected — Read-tool visual inspection was performed this session (slot positions, arrow direction, unclipped bilingual footer, correct Chinese glyph rendering all confirmed), but a human sign-off at ship time is still valuable, consistent with 05-01's precedent for the same asset."

duration: 15min
completed: 2026-07-31
status: complete
---

# Phase 06 Plan 03: Align in-app notice and dmg background to the measured 放行 flow Summary

**Rewrote `gatekeeper.step1`–`step4` in both locales so double-clicking the app again is the first step (not System Settings), added a standing node:test lock plus forbidden-fragment gate, and regenerated the dmg drag-install background's footer to match — bringing all three release-facing surfaces (release notes, in-app notice, dmg background) into agreement on the flow Phase 5 actually measured on real hardware.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-31T18:18:00Z (approx)
- **Completed:** 2026-07-31T18:21:25Z
- **Tasks:** 2
- **Files modified:** 5 (2 i18n files, 1 new test file, 2 regenerated PNGs)

## Accomplishments

- `gatekeeper.step1` in `zh-CN.js` and `en-US.js` now describes the second double-click as the action that resolves the block, framing the app quitting itself on the first attempt as expected rather than a crash — closing the exact gap `05-06-SUMMARY.md` Open Item 2 named (the user's only signal after the first denial used to be that the app disappeared, with nothing telling them to try again)
- `gatekeeper.step2`–`step4` kept as the System Settings → Privacy & Security fallback, the "仍要打开" confirmation, and the terminal-command last resort respectively — all eleven `gatekeeper.*` keys survive unchanged in both locales, and `buildGatekeeperNoticeHtml` needed zero changes
- New `frontend/src/lib/gatekeeperCopyParity.test.js` locks the step1-is-double-click / step2-is-fallback ordering and asserts the full forbidden-fragment list (`sudo`, `spctl`, `--master-disable`, `csrutil`, `~/Downloads`) against every value in both locales' `gatekeeper` blocks — fail-first evidence captured against the pre-rewrite copy (see TDD Gate Compliance)
- `assets/dmg-background.png` (600×400) and `assets/dmg-background@2x.png` (1200×800) regenerated via the same zero-dependency headless-Chromium process 05-01 established, replacing the "右键 → 打开" footer (a route `05-06-SUMMARY.md` records as never exercised) with a two-line bilingual signpost matching the release-notes template's framing, at the exact geometry `create-dmg` already depends on

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite the in-app gatekeeper steps to the measured flow in both locales, and lock the ordering** - `2973269` (feat)
2. **Task 2: Regenerate the dmg drag-install background so its footer describes the measured first-run flow** - `403a8a0` (feat)

**Plan metadata:** committed separately below (docs: complete plan)

_Note: Task 1 is `tdd="true"`; RED/GREEN was demonstrated in a single commit per task, since the fail-first run (against the pre-rewrite locale files) was verified by hand before the edit landed — see "TDD Gate Compliance" below for the exact failure message captured._

## Files Created/Modified

- `frontend/src/i18n/zh-CN.js` - `gatekeeper.step1`–`step4` rewritten; all other keys/values untouched
- `frontend/src/i18n/en-US.js` - `gatekeeper.step1`–`step4` rewritten (English mirror); all other keys/values untouched
- `frontend/src/lib/gatekeeperCopyParity.test.js` - New node:test locking step1/step2 ordering and the forbidden-fragment gate
- `assets/dmg-background.png` - Regenerated 600×400 dmg drag-install background, new footer text only
- `assets/dmg-background@2x.png` - Regenerated 1200×800 retina counterpart, same footer text

## Fail-First Evidence (Task 1, tdd="true")

`node --test frontend/src/lib/gatekeeperCopyParity.test.js` run against the pre-rewrite copy (before editing the locale files):

```
not ok 1 - gatekeeper.step1 describes double-clicking the app again as the primary action (both locales)
  error: 'zh-CN step1 应提到"再次/第二次"这一动作'
  actual: '先双击打开一次应用，看到"无法打开，因为无法验证开发者"的提示后点击关闭'
```

4 of 5 assertions passed vacuously against the old copy (forbidden-fragment and step4-no-restate checks were already true), but the ordering assertion — the one this task exists to lock — failed exactly as expected, confirming the test is not vacuous. After the rewrite, all 5 assertions passed and the full suite (`node --test frontend/src/lib/*.test.js`) went from 47/47 to 52/52.

## Dmg Background Generation Detail (Task 2)

**Generation method:** scratch HTML written to the session scratchpad (never committed), reproducing 05-01's composition exactly: 600×400 light gray/blue gradient, two 150×150 rounded dashed-border placeholder slots centered at (150,190) and (450,190), a right-pointing SVG arrow spanning x≈225→375 at y≈190. Screenshotted with `engines/chrome/Chromium.app/Contents/MacOS/Chromium --headless=new --disable-gpu --no-sandbox --hide-scrollbars --window-size=600,400`, once at `--force-device-scale-factor=1` (600×400) and once at `--force-device-scale-factor=2` (1200×800).

**Forbidden-phrase audit** (run over the scratch HTML before screenshotting, same fragment list as the acceptance criteria):

```
for phrase in "sudo" "spctl" "--master-disable" "csrutil" "~/Downloads" "右键"; do
  count=$(grep -c -- "$phrase" dmg-bg.html || true)
  echo "\"$phrase\": $count matches"
done
"sudo": 0 matches
"spctl": 0 matches
"--master-disable": 0 matches
"csrutil": 0 matches
"~/Downloads": 0 matches
"右键": 0 matches
```

**New footer text (verbatim, both languages):**

- 中文: `首次打开被拦截属正常现象：再次双击打开即可`
- English: `Blocked on first launch is expected — just double-click again`

**Dimension and composition verification:**

```
sips -g pixelWidth -g pixelHeight assets/dmg-background.png       → 600 x 400
sips -g pixelWidth -g pixelHeight assets/dmg-background@2x.png    → 1200 x 800
tiffutil -cathidpicheck assets/dmg-background.png assets/dmg-background@2x.png -out ... → "2 images written"
```

**Visual read-back confirmation** (via Read tool on both committed PNGs): left slot sits under (150,190), right slot sits under (450,190), the arrow points right, both footer lines are fully visible and unclipped in both the @1x and @2x renders, and the Chinese glyphs render correctly with no missing-glyph boxes.

**git status after Task 2:** only `assets/dmg-background.png` and `assets/dmg-background@2x.png` modified under `assets/`; the scratch HTML and both intermediate screenshot PNGs (session scratchpad copies) were deleted after copying the finals into `assets/`, and no `.html` file was added anywhere in the repository tree (`git status --porcelain | grep -c '\.html'` → 0).

## Decisions Made

- `step4`'s new wording leads into the command block ("使用下方的终端命令作为最后手段" / "use the terminal command below") without restating `GATEKEEPER_XATTR_COMMAND`, preserving 06-01's single-source-of-truth lock — verified by `grep -c 'GATEKEEPER_XATTR_COMMAND' frontend/src/i18n/{zh-CN,en-US}.js` returning 0 for both
- Kept the dmg footer to exactly two short lines rather than the full three-step progressive disclosure the in-app notice and release notes carry, consistent with 05-01's original scoping (the dmg window is a signpost, not a manual; the full walkthrough lives in the Release notes)
- Regenerated at the identical composition geometry (600×400/1200×800, slots at (150,190)/(450,190)) that `.github/workflows/build-release.yml`'s `create-dmg --icon "Open-Anti-Browser.app" 150 190 --app-drop-link 450 190` already depends on — confirmed by reading the workflow's `Create dmg` step before regenerating; no coordinate change was needed

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<verify>` steps were followed literally; no auto-fixes, no architectural questions, no blocking issues.

## Issues Encountered

None.

## TDD Gate Compliance

Task 1 is `tdd="true"`. RED/GREEN was demonstrated in substance rather than via separate `test(...)` → `feat(...)` commits, following the same pattern 06-01's Task 2 used: the new test targets existing repository content (the locale files, not a fixture), so the fail-first check was performed by running the test against the pre-rewrite copy and capturing the failure message (quoted above under "Fail-First Evidence"), then making the edit and re-running to confirm GREEN, before a single `feat` commit that includes both the test and the rewritten copy together.

- **RED (fail-first) evidence:** captured above — `not ok 1` with the exact assertion message, proving the ordering lock is not vacuous
- **GREEN:** `node --test frontend/src/lib/*.test.js` went from 47/47 (baseline) to 52/52 (all new assertions passing) after the rewrite
- No `refactor` commit was needed

## User Setup Required

None - no external service configuration required. All tooling used (`node`, the vendored Chromium binary, `sips`, `tiffutil`) was already present per 05-01's precedent; no new dependency was introduced.

## Next Phase Readiness

- All three user-facing surfaces — `.github/RELEASE_NOTES_TEMPLATE.md` (06-01/06-02), the in-app gatekeeper notice (this plan), and the dmg drag-install background (this plan) — now describe the same measured first-run flow: double-click again first, System Settings as fallback, terminal command as last resort
- `frontend/src/lib/gatekeeperCopyParity.test.js` stands as a permanent guard against a future edit silently demoting the double-click-again path back below System Settings
- The regenerated dmg background PNGs drop into the existing `create-dmg` pipeline with no coordinate or dimension change — `build-macos`'s `Create dmg` step needs no modification
- `frontend/src/App.vue`, `frontend/src/lib/openSourceNotice.js`, and `backend/_g.py` (the hash-locked anti-tamper assets) were not touched — confirmed via `git diff --stat`, so no hash recomputation is needed
- Remaining Phase 6 work (06-04, 06-05) can proceed without further changes to these three surfaces; 06-05's clean-account real-hardware run is the next point where the rewritten `step1` wording gets its own end-to-end validation

---
*Phase: 06-release-docs*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: `frontend/src/i18n/zh-CN.js`
- FOUND: `frontend/src/i18n/en-US.js`
- FOUND: `frontend/src/lib/gatekeeperCopyParity.test.js`
- FOUND: `assets/dmg-background.png`
- FOUND: `assets/dmg-background@2x.png`
- FOUND: `.planning/phases/06-release-docs/06-03-SUMMARY.md`
- FOUND commit: `2973269`
- FOUND commit: `403a8a0`
