---
phase: 06-release-docs
reviewed: 2026-07-31T21:35:10Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .github/RELEASE_NOTES_TEMPLATE.md
  - .github/workflows/build-release.yml
  - assets/dmg-background.png
  - assets/dmg-background@2x.png
  - backend/main.py
  - frontend/package.json
  - frontend/src/i18n/en-US.js
  - frontend/src/i18n/zh-CN.js
  - frontend/src/lib/gatekeeperCopyParity.test.js
  - frontend/src/lib/macosGatekeeperNotice.js
  - frontend/src/lib/macosGatekeeperNotice.test.js
  - frontend/src/lib/releaseNotesTemplate.test.js
  - tests/test_macos_desktop_runtime.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-07-31T21:35:10Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 6 adds macOS release documentation (Gatekeeper first-launch guidance, system-requirements
disclaimers) and a version bump (0.1.16 → 0.2.0), backed by unusually thorough test coverage
(`gatekeeperCopyParity.test.js`, `releaseNotesTemplate.test.js`, `macosGatekeeperNotice.test.js`,
`tests/test_macos_desktop_runtime.py`).

Verified explicitly per the phase's load-bearing invariants:

- **Byte-identity of the quarantine command.** `GATEKEEPER_XATTR_COMMAND` in
  `macosGatekeeperNotice.js:11` (`xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"`)
  is byte-identical to both occurrences in `RELEASE_NOTES_TEMPLATE.md` (lines 46 and 100) via
  direct `grep`. (The third leg of this invariant, `launch_app.py`'s rendered fallback message, is
  outside this review's file scope per the task's known-context note, but the in-scope test
  `tests/test_macos_desktop_runtime.py::BuildQuarantineFailureMessageTests` asserts the same
  literal against it.)
- **Safety boundary.** Grepped all reviewed files for `sudo`, `spctl`, `--master-disable`,
  `csrutil`, and `~/Downloads` — none present. No recursive quarantine removal targets anything
  broader than the single `Open-Anti-Browser.app` bundle path.
- **Version consistency.** `backend/main.py` has both `version="0.2.0"` FastAPI declarations
  (lines 23, 26) and `frontend/package.json` has `"version": "0.2.0"` — all three values that
  `scripts/release/check_version_consistency.py` compares agree. No mismatch.
- **i18n parity.** `en-US.js` and `zh-CN.js` gatekeeper step1–step4 keys carry matching content
  and structure (step1 = "double-click again" as primary path, step2 = System Settings fallback,
  no restatement of the xattr command in step4). Ran the full node:test suite for the three JS
  test files in scope — all 20 assertions pass.

No Critical/BLOCKER findings. Two minor documentation-quality items below (one Warning, two Info)
are newly identified by this review and were not already covered by the known-context exclusions
(the missing `checkout` fix, the macOS close-button UI-05 item, and the RESEARCH A2 body_path
ordering assumption — none of which are re-flagged here).

`assets/dmg-background.png` and `assets/dmg-background@2x.png` are binary PNGs — out of scope
for static review; no findings recorded against them.

## Warnings

### WR-01: No visual separator at the Chinese/English language boundary in the release notes template

**File:** `.github/RELEASE_NOTES_TEMPLATE.md:53-55`
**Issue:** The template uses a `---` horizontal rule to separate sections in two places: between
"关于签名与信任状态的说明" and "首次打开被拦截？这是正常现象" (line 31), and between "About Signing
and Trust" and "First launch blocked? This is expected" (line 85). But there is no `---` between
the end of the entire Chinese block (line 53, "...不是安全隐患。") and the start of the entire
English block (line 55, "## Before You Download: System Requirements") — the single biggest
content discontinuity in the file (a full language switch) is the one transition that gets no
visual divider, while two same-language, lower-stakes transitions do. Combined with
`generate_release_notes: true` appending GitHub's auto-generated changelog immediately after this
whole template (per `build-release.yml:822-823`), a reader skimming the rendered GitHub release
page has no visual cue marking where the Chinese doc ends and the English doc begins.
**Fix:** Add a `---` divider immediately before line 55, matching the pattern used at the other
two section boundaries:
```markdown
应用能够正常运行，是因为它不再带有系统隔离标记（quarantine），并不代表它已通过 Apple 签名认证或已被 Gatekeeper 信任——这是这类未签名应用的预期正常状态，不是安全隐患。

---

## Before You Download: System Requirements
```

## Info

### IN-01: Ordered-list numbering split across a raw-HTML `<details>` block relies on implicit CommonMark list-continuation behavior

**File:** `.github/RELEASE_NOTES_TEMPLATE.md:37-51` and `:91-105`
**Issue:** Both language sections open a numbered list with item `1.` outside a `<details>` block,
then continue the sequence with items `2.` and `3.` *inside* the collapsed `<details>` body. Per
CommonMark, a raw HTML block interrupts list continuation, so strict spec-compliant renderers may
treat `2.`/`3.` as the start of a *new*, separate ordered list rather than a continuation of item
`1.` (GFM's renderer does support an explicit start-number on the new list, so the visible numbers
would still read `1, 2, 3` in practice on github.com, but this has not been confirmed against an
actual rendered GitHub release preview in this review, and behavior can vary across Markdown
renderers that consume `body_path`, e.g. third-party release aggregators).
**Fix:** Before the next tagged release, open the rendered release page (or a PR/gist preview of
this exact file) and visually confirm items 1–2–3 render as one continuous numbered sequence in
both language sections. If not, consider flattening to a single list with sub-bullets instead of
nesting continuation items inside `<details>`.

### IN-02: `body_path` template duplicates full guidance per language with no anchor/TOC, growing release-note length substantially

**File:** `.github/RELEASE_NOTES_TEMPLATE.md` (whole file, 107 lines)
**Issue:** The template repeats the entire system-requirements + signing + Gatekeeper guidance
twice (once in Chinese, once in English) with no jump links between the two, and this entire
107-line block is prepended to GitHub's auto-generated changelog on every tagged release. This is
an intentional, human-directed design choice per the phase context (not a defect), but as the
document grows in future phases (e.g. if per-OS instructions for Windows are added here too) the
lack of a table of contents/anchor links will make the combined release note increasingly hard to
scan.
**Fix:** No action required now; consider adding `[English version below ↓](#before-you-download-system-requirements)` /
`[中文说明见上 ↑]` anchor links if this template grows further in a future phase.

---

_Reviewed: 2026-07-31T21:35:10Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
