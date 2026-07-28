---
phase: 05-ci
plan: 05
subsystem: infra
tags: [github-actions, release, softprops-action-gh-release, download-artifact, ci]

# Dependency graph
requires:
  - phase: 05-ci (05-03)
    provides: "build-macos job producing Open-Anti-Browser-macos-dmg artifact (upload-artifact only, no release call)"
  - phase: 05-ci (05-04)
    provides: "build-macos hard gates (version consistency, arch/dist/min-os, smoke test) — both build jobs proven green on real workflow_dispatch runs, giving this plan a stable baseline to diff against"
provides:
  - "release job in .github/workflows/build-release.yml — needs: [build, build-macos], tag-gated, downloads both artifacts via download-artifact merge-multiple, asserts both present, then calls softprops/action-gh-release@v2 exactly once for the whole workflow"
  - "windows build job's former inline Create GitHub Release step removed — build job now ends at Upload installer artifact; construction logic (checkout/setup/pip/npm/Fetch-Engine/pyinstaller/Inno Setup/upload-artifact) verified byte-for-byte unchanged"
  - "Real workflow_dispatch regression run (30402103536): build=success, build-macos=success, release=skipped, zero new GitHub Release created, Windows artifact confirmed downloadable at matching order-of-magnitude size"
affects: [05-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single release-publishing job pattern: multiple platform build jobs upload-artifact only; a lone downstream job (needs: [...all build jobs], tag-gated) does download-artifact --pattern --merge-multiple to a common directory, asserts completeness, then makes the one softprops/action-gh-release call for the entire workflow — eliminates concurrent-release races structurally (invariant: count(gh-release calls) == 1) rather than via locking/coordination"

key-files:
  created: []
  modified:
    - .github/workflows/build-release.yml

key-decisions:
  - "release job placed as third top-level sibling to build/build-macos (not nested under either), runs-on: ubuntu-latest since it only downloads artifacts and calls an action — no platform-specific tooling needed"
  - "release job does not declare its own permissions: block — relies on the workflow-level permissions: contents: write already declared at :9-10, avoiding a second declaration site for the one permission this workflow grants"
  - "Workflow top-level name:/on:/permissions: (lines 1-10) deliberately left unchanged despite name: still reading as Windows-only — renaming risks silently breaking any branch-protection rule that references a 'workflow / job' required-status-check context; documented here as the intentional non-change per plan's own explicit instruction"
  - "release-assets completeness assertion (Windows .exe + arm64 .dmg) placed as its own step before Create GitHub Release, so a partial artifact set fails loudly (non-zero exit) rather than producing a Release missing one platform's asset"

requirements-completed: [PKG-01, PKG-05]

coverage:
  - id: D1
    description: "release job added: needs: [build, build-macos] (all-succeed-or-skip gate, D-03), if: startsWith(github.ref, 'refs/tags/') (D-04 workflow_dispatch debug channel preserved), downloads both artifacts via merge-multiple, hard-asserts both Windows .exe and macOS arm64 .dmg present, calls softprops/action-gh-release@v2 exactly once for the whole workflow"
    requirement: "PKG-05"
    verification:
      - kind: other
        ref: "Local structural assertion (python3 -c ...) confirms softprops/action-gh-release count==1, release: job present, needs:/merge-multiple present, no softprops inside build job segment; git diff -U0 deletion lines are exactly the 8 lines of the old windows Create GitHub Release step; grep -c continue-on-error and if: always() both 0; release: segment contains no permissions:"
        status: pass
      - kind: other
        ref: "Real workflow_dispatch run 30402103536: build=success, build-macos=success, release=skipped (tag-gate correctly not satisfied on manual trigger); gh release list --limit 5 confirms zero new Release created"
        status: pass
    human_judgment: false
  - id: D2
    description: "Windows build job's former Create GitHub Release step removed with zero regression to the remaining construction logic (checkout/setup/pip install/npm build/Fetch-Engine/pyinstaller/Inno Setup/upload-artifact all byte-for-byte unchanged); confirmed via full step-name+conclusion list diff against the 05-03 baseline run"
    requirement: "PKG-01"
    verification:
      - kind: other
        ref: "gh run view 30402103536 --json jobs (build job step list) diffed item-by-item against gh run view 30393410452 --json jobs (05-03 baseline) — see 'Windows build job step comparison' section below"
        status: pass
      - kind: other
        ref: "gh run download 30402103536 --name Open-Anti-Browser-Setup — Open-Anti-Browser-Setup.exe retrieved successfully, 399,812,642 bytes vs 05-03 baseline's 399,368,819 bytes (same order of magnitude, +0.11%)"
        status: pass
    human_judgment: true
    rationale: "D-02 was rated costly reversibility because the affected path is the live v0.1.x Windows release channel and any regression would only surface at a real tag push. Automated checks prove step-list/artifact-size parity for this run, but full confidence in the production release path (the release job's actual softprops/action-gh-release call under a real tag ref) requires the milestone owner's sign-off before the next real v* tag push, since that exact code path is structurally impossible to exercise via workflow_dispatch (D-04's tag guard skips it by design)."

# Metrics
duration: 15min
completed: 2026-07-28
status: complete
---

# Phase 5 Plan 5: Release Job Consolidation (D-02) Summary

**Added a single downstream `release` job that gh-releases both platforms' artifacts together, removed the Windows `build` job's inline `Create GitHub Release` step, and proved zero regression to the Windows release channel on a real `workflow_dispatch` run (`build`=success, `build-macos`=success, `release`=skipped, no new Release created).**

## Performance

- **Duration:** ~15 min active work (Task 1 authoring was already present uncommitted in the working tree at session start; this plan's active work was verification, commit, and the real CI trigger/evidence-gathering cycle)
- **Started:** 2026-07-28T21:47:33Z (Task 1 commit `e1a4ea9`)
- **Completed:** 2026-07-28T21:59:32Z
- **Tasks:** 2 completed
- **Files modified:** 1 (`.github/workflows/build-release.yml`)

## Accomplishments

- New `release` job (`runs-on: ubuntu-latest`, `needs: [build, build-macos]`, `if: startsWith(github.ref, 'refs/tags/')`) downloads both platform artifacts into a common `release-assets/` directory via `actions/download-artifact@v4` with `pattern: 'Open-Anti-Browser-*'` + `merge-multiple: true`, hard-asserts both the Windows installer and the macOS arm64 dmg are present (non-zero exit if either is missing), then calls `softprops/action-gh-release@v2` exactly once for the entire workflow — structurally eliminating the two-jobs-both-call-gh-release race (T-05-20).
- Windows `build` job's inline `Create GitHub Release` step (the original `:112-119`) removed in its entirety — the job now ends at `Upload installer artifact`. All other steps (checkout, setup-python, setup-node, pip install, npm build, `Prepare browser engines`/`Fetch-Engine`, pyinstaller, Inno Setup, upload-artifact) left byte-for-byte unchanged, confirmed by `git diff -U0` showing exactly those 8 deleted lines and nothing else.
- Any build-job failure blocks the Release (D-03): `needs: [build, build-macos]` is the sole gating mechanism, with zero `continue-on-error` or `if: always()` anywhere in the file.
- `workflow_dispatch` debug channel fully preserved (D-04): on a manual trigger, `release` is `skipped` (not failed), while both build jobs run to completion and upload their artifacts normally.
- Real regression run (`30402103536`) proves all of the above on live infrastructure — see full evidence sections below.

## Task Commits

Each task was committed atomically:

1. **Task 1: 新增 release 汇合 job 并把 Windows 发布步骤移出 build job(D-02 / D-03 / D-04)** - `e1a4ea9` (feat)
2. **Task 2: workflow_dispatch 回归验证** - no additional code commit (verification-only task; its deliverable is the real CI run evidence documented in this SUMMARY)

**Plan metadata:** _pending — this commit_

## Files Created/Modified

- `.github/workflows/build-release.yml` - Removed windows `build` job's inline `Create GitHub Release` step (8 lines); added new `release` job (37 new lines) as third top-level sibling job with `needs: [build, build-macos]`, tag guard, artifact download/merge/assert, and the single `softprops/action-gh-release@v2` call.

## Decisions Made

- Kept `release` job's permissions implicit (relies on workflow-level `permissions: contents: write` at `:9-10`) rather than re-declaring on the job — avoids a second source of truth for the one permission this workflow needs.
- Left the workflow's top-level `name: Build & Release Windows Installer` unchanged even though it no longer accurately describes the workflow (it now also builds/releases macOS) — renaming risks silently breaking a branch-protection rule keyed on the `workflow / job` required-status-check context, which is a pure observational drawback with zero functional upside. Recorded here per the plan's explicit instruction to document this trade-off rather than fix it.
- `release-assets` completeness assertion (`Open-Anti-Browser-Setup.exe` + `Open-Anti-Browser-*-arm64.dmg` both present) is its own dedicated step ahead of `Create GitHub Release`, so a partial artifact set — e.g. one platform's `upload-artifact` silently producing an empty archive — fails the run loudly instead of producing a Release with only one platform's asset attached.

## Deviations from Plan

None - plan executed exactly as written. (Task 1's code changes were found already present, uncommitted, in the working tree at the start of this execution session — content was verified against every one of Task 1's acceptance criteria before being staged and committed as-is; no code was altered from what the plan specified.)

## Issues Encountered

None. Both the local structural verification and the real `workflow_dispatch` run passed on the first attempt — no re-push/re-trigger iteration was needed.

## Windows `build` Job Step Comparison (05-03 Baseline vs This Run)

**Baseline** — `gh run view 30393410452 --json jobs` (05-03's `workflow_dispatch` run), `build` job steps:

```
1  Set up job                                          success
2  Checkout                                             success
3  Set up Python 3.11                                   success
4  Set up Node.js 20                                    success
5  Install Python dependencies                          success
6  Build frontend                                       success
7  Prepare browser engines                              success
8  Build app with PyInstaller (onedir, engines bundled)  success
9  Build installer with Inno Setup                       success
10 Upload installer artifact                             success
11 Create GitHub Release                                 skipped   <- removed by this plan
20 Post Set up Node.js 20                                success
21 Post Set up Python 3.11                               success
22 Post Checkout                                          success
23 Complete job                                           success
```

**This run** — `gh run view 30402103536 --json jobs` (this plan's `workflow_dispatch` regression run), `build` job steps:

```
1  Set up job                                          success
2  Checkout                                             success
3  Set up Python 3.11                                   success
4  Set up Node.js 20                                    success
5  Install Python dependencies                          success
6  Build frontend                                       success
7  Prepare browser engines                              success
8  Build app with PyInstaller (onedir, engines bundled)  success
9  Build installer with Inno Setup                       success
10 Upload installer artifact                             success
18 Post Set up Node.js 20                                success
19 Post Set up Python 3.11                               success
20 Post Checkout                                          success
21 Complete job                                           success
```

**Conclusion: the ONLY difference is the removed `Create GitHub Release` step (step 11 in the baseline, which was already `skipped` there since that too was a `workflow_dispatch` run).** Every remaining step name and its relative order is identical between the two runs (the later `Post *`/`Complete job` step numbers shift down by one purely because the removed step's number is no longer allocated — this is GitHub Actions' own sequential step numbering, not a reordering). Zero regression to the Windows construction/upload path.

## Job Conclusions (Real Run 30402103536)

| Job | Conclusion | startedAt | completedAt |
|-----|-----------|-----------|--------------|
| `build-macos` | success | 2026-07-28T21:47:54Z | 2026-07-28T21:53:19Z |
| `build` | success | 2026-07-28T21:48:04Z | 2026-07-28T21:57:05Z |
| `release` | **skipped** | 2026-07-28T21:57:06Z | 2026-07-28T21:57:06Z |

`release`'s `startedAt`/`completedAt` are identical (instantaneous) because a skipped job records no execution time — it evaluated its `needs:`/`if:` gate immediately once both upstream jobs reported a conclusion, correctly found the manual (`workflow_dispatch`) ref does not satisfy `startsWith(github.ref, 'refs/tags/')`, and skipped without running any step. This is D-04's exact intended behavior.

## Parallelism Evidence (PKG-01)

`build-macos` (`startedAt` 21:47:54) and `build` (`startedAt` 21:48:04) started 10 seconds apart and ran concurrently for their full duration — `build-macos` finished at 21:53:19 while `build` was still in progress (it continued to 21:57:05). This is direct evidence the two platform build jobs execute in parallel, not sequentially, consistent with 05-03's original PKG-01 finding and unaffected by this plan's changes.

## Windows Artifact Download Confirmation

```
$ gh run download 30402103536 --name Open-Anti-Browser-Setup --dir <scratchpad>/05-05-artifact-current
$ ls -la <scratchpad>/05-05-artifact-current
-rw-r--r--  1 fanjin  wheel  399812642  Open-Anti-Browser-Setup.exe
```

Compared against the 05-03 baseline run's same-named artifact (retrieved via `gh api repos/:owner/:repo/actions/runs/30393410452/artifacts`): `399,368,819` bytes. Current run: `399,812,642` bytes — a difference of 443,823 bytes (+0.11%), same order of magnitude. Consistent with normal build-to-build variance (embedded timestamps/compression nondeterminism in the PyInstaller/Inno Setup toolchain); no structural regression indicated.

## Release List Confirmation (No New Release Created)

```
$ gh release list --limit 5
Open-Anti-Browser v0.1.16    Latest    v0.1.16                    2026-07-25T01:16:10Z
Open-Anti-Browser v0.1.15              v0.1.15                    2026-07-13T09:05:10Z
Open-Anti-Browser v0.1.14              v0.1.14                    2026-07-08T03:28:10Z
Fingerprint-Chromium kernel 149.0.7827.114    kernel-149.0.7827.114    2026-07-08T03:16:15Z
Open-Anti-Browser v0.1.13              v0.1.13                    2026-06-22T21:22:54Z
```

`v0.1.16` (2026-07-25) remains the latest Release — unchanged from before this plan's manual trigger, confirming the `release` job's `skipped` conclusion produced zero side effects on GitHub Releases.

## Local Structural Verification (Re-confirmed on Pushed Commit `e1a4ea9`)

```
$ python3 -c "t=open('.github/workflows/build-release.yml',encoding='utf-8').read();import re;assert t.count('softprops/action-gh-release')==1;assert re.search(r'^  release:',t,re.M);assert 'needs: [build, build-macos]' in t;assert 'merge-multiple: true' in t;b=t[t.index('  build:'):t.index('  build-macos:')];assert 'softprops' not in b;assert b.rstrip().endswith(\"if-no-files-found: error\");print('OK')"
OK
$ git diff -U0 0462c2d e1a4ea9 -- .github/workflows/build-release.yml | grep '^-' | grep -v '^---'
-      - name: Create GitHub Release
-        if: startsWith(github.ref, 'refs/tags/')
-        uses: softprops/action-gh-release@v2
-        with:
-          files: installer_out/Open-Anti-Browser-Setup.exe
-          generate_release_notes: true
-          name: "Open-Anti-Browser ${{ github.ref_name }}"
(8 lines total including trailing blank — exactly the removed step)
$ grep -c 'continue-on-error' .github/workflows/build-release.yml   # 0
$ grep -c 'if: always()' .github/workflows/build-release.yml        # 0
$ python3 -c "... 'permissions:' in release_job_segment ..."        # False
$ gh workflow view build-release.yml                                # exit 0 (YAML parses; local .venv lacks pyyaml, fallback used per environment note)
```

All Task 1 acceptance criteria confirmed against the actual pushed commit, not just the working-tree state prior to commit.

## User Setup Required

None - no external service configuration required. All verification used tools already authenticated in this environment (`gh` CLI, already-logged-in GitHub account with `repo` scope).

## Residual Risk (Explicitly Accepted Per Plan's Verification Boundary)

**The `release` job's actual publish path (the `softprops/action-gh-release@v2` call executing under a real tag ref) was never exercised by this plan's verification.** Verification was intentionally limited to `workflow_dispatch` triggers, per this plan's authorized scope — pushing a `v*` tag to test the real path is explicitly prohibited (a real tag push triggers an actual user-facing release). Under `workflow_dispatch`, the `release` job's `if: startsWith(github.ref, 'refs/tags/')` guard is never satisfied, so it always evaluates to `skipped` by design (D-04) — this skip behavior IS the acceptance criterion this plan proves, not a gap in it.

**Consequence:** the `release` job's actual `download-artifact` → completeness-assert → `softprops/action-gh-release` sequence, running end-to-end and actually publishing a Release, will first execute on the user's next real `v*` tag push (e.g. the eventual `v0.2.0` release). Everything short of that final live execution has been proven here (job wiring, gating logic, artifact completeness assertion logic, structural correctness of the `softprops` call's parameters carried over verbatim from the removed Windows step). The milestone owner should treat that first real tag push as the final, unavoidable confirmation point for D-02.

## Next Phase Readiness

- `release` job is live and proven to gate/skip correctly on `workflow_dispatch`; both build jobs remain fully green and unaffected.
- All five PKG requirements (PKG-01 through PKG-05) are now traced to Phase 5 plans and structurally complete; the one remaining unverified path is the real-tag publish flow (see Residual Risk above), which is out of this plan's authorized scope and will be exercised naturally at the project's next real release.
- 05-06 (the phase's remaining plan, if any real-machine/documentation work remains — see PROJECT.md's "Active" checklist item on release notes with unsigned-app first-open steps) can proceed; no blockers from this plan.
- Before the actual `v0.2.0` tag push (not this plan's task, reminder carried from 05-04's SUMMARY): `frontend/package.json` and `backend/main.py`'s two `version=` fields must all match the tag, or the `Resolve version` step will correctly fail the tag-triggered build by design.

---
*Phase: 05-ci*
*Completed: 2026-07-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/05-ci/05-05-SUMMARY.md`
- FOUND: commit `e1a4ea9` (Task 1)
