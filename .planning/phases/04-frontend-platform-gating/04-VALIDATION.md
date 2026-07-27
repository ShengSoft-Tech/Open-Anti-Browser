---
phase: 4
slug: frontend-platform-gating
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-27
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `04-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Node built-in `node:test` (frontend) — no framework config file; invoked directly |
| **Config file** | none — `node --test frontend/src/lib/` per CLAUDE.md |
| **Quick run command** | `node --test frontend/src/lib/` |
| **Full suite command** | `node --test frontend/src/lib/` (same — no separate "full" tier exists for frontend today) |
| **Estimated runtime** | ~5 seconds |

**Existing constraint (CLAUDE.md + `frontend/src/lib/proxyBypass.test.js`):** the one existing frontend
test does not import Vue or compile SFCs — it regex-extracts plain `function xxx(` declarations out of a
`.vue` file's `<script setup>` block and runs them in a sandboxed `vm` context. Any new pure-logic helper
this phase introduces should either live in a plain `.js` file under `frontend/src/lib/` (directly
testable — preferred) or, if it must live inside a `.vue` `<script setup>`, be declared as
`function xxx(` (not `const xxx = () =>`) to stay extractable.

---

## Sampling Rate

- **After every task commit:** Run `node --test frontend/src/lib/`
- **After every plan wave:** Run `node --test frontend/src/lib/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

*Seeded per-requirement; task IDs are filled in by `/gsd-validate-phase` once PLAN.md task IDs exist.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | UI-01 | — | N/A | unit | `node --test frontend/src/lib/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-01 (existing firefox profile row) | — | N/A | manual | — | N/A | ⬜ pending |
| TBD | TBD | TBD | UI-02 | — | N/A | unit | `node --test frontend/src/lib/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-03 | — | N/A | unit (i18n parity) | `node --test frontend/src/lib/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-04 | — | N/A | unit (localStorage gate + i18n parity) | `node --test frontend/src/lib/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/capabilitiesGating.js` (new) — pure gating functions backing the component logic
      (e.g. Firefox option visibility, window-feature gate), directly unit-testable without the
      extraction-regex trick
- [ ] `frontend/src/lib/macosGatekeeperNotice.js` (new) — first-run notice localStorage gate helpers,
      directly testable
- [ ] `frontend/src/lib/i18n-parity.test.js` (new) — deep-compares `Object.keys` of `zh-CN.js` vs
      `en-US.js`, catching missing-translation regressions for UI-03/UI-04 and future i18n additions
- [ ] No backend test gap — this phase makes zero backend changes; the capabilities contract it consumes
      is already covered by `tests/test_capabilities_api.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-existing firefox-engine profile row stays visible, deletable, and start-disabled on macOS | UI-01 | Requires a seeded profile fixture plus a rendered table; no component-mount harness exists in this repo | Seed `data/profiles.json` with a firefox-engine profile, launch on macOS, confirm the row renders with a "仅 Windows" marker, start is disabled, delete still works |
| Gatekeeper first-run modal copy and flow | UI-04 | Visual/OS-interaction surface; modal content correctness is a copy judgement | Clear the notice localStorage key, launch on macOS, confirm the modal appears once with the "Open Anyway" steps and the `xattr -dr com.apple.quarantine` command, and does not reappear after dismissal |
| macOS limits card readability and zh/en switch | UI-03 | Rendered-content judgement beyond key parity | Open Settings → platform limits card in both locales |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
