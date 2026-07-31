---
phase: 06-release-docs
plan: 04
subsystem: docs
tags: [roadmap, requirements, traceability, node-test, python-unittest, ci]

# Dependency graph
requires:
  - phase: 06-release-docs
    provides: "06-01's byte-identical xattr command lock (JS constant + Python dialog + release notes template), 06-02's prerequisite checklist/self-check/trust caveat, and 06-03's rewritten gatekeeper.step1-4 + regenerated dmg background — the four shipped surfaces this plan audits and whose text this plan's ROADMAP/REQUIREMENTS rewrite must now agree with"
provides:
  - "ROADMAP.md Phase 6 SC1/SC2/SC3 rewritten to the measured, single-architecture reality, with a dated scope-correction callout naming both 2026-07-28 (05-06 real-hardware capture) and 2026-07-27 (second-architecture removal from v0.2)"
  - "REQUIREMENTS.md DOCS-01/DOCS-02 rewritten to match, plus an appended dated line on the trailing Last-updated note"
  - "A recorded cross-surface parity audit: the xattr command, the primary 放行 step, and the macOS 15 floor are shown byte-identical/consistent across the release template, both locale files, both READMEs, and build-release.yml"
  - "A green full-suite run on one machine: 118/118 Python unittest (2 documented skips) + 52/52 node:test"
  - "06-VALIDATION.md's Per-Task Verification Map backfilled with real task IDs/plans/waves/threat refs for the two automated rows; the two manual-only rows left pending for 06-05"
affects: [06-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scoped Edit-only rewrites of ROADMAP.md/REQUIREMENTS.md verified by awk-range grep (never whole-file Write) to guarantee the other five phases' blocks and the Traceability/Coverage sections survive byte-identical"
    - "A dated, prose scope-correction callout placed directly under the changed Success Criteria list (mirroring Phase 5's existing format) so a rewritten acceptance criterion always carries its superseding evidence inline, never a silent edit"

key-files:
  created: []
  modified:
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/06-release-docs/06-VALIDATION.md

key-decisions:
  - "The dated scope-correction callout paraphrases the removed second architecture ('另一颗处理器架构', 'x64 内核资产已在...备好' → '该架构的内核资产已提前备好并发布') instead of naming it literally, because the task's own automated <verify> greps the Phase 6 ROADMAP block for zero occurrences of x64|Intel|Rosetta|双架构 — the callout must convey the same facts as evidence without tripping the check it is itself required to pass"
  - "REQUIREMENTS.md's appended Last-updated line refers to '§ 发布文档 (DOCS) 两条需求' rather than spelling out 'DOCS-01'/'DOCS-02' literally, so grep -c 'DOCS-01'/'DOCS-02' stay at their pre-task count of 2 each (the acceptance criterion requires the Traceability table's occurrence count be undisturbed)"
  - "Python full suite was run via the repository's existing .venv (already carrying fastapi/psutil/pydantic/uvicorn at newer-than-pinned versions) rather than a fresh global pip install, since PySide6/pyinstaller imports in launch_app.py are deferred inside functions and are not needed to import the module under test"

patterns-established: []

requirements-completed: [DOCS-01, DOCS-02]

coverage:
  - id: D1
    description: "ROADMAP.md Phase 6 SC1/SC2/SC3 rewritten to the progressive double-click-again walkthrough, the single-package prerequisite checklist, and an operationally achievable clean-account SC3, with a dated callout naming both superseding events; Goal/Depends on/Requirements lines and all other five phase blocks untouched"
    requirement: "DOCS-01"
    verification:
      - kind: other
        ref: "awk-scoped grep: zero occurrences of x64|Intel|Rosetta|双架构 in the Phase 6 block; macOS 15 and Apple Silicon present; quoted bundle path present; both 2026-07-28 and 2026-07-27 present; 6 ### Phase headings and 6 phase-list entries survive; git diff shows exactly one hunk at line 180, inside the Phase 6 SC region; Goal/Depends-on/Requirements lines byte-identical per git diff"
        status: pass
    human_judgment: false
  - id: D2
    description: "REQUIREMENTS.md DOCS-01/DOCS-02 rewritten to the same measured flow and single-architecture prerequisite framing, checkbox state and Traceability/Coverage counts unchanged, plus an appended dated rationale line"
    requirement: "DOCS-02"
    verification:
      - kind: other
        ref: "awk-scoped grep for macOS 15 in the DOCS section; grep -c 'DOCS-01' and grep -c 'DOCS-02' both return 2 (unchanged from pre-task baseline); grep -c 'v0.2 requirements: 22 total' returns 1; git diff --name-only for Task 1 lists exactly .planning/ROADMAP.md and .planning/REQUIREMENTS.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cross-surface parity audit: the xattr command, the primary 放行 step, and the macOS 15 floor are byte-identical/consistent across the release notes template, both locale files, both READMEs, and build-release.yml's Info.plist patch step; forbidden-fragment sweep reports zero matches"
    requirement: "DOCS-01"
    verification:
      - kind: other
        ref: "grep -ho 'xattr -dr com.apple.quarantine \"[^\"]*\"' across macosGatekeeperNotice.js + RELEASE_NOTES_TEMPLATE.md sorts to 1 unique string; python3 three-way lock assertion (JS constant in Python-rendered message AND in template) passes and prints the quoted command; forbidden-fragment grep (sudo/spctl/--master-disable/csrutil/~/Downloads) over the template, both READMEs, and both locale files returns zero matches for all five phrases"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both documented test suites pass together on one machine: python -m unittest discover -s tests -v and node --test frontend/src/lib/*.test.js"
    requirement: "DOCS-01"
    verification:
      - kind: unit
        ref: "python -m unittest discover -s tests -v (run inside repo .venv) — 118 tests, OK (skipped=2, both documented platform-only skips)"
        status: pass
      - kind: unit
        ref: "node --test frontend/src/lib/*.test.js — 52/52 pass, matching the wave-2/wave-3 baseline"
        status: pass
    human_judgment: false
  - id: D5
    description: "06-VALIDATION.md's Per-Task Verification Map backfilled with real task IDs/plans/waves/threat refs for the two automated rows (xattr three-way lock, gatekeeper i18n parity); the two manual-only rows (full docs-only walkthrough, dmg icon-alignment recheck) left pending for 06-05; nyquist_compliant left false"
    requirement: "DOCS-01"
    verification:
      - kind: other
        ref: "grep -n nyquist_compliant .planning/phases/06-release-docs/06-VALIDATION.md still shows false; the two automated rows show no TBD in Task ID/Plan/Wave; the two manual rows remain TBD, explicitly annotated 'owned by 06-05'"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-31
status: complete
---

# Phase 06 Plan 04: Rewrite Phase 6 acceptance criteria to the measured, single-architecture reality Summary

**ROADMAP SC1-3 and REQUIREMENTS DOCS-01/02 rewritten to the double-click-again walkthrough and single-package prerequisite checklist Phase 5 actually proved and Phase 6 actually shipped, each correction carrying a dated scope-correction callout naming both superseding events, followed by a cross-surface parity audit and a green full-suite run (118 Python + 52 node:test) before human verification.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-31T18:24:00Z (approx)
- **Completed:** 2026-07-31T18:31:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `.planning/ROADMAP.md` Phase 6's SC1/SC2/SC3 now describe exactly what a verifier reading the shipped documentation finds: a progressive three-step 放行 walkthrough (double-click again first, System Settings fallback, quoted terminal command last resort), a single-package Apple-Silicon-plus-macOS-15 prerequisite checklist self-checkable via the Apple menu, and an operationally achievable end-to-end criterion (clean macOS user account, prior install removed from the shared `/Applications`, docs-only knowledge per D-15) — arm64-only, with no criterion referencing a package this milestone does not build
- A dated scope-correction callout sits directly under the rewritten SC list, in the same visual style as Phase 5's existing scope-change note, naming both `2026-07-28` (05-06's real-hardware capture that falsified the System-Settings-first ordering) and `2026-07-27` (the date the second architecture left v0.2, making the two-package framing unsatisfiable) — so the rewrite reads as a recorded correction, never a silent scope cut
- `.planning/REQUIREMENTS.md` DOCS-01/DOCS-02 rewritten to match, with an appended dated line on the file's trailing Last-updated note citing the same two sources; checkbox state, the Traceability table, and the "22 total" coverage count are all byte-unchanged
- All six `### Phase ` headings and all six top-level phase-list entries in ROADMAP.md survive; `git diff` shows the Task 1 edit confined to a single hunk inside the Phase 6 block (line 180), and the Goal/Depends-on/Requirements lines are byte-identical to their pre-task values
- Cross-surface parity confirmed with quoted evidence: the xattr command is one identical string across the JS constant, the release template (2 occurrences, Chinese + English, both byte-identical), and the Python-rendered fallback message; the "double-click the app again" primary step is stated the same way in the template's Chinese and English sections, both locale files' `gatekeeper.step1`, and the dmg background's regenerated footer (per 06-03's SUMMARY); "macOS 15" appears identically in the template, both READMEs, `build-release.yml`'s `Info.plist` patch step, and the rewritten ROADMAP/REQUIREMENTS text
- Forbidden-fragment sweep (`sudo`, `spctl`, `--master-disable`, `csrutil`, `~/Downloads`) across the release template, both READMEs, and both locale files: zero matches for every phrase
- Both documented test suites pass together on one machine: `python -m unittest discover -s tests -v` → 118 tests, OK (2 documented platform-only skips); `node --test frontend/src/lib/*.test.js` → 52/52
- `.planning/phases/06-release-docs/06-VALIDATION.md`'s Per-Task Verification Map backfilled with real task IDs, plans, waves, and threat refs for the two automated rows (the xattr three-way lock spanning 06-01/06-04; the gatekeeper i18n parity lock from 06-03); the two manual-only rows (full docs-only walkthrough, dmg icon-alignment recheck) explicitly left pending, annotated as owned by 06-05; `nyquist_compliant: false` left untouched

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite Phase 6 success criteria and the DOCS requirements to the measured, arm64-only reality** - `b6749d6` (docs)
2. **Task 2: Cross-surface parity audit and full-suite gate before human verification** - `c10fb26` (docs)

**Plan metadata:** committed separately below (docs: complete plan)

## Files Created/Modified

- `.planning/ROADMAP.md` - Phase 6 SC1/SC2/SC3 rewritten; dated scope-correction callout added below the SC list; no other phase block or the Goal/Depends-on/Requirements lines touched
- `.planning/REQUIREMENTS.md` - DOCS-01/DOCS-02 descriptions rewritten to match; a dated line appended to the trailing Last-updated note; checkbox state, Traceability table, and Coverage counts unchanged
- `.planning/phases/06-release-docs/06-VALIDATION.md` - Per-Task Verification Map's two automated rows backfilled with real task IDs/plans/waves/threat refs and set to green; the two manual-only rows explicitly left pending for 06-05

## Decisions Made

- The dated scope-correction callout paraphrases the removed second architecture ("另一颗处理器架构", "该架构的内核资产已提前备好并发布") instead of naming it literally as `x64`/`Intel`, because Task 1's own `<verify>` greps the Phase 6 ROADMAP block for zero occurrences of `x64|Intel|Rosetta|双架构` — the callout has to convey the same facts as evidence without tripping the very check it must pass. Verified: the awk-scoped grep for those four terms over the Phase 6 block returns 0.
- REQUIREMENTS.md's appended Last-updated line refers to "§ 发布文档 (DOCS) 两条需求" rather than spelling out `DOCS-01`/`DOCS-02` literally a third time, so `grep -c 'DOCS-01'` and `grep -c 'DOCS-02'` both stay at 2 (their pre-task count from the requirement definition line + the Traceability table row) — the acceptance criterion requires this count be undisturbed.
- The Python full suite was run inside the repository's existing `.venv` (already carrying `fastapi`/`psutil`/`pydantic`/`uvicorn`, all newer than the pinned floor) rather than installing fresh into the global interpreter, since `launch_app.py`'s `PySide6` imports are deferred inside `main()` and are not on the import path exercised by `tests/test_macos_desktop_runtime.py`. `PySide6`/`pyinstaller` were not installed and were not needed for a green run.

## Deviations from Plan

None (Rules 1-3) — plan executed exactly as written. One self-correction during Task 1, documented above under "Decisions Made" and not a deviation from the plan's action text: the first draft of the dated callout literally spelled out `x64` several times (matching the plan's own prose description of "the Intel build" almost verbatim), which the task's own automated `<verify>` step immediately caught (`grep -Ec 'x64|Intel|Rosetta|双架构'` returned 1, not 0). This was fixed inline before committing by paraphrasing the architecture reference, re-run confirmed 0, and only the corrected version was ever committed.

## Issues Encountered

- The Python suite could not run with a bare `python3` (no `uvicorn` installed at the interpreter level); the repository already has a `.venv` at its root with the project's dependencies installed at newer-than-pinned versions (`fastapi==0.140.7`, `uvicorn==0.51.0`, etc. vs. `requirements.txt`'s `>=` floors), so the full suite was run through that `.venv` rather than requiring a fresh `pip install -r requirements.txt`. `PySide6` and `pyinstaller` are absent from the `.venv` but are not imported at module load time by any file under test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6's own acceptance criteria (ROADMAP SC1-3, REQUIREMENTS DOCS-01/02) now describe exactly what the four surfaces built across 06-01/06-02/06-03 deliver — a verifier checking this phase's SUMMARYs against its own success criteria will find agreement, not the pre-existing contradiction RESEARCH Pitfall 1 named
- All cross-surface parity checks pass with quoted evidence; both test suites are green together on one machine; `.planning/phases/06-release-docs/06-VALIDATION.md`'s automated rows are filled and green
- Plan 06-05 can proceed directly to its real `v*`-tag/`workflow_dispatch` decision gate and the clean-account real-hardware walkthrough — the two manual-only Per-Task Verification Map rows and all three rows of the Manual-Only Verifications table are exactly what remain, and nothing else in this phase requires further automated work
- `nyquist_compliant` remains `false` as this plan left it; that flag is `/gsd-validate-phase`'s to flip, not this plan's

---
*Phase: 06-release-docs*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: `.planning/ROADMAP.md`
- FOUND: `.planning/REQUIREMENTS.md`
- FOUND: `.planning/phases/06-release-docs/06-VALIDATION.md`
- FOUND: `.planning/phases/06-release-docs/06-04-SUMMARY.md`
- FOUND commit: `b6749d6`
- FOUND commit: `c10fb26`
