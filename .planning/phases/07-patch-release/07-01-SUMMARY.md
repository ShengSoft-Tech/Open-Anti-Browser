---
phase: 07-patch-release
plan: 01
subsystem: release
tags: [release-engineering, ci, versioning, unittest, node-test]

# Dependency graph
requires:
  - phase: 06-macos-uat-and-docs
    provides: check_version_consistency.py (three-way tag/package.json/main.py gate), releaseNotesTemplate.test.js locale-parity test harness, GATEKEEPER_XATTR_COMMAND lock
provides:
  - Four-way (tag/package.json/main.py/template-anchor) version consistency gate in scripts/release/check_version_consistency.py, backward compatible via keyword-defaulted template_path
  - Bilingual "本次更新 / What's Changed" release notes section describing only the macOS close-button fix, per-platform, in .github/RELEASE_NOTES_TEMPLATE.md
  - v0.2.1 landed atomically across all four version sources (RELEASE_VERSION anchor, frontend/package.json, backend/main.py x2) on main
affects: [07-02-tag-push, 07-03-release-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTML comment anchor (`<!-- RELEASE_VERSION: X.Y.Z -->`) decouples reader-facing release-notes wording from script-parsed version number"
    - "read_*_version() functions share signature shape: optional Path | None, default to module-level DEFAULT_*_PATH constant, .read_text(encoding=\"utf-8\"), explicit VersionMismatch on parse failure (no silent None/empty fallback)"

key-files:
  created: []
  modified:
    - scripts/release/check_version_consistency.py
    - tests/test_version_consistency.py
    - .github/RELEASE_NOTES_TEMPLATE.md
    - frontend/src/lib/releaseNotesTemplate.test.js
    - frontend/package.json
    - backend/main.py

key-decisions:
  - "D-09: version anchor as a single top-of-file HTML comment, not duplicated per locale; keeps prose free to change without touching the gate regex"
  - "D-10: three separate commits, each leaving main's four version sources self-consistent (Task 1 introduced the anchor at 0.2.0 matching main at the time; Task 3 bumped all four to 0.2.1 together)"
  - "D-01 costly property confirmed in effect: the release notes template is no longer version-agnostic/zero-maintenance — every future release must update the RELEASE_VERSION anchor and the per-platform bullets, and check_version_consistency.py now hard-enforces that via a fourth comparison term"

patterns-established:
  - "Version-gate extension pattern: new read_X_version() function + DEFAULT_X_PATH constant + keyword-defaulted parameter appended to check_version_consistency()'s signature tail, preserving main()'s zero-arg call site"

requirements-completed: [PKG-06]

coverage:
  - id: D1
    description: "check_version_consistency.py extended to a four-way (tag/package.json/main.py/template-anchor) comparison; CLI stdout contract (clean single-line version string) preserved"
    requirement: "PKG-06"
    verification:
      - kind: unit
        ref: "tests/test_version_consistency.py#CheckVersionConsistencyTemplateTests.test_tag_mode_all_four_consistent_returns_version"
        status: pass
      - kind: integration
        ref: "command: .venv/bin/python scripts/release/check_version_consistency.py v0.2.1 true (stdout == '0.2.1', exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Version-mismatch and missing-anchor failure modes reject with non-zero exit / VersionMismatch, never silently pass"
    requirement: "PKG-06"
    verification:
      - kind: unit
        ref: "tests/test_version_consistency.py#CheckVersionConsistencyTemplateTests.test_tag_mode_template_not_bumped_raises_with_template_value_in_message"
        status: pass
      - kind: unit
        ref: "tests/test_version_consistency.py#CheckVersionConsistencyTemplateTests.test_non_tag_mode_template_not_bumped_raises"
        status: pass
      - kind: unit
        ref: "tests/test_version_consistency.py#CheckVersionConsistencyTemplateTests.test_missing_template_anchor_raises"
        status: pass
      - kind: integration
        ref: "command: .venv/bin/python scripts/release/check_version_consistency.py v0.2.0 true (exit 1) after real v0.2.1 bump"
        status: pass
    human_judgment: false
  - id: D3
    description: "Release notes template has a bilingual 'What's Changed / 本次更新' section, per-platform bullets, no version-agnostic preamble, no CI-fix mention, doesn't touch the GATEKEEPER_XATTR_COMMAND lock"
    requirement: "PKG-06"
    verification:
      - kind: unit
        ref: "node --test frontend/src/lib/releaseNotesTemplate.test.js (all 53 assertions incl. FORBIDDEN_FRAGMENTS gate, GATEKEEPER_XATTR_COMMAND verbatim lock, new anchor-shape assertion)"
        status: pass
    human_judgment: false
  - id: D4
    description: "All four version sources (RELEASE_VERSION anchor, frontend/package.json, backend/main.py x2) read 0.2.1 on a single commit"
    requirement: "PKG-06"
    verification:
      - kind: other
        ref: "command: grep -c '0\\.2\\.0' frontend/package.json backend/main.py .github/RELEASE_NOTES_TEMPLATE.md == 0 for all three files"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-01
status: complete
---

# Phase 7 Plan 1: Version gate + release notes content Summary

**Extended `check_version_consistency.py` to a four-way tag/package.json/main.py/template-anchor gate, added a bilingual per-platform "What's Changed" section to the release notes template, and bumped all four version sources to 0.2.1 on main in three self-consistent commits.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-01T00:15:00Z (approx, per plan handoff)
- **Completed:** 2026-08-01T00:36:12Z
- **Tasks:** 3 (Task 1 tracer, Task 2 auto, Task 3 auto)
- **Files modified:** 6

## Accomplishments
- `scripts/release/check_version_consistency.py` now reads a `<!-- RELEASE_VERSION: X.Y.Z -->` anchor from `.github/RELEASE_NOTES_TEMPLATE.md` via a new `read_template_version()` and folds it into both tag-mode (4-way) and non-tag-mode (3-way) equality checks, with the CLI stdout contract (`stdout` = clean single-line version, diagnostics on `stderr`) verified byte-for-byte unchanged
- Missing-anchor and un-bumped-anchor failure modes are covered by 5 new/updated Python unit tests plus a real behavioral check (anchor physically removed from the repo file, gate observed to exit non-zero, file restored) and one new node:test assertion on anchor shape
- Release notes template now carries a bilingual "本次更新 / What's Changed" section, positioned before each language block's existing first heading, describing only the user-visible macOS close-button fix and explicitly noting "no Windows changes" — no version-agnostic preamble, no CI-pipeline-fix language
- `frontend/package.json`, both `backend/main.py` FastAPI `version=` fields, and the template anchor all bumped to `0.2.1` in one commit; `check_version_consistency.py v0.2.1 true` now returns `0.2.1` and `v0.2.0 true` is correctly rejected

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end wire-up of template anchor → gate script → CLI contract** - `1a94b57` (feat)
2. **Task 2: Negative and missing-anchor guardrails + node-side anchor assertion** - `7a191d9` (test)
3. **Task 3: Bilingual "What's Changed" content + bump all four version sources to 0.2.1** - `9957f80` (feat)

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified
- `scripts/release/check_version_consistency.py` - added `DEFAULT_TEMPLATE_PATH`, `_TEMPLATE_VERSION_RE`, `read_template_version()`; `check_version_consistency()` gained a keyword-defaulted `template_path` param and now does 4-way (tag mode) / 3-way (non-tag mode) equality checks; `main()` left byte-for-byte unchanged
- `tests/test_version_consistency.py` - added `_write_template()` fixture, `CheckVersionConsistencyTemplateTests` (4 cases: all-consistent, tag-mode un-bumped, non-tag-mode un-bumped, missing anchor), one new `CurrentRepoStateTests` self-check comparing the real repo's anchor to `package.json`; updated 4 pre-existing tests to pass the now-required `template_path` fixture
- `.github/RELEASE_NOTES_TEMPLATE.md` - added `RELEASE_VERSION` anchor (0.2.0 in Task 1, bumped to 0.2.1 in Task 3) as file's first line; added `## 本次更新` / `## What's Changed` sections ahead of each language block's first existing heading
- `frontend/src/lib/releaseNotesTemplate.test.js` - added one node:test assertion confirming exactly one RELEASE_VERSION anchor of semver shape
- `frontend/package.json` - `version` bumped 0.2.0 → 0.2.1
- `backend/main.py` - both FastAPI `version=` fields (app, open_api) bumped 0.2.0 → 0.2.1

## Decisions Made
- D-09 (locked in plan): version anchor is a single HTML comment on line 1 of the template, not duplicated per locale — keeps the gate regex decoupled from any future wording/layout changes to the prose sections
- D-10 (locked in plan): three commits, each leaving main's four version sources mutually consistent at the moment of landing — Task 1 introduced the anchor at `0.2.0` (matching main's then-current version) rather than jumping straight to `0.2.1`, avoiding a red `ci-tests.yml` run on an intermediate commit
- Pre-existing tests (`test_tag_mode_all_three_consistent_returns_version`, `test_tag_mode_mismatch_raises_with_all_three_values_in_message`, `test_non_tag_mode_package_and_main_agree_returns_package_version`, `test_non_tag_mode_mismatch_raises`) required updating to pass a `template_path` fixture once the default template path started pointing at the real repo file with `0.2.0` (later `0.2.1`) — otherwise they would fail non-deterministically as soon as the anchor diverged from their hardcoded test versions. This was not explicitly called out in the plan's task 1 action but follows directly from extending the function signature (Rule 1 — auto-fix, tests were structurally broken by the intended change, not a new feature).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 4 pre-existing tests to pass the new `template_path` argument**
- **Found during:** Task 1 (immediately after adding the template comparison to `check_version_consistency()`)
- **Issue:** `check_version_consistency()`'s default `template_path=None` resolves to the real repo template. Once the four-way comparison was added, the four pre-existing tests in `CheckVersionConsistencyTagModeTests`/`CheckVersionConsistencyNonTagModeTests` that didn't pass a `template_path` started reading the real repo's anchor (`0.2.0`) and comparing it against their fixture-only `package_path`/`main_path` values (e.g. `1.2.3`, `2.0.0`), causing `VersionMismatch` errors unrelated to what those tests intended to check.
- **Fix:** Added `template_path=_write_template(tmp_path, <matching version>)` to each of the four affected test calls, keeping each test's original intent (three/four-way agreement or intentional mismatch) intact.
- **Files modified:** tests/test_version_consistency.py
- **Verification:** `.venv/bin/python -m unittest tests.test_version_consistency -v` — all 11 tests (after Task 1) passed; grew to 15 after Task 2.
- **Committed in:** 1a94b57 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — pre-existing tests structurally broken by the intended signature extension, not a new bug introduced independently)
**Impact on plan:** Necessary consequence of Task 1's own action (extending `check_version_consistency()`'s comparison to four terms); no scope creep — same four tests, same assertions, just with a template fixture added.

## Issues Encountered
None beyond the deviation above.

**Full test suite counts (as required by plan output spec):**
- Python: baseline 122 tests (2 skip) → final **127 tests (2 skip)**, all passing (5 new: 1 from Task 1, 4 from Task 2)
- node:test: baseline 52 → final **53**, all passing (1 new, from Task 2)

**Behavioral verification of the anchor-removal gate (Task 2 acceptance criterion), actual observation:**
1. Backed up `.github/RELEASE_NOTES_TEMPLATE.md` to the scratchpad directory
2. Removed the `<!-- RELEASE_VERSION: 0.2.0 -->` line (state at that point in Task 2, before Task 3's bump)
3. Ran `.venv/bin/python scripts/release/check_version_consistency.py v0.2.0 true` → exit code **1**, stderr: `错误: 在 .github/RELEASE_NOTES_TEMPLATE.md 中未找到 \`<!-- RELEASE_VERSION: X.Y.Z -->\` 锚点。...`
4. Restored the file from the scratchpad backup byte-for-byte
5. Re-ran the same command → exit code **0**, stdout `0.2.0`
6. `git diff` confirmed zero residual diff on the template file after restoration

**D-01 costly-property confirmation:** the release notes template's D-01/D-02 changes are now in effect on main. `.github/RELEASE_NOTES_TEMPLATE.md` is no longer version-agnostic/zero-maintenance content — its `RELEASE_VERSION` anchor and its `## 本次更新`/`## What's Changed` bullets must be updated on every future release, and `check_version_consistency.py`'s four-way comparison will hard-block a tag push if the anchor is left behind. This is an intentional, planned tradeoff (D-01/D-02), not a regression.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- main now has a commit (`9957f80`) where all four version sources agree on `0.2.1`, the release notes template's content is the final publishable "What's Changed" text, and the full Python + node test suites are green — this is the commit `07-02` should tag as `v0.2.1`
- `07-02`'s real tag push and `07-03`'s release-job verification are unblocked; nothing in this plan touched `.github/workflows/build-release.yml` or `launch_app.py`, per the plan's explicit scope boundary
- Nothing was pushed to origin in this plan, per the sequential-executor instructions — that remains Wave 2's job under a human checkpoint

---
*Phase: 07-patch-release*
*Completed: 2026-08-01*

## Self-Check: PASSED

All 6 modified files and the SUMMARY.md itself confirmed present on disk; all 4 commit hashes (1a94b57, 7a191d9, 9957f80, eb6493b) confirmed present in `git log --oneline --all`.
