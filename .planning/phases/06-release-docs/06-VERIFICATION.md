---
phase: 06-release-docs
verified: 2026-07-31T22:15:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: none
  note: "No previous VERIFICATION.md existed for this phase; this is the initial verification."
---

# Phase 6: 发布文档与端到端验证 Verification Report

**Phase Goal:** macOS 用户拿到未签名的 dmg 后，无需开发者协助即可自行完成放行、安装并开始使用
**Verified:** 2026-07-31T22:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Context Acknowledgement

This phase deliberately rewrote its own acceptance criteria twice, with dated rationale recorded in
both ROADMAP.md and REQUIREMENTS.md:

1. **2026-07-31 (commit `b6749d6`, plan 06-04):** ROADMAP SC1/SC2/SC3 and REQUIREMENTS DOCS-01/DOCS-02
   rewritten from their 2026-07-23 originals ("系统设置 first", dual-architecture verification) to the
   measured reality — confirmed present in `.planning/ROADMAP.md` lines 185-188 and
   `.planning/REQUIREMENTS.md` line 122.
2. **2026-07-31 (commit `1f63b37`, plan 06-05):** SC3 further narrowed — D-13's clean-account
   requirement waived by explicit developer decision; confirmed present as a dated OVERRIDE block
   under D-13 in `.planning/phases/06-release-docs/06-CONTEXT.md` (lines 79-80, original text
   preserved unedited above it) and a matching `2026-07-31 SC3 收窄` callout in ROADMAP.md
   (lines 187-188).

Both rewrites were verified against the actual commit history and file contents (not just the
SUMMARY narrative) — see "Requirements Coverage" and "Key Link Verification" below.

Four items are explicitly **not** claimed as verified anywhere in the codebase or planning docs,
matching the developer's briefing — checked by direct grep across all Phase 6 planning artifacts:

| Item | Where it is honestly recorded as unverified |
|---|---|
| 「系统设置 → 隐私与安全性 → 仍要打开」 fallback path | ROADMAP SC3 text itself, CONTEXT.md D-13 override, 06-05-SUMMARY.md (D6, Qualifier 2, Residual Risk 3) |
| B1 first-launch dialog's verbatim title/button wording | 06-05-SUMMARY.md (D7, Qualifier 3, Residual Risk 4) — no fabricated text found anywhere |
| `524aeb1`'s checkout fix never executed by real CI | 06-05-SUMMARY.md (Residual Risk 1) — **confirmed accurate.** `524aeb1` is NOT an ancestor of `v0.2.0` (the tag points at `95850b0`, and the fix was pushed to `main` afterwards, per the plan's no-second-tag instruction). `git show v0.2.0:.github/workflows/build-release.yml` shows the `release` job's first step is `Download all build artifacts` — no checkout. Run `30656303074` therefore did NOT contain the fix. It has genuinely never been exercised by any CI run; first real execution is Phase 7's tag push |
| RESEARCH A2 (`body_path` ordering vs. auto-changelog) | 06-05-SUMMARY.md (Residual Risk 2) — confirmed: the live Release body was hand-assembled by `gh release edit`, not produced by the fixed pipeline, so A2 remains formally open despite the corrected page showing the right order |

**Note on Residual Risk 1 (checked, and it holds).** An initial reading suggested `524aeb1` might
have been present at the `v0.2.0` tag and therefore already exercised. Direct checks refute that:

- `git merge-base --is-ancestor 524aeb1 v0.2.0` → false (`524aeb1` is NOT in the tag)
- `git show v0.2.0:.github/workflows/build-release.yml` → the `release` job's first step is
  `Download all build artifacts`; there is no `actions/checkout` step
- the tag points at `95850b0`; `524aeb1` was pushed to `main` afterwards, consistent with the plan's
  explicit "do not push a second tag" instruction

So run `30656303074` — the one and only real tag-push execution — did **not** contain the checkout
fix. 06-05-SUMMARY.md's residual-risk framing is accurate, not overstated: the fix has never been
exercised by any CI run, and its first real execution belongs to Phase 7.

(A note of caution for anyone re-checking this: grepping the whole workflow file for
`actions/checkout` yields a false positive — the `build` and `build-macos` jobs have always had
checkout steps. The `release` job is the only one that lacked it, so the check must be scoped to
that job.)

A phase whose central deliverable is "documentation a human could follow unaided" cannot be fully
machine-verified. The single largest human-attestation-dependent claim in this report is the
Task 3 checkpoint:human-verify resume-signal ("approved") in 06-05-SUMMARY.md — a real person, on
real hardware, following only the shipped documentation. That attestation is treated below as
already-executed human verification evidence (the phase's own gated checkpoint, not a re-ask), not
re-litigated as a pending item — but its narrowed scope (primary path only, fallback explicitly
excluded) is preserved rather than smoothed into a blanket pass.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Release notes present the progressive three-step 放行 walkthrough (double-click-again primary, System Settings fallback, double-quoted `xattr` last resort) matching the Phase 5 measured path (ROADMAP SC1) | ✓ VERIFIED | `.github/RELEASE_NOTES_TEMPLATE.md` lines 33-53 (Chinese) and 87-107 (English) read directly; step 1 is bolded/standalone, steps 2-3 are inside `<details>`; command block reads `xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"` |
| 2 | Release notes/README provide a prerequisite checklist (Apple Silicon + macOS 15) with GUI-first self-check, no two-package choice framing (ROADMAP SC2) | ✓ VERIFIED | Template lines 1-25/55-79 read directly; README.md/README_EN.md `## 下载`/`## Download` sections read directly (2 new bullets, "Apple Silicon"/"macOS 15" present, no `xattr`/`系统设置`/`System Settings` duplicated) |
| 3 | A person using only shipped documentation can download, approve, install, create a profile, and launch a Chrome profile on Apple Silicon; scope narrowed to existing-account per D-13 override (ROADMAP SC3, narrowed) | ✓ VERIFIED (narrowed, matches phase's own accepted scope) | `checkpoint:human-verify` resume-signal "approved" in 06-05-SUMMARY.md, covering primary 放行 path / self-check / install / create-and-launch Chrome profile; System Settings fallback explicitly excluded from scope and recorded as not-verified per the ROADMAP's own narrowed SC3 text — this is not a gap, it is what the roadmap itself now asks for |
| 4 | DOCS-01 (REQUIREMENTS.md) text matches the rewritten SC1 | ✓ VERIFIED | `.planning/REQUIREMENTS.md` line 47 read directly, matches template wording; commit `b6749d6` confirmed in git log |
| 5 | DOCS-02 (REQUIREMENTS.md) text matches the rewritten SC2 | ✓ VERIFIED | `.planning/REQUIREMENTS.md` line 48 read directly |
| 6 | The terminal fallback command is byte-identical across JS constant, Python fallback dialog, and release notes template | ✓ VERIFIED | `frontend/src/lib/macosGatekeeperNotice.js:11`, `launch_app.py:135`, `.github/RELEASE_NOTES_TEMPLATE.md` (both occurrences) all read directly — same string, quoted bundle path |
| 7 | No user-facing surface instructs weakening system-wide security or implies Apple/Gatekeeper trust/approval | ✓ VERIFIED | Direct grep for `sudo`/`spctl`/`--master-disable`/`csrutil`/`~/Downloads`/`右键` across template, both READMEs, both locale files: 0 matches each; approval-implying phrase regex: 0 matches |
| 8 | Both documented test suites pass together | ✓ VERIFIED | Re-ran independently: `node --test frontend/src/lib/*.test.js` → 52/52 pass; `.venv/bin/python -m unittest discover -s tests` → 122 tests, OK (skipped=2) |
| 9 | A real GitHub Release exists with both installers attached and a body matching the template, in the correct order (hand-written content before auto-changelog) | ✓ VERIFIED | `gh release view v0.2.0 --json body,assets` fetched live: assets = `Open-Anti-Browser-0.2.0-arm64.dmg` + `Open-Anti-Browser-Setup.exe`; body opens with "下载前必读：系统要求" and ends with the `Full Changelog` line, template content in full |
| 10 | Phase 7 (UI-05, PKG-06) exists as a real roadmap/requirements entry, not an unrecorded promise, and is not falsely marked complete | ✓ VERIFIED | `.planning/ROADMAP.md` § Phase 7 (lines 208-225) and `.planning/REQUIREMENTS.md` § v0.2.1 补丁 (lines 50-53) read directly; Traceability table marks both `Pending`, not `Complete`; commits `8f2ba5a`/`6b2629f` confirmed in git log |
| 11 | The macOS close-button defect (UI-05) found during Phase 6 UAT is fixed on `main` but correctly excluded from Phase 6's own completion scope | ✓ VERIFIED | `a886dc7` confirmed in git log, not counted in DOCS-01/DOCS-02 completion per 06-05-SUMMARY's own framing; verification of the fix on real hardware explicitly deferred to Phase 7 |
| 12 | Workflow `release` job wires `body_path` to the committed template and retains `generate_release_notes: true` | ✓ VERIFIED | `.github/workflows/build-release.yml` lines 785-822 read directly: `Checkout` step present (added by `524aeb1`), `body_path: .github/RELEASE_NOTES_TEMPLATE.md`, `generate_release_notes: true` both present |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/RELEASE_NOTES_TEMPLATE.md` | Bilingual prerequisite checklist + progressive 放行 walkthrough + trust caveat | ✓ VERIFIED | 108 lines, both languages complete, all four content blocks present |
| `frontend/src/lib/releaseNotesTemplate.test.js` | Node-side lock: template ↔ JS constant ↔ CI wiring | ✓ VERIFIED | Exists, imports `GATEKEEPER_XATTR_COMMAND`, part of the 52-test green run |
| `frontend/src/lib/macosGatekeeperNotice.js` | Quoted `GATEKEEPER_XATTR_COMMAND` | ✓ VERIFIED | Line 11, quoted target confirmed |
| `launch_app.py` | Quoted `build_quarantine_failure_message` | ✓ VERIFIED | Line 135, `f'xattr -dr {QUARANTINE_ATTRIBUTE} "{target}"'` |
| `frontend/src/lib/gatekeeperCopyParity.test.js` | Lock on step1=double-click-again, step2=System Settings fallback | ✓ VERIFIED | Exists, part of green test run |
| `frontend/src/i18n/zh-CN.js` / `en-US.js` § `gatekeeper` | step1-4 rewritten to measured flow | ✓ VERIFIED | Both read directly; step1 = double-click, step2 = System Settings fallback, no command duplication |
| `README.md` / `README_EN.md` § 下载/Download | Two-bullet prerequisite pointer | ✓ VERIFIED | Both read directly, 5 bullets total each, no walkthrough duplication |
| `assets/dmg-background.png` / `@2x.png` | Regenerated footer matching measured flow | ✓ VERIFIED | 600×400 / 1200×800 confirmed via `sips`, matching required geometry |
| `.planning/ROADMAP.md` Phase 6 block | Rewritten SC1-3 with dated callouts | ✓ VERIFIED | Read directly, both 2026-07-27/28 and 2026-07-31 callouts present |
| `.planning/REQUIREMENTS.md` DOCS section | Rewritten DOCS-01/02 | ✓ VERIFIED | Read directly, matches template wording, traceability/coverage counts undisturbed (22 total, unchanged) |
| `.github/workflows/build-release.yml` release job | `Checkout` + `body_path` + `generate_release_notes: true` | ✓ VERIFIED | All three present in the live file |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `.github/workflows/build-release.yml` release job | `.github/RELEASE_NOTES_TEMPLATE.md` | `body_path` input | ✓ WIRED | Confirmed in file; confirmed by a **real tag push** (run `30656303074`, `release` job `success`) — the strongest possible wiring evidence |
| `frontend/src/lib/releaseNotesTemplate.test.js` | `frontend/src/lib/macosGatekeeperNotice.js` | imports `GATEKEEPER_XATTR_COMMAND` | ✓ WIRED | Confirmed by grep and green test run |
| `README.md`/`README_EN.md` | GitHub Releases page | link + deferral (no duplicated walkthrough) | ✓ WIRED | Confirmed: links present, no `xattr`/`系统设置`/`System Settings` text found in download sections |
| `.planning/REQUIREMENTS.md` DOCS-01/02 | `.planning/ROADMAP.md` Phase 6 SC1/SC2 | text must agree after rewrite | ✓ WIRED | Both texts describe the same double-click-first / prerequisite-checklist story |
| `assets/dmg-background*.png` | `build-macos` job's `create-dmg` step | pixel geometry (150,190)/(450,190), 600×400/1200×800 | ✓ WIRED | Dimensions confirmed via `sips`; geometry unchanged per 06-03-SUMMARY and workflow file's `create-dmg` invocation (not independently re-measured pixel-by-pixel by this verifier, but dimensions and the real `build-macos` job succeeding on the `v0.2.0` run is strong indirect confirmation the composition is still valid) |

### Data-Flow Trace (Level 4)

Not applicable in the conventional sense (no dynamic UI state/API data) — the closest analogue is the
"does the real published artifact actually contain what the source files say" check, which was
performed directly against the live GitHub Release (see Truth 9 above) rather than trusting the
repository content alone. This is the strongest form of Level 4 verification available for a
documentation-delivery phase: the artifact was traced all the way to its live, public destination.

### Behavioral Spot-Checks / Probe Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Node test suite green | `node --test frontend/src/lib/*.test.js` | 52/52 pass, 0 fail | ✓ PASS |
| Python test suite green | `.venv/bin/python -m unittest discover -s tests` | 122 tests, OK (skipped=2) | ✓ PASS |
| Byte-identical command across surfaces | `grep -c` on JS constant, template, Python message | Identical string, quoted path, confirmed | ✓ PASS |
| Real Release body matches template + correct ordering | `gh release view v0.2.0 --json body` | Template content present, hand-written block precedes `Full Changelog` line | ✓ PASS |
| Real tag-push CI run (`build`, `build-macos`, `release`) | `gh run view 30656303074 --json jobs` | All three: `success` | ✓ PASS |
| Prior `workflow_dispatch` regression (06-01) | `gh run view 30653333767 --json jobs` | `build`/`build-macos` success, `release` skipped (as designed on a branch ref) | ✓ PASS |
| GitHub's actual CommonMark rendering of the nested `<details>` ordered list (code review IN-01) | `curl` the live release page HTML, inspect for `<ol start="2">` | Found `<ol start="2">` — GitHub renders the continuation correctly, numbering displays as 1, 2, 3 | ✓ PASS — resolves code review IN-01 as a non-issue, confirmed against real rendering rather than left as a hypothetical |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DOCS-01 | 06-01, 06-03, 06-04, 06-05 | Progressive 放行 walkthrough, byte-identical quoted command | ✓ SATISFIED | All four consumer surfaces agree; real Release confirms |
| DOCS-02 | 06-02, 06-04 | Prerequisite checklist, GUI self-check, single-package framing | ✓ SATISFIED | Template + both READMEs confirmed |

No orphaned requirements: REQUIREMENTS.md Traceability table maps only DOCS-01/DOCS-02 to Phase 6;
UI-05/PKG-06 are correctly mapped to Phase 7 and marked `Pending`, not claimed as Phase 6 deliverables.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.github/RELEASE_NOTES_TEMPLATE.md` | ~53-55 | Missing `---` divider between the Chinese and English blocks (code review WR-01) | ℹ️ Info (documentation polish, not a phase-goal blocker) | A reader skimming the combined release page has no visual cue at the language switch; step 1 in each language remains bolded/standalone regardless, so the primary instruction is still easy to find. Non-blocking. |
| — | — | No `TBD`/`FIXME`/`XXX` markers found in any file touched by this phase | — | Debt-marker gate: clean |

No blocker-level anti-patterns found in any file this phase modified.

### Human Verification Required

None outstanding. The phase's one inherently-human-only check (D-15's "does the documentation
suffice for an unassisted user") was already executed as a gated `checkpoint:human-verify` during
plan 06-05 execution, with an explicit resume-signal ("approved") and an honestly narrowed scope
(System Settings fallback path excluded and recorded as not-verified, matching ROADMAP's own current
SC3 text). This verifier is not asking for that checkpoint to be re-run — the roadmap itself now
defines success narrowly enough that the exercised paths satisfy it, and the exclusion is preserved
in this report rather than silently absorbed.

The one candidate human-verification item raised by the code review (IN-01, CommonMark list-rendering
risk) was resolved above by directly fetching and inspecting the live rendered release page — no
human visual check remains necessary for that item.

### Gaps Summary

No gaps found. All 12 must-have truths derived from ROADMAP's own (twice-rewritten, dated) Success
Criteria and REQUIREMENTS DOCS-01/DOCS-02 are verified against the live codebase and the live,
public GitHub Release — not merely against SUMMARY.md narrative. Every plan's `must_haves.prohibitions`
(safety boundary, no-trust-implication) was independently re-checked with fresh greps against the
current file contents, not inherited from the SUMMARYs' own claims.

The phase's honesty about its own limits is itself a positive signal worth stating plainly: four
items are explicitly carried forward as unverified (System Settings fallback path, B1 dialog wording,
the checkout-fix's first real tag-push exercise, and RESEARCH assumption A2's ordering question), and
none of them is misrepresented as passed anywhere in the codebase or planning documents — confirmed by
direct search, not by trusting the SUMMARY's own assertion that this is so. These four items are
correctly routed to Phase 7 (UI-05, PKG-06) rather than left as silent Phase 6 debt.

One minor, non-blocking documentation-polish item (WR-01, missing section divider) remains from the
code review; it does not affect the phase's core deliverable (an unassisted user reaching a working
Chrome profile) and is not required to be fixed before this phase closes.

---

*Verified: 2026-07-31T22:15:00Z*
*Verifier: Claude (gsd-verifier)*
