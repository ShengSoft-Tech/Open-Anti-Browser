---
phase: 02-macos
plan: 01
subsystem: infra
tags: [bash, ditto, lipo, codesign, gh-cli, macos, release-engineering, rosetta]

# Dependency graph
requires:
  - phase: 01-backend-cross-platform
    provides: config.py platform-aware path resolution (macOS branch already in place, awaiting URL backfill)
provides:
  - "scripts/release/verify_and_upload_macos_kernel.sh — a self-contained, idempotent bash script that ditto round-trips a macOS fingerprint-chromium .app/zip, verifies BOTH the launcher and Framework binary architectures via lipo, sanity-checks the ad-hoc signature via codesign, runs a native/Rosetta CDP launch smoke test, and (non-dry-run) uploads via gh release upload --clobber"
  - "--dry-run self-test mode proven end-to-end against the real arm64 build in ../fingerprint-chromium, ~17s runtime"
  - "x86_64 branch (arch -x86_64, long retry budget) and gh upload logic structurally in place (bash -n valid), real x64 verification deferred to 02-04 pending the sibling repo's x64 build"
affects: [02-02-config-url-backfill, 02-03-arm64-real-upload, 02-04-x64-real-upload]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kernel release verify+upload as an in-repo, idempotent, --dry-run-capable bash script (first scripts/ directory and .sh file in this repo)"
    - "Dual-binary architecture verification (launcher stub + Framework binary reached via Versions/Current symlink) — never trust the launcher alone"
    - "Architecture-dependent retry budgets for CDP smoke tests (short native, long Rosetta cold-start)"
    - "Upload asset filename resolved from backend.config Python constants at upload time (SSOT), never hardcoded in the shell script"

key-files:
  created:
    - scripts/release/verify_and_upload_macos_kernel.sh
  modified: []

key-decisions:
  - "Upload asset is always re-staged to $SCRATCH/$ZIP_NAME (config.py-resolved name) before gh release upload, rather than trusting the input artifact's own filename — guarantees the published GitHub asset name matches the SSOT constant byte-for-byte regardless of what the input zip/app happened to be named locally"
  - "Task 1's smoke_test() implementation already parameterized retries/interval and the arch -x86_64 launch prefix by $expected_arch, so Task 2 only needed to add the gh upload step on top — a natural consequence of writing one retry-budget-aware function instead of two arch-specific ones"

requirements-completed: [KERNEL-01, KERNEL-02, KERNEL-03]

coverage:
  - id: D1
    description: "Dual-binary (launcher + Framework) arm64 architecture verification via lipo, run end-to-end via --dry-run against the real sibling-repo build"
    requirement: KERNEL-03
    verification:
      - kind: manual_procedural
        ref: "bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch arm64 ../fingerprint-chromium/build/src/out/Default/Chromium.app"
        status: pass
    human_judgment: false
  - id: D2
    description: "Architecture mismatch guard: --dry-run --arch x86_64 against an arm64 bundle must exit non-zero at the lipo check"
    requirement: KERNEL-03
    verification:
      - kind: manual_procedural
        ref: "bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch x86_64 ../fingerprint-chromium/build/src/out/Default/Chromium.app (expect exit 1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Native CDP launch smoke test (arm64) confirms 149.0.7827.114 responds on /json/version, then kills the process with no leftover"
    requirement: KERNEL-03
    verification:
      - kind: manual_procedural
        ref: "same --dry-run --arch arm64 invocation; pgrep -fl 'Chromium.app.*tmp\\.' confirmed empty after run"
        status: pass
    human_judgment: false
  - id: D4
    description: "gh release upload --clobber step with SSOT filename resolution from backend.config, gated off entirely under --dry-run; no token literals in the script"
    requirement: KERNEL-01
    verification:
      - kind: manual_procedural
        ref: "grep -c 'gh release upload' / '--clobber' / 'ShengSoft-Tech/Open-Anti-Browser' scripts/release/verify_and_upload_macos_kernel.sh; grep -c 'GH_TOKEN|--token|ghp_' == 0; --dry-run output includes 'dry-run: skipping upload'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Real x64 upload and real Rosetta smoke test against an actual x64 build — cannot be exercised in this plan since no x64 build exists yet"
    human_judgment: true
    rationale: "Sibling repo has not produced a real x86_64 Chromium.app (downloads-macos-x64.ini absent). This plan only proves the x86_64 code path is structurally correct (bash -n, arch -x86_64 present, long retry budget present) and that the mismatch guard rejects an arm64 bundle when --arch x86_64 is requested. Real end-to-end x64 verification is explicitly deferred to 02-04 per the plan's success_criteria."

# Metrics
duration: 20min
completed: 2026-07-24
status: complete
---

# Phase 2 Plan 1: macOS Kernel Verify+Upload Script Summary

**Idempotent bash verify-and-upload script (ditto round-trip → dual-binary lipo arch check → codesign sanity check → native/Rosetta CDP smoke test → gh release upload --clobber), proven end-to-end via --dry-run against the real sibling-repo arm64 build in ~17s.**

## Performance

- **Duration:** 20 min (includes an interactive tracer-feedback checkpoint pause)
- **Started:** 2026-07-24T23:xx (plan load)
- **Completed:** 2026-07-24T23:45:49-07:00 (Task 2 commit)
- **Tasks:** 2
- **Files modified:** 1 (new file)

## Accomplishments
- New `scripts/release/verify_and_upload_macos_kernel.sh` (first `scripts/` directory and first `.sh` file in the repo) implementing the full KERNEL-03 upload-gate pipeline: ditto round-trip → dual-binary `lipo -archs` check (launcher stub AND Framework binary, reached via the real `Versions/Current` symlink) → `codesign -dv` ad-hoc signature sanity check → CDP `/json/version` launch smoke test with architecture-dependent retry budgets.
- `--dry-run --arch arm64` ran end-to-end against the real, currently-available arm64 build in `../fingerprint-chromium/build/src/out/Default/Chromium.app` — exit 0, both `lipo -archs` lines report `arm64`, CDP smoke test passes with `149.0.7827.114`, no leftover process, total runtime ~16.75s (well under the 30s budget).
- `--dry-run --arch x86_64` against the same arm64 bundle correctly fails non-zero at the architecture-check stage with an `ARCH` mismatch message — negative self-test for the KERNEL-03 guard.
- x86_64 Rosetta smoke branch (`arch -x86_64` prefix, ~30×2s retry budget) and the `gh release upload kernel-149.0.7827.114 ... --clobber --repo ShengSoft-Tech/Open-Anti-Browser` step are structurally in place and `bash -n` valid; the upload step resolves its asset filename from `backend.config` constants at runtime (not present yet — added in 02-02 — but `--dry-run` never reaches that code path, so this plan's self-tests are unaffected).
- No token literals anywhere in the script (`GH_TOKEN`/`--token`/`ghp_` grep count is 0); relies entirely on the already-authenticated `gh auth login` session.
- Script confirmed NOT gitignored (`git check-ignore` produces no output) — correctly committed per D-11's kernel-release-tooling category.

## Task Commits

Each task was committed atomically:

1. **Task 1: arm64 内核 verify 流水线端到端(tracer,--dry-run 自测)** - `b432ebc` (feat)
2. **Task 2: x64 Rosetta 冒烟分支 + gh 上传步骤(横向扩展)** - `9ad3200` (feat)

_Task 1 is a `type="tracer"` task. Since neither `AUTO_CHAIN` nor `AUTO_CFG` was active, the execution protocol required stopping after Task 1's commit to return a `checkpoint:human-verify` on the proven tracer slice before beginning Task 2's expansion work. The coordinator approved the tracer slice and Task 2 proceeded._

## Files Created/Modified
- `scripts/release/verify_and_upload_macos_kernel.sh` - New idempotent verify+upload script: CLI (`<artifact-path>`, `--dry-run`, `--arch arm64|x86_64`), ditto-only extraction/packaging, dual-binary `lipo -archs` architecture assertions, `codesign -dv` sanity check, architecture-aware CDP smoke test (`smoke_test()`), and a `gh release upload --clobber` step gated off under `--dry-run` that resolves its asset name from `backend.config`.

## Decisions Made
- Upload asset is always re-staged at `$SCRATCH/$ZIP_NAME` (the config.py-resolved SSOT filename) before calling `gh release upload`, rather than uploading the input artifact under its own possibly-different local filename — guarantees the published GitHub asset name matches the SSOT constant exactly.
- `smoke_test()` was written once, parameterized by `$expected_arch` (retries/interval + the `arch -x86_64` launch prefix), rather than as two separate arch-specific functions — this meant Task 1's tracer implementation already contained the x86_64 retry-budget logic and Rosetta launch prefix; Task 2's actual new work was narrowly the `gh release upload` step itself.

## Deviations from Plan

None - plan executed exactly as written. Task 1's `smoke_test()` implementation happened to already include the x86_64 branch logic described for Task 2 (a natural side effect of writing one parameterized function instead of two), but this is a structural implementation detail, not a scope deviation — Task 2's acceptance criteria (gh upload step, SSOT filename resolution, no token literals, negative arch-mismatch self-test) were all delivered as specified.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. (`gh` CLI is already authenticated per RESEARCH.md; the script relies on that existing session, never a token literal.)

## Next Phase Readiness

- 02-02 can now backfill `backend/config.py` with `CHROME_ENGINE_ZIP_URL_MACOS_ARM64` / `CHROME_ENGINE_ZIP_URL_MACOS_X64` — this script's upload step already expects exactly those two constant names via `python3 -c "from backend.config import ..."`.
- 02-03 (arm64 real upload, human-gated checkpoint) can run this same script without `--dry-run` once the sibling repo's post-D-02 rebuild (LOG(INFO) calibration line removed) lands and 02-02's config.py constants exist.
- 02-04 (x64 real upload) can run the same script's x86_64 branch once the sibling repo produces an actual x64 build — the code path is structurally ready and self-tested for the mismatch-guard case, but has not been exercised against a real x86_64 binary (no such binary exists yet; this is an explicit, expected gap per RESEARCH.md Open Question 2).

---
*Phase: 02-macos*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: scripts/release/verify_and_upload_macos_kernel.sh
- FOUND: .planning/phases/02-macos/02-01-SUMMARY.md
- FOUND commit: b432ebc
- FOUND commit: 9ad3200
