---
phase: 06-release-docs
plan: 05
subsystem: release-infra
tags: [github-actions, release, softprops-action-gh-release, gatekeeper, uat, documentation, uat-clean-account]

# Dependency graph
requires:
  - phase: 06-release-docs (06-04)
    provides: "Release notes template wired into release job via body_path, all copy surfaces (release template, in-app i18n, dmg background) aligned on the measured 再双击一次 flow"
  - phase: 05-ci (05-05)
    provides: "release job structure (needs: [build, build-macos], tag-gated, single softprops/action-gh-release call) — this plan is the first time it has ever run against a real tag"
provides:
  - "Real v0.2.0 tag pushed and its release job observed executing (success, not skipped) for the first time ever"
  - "Discovery and fix of a real defect: the release job had no actions/checkout step, so body_path: .github/RELEASE_NOTES_TEMPLATE.md pointed at a file that did not exist on the runner — softprops/action-gh-release silently dropped it instead of failing"
  - "Fixed release job (checkout step added, commit 524aeb1) for future tag pushes; current v0.2.0 Release body manually corrected via gh release edit so the live page carries the intended documentation"
  - "05-ci Phase 5's pending real-tag-push UAT item closed as pass"
  - "Clean-account walkthrough approved by the developer, with D-13's clean-account requirement explicitly waived (existing-account run instead) and three named residual gaps carried forward rather than hidden inside the pass"
  - "A separate runtime defect (macOS close-button hides to menu bar and never returns) surfaced during the walkthrough, fixed on main (a886dc7), and routed to a new Phase 7 (UI-05) rather than folded into this plan's scope"
affects: []

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
    - .planning/ROADMAP.md
    - .planning/phases/06-release-docs/06-CONTEXT.md
    - .planning/phases/06-release-docs/06-VALIDATION.md
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md

key-decisions:
  - "Task 1 checkpoint:decision resolved by the developer before this execution began: option-a (push a real v0.2.0 tag and verify against the published Release), not option-b (workflow_dispatch artifact). Only the option-a branch of Task 2 was executed; the option-b branch was never touched."
  - "The missing-checkout bug was fixed in the workflow (Rule 1 — auto-fix bug found during task execution) WITHOUT pushing a second tag, per the plan's explicit one-way-door instruction. The fix is committed to main and was NOT exercised by any real automated run in this plan — that is a residual risk, carried to Phase 7."
  - "The already-published v0.2.0 Release's body was hand-corrected via `gh release edit --notes-file` (template content + the previously-fetched auto-changelog line, in that order) rather than left broken, because Task 3's clean-account verifier needed a usable Release page to read as 'shipped documentation' — an empty/near-empty Release page would have made Task 3 unexecutable as specified."
  - "D-13's clean-account requirement was waived by explicit developer decision (2026-07-31, commit 1f63b37): the walkthrough ran in the developer's existing account instead of a freshly created one. Consequence accepted and recorded: the System Settings fallback path's UI state is driven by a per-user Gatekeeper denial breadcrumb this account already carries (05-06-SUMMARY.md:189), so it was scored as not verified rather than passed."
  - "The B1 first-launch dialog's verbatim title/button wording — a byproduct CONTEXT.md's Deferred Ideas hoped this phase's real install would capture — was NOT captured during this run. Recorded as still-open and carried forward rather than fabricated."
  - "A runtime defect surfaced by the walkthrough (macOS close button hides to menu bar, Dock icon does not restore it) was fixed directly (a886dc7) but its verification, and the still-unproven release-pipeline fix (524aeb1) and RESEARCH assumption A2, were routed to a new Phase 7 rather than re-opening this plan or Phase 6's scope."

requirements-completed: [DOCS-01, DOCS-02]

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
    rationale: "Whether the manually-reconstructed body faithfully represents what the FIXED workflow will actually produce on the next real tag push is not itself verified by an automated CI run — that verification belongs to Phase 7's real v0.2.1 tag push, not this plan."
  - id: D4
    description: "05-ci Phase 5's pending real-tag-push UAT test 1 updated from [pending] to [pass] with run id, job conclusions, and Release URL"
    requirement: null
    verification:
      - kind: other
        ref: ".planning/phases/05-ci/05-UAT.md test 1 result: [pass], evidence section names run 30656303074 and https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/tag/v0.2.0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Clean-account (D-13/D-15) end-to-end walkthrough performed against the real v0.2.0 dmg, with the clean-account requirement explicitly waived by the developer and the walkthrough run in the existing, Phase-5-contaminated account instead"
    requirement: [DOCS-01, DOCS-02]
    verification:
      - kind: human
        ref: "Developer resume-signal: 'approved' — primary 放行 path ('再双击一次'), prerequisite self-check, install, and create-and-start-a-Chrome-profile all fully exercised with zero unfixed documentation gaps found on the paths that were exercised"
        status: pass
    human_judgment: true
    rationale: "This is D-15's own scoring rule: a human executing shipped instructions is the only instrument that can judge sufficiency. The developer's approval covers the exercised paths only — see the three named qualifiers below, which are NOT folded into this pass."
  - id: D6
    description: "System Settings fallback path ('系统设置 → 隐私与安全性 → 仍要打开') NOT exercised — recorded as not verified, not as passed, because this account's Gatekeeper denial breadcrumb (written by Phase 5's 05-06 testing) makes its UI state unrepresentative of a genuinely new user"
    requirement: [DOCS-01]
    verification:
      - kind: other
        ref: "05-06-SUMMARY.md:189 records this account's syspolicyd 'Adding Gatekeeper denial breadcrumb (open)' entry from 2026-07-28, predating this walkthrough"
        status: fail
    human_judgment: true
    rationale: "Recorded as an explicit residual risk, not smoothed into D5's pass. Re-verification requires a genuinely clean system user account."
  - id: D7
    description: "B1 first-launch dialog verbatim title/button wording — a deferred capture goal from CONTEXT.md's Deferred Ideas — was NOT captured during this walkthrough"
    requirement: null
    verification:
      - kind: other
        ref: "No dialog title or button text was supplied by the developer's resume-signal; none is fabricated here"
        status: fail
    human_judgment: false
  - id: D8
    description: "Out-of-scope runtime defect (macOS close button hides to menu bar, does not restore from Dock) surfaced during the walkthrough, fixed on main, and routed to a new Phase 7 as requirement UI-05 rather than treated as part of this plan"
    requirement: null
    verification:
      - kind: other
        ref: "Fix commit a886dc7 on main; Phase 7 added to ROADMAP.md/REQUIREMENTS.md/STATE.md via commits 8f2ba5a, 6b2629f; published v0.2.0 dmg (tag points at 95850b0) predates a886dc7 and does NOT contain the fix, which is why the defect reproduced during the walkthrough"
        status: pass
    human_judgment: false

# Metrics
duration: 50min
completed: 2026-07-31
status: complete
---

# Phase 6 Plan 5: Real v0.2.0 Tag Push, Release Body Defect Found and Fixed, Clean-Account Walkthrough Approved (With Narrowed Scope) Summary

**Pushed the milestone's real `v0.2.0` tag per the developer's explicit option-a decision, which exposed and fixed a genuine release-pipeline defect (the `release` job silently dropped its hand-written Release body because it had no `actions/checkout` step); then ran the D-13/D-15 clean-account documentation walkthrough with the clean-account requirement explicitly waived by the developer, who approved the run as covering the primary path, prerequisite self-check, install, and Chrome-profile creation with zero unfixed documentation gaps — while the System Settings fallback path stays unverified, the first-launch dialog wording stays uncaptured, and the release-job fix itself stays unproven by a real automated run. A separate runtime defect surfaced during the walkthrough (macOS close button doesn't quit the app) was fixed and routed to a new Phase 7 rather than folded into this plan.**

## Performance

- **Duration:** ~50 min total (Tasks 1-2: ~35 min; Task 3 + finalization: ~15 min)
- **Started:** 2026-07-31T18:32:33Z
- **Completed:** 2026-07-31 (all three tasks)
- **Tasks:** 3 of 3 completed
- **Files modified:** 9 (4 in Tasks 1-2; 5 more in Task 3 finalization: ROADMAP.md, 06-CONTEXT.md, 06-VALIDATION.md, REQUIREMENTS.md, STATE.md)

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

**IMPORTANT — this "falsified" finding is about the file being absent, not about ordering.** RESEARCH assumption A2 (whether hand-written content is *ordered* before the auto-changelog when both are present) remains formally **unverified** by any real CI run — see Residual Risks below. The manual repair performed in this plan demonstrates an ordering, but that ordering was assembled by this agent, not produced by the (now-fixed) automated pipeline.

### Fix applied (Rule 1 — auto-fix bug found during task execution)

Added the missing checkout step:

```diff
     steps:
+      - name: Checkout
+        uses: actions/checkout@v4
+
       - name: Download all build artifacts
```

Committed as `524aeb1` (`fix(ci): add missing checkout step to release job`) and pushed directly to `main` — **no second tag was pushed**, per the plan's explicit one-way-door instruction ("do not push a second corrective tag without returning to the orchestrator"). This fix has never been exercised by any real automated `release` job run in this plan or since — see Residual Risks below.

### The live v0.2.0 Release body was also hand-corrected

Because Task 3's clean-account verifier needed a Release page that actually contains the documentation to read (that is the entire premise of the D-15 experiment), the already-published `v0.2.0` Release's body was corrected in place via:

```
gh release edit v0.2.0 --notes-file <template content + fetched changelog line, in that order>
```

This is **not** a re-run of the (now-fixed) CI pipeline — it is a manual, one-time repair of this specific Release's metadata using content assembled by this agent, not generated by the workflow. It restored the intended reading experience for Task 3, but the actual behavior of the *fixed* pipeline (checkout step + `body_path` + `generate_release_notes: true` together) remains formally unverified by any real automated run.

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

### dmg acquisition for the integrity check — deliberately NOT the acquisition used for Task 3

The plan required the dmg used for Task 3's install to be acquired "using a normal browser download so the file receives a genuine quarantine attribute." A separate, non-installing `gh release download` copy was made purely to confirm the published asset is a structurally valid disk image (`hdiutil imageinfo` exit 0) before handing off — that copy was never opened, mounted beyond metadata inspection, or installed, and was explicitly excluded from Task 3.

## Task 3: Clean-account walkthrough — approved, with clean-account requirement waived and scope narrowed

### The developer's resume-signal: `approved`

The developer ran the D-13/D-15 walkthrough and reported it complete with **zero unfixed documentation gaps** on the paths actually exercised: reading the Release page as shipped, the prerequisite hardware/OS self-check via the Apple menu, dragging the dmg to install, the primary 放行 path ("再双击一次"), and creating and starting a Chrome profile through to a visible fingerprint Chromium window.

**This is the phase's headline result, and it is reported honestly as "approved with a documented, narrowed scope" — not as "everything verified."** Three things about how the run deviated from the plan's written procedure are recorded here precisely because they must not be silently absorbed into a blanket pass.

### Qualifier 1 — D-13's clean-account requirement was explicitly waived (developer decision, 2026-07-31)

The walkthrough ran in the developer's **existing** macOS account, not a newly created one. This was an explicit developer decision, not a shortcut taken by this agent, and it is already recorded in three places that this SUMMARY references rather than re-litigates:

- `.planning/ROADMAP.md` § Phase 6 — SC3 rewritten, with a `2026-07-31 SC3 收窄` dated callout
- `.planning/phases/06-release-docs/06-CONTEXT.md` — a dated OVERRIDE note appended under D-13, original text preserved unedited
- `.planning/phases/06-release-docs/06-VALIDATION.md` — the Manual-Only Verifications table's rows updated to record the waiver and its consequence

Commit: `1f63b37`.

### Qualifier 2 — the System Settings fallback path is unverified, not passed

**Consequence of Qualifier 1, already accepted:** the fallback step 「系统设置 → 隐私与安全性 → 仍要打开」 was **not exercised** during this walkthrough and must be recorded as **未验证 / not verified** — explicitly not folded into the pass. Reason: that path's UI state (whether an "仍要打开" entry appears at all) is driven by a per-user Gatekeeper denial breadcrumb, and this exact account already had one written into it by Phase 5's 05-06 testing on 2026-07-28 (`05-06-SUMMARY.md:189`, `Adding Gatekeeper denial breadcrumb (open)`). What the developer would see at that step in this account does not represent what a genuinely new user's account would show. The primary path (「再双击一次」), the prerequisite self-check, the install, and the create-and-start-a-Chrome-profile leg were all fully exercised and are reported as passed.

**Do not read SC3 or DOCS-01 as "fully verified" without this qualifier** — the developer's approval and this plan's `requirements-completed: [DOCS-01, DOCS-02]` cover the paths that were actually exercised, per ROADMAP's own narrowed SC3 wording, not the full four-path branching document as originally scoped.

### Qualifier 3 — the B1 first-launch dialog's verbatim wording remains uncaptured

CONTEXT.md's Deferred Ideas listed capturing the first-launch dialog's exact title and button labels as a byproduct this phase's real install would "顺带把这个补上" (incidentally pick up). It did not happen during this run. **This is recorded as still-open and carried forward as a deferred item** — no dialog title or button text is written into this SUMMARY, because none was supplied by the developer's resume-signal. Fabricating it would misrepresent an unobserved fact as a captured one, which is a worse failure than leaving the gap open.

### Out-of-scope finding: a separate runtime defect, fixed and routed to Phase 7 — not a Phase 6 documentation gap

During the walkthrough the developer hit a defect that is **not a documentation gap**: clicking the macOS window close button (the red traffic-light "X") hides the app to the menu bar and leaves the process running, and clicking the Dock icon afterward does not bring the window back — the only escape was right-click Dock → Quit.

This is a runtime behavior defect, not something any amount of better release-notes wording could fix, so it does not belong to Phase 6's DOCS-01/DOCS-02 scope and is **not** counted as a Phase 6 documentation gap and does **not** block this plan.

Disposition:
- **Fixed already:** commit `a886dc7` — macOS now quits cleanly on window close; Windows/Linux tray-minimize behavior is unchanged.
- **Routed to a new Phase 7** ("补丁发布与发布链路验证"), tracked as requirement **UI-05**, added via ROADMAP.md/REQUIREMENTS.md/STATE.md updates in commits `8f2ba5a` and `6b2629f`.
- **launch_app.py was not touched by this plan** — the fix landed on main before this finalization step, and its real-machine verification is explicitly Phase 7's job, not this plan's.
- **Why it reproduced:** the published v0.2.0 dmg's tag points at commit `95850b0` (the version-bump commit), which **predates** `a886dc7`. The dmg the developer installed during the walkthrough therefore did not contain the fix, which is exactly why the defect was reproducible in the first place. Phase 7's own real `v0.2.1` tag push is what will prove the fix in a shipped artifact.

## Residual Risks — carried forward explicitly, NOT merged into the "passed" narrative

This plan closes Task 3 with a developer approval, but four things this plan does **not** close are listed here precisely so they are not lost inside that approval:

1. **`524aeb1` (the release job's `actions/checkout` fix) has never been executed by real CI.** It was pushed to `main` as a normal commit, deliberately without a second tag push, per the plan's one-way-door instruction. The only way to prove it actually works is a real `v*` tag push exercising the `release` job end-to-end — that first real run is Phase 7's job (SC2, `v0.2.1`).
2. **`06-RESEARCH.md` assumption A2 (whether `body_path` content is prepended before the auto-generated changelog) remains formally unverified.** The v0.2.0 attempt did not answer the ordering question at all — it failed for a more basic reason (the body_path file was absent from the runner entirely), and the ordering demonstrated in this SUMMARY's "corrected live body" section was manually assembled by this agent, not produced by the automated pipeline. Phase 7's real `v0.2.1` tag push (SC3) is what will confirm or falsify A2 for real.
3. **The System Settings fallback path (「系统设置 → 隐私与安全性 → 仍要打开」) is unverified**, per Qualifier 2 above — this account's pre-existing Gatekeeper denial breadcrumb makes it unrepresentative of a new user. Re-verification requires a genuinely clean system user account.
4. **The B1 first-launch dialog's verbatim title and button wording remains uncaptured**, per Qualifier 3 above — this is a deferred item, not a fabricated fact.

None of these four are Phase 6 documentation gaps requiring a fix inside this plan — they are honestly-scoped unknowns that the developer's `approved` signal does not paper over.

## Task Commits

1. **Task 2 (version bump)** - `95850b0` (chore)
2. **Task 2 (workflow fix, Rule 1 deviation)** - `524aeb1` (fix)
3. **Task 2 (05-UAT.md closure)** - `b2d7330` (test)
4. **Task 3 (SC3 narrowing, D-13 waiver documented before/independent of this finalization)** - `1f63b37` (docs)
5. **Task 3 out-of-scope finding (macOS close-button fix)** - `a886dc7` (fix, pre-existing on main before this finalization step)
6. **Task 3 out-of-scope finding (Phase 7 added)** - `8f2ba5a`, `6b2629f` (docs)

Task 1 required no commit (decision was already resolved before this session; recorded here in prose per the plan's `must_haves`).

**Tag:** `v0.2.0` (annotated, points at `95850b0`) — pushed exactly once, per the one-way-door instruction.

## Files Created/Modified

- `frontend/package.json` — version `0.1.16` -> `0.2.0`
- `backend/main.py` — both `version=` fields `0.1.16` -> `0.2.0`
- `.github/workflows/build-release.yml` — added missing `actions/checkout@v4` step to the `release` job (3 lines)
- `.planning/phases/05-ci/05-UAT.md` — test 1 result `[pending]` -> `[pass]`, with evidence block
- `.planning/ROADMAP.md` — Phase 6 SC3 rewritten with a `2026-07-31 SC3 收窄` callout; Phase 6 plan checklist and progress row updated to 5/5 complete; Phase 7 added
- `.planning/phases/06-release-docs/06-CONTEXT.md` — dated OVERRIDE note appended under D-13
- `.planning/phases/06-release-docs/06-VALIDATION.md` — Manual-Only Verifications rows and Per-Task Verification Map rows updated to real outcomes
- `.planning/REQUIREMENTS.md` — DOCS-01/DOCS-02 already marked complete (06-04); UI-05 added for Phase 7
- `.planning/STATE.md` — position, decisions, session updated to reflect plan completion

## Decisions Made

- Only the option-a branch of Task 2 was executed; option-b was never touched (per the pre-resolved checkpoint decision and threat T-06-14).
- The missing-checkout bug was fixed via a normal commit to `main`, not via a second tag push — the plan explicitly forbids pushing a second corrective tag without returning to the orchestrator, and this fix does not require re-tagging to land in the repository. Its first real automated exercise is Phase 7's job.
- The already-published Release's body was manually corrected rather than left broken, because an unusable Release page would have made Task 3's D-15 verification unexecutable as specified. This is documented as a hand-repair, not a proof that the fixed pipeline renders correctly end-to-end — that remains open, tracked as Residual Risk 1/2.
- D-13's clean-account requirement was waived by explicit developer decision, with the consequence (System Settings fallback unverified) accepted and recorded rather than hidden — see Qualifier 1/2 above.
- The B1 dialog wording gap was left open rather than fabricated — see Qualifier 3 above.
- The out-of-scope close-button defect was fixed and routed to a new Phase 7 (UI-05) rather than expanding this plan's scope or blocking its completion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `release` job missing `actions/checkout`, silently dropping `body_path` content**
- **Found during:** Task 2, immediately after the first real tag-push run completed
- **Issue:** `.github/RELEASE_NOTES_TEMPLATE.md` (referenced via `body_path`) did not exist on the `release` job's runner because no checkout step had ever been added when the job was created in 05-05/06-01; `softprops/action-gh-release@v2` silently ignored the missing file instead of failing
- **Fix:** Added `actions/checkout@v4` as the first step of the `release` job
- **Files modified:** `.github/workflows/build-release.yml`
- **Commit:** `524aeb1`
- **Not fully verified:** this fix has not itself been exercised by a real automated run in this plan or since. Carried forward as Residual Risk 1 to Phase 7.

**2. [Rule 1 - Bug, out-of-scope discovery] macOS window close button hides the app instead of quitting it**
- **Found during:** Task 3's clean-account walkthrough (developer-reported)
- **Issue:** Clicking the red traffic-light close button hid the app to the menu bar / Dock without quitting the process; the Dock icon did not restore the window; the only recovery was right-click Dock → Quit
- **Fix:** `a886dc7` — macOS now quits fully on window close (Windows/Linux unchanged)
- **Files modified:** `launch_app.py` (already committed to main before this finalization step; **not modified by this plan or this finalization**)
- **Not a Phase 6 gap:** this is a runtime behavior defect, not a documentation defect, so it is not counted against DOCS-01/DOCS-02 or against this plan's completion. Routed to a new Phase 7 as requirement UI-05 (commits `8f2ba5a`, `6b2629f`). Its real-machine verification is explicitly out of this plan's scope.

No other deviations. The version bump, tag push, and UAT closure were executed exactly as the plan specified.

## Open Items / Residual Risk (carried forward, not smoothed over)

1. **The fixed `release` job's checkout+body_path+generate_release_notes interaction is unverified by any real CI run.** It will first be exercised on Phase 7's real `v0.2.1` tag push.
2. **RESEARCH assumption A2 (body_path ordering relative to the auto-generated changelog) remains formally unverified.** The v0.2.0 attempt failed for a different, more basic reason (the file was entirely absent from the runner) — Phase 7's real tag push is what will actually settle A2.
3. **The System Settings fallback path («仍要打开») is unverified**, not passed — this account's pre-existing Gatekeeper denial breadcrumb (written by Phase 5) makes its current UI state unrepresentative of a genuinely new user. Re-verification requires a truly clean system account.
4. **The B1 first-launch dialog's verbatim title/button wording remains uncaptured** — a deferred item from CONTEXT.md's Deferred Ideas that this phase's real install did not, in the end, pick up.

None of these four block this plan's completion — they are the honestly-scoped boundary of what "approved" means here, and none is a Phase 6 documentation defect requiring a fix inside this plan.

## Known Stubs

None — no UI/data stubs introduced by this plan (it touches release infrastructure, version metadata, and planning-tracking documents only).

## Threat Flags

None beyond what the plan's own threat model already anticipated (T-06-12 through T-06-16 all directly addressed by this task's design; no new surface introduced). The out-of-scope close-button defect is a runtime/UX defect, not a new trust-boundary surface, and its fix (`a886dc7`) touches only `launch_app.py`'s own event handling, already covered by Phase 5's existing threat register.

---
*Phase: 06-release-docs*
*Plan 06-05: complete — all 3 tasks executed*
*2026-07-31*

## Self-Check: PASSED

- FOUND: commit `95850b0` (version bump)
- FOUND: commit `524aeb1` (checkout fix)
- FOUND: commit `b2d7330` (UAT closure)
- FOUND: commit `1f63b37` (SC3 narrowing / D-13 waiver)
- FOUND: commit `a886dc7` (macOS close-button fix)
- FOUND: commit `8f2ba5a` (Phase 7 added)
- FOUND: commit `6b2629f` (Phase 7 rename)
- FOUND: tag `v0.2.0` (points at `95850b0`)
- FOUND: Release https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/tag/v0.2.0
- CONFIRMED: `node --test frontend/src/lib/*.test.js` — 52/52 pass
- CONFIRMED: `.venv/bin/python -m unittest discover -s tests` — 122 tests, OK (skipped=2)
