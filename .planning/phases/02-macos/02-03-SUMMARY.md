---
phase: 02-macos
plan: 03
subsystem: release
tags: [gh-release, macos, arm64, ditto, codesign, cdp-smoke, kernel-upload]

# Dependency graph
requires:
  - phase: 02-01
    provides: scripts/release/verify_and_upload_macos_kernel.sh (upload-gate script — ditto round-trip, double-binary arch check, codesign, CDP smoke, gh release upload --clobber)
  - phase: 02-02
    provides: backend.config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64 (SSOT asset filename the script resolves at runtime)
provides:
  - "Real `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` asset published on GitHub release kernel-149.0.7827.114"
  - "First real (non-dry-run) execution of verify_and_upload_macos_kernel.sh against a post-D-02 sibling-repo build artifact — proves the whole upload-gate pipeline end to end on real bits"
affects: [02-04-x64-real-upload, phase-5-ci-macos-job, installer-macos-arm64-download-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-repo artifact handoff for irreversible publish actions requires two human-gated checkpoints (pre-upload handoff confirmation + post-upload asset confirmation) bracketing a single automated real-upload task — LOG(INFO) diagnostic presence in a sibling-repo build cannot be statically detected from zip contents alone, so the boundary is human judgment, not automation"
    - "Post-upload independent re-download + SHA-256 comparison against the pre-upload local artifact, re-run through the same lipo/codesign checks, as belt-and-suspenders verification beyond the plan's minimum bar"

key-files:
  created: []
  modified: []

key-decisions:
  - "Task 1 handoff confirmed via human reply (\"approved,arm64 zip 路径=...\") after independent recon: sibling-repo commit a5d342a7 (2026-07-22T17:47:58-07:00) removed the LOG(INFO) diagnostic; the on-disk build at ../fingerprint-chromium predated that commit (mtime 2026-07-22T14:27:24), so the human-provided zip at /Users/fanjin/bfwg/kernel-artifacts/ (repacked 2026-07-25T10:24, after a5d342a7) was accepted as the correct post-D-02 artifact rather than any local build directory"
  - "Task 2 executed the real (non-dry-run) verify_and_upload_macos_kernel.sh rather than trusting the human's self-check numbers — independently reproduced lipo/codesign/CDP-smoke results before allowing the real gh release upload --clobber to proceed"
  - "Task 3's optional verification step (re-download) was performed, not skipped: downloaded asset SHA-256 matched the pre-upload local zip's SHA-256 exactly, confirming zero corruption across gh release upload --clobber"

requirements-completed: [KERNEL-01, KERNEL-03]

coverage:
  - id: D1
    description: "gh release view kernel-149.0.7827.114 asset list contains ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip (KERNEL-01)"
    requirement: KERNEL-01
    verification:
      - kind: other
        ref: "gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name' | grep -F 'ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip' (live GitHub API call, real asset)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uploaded arm64 zip passed independent script re-verification (double-binary arch=arm64, codesign adhoc+linker-signed, CDP smoke returning 149.0.7827.114) before upload (KERNEL-03)"
    requirement: KERNEL-03
    verification:
      - kind: other
        ref: "bash scripts/release/verify_and_upload_macos_kernel.sh --arch arm64 <zip> (real run, not --dry-run) — all 4 stages passed, then real gh release upload --clobber executed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Uploaded asset is the post-D-02 (LOG(INFO)-free) sibling-repo build, confirmed via human cross-repo handoff — cannot be statically verified from zip bytes alone"
    requirement: KERNEL-01
    verification: []
    human_judgment: true
    rationale: "LOG(INFO) diagnostic presence/absence in a compiled macOS binary is a runtime-gated log line (Pitfall 6) that cannot be detected by static inspection of the zip; correctness of the sibling-repo build provenance is inherently a human cross-repo judgment call, confirmed via explicit checkpoint approval"

# Metrics
duration: ~35min
completed: 2026-07-25
status: complete
---

# Phase 2 Plan 3: macOS arm64 Kernel Real Upload Summary

**Real post-D-02 arm64 `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` (155,462,650 bytes) published to GitHub release `kernel-149.0.7827.114` after independent double-binary arch + codesign + CDP-smoke re-verification, closing KERNEL-01/KERNEL-03 on the arm64 side.**

## Performance

- **Duration:** ~35 min (spanning two human-gated checkpoints across a session)
- **Started:** 2026-07-24T23:50:15Z (per STATE.md `stopped_at: Completed 02-02-PLAN.md`)
- **Completed:** 2026-07-25T17:30:04Z
- **Tasks:** 3 (2 human-verify checkpoints + 1 automated verify-and-upload)
- **Files modified:** 0 (no repository file changes — this plan's output is a GitHub release asset)

## Accomplishments

- Confirmed (Task 1, human-gated) that the arm64 artifact at `/Users/fanjin/bfwg/kernel-artifacts/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` is a genuine post-D-02 rebuild: sibling-repo commit `a5d342a7` (2026-07-22T17:47:58-07:00, `feat(08-01): remove 021 entropy-gate LOG(INFO) diagnostic before Windows packaging`) removed the runtime-gated calibration log line; the artifact was repacked 2026-07-25T10:24, after that commit, per the human's own `ditto -c -k --keepParent` timestamp and self-check (`lipo -archs` both arm64, `codesign -dv` adhoc+linker-signed).
- Ran the real (non-dry-run) `scripts/release/verify_and_upload_macos_kernel.sh --arch arm64` against the artifact — independently reproduced all four verification stages rather than trusting the human's self-check alone: ditto round-trip extraction, double-binary arch check (launcher + Framework both `arm64`), codesign adhoc/linker-signed survival, and a real local CDP smoke test (`/json/version` returned `149.0.7827.114`).
- Executed the real `gh release upload kernel-149.0.7827.114 ... --clobber --repo ShengSoft-Tech/Open-Anti-Browser`; pre-upload snapshot confirmed the asset did not previously exist (only Windows `-1.1/-1.2/-1.4` assets were present), post-upload snapshot confirmed `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` now exists (155,462,650 bytes).
- Went beyond the plan's minimum Task 3 bar: re-downloaded the published asset (`gh release download ... --repo ShengSoft-Tech/Open-Anti-Browser`) into a fresh temp dir and confirmed its SHA-256 (`d6fea338a373a167c6c3e5f987608bca190f23cb80bdb81949df62dd61bd5315`) matches the pre-upload local zip's SHA-256 exactly, then re-ran `ditto -x -k` + `lipo -archs` + `codesign -dv` on the freshly re-downloaded copy — all identical results, proving zero corruption through the upload/download round trip.
- Human approved Task 3 (asset confirmed in release, correctly named, downloadable) via explicit "approved" reply.

## Task Commits

This plan produced no repository file changes (per its own `<files>` annotation: "无仓库文件改动;调用 02-01 脚本执行 verify + gh 上传"), so no per-task commits were made for Tasks 1–3. The only commit from this plan is the final docs/state metadata commit (see below).

1. **Task 1: 确认兄弟仓库 post-D-02 arm64 产物就位(handoff)** — human-verify checkpoint, approved (no repo changes)
2. **Task 2: 上传前把关并发布 arm64 内核到 kernel release** — automated verify + real `gh release upload --clobber` (no repo changes; external GitHub release state changed)
3. **Task 3: 人工确认 arm64 资产已在 release 且可下载** — human-verify checkpoint, approved (no repo changes)

**Plan metadata:** committed alongside this SUMMARY (see final commit hash in git log after this file lands)

## Files Created/Modified

None in this repository. External artifact: `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` asset added to GitHub release `kernel-149.0.7827.114` (repo `ShengSoft-Tech/Open-Anti-Browser`).

## Decisions Made

- Accepted the human-provided zip path as the correct post-D-02 artifact based on independent recon (sibling-repo commit timestamp vs. on-disk stale build mtime), not solely on the human's assertion — this is the "trust but verify" pattern the plan's Pitfall 6 called for.
- Ran the real verify script rather than accepting the human's manual `lipo`/`codesign` self-check as sufficient — the plan explicitly required the script to run independently before allowing the real upload, and this was followed literally.
- Added an unplanned but low-cost extra verification (re-download + SHA-256 comparison + re-run lipo/codesign on the downloaded copy) during Task 3 to strengthen confidence beyond the plan's "可选" (optional) download step, since the upload is `reversibility rating="costly"` and cheap to double-check now versus expensive to debug later.

## Deviations from Plan

None — plan executed exactly as written, including both blocking human-verify checkpoints. No Rule 1-4 auto-fixes were needed; the script passed cleanly on the first real run with no architecture/codesign/smoke failures.

## Issues Encountered

- `gh release download` initially failed with `failed to run git: fatal: not a git repository` when run from a `mktemp -d` scratch directory outside any git repo — `gh` needs `--repo <owner>/<name>` to be told explicitly which repo to target when not run inside a git checkout. Resolved immediately by adding `--repo ShengSoft-Tech/Open-Anti-Browser` to the download command; this was a verification-tooling quirk, not a defect in the plan's own script (which already always passes `--repo` explicitly to `gh release upload`).

## User Setup Required

None — `gh auth status` was already valid (account `bfwg`, `repo` scope) at Task 1 time, satisfying the plan's `user_setup` precondition.

## Next Phase Readiness

- KERNEL-01 and KERNEL-03 are closed on the **arm64** side. The `kernel-149.0.7827.114` release now has a working, verified `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` asset that `backend.config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64` already points to (02-02).
- 02-04 (x64 real upload) is unblocked to proceed independently — this plan intentionally split arm64 from x64 (RESEARCH Open Question 2) so the x64 side's separate cross-repo blocker does not gate arm64's release.
- No changes needed to `scripts/release/verify_and_upload_macos_kernel.sh` or `backend/config.py` — both worked exactly as designed against a real artifact, with zero deviations.

---
*Phase: 02-macos*
*Completed: 2026-07-25*

## Self-Check: PASSED

- FOUND: .planning/phases/02-macos/02-03-SUMMARY.md
- FOUND: scripts/release/verify_and_upload_macos_kernel.sh (unchanged, pre-existing from 02-01)
- FOUND (live GitHub API): gh release view kernel-149.0.7827.114 --json assets contains `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` (155,462,650 bytes)
- No task commit hashes to verify — Tasks 1–3 made zero repository file changes (documented above), consistent with the plan's `<files>` annotation
