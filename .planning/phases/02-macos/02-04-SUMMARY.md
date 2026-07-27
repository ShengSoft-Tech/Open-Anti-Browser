---
phase: 02-macos
plan: 04
subsystem: release
tags: [gh-release, macos, x64, x86_64, rosetta, ditto, codesign, cdp-smoke, kernel-upload]

# Dependency graph
requires:
  - phase: 02-01
    provides: scripts/release/verify_and_upload_macos_kernel.sh (upload-gate script — ditto round-trip, double-binary arch check, codesign, CDP smoke with x86_64/Rosetta branch, gh release upload --clobber)
  - phase: 02-02
    provides: backend.config.CHROME_ENGINE_ZIP_URL_MACOS_X64 (SSOT asset filename the script resolves at runtime)
provides:
  - "Real `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip` asset (165,782,894 bytes) published on GitHub release kernel-149.0.7827.114 — completes the macOS dual-arch kernel pair (arm64 + x64)"
  - "First real (non-dry-run) execution of the script's x86_64 branch against a real Intel cross-compile artifact — proves the Rosetta-2 CDP smoke path end to end on real x64 bits"
  - "Arch-conditional codesign gate: x86_64 skips the linker-signed assertion (platform design), x64 integrity now anchored by dual-binary arch assertion + Rosetta launch smoke"
affects: [phase-5-ci-macos-job, installer-macos-x64-download-path, fingerprint-chromium-260726-jui-deviation-2]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "codesign gate is architecture-conditional: arm64 Mach-O is mandatorily signed (ld64.lld auto -adhoc_codesign, flags=0x20002), x86_64 is unsigned by platform design (linker default -no_adhoc_codesign) — so a uniform codesign check is a platform-category error; x64 integrity is instead proven by the stronger stage-4 real launch smoke"
    - "Cross-repo artifact handoff for irreversible publish actions uses two human-gated checkpoints (pre-upload handoff confirmation + post-upload asset confirmation) bracketing a single automated real-upload task — same convention as 02-03"

key-files:
  created: []
  modified:
    - "scripts/release/verify_and_upload_macos_kernel.sh — stage 3 (codesign) gated behind --arch arm64; x86_64 skips it with an explanatory echo (fix 02b6688). arm64 branch kept byte-for-byte strict. Header comment updated."

key-decisions:
  - "x64 kernel ships UNSIGNED — accepted, not a defect. x86_64 Mach-O is not mandatorily signed (linker default -no_adhoc_codesign); the artifact launches and self-reports 149.0.7827.114 via `arch -x86_64`. Signing parity with arm64 is cosmetic, not functional, and not worth a mac-toolchain patch + full relink. The arch-conditional skip (02b6688) is therefore the FINAL design, not a temporary workaround."
  - "Rejected `codesign --force --sign -` as a workaround: it yields only flags=0x2 (adhoc), never the 0x20000 linker-signed bit, and risks corrupting the 385MB nested bundle. If linker-signed x64 is ever wanted, the correct fix is a quilt patch in fingerprint-chromium injecting -adhoc_codesign at link time — deferred to that repo as its own item (260726-jui deviation 2)."
  - "Corrected a prior-session recheck error: the earlier claim that sibling-repo kernel-artifacts/ and out/ dirs had been deleted was a path-basis mistake — actual locations are ../kernel-artifacts/ (repo sibling) and build/src/out/, both always present. Fixed in STATE.md (commit 205b583)."
  - "Ran the real (non-dry-run) verify script rather than trusting the human's self-check numbers — independently reproduced dual-binary x86_64 arch assertion + Rosetta CDP smoke before allowing the real gh release upload --clobber."

requirements-completed: [KERNEL-02, KERNEL-03]

coverage:
  - id: D1
    description: "gh release view kernel-149.0.7827.114 asset list contains ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip (KERNEL-02)"
    requirement: KERNEL-02
    verification:
      - kind: other
        ref: "gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name' | grep -F 'ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip' (live GitHub API call, real asset, 165,782,894 bytes)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uploaded x64 zip passed independent script re-verification (double-binary arch=x86_64, codesign skipped by platform design, Rosetta-2 CDP smoke returning 149.0.7827.114) before upload (KERNEL-03)"
    requirement: KERNEL-03
    verification:
      - kind: other
        ref: "bash scripts/release/verify_and_upload_macos_kernel.sh --arch x86_64 <zip> (real run, not --dry-run) — stage 2 dual x86_64 arch assertion + stage 4 `arch -x86_64` Rosetta CDP smoke passed, then real gh release upload --clobber executed"
        status: pass
    human_judgment: false
  - id: D3
    description: "x64 asset name is byte-for-byte identical to config.CHROME_ENGINE_ZIP_URL_MACOS_X64 basename and carries the explicit `x64` architecture identifier (KERNEL-03 / SSOT)"
    requirement: KERNEL-03
    verification:
      - kind: other
        ref: "release asset name == basename(CHROME_ENGINE_ZIP_URL_MACOS_X64) == ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip; release-side size 165782894B == local artifact size 165782894B"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-07-27
status: complete
---

# Phase 2 Plan 4: macOS x64 Kernel Real Upload Summary

**Real Intel `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip` (165,782,894 bytes) published to GitHub release `kernel-149.0.7827.114` after dual-binary x86_64 arch assertion + `arch -x86_64` Rosetta-2 CDP smoke, with the codesign stage made arch-conditional; closes KERNEL-02 and the x64 side of KERNEL-03 and completes the macOS dual-arch kernel pair.**

## Performance

- **Duration:** ~40 min (spanning a long cross-repo block that finally cleared, then two human-gated checkpoints)
- **Started:** 2026-07-25 (02-04 Task 1 checkpoint first held; sibling-repo x64 artifact not yet delivered)
- **Completed:** 2026-07-27T04:55:35Z
- **Tasks:** 3 (2 human-verify checkpoints + 1 automated verify-and-upload), preceded by a mandatory arch-conditional script fix
- **Files modified:** 1 (`scripts/release/verify_and_upload_macos_kernel.sh` — arch-conditional codesign gate)

## Accomplishments

- Confirmed (Task 1, human-gated) delivery of the real post-D-02 x64 cross-compile artifact at `/Users/fanjin/bfwg/kernel-artifacts/ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip` (165,782,894 bytes, SHA-256 `a9eb22f9bb25bc03ace4a54dc759e6b21a96ad26d0f1383b1f3141a470ac158e`), sharing the same post-D-02 source tree as arm64. Sibling-repo commits `91d6603b` / `f0985747` / `30d2553a` added `downloads-macos-x64.ini`, split `flags.macos-arm64.gn` / `flags.macos-x64.gn` from a neutralized `flags.macos.gn`, and produced the x64 build.
- Made a required prerequisite fix to the 02-01 upload-gate script (commit `02b6688`): stage 3 codesign checks (adhoc + linker-signed) now run only under `--arch arm64`; `--arch x86_64` skips them with an explanatory echo. x86_64 Mach-O binaries are unsigned by platform design (`ld64.lld` defaults to `-no_adhoc_codesign` for x86_64), so `codesign -dv` returned "code object is not signed at all" and exited non-zero at line 116 before the smoke test could run. The arm64 branch is kept byte-for-byte strict.
- Ran the real (non-dry-run) `scripts/release/verify_and_upload_macos_kernel.sh --arch x86_64` against the artifact — independently reproduced the stage-2 dual-binary architecture assertion (launcher + Framework both `x86_64`) and the stage-4 `arch -x86_64` Rosetta-2 CDP smoke (`/json/version` returned `149.0.7827.114`) rather than trusting the human's self-check alone.
- Executed the real `gh release upload kernel-149.0.7827.114 ... --clobber --repo ShengSoft-Tech/Open-Anti-Browser`; post-upload snapshot confirmed `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip` now exists (165,782,894 bytes) alongside the arm64 asset — the release now carries both macOS architectures (155.5MB arm64 + 165.8MB x64).
- Confirmed the uploaded asset name is byte-for-byte identical to `basename(config.CHROME_ENGINE_ZIP_URL_MACOS_X64)` and that the release-side size matches the local artifact exactly (165782894B), evidencing zero corruption through the upload.
- Human approved Task 3 (x64 asset confirmed in release, correctly named with the `x64` identifier, dual-arch complete) via explicit "approved" reply.

## Task Commits

Unlike 02-03, this plan required one repository code change (the arch-conditional script fix), committed atomically before the upload:

1. **Prerequisite fix: arch-conditional codesign gate** — `02b6688` (fix) — gate stage-3 codesign behind `--arch arm64`; x86_64 skips.
2. **Task 1: 确认兄弟仓库 x64 交叉编译产物交付(handoff)** — human-verify checkpoint, approved (no repo changes)
3. **Task 2: 上传前把关(含 Rosetta 冒烟)并发布 x64 内核到 kernel release** — automated verify + real `gh release upload --clobber` (no repo changes; external GitHub release state changed)
4. **Task 3: 人工确认 x64 资产已在 release 且架构正确** — human-verify checkpoint, approved (no repo changes)

Supporting docs/state commits: `88494cf` (third recheck record), `205b583` (upload record + path-error correction). Plan metadata committed alongside this SUMMARY.

## Files Created/Modified

- `scripts/release/verify_and_upload_macos_kernel.sh` — stage 3 codesign check gated behind `--arch arm64`; x86_64 skips with an explanatory echo; header comment updated to note arch-conditionality. arm64 path unchanged.

External artifact: `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip` asset added to GitHub release `kernel-149.0.7827.114` (repo `ShengSoft-Tech/Open-Anti-Browser`).

## Decisions Made

- **x64 stays unsigned — accepted as final design.** x86_64 does not mandate signing; the artifact launches and self-reports its version under Rosetta. Signing parity is cosmetic; the arch-conditional skip is the permanent design, not a stopgap. See key-decisions.
- Ran the real verify script rather than accepting the human's manual `lipo`/smoke self-check as sufficient — same "trust but verify" convention as 02-03.
- Corrected an earlier path-basis recheck error in STATE.md (sibling-repo artifact dirs were never deleted; wrong paths were inspected).

## Deviations from Plan

The plan declared `files_modified: []` ("本 plan 不新增代码符号"), but one repository file change was required and made:

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical / platform-correctness] Arch-conditional codesign gate**
- **Found during:** Task 2 precondition analysis (before running the real x86_64 verify)
- **Issue:** The 02-01 script asserted codesign adhoc + linker-signed unconditionally. x86_64 Mach-O binaries are unsigned by platform design, so `codesign -dv` exits non-zero at stage 3 and the script dies before the smoke test — the x64 upload could never pass under the original script.
- **Fix:** Gate stage 3 behind `--arch arm64`; x86_64 skips codesign with an explanatory echo. arm64 kept byte-for-byte strict. x64 integrity remains covered by stage-2 dual-binary arch assertion + stage-4 Rosetta launch smoke.
- **Files modified:** scripts/release/verify_and_upload_macos_kernel.sh
- **Verification:** Real `--arch x86_64` run passed cleanly; `bash -n` syntax OK; arm64 branch untouched (02-03's arm64 upload remains valid).
- **Committed in:** `02b6688` (standalone fix commit, before the upload)

---

**Total deviations:** 1 (1 platform-correctness fix to an upstream-plan script). One user-directed scope decision: skip only stage 3, keep stage 4 for x86_64 (user confirmed via AskUserQuestion — the literal "skip stages 3/4" instruction was narrowed to stage 3 only, because the user's own reasoning and evidence were codesign-specific and the plan requires the x64 smoke test).
**Impact on plan:** The fix is necessary for correctness — without it KERNEL-02/03 x64 closure is impossible. No scope creep; arm64 behavior unchanged.

## Issues Encountered

- Long cross-repo block: from 2026-07-25 the plan sat at the Task 1 blocking checkpoint across three rechecks while the sibling `fingerprint-chromium` repo lacked `downloads-macos-x64.ini` and an x64 build. Cleared 2026-07-27 when that repo delivered the real cross-compile artifact (commits 91d6603b/f0985747/30d2553a). Correctly refused, throughout, to substitute an arm64 zip for the x64 slot (A-K02 / T-02-05).

## User Setup Required

None — sibling-repo x64 cross-compile was delivered by the user; `gh auth status` valid (account `bfwg`); Rosetta 2 available (`arch -x86_64 /usr/bin/true` exit 0).

## Next Phase Readiness

- KERNEL-02 and KERNEL-03 are closed on the **x64** side. The `kernel-149.0.7827.114` release now carries both macOS assets that `backend.config` points to (arm64 + x64), so the dual-dmg / dual-arch download path Phase 5 depends on has real bits behind it.
- Phase 5 (CI packaging/release) can now validate the macOS packaging path end to end against real kernel assets rather than local mocks.
- Deferred to sibling repo (optional, non-blocking): `fingerprint-chromium` 260726-jui deviation 2 — whether to add a quilt patch injecting `-adhoc_codesign` for x64 linker-signed parity. Decision recorded here as won't-fix unless that repo chooses to pursue it; if it ever does, OAB can then restore a uniform codesign gate by reverting 02b6688.

---
*Phase: 02-macos*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: .planning/phases/02-macos/02-04-SUMMARY.md
- FOUND: scripts/release/verify_and_upload_macos_kernel.sh (modified — arch-conditional codesign, commit 02b6688)
- FOUND (live GitHub API): gh release view kernel-149.0.7827.114 --json assets contains `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip` (165,782,894 bytes)
- VERIFIED: release-side x64 size (165782894B) == local artifact size (165782894B); asset name == basename(CHROME_ENGINE_ZIP_URL_MACOS_X64)
- Task commits: 02b6688 (fix, present in git log); Tasks 1/3 made zero repo changes (human checkpoints), Task 2 changed external GitHub release state only
