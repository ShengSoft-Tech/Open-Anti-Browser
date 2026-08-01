---
phase: 7
slug: patch-release
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-31
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (repo root, no pytest) + Node `node:test` (`frontend/src/lib/*.test.js`) |
| **Config file** | none — commands are documented in `CLAUDE.md` |
| **Quick run command** | `.venv/bin/python -m unittest tests.test_version_consistency -v` (version-gate changes) · `node --test frontend/src/lib/*.test.js` (template/frontend changes) |
| **Full suite command** | `.venv/bin/python -m unittest discover -s tests -v` && `node --test frontend/src/lib/*.test.js` |
| **Estimated runtime** | ~30 seconds (Python suite) + ~3 seconds (node suite) |

**Baseline at plan time:** 122 Python tests (2 skipped — Windows-only branches, expected on macOS) + 52/52 node:test.

---

## Sampling Rate

- **After every task commit:** Run the matching quick command (`tests.test_version_consistency` for the gate, `node --test frontend/src/lib/*.test.js` for the template)
- **After every plan wave:** Run both full suite commands
- **Before `/gsd-verify-work`:** Full suite green **AND** real `v0.2.1` tag push complete **AND** SC1 real-machine check passed **AND** SC2/SC3 observations recorded
- **Max feedback latency:** ~35 seconds

---

## Per-Task Verification Map

> Task IDs are filled in by the planner; the rows below bind each phase requirement to its verification substrate.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 1 | PKG-06 | T-07-01 (tag bypasses version gate / Tampering) | Version gate rejects any tag whose version disagrees with template / package.json / main.py | unit | `.venv/bin/python -m unittest tests.test_version_consistency -v` | ❌ W0 (new test class) | ⬜ pending |
| TBD | TBD | 1 | PKG-06 | T-07-02 (release body carries misleading commands / Tampering) | Template edit introduces no forbidden fragment (`sudo` / `spctl` / `--master-disable` / `csrutil`) | unit | `node --test frontend/src/lib/*.test.js` | ✅ (Phase 6 `releaseNotesTemplate.test.js`) | ⬜ pending |
| TBD | TBD | 2 | PKG-06 | — | Release body renders template content with zero `gh release edit` | manual_procedural | none — human inspection of the published Release page after the real `v0.2.1` tag push (this IS SC2/SC3) | ❌ W0 (phase output) | ⬜ pending |
| TBD | TBD | 2 | UI-05 | — | Close button makes the process actually disappear (`ps` / Activity Monitor) | manual_procedural | none — human real-machine check on the frozen `.app` (see Manual-Only Verifications) | ❌ W0 (phase output) | ⬜ pending |
| — (pre-existing) | — | — | UI-05 regression guard | — | No SIGSEGV within 18s; `osascript ... to quit` exits within bounded timeout | integration (CI) | `build-macos` job → "GUI launch smoke test" step in `.github/workflows/build-release.yml` | ✅ (built in 05-02 / 05-06) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/release/check_version_consistency.py` — add `read_template_version()` plus the extended comparison (D-02); preserve the existing CLI contract (`<ref_name> <is_tag>`, stdout = version only)
- [ ] `tests/test_version_consistency.py` — add a test class covering the template-version branch: positive match, negative (template not bumped), and missing-anchor
- [ ] `.github/RELEASE_NOTES_TEMPLATE.md` — add the version anchor + bilingual 「本次更新 / What's Changed」 section (D-01/D-03/D-04)
- [ ] No framework install needed — `unittest` and `node:test` are both already available; `.venv` is verified to run the full suite

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| macOS 窗口关闭按钮点击后进程真正消失 | UI-05 | Clicking a specific window's close button requires System Events UI Scripting, gated by `kTCCServiceAccessibility`; GitHub-hosted runners keep SIP on with no non-interactive way to grant it (07-RESEARCH Pitfall 3). No automated equivalent exists. | On the developer's macOS 15.7 arm64 machine, launch the **frozen `.app`** (not `python launch_app.py` — see Pitfall 4), click the window close button, then confirm with `ps aux \| grep -i open-anti-browser` (or Activity Monitor) that no process survives and none is spinning at ~60% CPU. Record the command output as evidence. |
| Release 正文由流水线自动渲染,无需 `gh release edit` | PKG-06 | Only a real `v*` tag push executes the `release` job (`if: startsWith(github.ref, 'refs/tags/')`); `workflow_dispatch` structurally skips it (07-RESEARCH Pitfall 1). | After pushing `v0.2.1`, open the published Release page and confirm the hand-written template content is present without any manual edit. |
| 手写正文与自动 changelog 的实际先后顺序 | PKG-06 (SC3) | Rendering order can only be observed on a real published Release body. | On the same Release page, record which block appears first and judge or refute `06-RESEARCH.md` assumption A2. Capture the observation verbatim in the plan SUMMARY. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (manual_procedural tasks are explicitly exempted above and are the phase's own deliverable)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
