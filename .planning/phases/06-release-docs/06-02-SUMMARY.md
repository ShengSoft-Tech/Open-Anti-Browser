---
phase: 06-release-docs
plan: 02
subsystem: docs
tags: [release-notes, gatekeeper, macos-15, readme, node-test]

# Dependency graph
requires:
  - phase: 06-release-docs
    provides: "06-01's .github/RELEASE_NOTES_TEMPLATE.md (bilingual 放行 walkthrough), releaseNotesTemplate.test.js lock, and the byte-identical GATEKEEPER_XATTR_COMMAND wiring this plan must not disturb"
provides:
  - "Bilingual prerequisite checklist (Apple Silicon + macOS 15) placed above the 放行 walkthrough in .github/RELEASE_NOTES_TEMPLATE.md"
  - "Bilingual GUI-first self-check (About This Mac path) plus optional uname/sw_vers terminal alternative"
  - "Bilingual, conservatively-worded unsupported-hardware expectations, explicitly marked as inferred/not observed on real hardware (D-08)"
  - "Bilingual trust caveat: not Apple-signed, not notarized, runs because unquarantined (not approved), Gatekeeper assessment still reports a rejection"
  - "Two-bullet macOS prerequisite pointer added to README.md § 下载 and README_EN.md § Download, deferring the full walkthrough to the Release page (D-11)"
affects: [06-03, 06-04, 06-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Prerequisite/self-check/trust-caveat content placed as new sections ABOVE an existing locked walkthrough section, never editing inside it, so the existing consistency-lock test continues to prove non-regression by construction (diff-additive only)."
    - "Intel/x64 vocabulary confined to a single 'what to expect if unsupported' sentence per language, so a negative grep for 'intel|x64|rosetta' scoped to that sentence stays auditable and cannot leak into the prerequisite bullet (which states only the positive Apple Silicon requirement)."

key-files:
  created: []
  modified:
    - .github/RELEASE_NOTES_TEMPLATE.md
    - README.md
    - README_EN.md

key-decisions:
  - "Trust-caveat wording uses '担保'/endorsement instead of '认可'/'信任' near Apple/Gatekeeper, as an extra safety margin beyond the literal acceptance-criteria regex, to fully avoid any phrase that could be read as implying approval or trust."
  - "README pointer bullets restate only the two prerequisite conditions and a link to the Release page — no step numbers, no terminal command, no trust caveat — keeping .github/RELEASE_NOTES_TEMPLATE.md the single source of truth per D-11."

patterns-established:
  - "New release-notes sections precede the existing walkthrough per language, keeping each language self-contained (Chinese reader never needs the English section and vice versa), consistent with 06-01's existing structure."

requirements-completed: [DOCS-01, DOCS-02]

coverage:
  - id: D1
    description: "Bilingual prerequisite checklist, GUI-first self-check, unsupported-hardware expectations, and trust caveat added to .github/RELEASE_NOTES_TEMPLATE.md above the 放行 walkthrough"
    requirement: "DOCS-02"
    verification:
      - kind: unit
        ref: "node --test frontend/src/lib/*.test.js (47/47 pass, includes releaseNotesTemplate.test.js's byte-identical xattr command and body_path wiring checks)"
        status: pass
      - kind: other
        ref: "grep -c 'macOS 15' .github/RELEASE_NOTES_TEMPLATE.md == 5 (>=2 required); grep -Ec 'macOS 1[234]|macOS 11' == 0; grep -c 'uname -m && sw_vers -productVersion' == 2; grep -Eic 'Apple Silicon|Apple M' == 4; grep -Eic 'notariz|公证' == 2; grep -Eic approval-implying-phrase-regex == 0; grep -c sudo|spctl|--master-disable|csrutil == 0 each"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two-bullet macOS prerequisite pointer added above the existing three download links in both README.md § 下载 and README_EN.md § Download, without duplicating the walkthrough"
    requirement: "DOCS-02"
    verification:
      - kind: other
        ref: "awk-scoped bullet count == 5 in both files; grep for xattr/系统设置/System Settings/Privacy & Security == 0 in both download sections; git diff --stat shows insertions only, no deletions"
        status: pass
    human_judgment: false
  - id: D3
    description: "The 放行 walkthrough section committed in 06-01 was not modified, reworded, or restructured by this plan's edits"
    requirement: "DOCS-01"
    verification:
      - kind: other
        ref: "git diff ae6f215..HEAD -- .github/RELEASE_NOTES_TEMPLATE.md | grep '^-' returns nothing (diff-additive only)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-07-31
status: complete
---

# Phase 06 Plan 02: Prerequisite checklist, self-check, and trust caveat Summary

**Bilingual macOS-15/Apple-Silicon prerequisite checklist, GUI-first self-check, conservatively-worded unsupported-hardware note, and unsigned/not-notarized trust caveat added above the existing 放行 walkthrough, plus a two-bullet pointer in both READMEs deferring to the Release page.**

## Performance

- **Duration:** ~6 min (task execution only; excludes upfront plan/context reading)
- **Started:** 2026-07-31T18:11:00Z (approx)
- **Completed:** 2026-07-31T18:16:25Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `.github/RELEASE_NOTES_TEMPLATE.md` now lets a reader determine, from the Release page alone and using only the Apple menu (关于本机 / About This Mac), whether their Mac qualifies — before reading how to open the app
- The macOS-below-15 and Intel-Mac failure descriptions are worded as expectations, not measured fact, with an explicit sentence in both languages stating neither has been observed on real hardware (CONTEXT.md D-08 compliance)
- A trust caveat in both languages states plainly: not Apple-signed, not notarized, runs because unquarantined (not because Apple/Gatekeeper approved it), and a Gatekeeper assessment of the bundle still reports a rejection
- Both READMEs' download sections now carry a two-bullet macOS prerequisite pointer (Apple Silicon + macOS 15, Windows unaffected) that links to the Release page instead of repeating any step — `.github/RELEASE_NOTES_TEMPLATE.md` remains the single source of truth (D-11)
- `node --test frontend/src/lib/*.test.js` still passes 47/47 after both tasks — the 06-01 consistency lock (byte-identical `xattr` command, `body_path` wiring) is unaffected because all new content was added as new sections, never editing inside the locked walkthrough

## Task Commits

Each task was committed atomically:

1. **Task 1: Prerequisite checklist, unsupported-hardware expectations, and the trust caveat — both languages** - `e63bce7` (docs)
2. **Task 2: Two-line macOS prerequisite pointer in both README download sections** - `52add56` (docs)

**Plan metadata:** committed separately below (docs: complete plan)

## Files Created/Modified

- `.github/RELEASE_NOTES_TEMPLATE.md` - Added "下载前必读：系统要求" / "Before You Download: System Requirements" and "关于签名与信任状态的说明" / "About Signing and Trust" sections in both languages, placed above the existing (06-01) 放行 walkthrough
- `README.md` - Two new bullets in `## 下载` above the three existing links: macOS prerequisite line, and a pointer to the Release page for the first-launch approval steps
- `README_EN.md` - English mirror of the same two bullets in `## Download`

## Decisions Made

- Confined all Intel/x64/rosetta vocabulary to the single "what to expect if unsupported" sentence per language (never in the prerequisite bullet, which states only the positive Apple Silicon requirement), so the acceptance criterion's implicit scoping intent ("only inside the unsupported-hardware sentence") holds by construction — verified: both language occurrences of `intel|x64|x86_64|rosetta` are exactly the two "what to expect" sentences, quoted verbatim below.
- Used "担保" (endorsement) rather than "认可"/"信任" adjacent to Apple/Gatekeeper in the Chinese trust caveat, and avoided "approved"/"trusts" as affirmative predicates in English, as an extra safety margin beyond the literal negative-grep acceptance criteria, to make the "not implying Apple/Gatekeeper approval" intent unambiguous under any reading, not just the specific enumerated regex.
- README pointer bullets state only the two prerequisite conditions plus a Release-page link — no step numbers, no terminal command, no trust caveat — so `.github/RELEASE_NOTES_TEMPLATE.md` remains the single place these facts are spelled out (D-11), preventing the three-way drift surface Phase 5 experienced twice.

**Unsupported-hardware sentences, quoted verbatim (per acceptance criteria):**

- Chinese: "如果系统版本低于 macOS 15，预计应用会被系统拒绝打开；如果是 Intel（x64）Mac，则无法运行这个仅支持 arm64 架构的安装包。以上两种情况均未在真实设备上实测验证，是根据应用声明的最低系统版本与单一架构构建方式推断得出，仅供参考。"
- English: "On macOS versions earlier than 15, the app is expected to be refused by the system when you try to open it. On an Intel (x64) Mac, this arm64-only package cannot run at all. Neither outcome has been verified on real hardware — both are inferred from the app's declared minimum system version and its single-architecture build, and are provided for reference only."

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1-4 auto-fixes were required; both tasks executed as planned.

### Note on a stale acceptance-criterion count (not a deviation, documented for auditability)

Task 1's acceptance criteria include: `grep -c 'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"' .github/RELEASE_NOTES_TEMPLATE.md still returns 1`. The actual baseline count going into this plan was already **2** (06-01's D-15 human-directed correction made the English fallback repeat the command verbatim, matching the Chinese section — see 06-01-SUMMARY.md's "Deviations from Plan" §1). This plan's edits did not touch the walkthrough section at all (`git diff ae6f215..HEAD -- .github/RELEASE_NOTES_TEMPLATE.md | grep '^-'` returns nothing), so the count is unchanged from baseline: still 2, not disturbed. The criterion's literal number (1) reflects a plan draft written before 06-01's D-15 correction landed; the criterion's actual intent — "plan 06-01's locked command block was not disturbed" — is satisfied and verified via the diff-additive check above.

---

**Total deviations:** 0 auto-fixed; 1 stale-criterion note documented above.
**Impact on plan:** None — both tasks executed exactly as specified; the stale count in the acceptance criteria text does not reflect any actual regression.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `.github/RELEASE_NOTES_TEMPLATE.md` now fully satisfies DOCS-02's replacement scope (D-05/D-14): a reader can self-qualify via the Apple menu alone, understands the un-tested nature of the failure modes, and understands the actual (non-)trust semantics of an ad-hoc-signed app
- Both READMEs point at the Release page for the walkthrough with zero duplicated steps, closing D-11's single-source-of-truth requirement
- `node --test frontend/src/lib/*.test.js` remains green (47/47) — no new test file was needed since this plan added prose, not new constants/wiring surfaces requiring their own lock
- Remaining phase work (06-03/06-04/06-05, per ROADMAP) can proceed; this plan introduced no new blockers

---
*Phase: 06-release-docs*
*Completed: 2026-07-31*

## Self-Check: PASSED

- FOUND: `.planning/phases/06-release-docs/06-02-SUMMARY.md`
- FOUND: `.github/RELEASE_NOTES_TEMPLATE.md`
- FOUND: `README.md`
- FOUND: `README_EN.md`
- FOUND commit: `e63bce7`
- FOUND commit: `52add56`
