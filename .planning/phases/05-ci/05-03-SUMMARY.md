---
phase: 05-ci
plan: 03
subsystem: infra
tags: [github-actions, macos, pyinstaller, codesign, create-dmg, ci]

# Dependency graph
requires:
  - phase: 05-ci (05-01)
    provides: "assets/app.icns and assets/dmg-background.png(+@2x) — consumed by pyinstaller --icon and create-dmg --background"
  - phase: 05-ci (05-02)
    provides: "launch_app.py macOS Cmd+Q interception and quarantine self-strip — packaged into the .app bundle built by this plan"
provides:
  - "build-macos job in .github/workflows/build-release.yml — end-to-end arm64 packaging path: kernel download -> pyinstaller .app -> Info.plist patch -> kernel injection -> layered ad-hoc codesign -> dual codesign --verify --deep --strict gate -> create-dmg -> dmg content verification -> upload-artifact"
  - "One real workflow_dispatch success (run 30394320282) with both build (windows) and build-macos jobs green in the same run, dmg downloaded and independently re-verified locally"
  - "Real-machine evidence for RESEARCH A2 (PySide6/QtWebEngine nested bundle structure), A3 (Qt LC_BUILD_VERSION minos=13.0), and A4 (create-dmg behavior on the real macos-15 sandbox session)"
affects: [05-04, 05-05, 05-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "build-macos job mirrors windows build job's checkout/setup/install/build-frontend steps verbatim (same requirements.txt/package.json), then diverges into an all-bash macOS-only tail (create-dmg install, kernel ditto/inject, plutil Info.plist patch, layered ad-hoc codesign, create-dmg, dmg content verify)"
    - "engines/chrome/ is a placeholder-only directory at build time (real kernel content lives in $RUNNER_TEMP, injected into Contents/Resources/engines/chrome/Chromium.app post-build via ditto) so PyInstaller's --add-data engines:engines only needs to establish the symlink structure, not copy a 400MB tree"
    - "Nested-bundle codesign step enumerates Qt/PySide6 bundles under Contents/Frameworks via recursive `find` (not a shallow glob) and signs by path-depth-descending order, excluding the already-signed kernel subtree"

key-files:
  created: []
  modified:
    - .github/workflows/build-release.yml

key-decisions:
  - "Windows build job left byte-for-byte unchanged; build-macos is a new sibling job under jobs:, verified via `git diff -U0 | grep '^-'` returning empty"
  - "Release publishing NOT added in this plan — build-macos only uploads the Open-Anti-Browser-macos-dmg artifact; the release job that gh-releases both platforms' artifacts together is D-02's scope, deferred to 05-05"
  - "Resolve version step reads frontend/package.json on non-tag (workflow_dispatch) triggers rather than falling back to a hardcoded 0.0.0, so manual test runs produce a real, traceable APP_VERSION (0.1.16 in both real runs)"
  - "[Rule 1 - Bug, mid-Task-2 auto-fix] Enumerate step's A2/A3 otool sampling originally globbed directly under Contents/Frameworks/Qt*.framework; real run 1 showed PySide6 6.9+ nests all Qt frameworks and QtWebEngineProcess.app under Contents/Frameworks/PySide6/Qt/lib/ instead, so the glob matched nothing. Fixed to use recursive `find` for QtCore/QtWidgets/QtWebEngineCore/QtWebEngineProcess.app, re-ran, captured real minos=13.0 data. The nested-bundle *signing* step was unaffected by this bug (it already used recursive find) — only the diagnostic sampling was silently empty in run 1."

patterns-established:
  - "macOS CI job diagnostic steps must resolve real PyInstaller/PySide6 output paths via `find`, never assume a flat Contents/Frameworks/*.framework layout — confirmed here that PySide6 6.9+ nests everything one level deeper under Contents/Frameworks/PySide6/Qt/lib/"

requirements-completed: [PKG-01, PKG-04]
# PKG-02/PKG-03 were already marked complete in 05-02-SUMMARY.md (launch_app.py Cmd+Q/quarantine logic);
# this plan closes PKG-01 (macOS job triggers and runs in parallel with the unmodified Windows job, both
# green in the same workflow_dispatch run) and PKG-04 (dmg contains .app + Applications alias + custom
# background, correctly named with version+arch, verified after mount both in CI and locally post-download).

coverage:
  - id: D1
    description: "build-macos job added to build-release.yml: kernel download -> pyinstaller .app -> Info.plist patch -> kernel injection -> layered ad-hoc codesign -> dual codesign --verify --deep --strict gate -> create-dmg -> dmg content verify -> upload-artifact, with Windows build job left completely untouched"
    requirement: "PKG-01"
    verification:
      - kind: other
        ref: "git diff -U0 .github/workflows/build-release.yml | grep '^-' returns empty (zero deletions/modifications to existing content); real workflow_dispatch run 30394320282 shows both `build` and `build-macos` jobs concluded success in the same run"
        status: pass
    human_judgment: true
    rationale: "The plan's own probe_assumptions section explicitly leaves the deeper 'parallelism/resource-contention/one-job-failing-affects-the-other' aspect of PKG-01 unresolved by design (no automated test can prove that, and 05-05's D-03 'all-succeed-or-no-release' policy is the indirect backstop) — the literal PKG-01 checklist text (macOS job triggers and runs parallel to the unmodified Windows job) is proven here, but a human should be aware the deeper resource-contention question remains an open assumption."
  - id: D2
    description: "dmg contains .app + /Applications alias + custom drag-install background (.background dir present) + is named Open-Anti-Browser-{version}-arm64.dmg; codesign --verify --deep --strict on both outer .app and inner Chromium.app passes after dmg mount, both in CI and on a local re-download"
    requirement: "PKG-04"
    verification:
      - kind: other
        ref: "CI job 90393404928 'Verify dmg contents' step: all four assertions pass, both codesign --verify --deep --strict calls exit 0; local re-verification after `gh run download` + `hdiutil attach` on this machine: both codesign calls exit 0 (see 'Local Round-Trip Verification' section below)"
        status: pass
    human_judgment: true
    rationale: "Automated checks cover file presence, naming, and signature validity, but the actual drag-install visual experience (background image legibility/alignment in a real Finder window, icon drop-target feel) can only be judged by a human — deferred to the 05-06 real-machine checkpoint per D-15."
  - id: D3
    description: "Real-machine evidence gathered for RESEARCH Assumptions A2 (PySide6/QtWebEngine nested bundle structure), A3 (Qt binaries' LC_BUILD_VERSION minos value), and A4 (create-dmg behavior under the real macos-15 CI sandbox session)"
    requirement: null
    verification:
      - kind: other
        ref: "CI job 90393404928 steps 'Enumerate nested bundles and minimum OS versions (A2/A3 diagnostics)' and 'Create dmg' — full logs captured and quoted in this SUMMARY"
        status: pass
    human_judgment: false

# Metrics
duration: 50min
completed: 2026-07-28
status: complete
---

# Phase 5 Plan 3: macOS build-macos CI Job — Packaging, Signing, DMG Summary

**Added a `build-macos` job (macos-15) to `.github/workflows/build-release.yml` that runs the full arm64 packaging tracer end-to-end — kernel download, PyInstaller `.app` build, Info.plist patch, layered ad-hoc codesign with a dual inner/outer verification gate, and `create-dmg` packaging — and validated it with two real `workflow_dispatch` runs, the second producing a clean pass after fixing a diagnostic-only bug found in the first.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-07-28T19:20:00Z (approx.)
- **Completed:** 2026-07-28T20:12:00Z
- **Tasks:** 2 completed (Task 1: job authoring; Task 2: real CI trigger + evidence gathering, including one mid-task Rule-1 fix and re-run)
- **Files modified:** 1 (`.github/workflows/build-release.yml`)

## Accomplishments
- `build-macos` job added as a new sibling to the existing `build` (Windows) job — zero changes to any existing line in the workflow (`git diff -U0 | grep '^-'` returns empty).
- End-to-end path implemented and proven on real infrastructure: kernel `ditto` download from `backend.config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64` (SSOT) → `pyinstaller --onedir --windowed --icon assets/app.icns --osx-bundle-identifier com.shengsoft.openantibrowser` → `plutil -replace` Info.plist patch (before any signing) → kernel injection via `ditto` into `Contents/Resources/engines/chrome/Chromium.app` → layered ad-hoc `codesign` (Chromium Helpers → Framework → Chromium.app → Qt/PySide6 nested bundles depth-descending → outer `.app`, no `--deep --sign` anywhere) → dual `codesign --verify --deep --strict` gate (outer + inner) → `create-dmg` → dmg content verification (post-mount) → `upload-artifact`.
- **Two real `workflow_dispatch` runs, both fully green**: run `30393410452` (first, found the diagnostic bug) and run `30394320282` (second, corrected). In both, `build` (Windows) and `build-macos` completed `success` in the same run, and Windows's `Create GitHub Release` step was `skipped` as expected (manual trigger, non-tag ref) — confirming zero Windows regression.
- Downloaded the produced dmg from run `30394320282`'s artifact, mounted it on this local arm64 Mac, and independently re-ran both `codesign --verify --deep --strict` checks — both exit 0, proving the signature survives the full CI-artifact-upload → download → mount round trip.
- Real-machine evidence captured for RESEARCH Assumptions A2, A3, and A4 (see dedicated section below) — all three were previously `[ASSUMED]`/`[Tertiary confidence]` in `05-RESEARCH.md`.

## Task Commits

Each task was committed atomically:

1. **Task 1: build-macos job — 内核 → .app → 签名 → dmg 端到端一条路径** - `304efff` (feat)
2. **Task 2 (mid-task Rule-1 auto-fix): recurse into PySide6/Qt/lib for A2/A3 diagnostic otool sampling** - `28f7388` (fix)

Task 2 itself is a real-infrastructure-trigger task (no additional file changes beyond the one fix commit above); its deliverable is the CI run evidence documented in this SUMMARY, not a code commit.

**Plan metadata:** _pending — this commit_

_Note: No TDD tasks in this plan (Task 1 is a tracer, Task 2 is a real-CI-trigger auto task); Task 2's only code change is the Rule-1 diagnostic-step fix committed as `28f7388`._

## Files Created/Modified
- `.github/workflows/build-release.yml` - Added `build-macos` job (lines 120-461 approx.); Windows `build` job and workflow header (`name:`/`on:`/`permissions:`) untouched.

## Local Round-Trip Verification

```
$ gh run download 30394320282 --name Open-Anti-Browser-macos-dmg --dir <scratchpad>/dmg-download
$ hdiutil attach -nobrowse -readonly -mountpoint <scratchpad>/local-mount <scratchpad>/dmg-download/Open-Anti-Browser-0.1.16-arm64.dmg
$ codesign --verify --deep --strict <mount>/Open-Anti-Browser.app
  -> exit code: 0
$ codesign --verify --deep --strict <mount>/Open-Anti-Browser.app/Contents/Resources/engines/chrome/Chromium.app
  -> exit code: 0
$ hdiutil detach <mount>
```

Mount contents confirmed: `Open-Anti-Browser.app`, `Applications -> /Applications` (symlink alias), `.background/` directory all present.

## Decisions Made
- Kept Task 1's Info.plist patch strictly limited to the three keys RESEARCH Pattern 3 identified as not auto-set by PyInstaller (`CFBundleShortVersionString`, `CFBundleVersion`, `LSMinimumSystemVersion`), rather than re-verifying the "already-set" list — real run confirmed the build succeeded with this minimal set.
- Nested-bundle signing step enumerates Qt/PySide6 bundles via `find "$APP/Contents/Frameworks" \( -name "*.app" -o -name "*.framework" \) -not -path "*/engines/*"` (recursive, excludes the already-handled kernel subtree) rather than a shallow directory glob — this was the correct choice from the start for *signing* (it worked in both runs); only the separate *diagnostic* otool-sampling loop had the shallow-glob bug (see Deviations).
- `hdiutil detach "/Volumes/Open-Anti-Browser $APP_VERSION" 2>/dev/null || true` used as a best-effort idempotent pre-clean before `create-dmg`, rather than a hard assertion — consistent with the plan's PKG-04 idempotency probe answer (ephemeral GH runners start clean, so this line is dead code on CI but protects a hypothetical local/self-hosted re-run).
- Did not add the `release` job (D-02) in this plan — the plan's own scope and acceptance criteria explicitly reserve that for 05-05; `build-macos` only does `upload-artifact`, matching the acceptance criterion that `softprops/action-gh-release` must NOT appear in the `build-macos` segment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A2/A3 diagnostic otool sampling glob matched zero Qt binaries**
- **Found during:** Task 2, after the first real `workflow_dispatch` run (`30393410452`) completed successfully but its "Enumerate nested bundles and minimum OS versions (A2/A3 diagnostics)" step log showed no `LC_BUILD_VERSION`/`minos` output at all — the loop over `"$FRAMEWORKS_DIR"/Qt*.framework "$FRAMEWORKS_DIR"/QtWebEngineProcess.app` silently matched nothing.
- **Issue:** The step assumed Qt frameworks and `QtWebEngineProcess.app` live directly under `Contents/Frameworks/`. The same run's "嵌套 bundle 枚举" (which uses recursive `find`, not a glob) proved the real layout: PySide6 6.9+ places ~110 `Qt*.framework` bundles and the single `QtWebEngineProcess.app` under `Contents/Frameworks/PySide6/Qt/lib/` — one directory level deeper than assumed. RESEARCH's Open Question 2 ("PySide6/QtWebEngine 嵌套 bundle 的实际签名结构是否与 Chromium.app 一致") is answered by this: the *kind* of nesting is the same (one `.app` inside a framework's `Helpers/` dir), but the *path depth* differs from a naive top-level assumption.
- **Fix:** Rewrote the sampling loop to use `find "$APP/Contents/Frameworks" -name "<Target>" -print -quit` for four representative binaries (QtCore, QtWidgets, QtWebEngineCore, QtWebEngineProcess.app), matching the same recursive-search discipline the (already-correct) signing step used.
- **Files modified:** `.github/workflows/build-release.yml`
- **Verification:** Re-triggered `workflow_dispatch` (run `30394320282`); the corrected step's log now shows all four binaries with `minos 13.0` — see "RESEARCH Assumptions Validated" below.
- **Committed in:** `28f7388`

**Important note on scope:** This bug only affected the *diagnostic* step's own output (a warning-free but silently-empty log section) — it did NOT affect packaging correctness. The *signing* step (`Sign nested bundles and app`) already used recursive `find` from the start and correctly signed all ~110 Qt frameworks plus `QtWebEngineProcess.app` in both runs, as proven by the `codesign --verify --deep --strict` outer-app gate passing in run 1 already.

---

**Total deviations:** 1 auto-fixed (1 bug, diagnostic-only, zero packaging/signing impact)
**Impact on plan:** No scope creep. Both runs of `build-macos` fully succeeded; the fix only improved the fidelity of A2/A3 evidence gathering, which Task 2's acceptance criteria explicitly requires.

## Issues Encountered

None beyond the one auto-fixed diagnostic bug above. Both real `workflow_dispatch` runs completed on the first attempt at every packaging/signing/dmg step — no `codesign` failures, no `create-dmg` failures, no `_g.py`-style startup rejection observed (Task 1's job doesn't run a `--backend-only` smoke test — that's D-14 item 4, scoped to a later plan per the plan's own task list, which only covers Task 1's listed steps).

## RESEARCH Assumptions Validated (A2 / A3 / A4)

### A2 — PySide6/QtWebEngine nested bundle structure (previously `[ASSUMED]`, LOW confidence)

Real structure captured from `dist/Open-Anti-Browser.app` (job `90393404928`, "Enumerate nested bundles" step, full `find` output):

- **~110 independent `Qt*.framework` bundles**, all under `Contents/Frameworks/PySide6/Qt/lib/` (e.g. `Qt3DAnimation.framework` ... `QtWidgets.framework`), **not** directly under `Contents/Frameworks/` as the RESEARCH document's structural analogy to Chromium assumed.
- **Exactly one nested `.app`**: `Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework/Versions/A/Helpers/QtWebEngineProcess.app` — structurally analogous to Chromium's `Helper.app` pattern (one process-launcher `.app` nested inside a framework's `Helpers/` directory), confirming RESEARCH Open Question 2's expectation that the *kind* of nesting matches Chromium's, even though the *path depth* differs.
- A duplicate top-level `Python.framework` also appears at both `Contents/Frameworks/Python.framework` and `Contents/Resources/Python.framework` (PyInstaller's standard symlink-pair layout, unrelated to Qt).
- **Signing conclusion:** because the "Sign nested bundles" step used recursive `find -not -path "*/engines/*"` (not a shallow glob) from the start, it correctly caught and signed all of the above in both runs — proven by the outer `.app`'s `codesign --verify --deep --strict` passing. **A2 is now resolved**: the Chromium-analogy signing approach works for the real PySide6 layout without modification, but any future diagnostic/inspection tooling must search recursively, not assume a flat `Contents/Frameworks/*.framework` layout (see the Rule-1 fix above).

### A3 — `LSMinimumSystemVersion` real value (previously `[ASSUMED]` 12.0, LOW confidence)

`otool -l | grep -A3 LC_BUILD_VERSION` on four representative Qt binaries (run `30394320282`, corrected diagnostic step):

```
--- dist/Open-Anti-Browser.app/Contents/Frameworks/PySide6/Qt/lib/QtCore.framework/Versions/Current/QtCore ---
      cmd LC_BUILD_VERSION
  cmdsize 32
 platform 1
    minos 13.0
--- dist/Open-Anti-Browser.app/Contents/Frameworks/PySide6/Qt/lib/QtWidgets.framework/Versions/Current/QtWidgets ---
    minos 13.0
--- dist/Open-Anti-Browser.app/Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework/Versions/Current/QtWebEngineCore ---
    minos 13.0
--- .../QtWebEngineCore.framework/Versions/A/Helpers/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess ---
    minos 13.0
```

**A3 is now resolved with a concrete, actionable finding: the real minimum is `13.0` (macOS Ventura), not the `12.0` (Monterey) this plan's Info.plist patch currently writes.** This plan intentionally left `LSMinimumSystemVersion` at the RESEARCH-recommended placeholder value of `12.0` per the plan's own scoping ("A3 未验证,05-04 会加一道 otool -l 断言把它核销") — **05-04 must update the hardcoded `"12.0"` string to `"13.0"` (or derive it from this otool measurement) and add the hard assertion the plan text anticipates**, otherwise the shipped `Info.plist` will understate the app's real minimum OS requirement and could let it install on macOS 12.x where QtWebEngine/QtWidgets would fail to load.

### A4 — `create-dmg` behavior under the real macos-15 CI sandbox session (previously `[Tertiary confidence]`, unverified on real GH runner)

Full `Create dmg` step log (run `30394320282`, job `90393404928`):

```
2 images written to /Users/runner/work/_temp/dmg-background.tiff.
Creating disk image...
created: .../rw.8792.Open-Anti-Browser-0.1.16-arm64.dmg
Mounting disk image...
Copying background file '/Users/runner/work/_temp/dmg-background.tiff'...
Making link to Applications dir...
Will sleep for 5 seconds to workaround occasions "Can't get disk (-1728)" issues...
Running AppleScript to make Finder stuff pretty: /usr/bin/osascript ...
waited 1 seconds for .DS_STORE to be created.
Done running the AppleScript...
Fixing permissions...
Done fixing permissions
Skipping blessing on sandbox
Deleting .fseventsd
Unmounting disk image...
"disk6" ejected.
Compressing disk image...
...
created: .../Open-Anti-Browser-0.1.16-arm64.dmg
Not setting 'internet-enable' on the dmg, per caller request
Disk image done
create-dmg 成功产出: Open-Anti-Browser-0.1.16-arm64.dmg
```

**A4 is now resolved: `create-dmg` completes fully and successfully on the real GitHub Actions `macos-15` runner, exit code 0.** The `"Skipping blessing on sandbox"` line RESEARCH flagged as a possible degradation signal did appear (confirming the CI session is indeed sandboxed relative to a full interactive desktop), but it is a **non-fatal, expected skip** — the AppleScript step completed ("Done running the AppleScript..."), the background image and Applications link were both applied, and the final dmg was produced and later verified (both in-CI and locally) to contain all required elements with intact signatures. No AppleScript permission errors occurred. The step's "don't swallow the exit code" design (per the plan's explicit instruction) worked as intended — if `create-dmg` had failed, the `set -euo pipefail` script would have aborted before printing the success line, and it did not.

### Inject Chrome kernel — symlink assertion outcome

`Contents/Frameworks/engines` was found to already be a symlink to `../Resources/engines` in both real runs (the success branch, not the fallback-and-build branch):

```
断言通过: dist/Open-Anti-Browser.app/Contents/Frameworks/engines 是符号链接 -> ../Resources/engines
```

The "偏离告示 - 不是符号链接，显式补建" fallback branch was **not** triggered — confirming RESEARCH Pattern 1's finding holds on the real macos-15 runner exactly as it did on the researcher's local machine.

## User Setup Required

None - no external service configuration required. All steps run entirely within the existing GitHub Actions `macos-15` runner using tools already available (Homebrew, system `codesign`/`plutil`/`otool`/`hdiutil`/`ditto`) or fetched via `brew install create-dmg` (already audited OK in `05-RESEARCH.md`'s Package Legitimacy Audit).

## Next Phase Readiness

- `build-macos` job is live, proven twice on real infrastructure, and produces a downloadable, doubly-signed-and-verified dmg artifact (`Open-Anti-Browser-macos-dmg`, glob `Open-Anti-Browser-*-arm64.dmg`).
- **Actionable finding for 05-04:** `LSMinimumSystemVersion` should be bumped from the placeholder `"12.0"` to the measured `"13.0"` (or derived from a fresh `otool -l` assertion at build time) — see A3 section above. This is the primary carry-forward item.
- **Actionable finding for 05-04 (version-consistency step, D-08):** this plan's `Resolve version` step only takes the version value (tag or `package.json` fallback); it does not yet cross-check against `backend/main.py`'s two `version=` FastAPI fields. RESEARCH's "版本一致性校验" Code Example is available and unused by this plan — 05-04 is the plan scoped to add it.
- 05-05 can now add the `release` job (D-02) that downloads both `Open-Anti-Browser-Setup` (Windows) and `Open-Anti-Browser-macos-dmg` (macOS) artifacts and publishes them to a single GitHub Release — this plan intentionally left both build jobs artifact-only, matching D-02's required shape.
- 05-06's real-machine checkpoint can now download an actual CI-produced dmg (this plan proved the download+mount+codesign round trip works) to test the full drag-install and first-launch Gatekeeper/quarantine experience.
- No blockers. `assets/app.icns` and `assets/dmg-background.png`(+@2x) from 05-01 render correctly in the real dmg (background image was applied without error per the A4 log above); `launch_app.py`'s Cmd+Q/quarantine logic from 05-02 is packaged into the `.app` bundle by this job's PyInstaller step (not yet exercised at runtime — that's 05-06's job).

---
*Phase: 05-ci*
*Completed: 2026-07-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/05-ci/05-03-SUMMARY.md`
- FOUND: `.github/workflows/build-release.yml`
- FOUND: commit `304efff` (Task 1)
- FOUND: commit `28f7388` (Task 2 Rule-1 fix)
