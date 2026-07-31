---
phase: 06-release-docs
plan: 05
subsystem: release-infra
tags: [github-actions, release, softprops-action-gh-release, gatekeeper, uat, documentation]

# Dependency graph
requires:
  - phase: 06-release-docs (06-04)
    provides: "Release notes template wired into release job via body_path, all copy surfaces (release template, in-app i18n, dmg background) aligned on the measured 再双击一次 flow"
  - phase: 05-ci (05-05)
    provides: "release job structure (needs: [build, build-macos], tag-gated, single softprops/action-gh-release call) — this plan is the first time it has ever run against a real tag"
provides:
  - "Real v0.2.0 tag pushed and its release job observed executing (success, not skipped) for the first time ever"
  - "Discovery and fix of a real defect: the release job had no actions/checkout step, so body_path: .github/RELEASE_NOTES_TEMPLATE.md pointed at a file that did not exist on the runner — softprops/action-gh-release silently dropped it instead of failing, and the first v0.2.0 Release was published with ONLY the auto-generated changelog line, none of the hand-written documentation"
  - "Fixed release job (checkout step added, commit 524aeb1) for future tag pushes; current v0.2.0 Release body manually corrected via gh release edit so the live page carries the intended documentation"
  - "05-ci Phase 5's pending real-tag-push UAT item closed as pass"
affects: [06-05 Task 3 (clean-account human verification, not yet executed)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "release job requires its own actions/checkout step to read any repo-committed file via body_path — download-artifact/softprops-only jobs do not implicitly have repo contents on the runner"

key-files:
  created: []
  modified:
    - frontend/package.json
    - backend/main.py
    - .github/workflows/build-release.yml
    - .planning/phases/05-ci/05-UAT.md

key-decisions:
  - "Task 1 checkpoint:decision resolved by the developer before this execution began: option-a (push a real v0.2.0 tag and verify against the published Release), not option-b (workflow_dispatch artifact). Only the option-a branch of Task 2 was executed; the option-b branch was never touched."
  - "The missing-checkout bug was fixed in the workflow (Rule 1 — auto-fix bug found during task execution) WITHOUT pushing a second tag, per the plan's explicit one-way-door instruction. The fix is committed to main and will first be exercised by CI on the next real tag push — it is not yet proven by an actual automated run."
  - "The already-published v0.2.0 Release's body was hand-corrected via `gh release edit --notes-file` (template content + the previously-fetched auto-changelog line, in that order) rather than left broken, because Task 3's clean-account verifier needs a usable Release page to read as 'shipped documentation' — an empty/near-empty Release page would make Task 3 unexecutable as specified."

requirements-completed: []  # DOCS-01/DOCS-02 remain unresolved per plan's flagged_assumptions — Task 3 (not yet run) is what would close them

coverage:
  - id: D1
    description: "Version bumped 0.1.16 -> 0.2.0 in frontend/package.json and both backend/main.py version= fields, verified locally with scripts/release/check_version_consistency.py before pushing the tag"
    requirement: null
    verification:
      - kind: other
        ref: "python3 scripts/release/check_version_consistency.py v0.2.0 true -> printed '0.2.0', exit 0"
        status: pass
      - kind: other
        ref: "grep -c '\"version\": \"0.2.0\"' frontend/package.json == 1; grep -c 'version=\"0.2.0\"' backend/main.py == 2"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real v0.2.0 annotated tag pushed exactly once; build, build-macos, and release jobs all ran and all succeeded (release transitioned from its permanent skipped state to success for the first time)"
    requirement: null
    verification:
      - kind: other
        ref: "gh run view 30656303074 --json jobs -> build-macos: success, build: success, release: success"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Release body's actual rendering was observed, found broken (body_path content entirely absent, not merely mis-ordered), root-caused (release job missing actions/checkout), fixed in the workflow, and the live Release corrected"
    requirement: null
    verification:
      - kind: other
        ref: "gh release view v0.2.0 --json body before fix == only '**Full Changelog**: ...' line; after gh release edit, body opens with the template's 系统要求 section and ends with the same changelog line"
        status: pass
    human_judgment: true
    rationale: "Whether the manually-reconstructed body faithfully represents what the FIXED workflow will actually produce on the next real tag push is not itself verified by an automated CI run — a human/maintainer judgment call to accept the hand-assembled body as an interim substitute is implicit here."
  - id: D4
    description: "05-ci Phase 5's pending real-tag-push UAT test 1 updated from [pending] to [pass] with run id, job conclusions, and Release URL"
    requirement: null
    verification:
      - kind: other
        ref: ".planning/phases/05-ci/05-UAT.md test 1 result: [pass], evidence section names run 30656303074 and https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/tag/v0.2.0"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-07-31
status: in-progress
---

# Phase 6 Plan 5: Real v0.2.0 Tag Push, Release Body Defect Found and Fixed, UAT Closed (Tasks 1-2) Summary

**Pushed the milestone's real `v0.2.0` tag per the developer's explicit option-a decision; this exposed a genuine, previously-unexercisable defect — the `release` job had no `actions/checkout` step, so its `body_path` reference to the hand-written release-notes template silently resolved to nothing and the first-published Release contained only the auto-generated changelog. Fixed the workflow and hand-corrected the live Release, then closed Phase 5's year-old pending UAT item. Task 3 (clean-account human verification) has not been executed — this plan stops at that checkpoint.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-31T18:32:33Z
- **Completed (Tasks 1-2 only):** 2026-07-31T19:10Z (approx)
- **Tasks:** 2 of 3 completed (Task 3 is a `checkpoint:human-verify` requiring a real macOS machine and a new user account — not executable by this agent)
- **Files modified:** 4

## Task 1: Decision (already resolved before this run)

**Selected option: option-a — push a real `v0.2.0` tag and verify against the published GitHub Release.**

This decision was made by the developer at the `checkpoint:decision` gate *before* this execution session began and *before* any tag existed, per the orchestrator's `<resolved_decision_checkpoint>` instructions. This executor did not re-ask the question and did not execute any part of the option-b branch (no `workflow_dispatch` was triggered, no artifact was downloaded as a substitute). Everything below is the option-a branch only.

## Task 2: Acquire the dmg via the real Release, and confirm `body_path` rendering (option-a branch only)

### Version bump

`frontend/package.json` and both `backend/main.py` `version=` fields moved from `0.1.16` to `0.2.0`. Verified locally before any push:

```
$ python3 scripts/release/check_version_consistency.py v0.2.0 true
版本一致: 0.2.0
0.2.0            # exit 0
$ grep -c '"version": "0.2.0"' frontend/package.json   # 1
$ grep -c 'version="0.2.0"' backend/main.py            # 2
```

Committed as `95850b0` (`chore(release): bump version to 0.2.0`) and pushed to `main`.

### Tag push and CI run

```
$ git tag -a v0.2.0 -m "Open-Anti-Browser v0.2.0" 95850b0
$ git push origin v0.2.0
 * [new tag]         v0.2.0 -> v0.2.0
```

Run `30656303074` (event: `push`, `headBranch: v0.2.0`), watched to completion:

| Job | Conclusion | Started | Completed |
|-----|-----------|---------|-----------|
| `build-macos` | success | 2026-07-31T18:43:40Z | 2026-07-31T18:50:19Z |
| `build` | success | 2026-07-31T18:43:39Z | 2026-07-31T18:52:16Z |
| `release` | **success** | 2026-07-31T18:52:18Z | 2026-07-31T18:52:49Z |

This is the first time in the project's history that the `release` job has run to completion instead of being structurally skipped (`if: startsWith(github.ref, 'refs/tags/')` was never satisfied by any of Phase 5's 8 `workflow_dispatch` regression runs, nor by 06-01's dispatch regression).

Release published at: **https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/tag/v0.2.0**
Assets: `Open-Anti-Browser-0.2.0-arm64.dmg`, `Open-Anti-Browser-Setup.exe` — both present, versioned filenames match the tag.

### The finding: RESEARCH assumption A2 — falsified, and worse than expected

RESEARCH assumption A2 asked whether `body_path` content is prepended before the auto-generated changelog (README-documented behavior, MEDIUM confidence, never observed). The real answer, observed directly from the first real tag-push run:

**`body_path` content did not appear in the Release body at all — not before the changelog, not after it, not anywhere. The published body was exactly:**

```
**Full Changelog**: https://github.com/ShengSoft-Tech/Open-Anti-Browser/compare/v0.1.16...v0.2.0
```

That is the *entire* body that was live on the public Release page immediately after the run completed. None of the hand-written prerequisite checklist, GUI self-check, progressive 放行 walkthrough, or trust caveat from `.github/RELEASE_NOTES_TEMPLATE.md` was present.

**Root cause, found by inspection:** the `release` job (`.github/workflows/build-release.yml:785-822` as it stood before this plan) has no `actions/checkout` step — its steps are `Download all build artifacts` → `List and verify release assets` → `Create GitHub Release`. The repository's working tree was never checked out onto that runner, so the file at `body_path: .github/RELEASE_NOTES_TEMPLATE.md` did not exist on disk. `softprops/action-gh-release@v2` did not fail or warn on the missing file — it silently proceeded as if `body_path` had not been set, falling back to only `generate_release_notes: true`'s output.

This is a genuine defect that no `workflow_dispatch` regression run (Phase 5's 8 runs, or 06-01's) could ever have caught, because the `release` job is tag-gated and always evaluates to `skipped` on a dispatch trigger — the job's steps, including this one, simply never execute under `workflow_dispatch`. It took a real tag push to expose it, which is exactly the "one hop no dispatch run can prove" this task's `key_links` entry anticipated — just not in the way RESEARCH's ordering question framed it.

### Fix applied (Rule 1 — auto-fix bug found during task execution)

Added the missing checkout step:

```diff
     steps:
+      - name: Checkout
+        uses: actions/checkout@v4
+
       - name: Download all build artifacts
```

Committed as `524aeb1` (`fix(ci): add missing checkout step to release job`) and pushed directly to `main` — **no second tag was pushed**, per the plan's explicit one-way-door instruction ("do not push a second corrective tag without returning to the orchestrator"). This fix will first be exercised by an actual `release` job run on the *next* real tag push; it has not itself been proven by automation in this session, since doing so would require exactly the kind of second tag push the plan forbids without returning to the orchestrator first. This is recorded as an open item below, not smoothed over.

### The live v0.2.0 Release body was also hand-corrected

Because Task 3's clean-account verifier needs a Release page that actually contains the documentation to read (that is the entire premise of the D-15 experiment), the already-published `v0.2.0` Release's body was corrected in place via:

```
gh release edit v0.2.0 --notes-file <template content + fetched changelog line, in that order>
```

This is **not** a re-run of the (now-fixed) CI pipeline — it is a manual, one-time repair of this specific Release's metadata using content assembled by this agent, not generated by the workflow. It restores the intended reading experience for Task 3, but the actual behavior of the *fixed* pipeline (checkout step + `body_path` + `generate_release_notes: true` together) remains formally unverified by any real automated run.

**First 20 lines of the corrected, live Release body (verbatim):**

```
## 下载前必读：系统要求

**硬件与系统要求（需同时满足）：**

- Apple Silicon（M 系列）芯片
- macOS 15 或更新版本

本次发布只提供一个安装包，为 arm64 架构，不提供其他架构版本可供选择。

**如何自查（推荐使用图形界面，无需打开终端）：**

1. 点击屏幕左上角的苹果 Logo，选择"关于本机"
2. 查看"芯片"一行：必须显示 Apple M 系列芯片（例如 Apple M1 / M2 / M3 / M4 等）
3. 查看系统版本号：必须是 macOS 15 或更高

如果你习惯使用终端，也可以执行以下命令进行自查（可选，并非必需）：

```
uname -m && sw_vers -productVersion
```
```

**Last lines (confirms ordering: hand-written content first, auto-changelog last):**

```
The app runs because it is no longer quarantined by the system, not because it has been signed
by Apple or trusted by Gatekeeper — this is the expected, normal state for an app like this, not
a security concern.


**Full Changelog**: https://github.com/ShengSoft-Tech/Open-Anti-Browser/compare/v0.1.16...v0.2.0
```

### Acceptance criteria checks (all against the corrected live body)

```
$ gh release view v0.2.0 --json body -q '.body' | grep -c 'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"'
2
$ for frag in sudo spctl --master-disable csrutil "~/Downloads"; do grep -Fc -- "$frag" <body>; done
sudo => 0
spctl => 0
--master-disable => 0
csrutil => 0
~/Downloads => 0
$ gh release view v0.2.0 --json assets -q '.assets[].name'
Open-Anti-Browser-0.2.0-arm64.dmg
Open-Anti-Browser-Setup.exe
```

All pass.

### 05-ci UAT test 1: closed

`.planning/phases/05-ci/05-UAT.md` test 1 (pending since 2026-07-29, the real-tag-push verification Phase 5 deliberately deferred rather than triggering purely to test) is now `result: [pass]`, with the run id, the three job conclusions, and the Release URL recorded in an `evidence:` block, and a note that this same run surfaced and fixed the checkout-step defect. Committed as `b2d7330`.

### dmg acquisition — deliberately NOT completed by this agent

The plan requires the dmg to be acquired "using a normal browser download so the file receives a genuine quarantine attribute — a `gh` or `curl` download does not reproduce what a real user's file looks like." This agent has no GUI/browser capability and cannot perform that download in a way that produces a real per-user quarantine attribute — and the clean macOS user account that download must happen under does not exist yet (it is created in Task 3's own setup steps).

What this agent did instead, strictly as a **non-installing integrity check**, not as the acquisition the plan describes:

```
$ gh release download v0.2.0 --pattern "*.dmg" --dir <scratchpad>/integrity-check-only
$ hdiutil imageinfo <scratchpad>/integrity-check-only/Open-Anti-Browser-0.2.0-arm64.dmg > /dev/null && echo "acquired dmg is a readable disk image"
acquired dmg is a readable disk image
```

This file was **not** opened, mounted (beyond `hdiutil imageinfo`'s metadata-only read, which does not attach the volume), or installed, and it must **not** be used for Task 3 — it was downloaded via `gh`, not a browser, under the developer's own account, so it carries none of the quarantine/LaunchServices state a real user's file would have. It exists solely to confirm the published dmg asset is a structurally valid disk image before handing this off.

**The real acquisition for Task 3 must happen as part of Task 3's own setup**: from the new clean macOS user account, open a real browser, navigate to https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/tag/v0.2.0, and download the `.dmg` asset from there — that is the only way to get a file carrying a genuine per-user quarantine attribute, and creating that account is itself the first step of Task 3.

## Task Commits

1. **Task 2 (version bump)** - `95850b0` (chore)
2. **Task 2 (workflow fix, Rule 1 deviation)** - `524aeb1` (fix)
3. **Task 2 (05-UAT.md closure)** - `b2d7330` (test)

Task 1 required no commit (decision was already resolved before this session; recorded here in prose per the plan's `must_haves`).

**Tag:** `v0.2.0` (annotated, points at `95850b0`) — pushed exactly once, per the one-way-door instruction.

## Files Created/Modified

- `frontend/package.json` — version `0.1.16` -> `0.2.0`
- `backend/main.py` — both `version=` fields `0.1.16` -> `0.2.0`
- `.github/workflows/build-release.yml` — added missing `actions/checkout@v4` step to the `release` job (3 lines)
- `.planning/phases/05-ci/05-UAT.md` — test 1 result `[pending]` -> `[pass]`, with evidence block

## Decisions Made

- Only the option-a branch was executed; option-b was never touched (per the pre-resolved checkpoint decision and threat T-06-14).
- The missing-checkout bug was fixed via a normal commit to `main`, not via a second tag push — the plan explicitly forbids pushing a second corrective tag without returning to the orchestrator, and this fix does not require re-tagging to land in the repository (it will simply be exercised by whichever tag is pushed next).
- The already-published Release's body was manually corrected rather than left broken, because an unusable Release page would make Task 3's D-15 verification unexecutable as specified. This is documented as a hand-repair, not a proof that the fixed pipeline renders correctly end-to-end — that remains open.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `release` job missing `actions/checkout`, silently dropping `body_path` content**
- **Found during:** Task 2, immediately after the first real tag-push run completed
- **Issue:** `.github/RELEASE_NOTES_TEMPLATE.md` (referenced via `body_path`) did not exist on the `release` job's runner because no checkout step had ever been added when the job was created in 05-05/06-01; `softprops/action-gh-release@v2` silently ignored the missing file instead of failing
- **Fix:** Added `actions/checkout@v4` as the first step of the `release` job
- **Files modified:** `.github/workflows/build-release.yml`
- **Commit:** `524aeb1`
- **Not fully verified:** this fix has not itself been exercised by a real automated run (that would require a second tag push, which the plan forbids without returning to the orchestrator first). It is a residual risk carried forward — see Open Items below.

No other deviations. The version bump, tag push, and UAT closure were executed exactly as the plan specified.

## Open Items / Residual Risk (carried forward, not smoothed over)

1. **The fixed `release` job's checkout+body_path+generate_release_notes interaction is unverified by any real CI run.** It will first be exercised on the next actual `v*` tag push. Until then, whether the *automated* pipeline reproduces the hand-assembled ordering demonstrated in this SUMMARY (template first, auto-changelog last) is an open question, not a proven fact.
2. **Task 3 (clean-account human verification) has not been executed.** This SUMMARY covers Tasks 1-2 only. `status: in-progress` in this file's frontmatter reflects that the plan is not yet complete.
3. **The dmg used for Task 3 must be freshly downloaded via a real browser from the new clean macOS account** — the `gh release download` copy made in this session is for integrity-checking only and must not be used for the install walkthrough.

## Known Stubs

None — no UI/data stubs introduced by this plan (it touches release infrastructure and version metadata only).

## Threat Flags

None beyond what the plan's own threat model already anticipated (T-06-12 through T-06-16 all directly addressed by this task's design; no new surface introduced).

---
*Phase: 06-release-docs*
*Tasks 1-2 completed: 2026-07-31*
*Task 3: not yet executed — see checkpoint*
