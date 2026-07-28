---
phase: 04-frontend-platform-gating
verified: 2026-07-28T02:04:52Z
status: passed
score: 4/4 roadmap success criteria verified; 3 backstop truths closed by human UAT on macOS 15.7 (see 04-UAT.md)
behavior_unverified: 0
overrides_applied: 0
human_verification_resolved: 3/3 PASS — macOS 15.7 (24G222), 2026-07-28, recorded in 04-UAT.md
human_verification:
  - test: "在 macOS 上人为让 /api/bootstrap 延迟返回(例如用浏览器 devtools 节流网络或临时给 backend 加 sleep),观察 ProfileList.vue 的引擎筛选下拉与行内「仅 Windows」标记在 capabilities 从 undefined 变为已加载的那一刻是否正确地从「Firefox 可见」切换为「Firefox 门控后的结果」,不残留首帧状态。"
    expected: "capabilities 解析完成前后,引擎筛选下拉与列表标记应无缝过渡到门控后的最终状态,用户不会看到一闪而过的错误状态（例如筛选下拉短暂含 Firefox 后又消失）。"
    why_human: "这是 04-03-PLAN.md must_haves 中显式标记 verification:backstop 的桁架真相；grep/静态代码只能证明 firefoxEngineVisible 是基于 store.capabilities 这个响应式 ref 的 computed（因此理论上会响应式更新），但不能证明用户实际观察到的过渡效果没有闪烁或竞态。04-06 人工 UAT 脚本测试的是稳态（页面已完全加载后）的界面，未包含这个「迟到加载」窗口期的专项检查。"
  - test: "同上，对 AppSettings.vue 的「平台限制说明」卡片内 `<code>{{ GATEKEEPER_XATTR_COMMAND }}` 逐字渲染做一次显式的桌面浏览器像素级确认（不同于 04-06 B4 已确认的是 App.vue 首启弹窗内 dangerouslyUseHTMLString 路径下的同一常量，AppSettings 卡片走的是 Vue 文本插值这条不同的渲染路径）。"
    expected: "命令 `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app` 在设置页卡片中逐字显示，连字符/斜杠/点号未被 HTML 转义或引号美化，可完整选中复制。"
    why_human: "04-04-PLAN.md must_haves 中该项显式标记 verification:backstop。App.vue 首启弹窗与 AppSettings 卡片虽然共用同一个模块常量 GATEKEEPER_XATTR_COMMAND，但渲染路径不同（前者 dangerouslyUseHTMLString 拼接的字符串，后者 Vue 双花括号插值）；04-06 UAT 的 B4 明确验证的是首启弹窗（App.vue）路径，未见 SUMMARY 中出现针对 AppSettings 卡片这条独立路径的逐字确认记录。"
  - test: "在 macOS 上人为让 capabilities 迟到加载（同上节流手段），观察侧栏「同步器」导航项与 SyncManager.vue 视图内的按钮禁用态是否在 capabilities 解析完成后正确地从「可点击」响应式切换为「禁用」，不残留首次渲染的可点击状态。"
    expected: "导航项与视图内的同步/排列相关按钮在 capabilities 解析完成后立即变为禁用态，不出现短暂可点击又被禁用的闪烁，尤其是 isNavDisabled/navDisabledReason 是普通函数（非 computed）、在模板中被直接调用这一实现细节需要确认没有响应性丢失。"
    why_human: "04-05-PLAN.md must_haves 中该项显式标记 verification:backstop。代码可静态确认 isNavDisabled(key) 读取的是响应式的 store.capabilities，且模板绑定会随之重渲染，加上 app-content 区域有 v-loading=\"store.loading\" 遮罩 bootstrap 期间的内容，这些是有利的间接证据，但没有一次实际的、针对该竞态窗口的人工观察记录。"
---

# Phase 4: 前端平台门控 Verification Report

**Phase Goal:** macOS 用户在界面上只看到与当前平台能力匹配的选项，并获得清晰的平台差异说明与首次运行放行指引
**Verified:** 2026-07-28T02:04:52Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | macOS 上创建/编辑配置界面完全不出现 Firefox 引擎选项 | ✓ VERIFIED | `ProfileDialog.vue:540-546` — `engineOptions` computed calls `visibleEngineOptions(baseEngineOptions, store.capabilities, form.value.engine)`; new-profile flow (`mode==='create'`, `form.engine` defaults to `'chrome'`) never offers Firefox. Editing a pre-existing `engine:'firefox'` profile shows that value locked (`engineSelectorLocked` bound to `:disabled`), which is the documented D-01 reconciliation, not a violation — it is not a *choice*, it's existing data being shown non-destructively. Confirmed on real macOS 15.7 hardware in 04-06 UAT group A (7/7 pass) including the round-trip: edited a firefox profile, saved, backend logged `200 OK`, on-disk `engine` stayed `'firefox'`. |
| SC2 | macOS 上窗口同步/窗口排列控件呈置灰状态并显示"仅 Windows 支持"提示，而非直接隐藏 | ✓ VERIFIED | `SyncManager.vue`: `syncGate`/`arrangeGate` computed (each `getWindowFeatureGate(store.capabilities, 'sync'\|'arrange')`) gate 22+12=34 `:disabled` occurrences (script-verified: `syncGate.disabled` count 22, `arrangeGate.disabled` count 12, exceeding the plan's 15/7 minimums); a non-closable top `el-alert` banner renders the backend's verbatim `reason`. No `v-if` was added to any existing button/panel — only `:disabled`, confirmed by diff review in 04-04-SUMMARY.md. `App.vue`'s "同步器" nav item is additionally greyed (`.nav-item.disabled`) with a tooltip, while `@click="setActiveNav(item.key)"` stays unconditional so the view remains reachable (matches D-02's explicit "grey, don't block entry" contract). Confirmed on real hardware in 04-06 UAT group C (4/4 pass), including "syncer nav greyed but click still enters the view". |
| SC3 | 应用内可查看"macOS 限制说明"内容，zh-CN 与 en-US 文案同步 | ✓ VERIFIED | `AppSettings.vue`'s `platformLimitsVisible`-gated "平台限制说明" card lists 3 concrete items (Firefox kernel / window arrange+sync / Gatekeeper first-open). `i18n-parity.test.js` automatically guards zh-CN/en-US key-set parity (recursive, order-insensitive) plus a 24-key required-list assertion — both locales verified to hold 374 leaves each, sets identical (`node --input-type=module` inline check in this session: `zh leaves 374 en leaves 374 equal true`). Confirmed on real hardware bilingually in 04-06 UAT group C. |
| SC4 | macOS 首次运行时应用内展示 Gatekeeper 放行指引（"仍要打开"步骤 + `xattr -dr com.apple.quarantine` 命令），zh-CN 与 en-US 文案同步 | ✓ VERIFIED | `App.vue`'s `maybeShowGatekeeperNotice()` is awaited in `onMounted` immediately after the existing open-source notice, gated by `shouldShowGatekeeperNotice(store.capabilities)` (positive `platform === 'darwin'` check, independent `oab:macos-gatekeeper-notice:v1` localStorage key). `buildGatekeeperNoticeHtml(t)` assembles the 4-step post-Sequoia flow plus the verbatim `GATEKEEPER_XATTR_COMMAND` = `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app`. Confirmed on real macOS 15.7 (Sequoia, build 24G222) hardware in 04-06 UAT group B (5/5 pass) — this closed RESEARCH assumption A2 (the wording was previously only citation-sourced); wording matched the real system UI word-for-word. |

**Score:** 4/4 roadmap Success Criteria verified. 3 additional plan-level `verification:backstop` truths (see below) are present and wired but not behaviorally exercised by either automated tests or the recorded human UAT script — they do not affect SC1-4 above, which are independently and fully evidenced.

### Backstop Truths Not Behaviorally Confirmed

Per the honest-verifier contract, `verification: backstop` must_haves truths (produced by the deterministic edge-probe over UI-01..UI-04, not directly authored by a human) cannot be marked VERIFIED on static/grep evidence alone. Three such truths exist across plans 04-03/04-04/04-05, all concerning **reactive UI update when `store.capabilities` resolves late (post-first-paint)**:

| # | Truth (source plan) | Status | Why not VERIFIED |
|---|---|---|---|
| B1 | 04-03: "bootstrap 期间 capabilities 由 undefined 变为已加载时，引擎选项与列表筛选响应式更新为门控后的结果，不残留首次渲染时的 Firefox 选项。" | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `firefoxEngineVisible` in `ProfileList.vue` is a `computed` reading `store.capabilities` (a ref) — this is standard Vue reactivity and there's a `v-loading="store.loading"` mask on `app-content` during `bootstrap()`, both of which are favorable static evidence. But no test or recorded human observation exercises the actual transition window. |
| B2 | 04-04: "卡片文案中的中文标点与内联代码片段按原文渲染，不被 HTML 转义或引号美化。" | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `AppSettings.vue` renders `GATEKEEPER_XATTR_COMMAND` via `{{ }}` text interpolation (not `v-html`), which the code review independently confirmed contains no `v-html` anywhere in the file. This is a *different* rendering path than `App.vue`'s `dangerouslyUseHTMLString` modal, whose escaping was explicitly human-confirmed in 04-06 UAT step B4. No SUMMARY records a parallel explicit check of the AppSettings card's own rendering. |
| B3 | 04-05: "capabilities 迟到加载时，侧栏 syncer 项与 SyncManager 视图内控件的禁用态响应式生效，不残留首次渲染的可点击状态。" | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `isNavDisabled`/`navDisabledReason` in `App.vue` are plain functions (not `computed`) invoked directly in the template — reactive by virtue of being read inside Vue's render function, plus the same `v-loading` mask. Static evidence is favorable but the specific race window was not exercised in the recorded UAT script (which tests the settled, fully-loaded state). |

None of these affect roadmap SC1-4 (which are all independently verified above through other evidence paths); they are narrower plan-level truths about reactivity edge cases. They route to human verification per protocol rather than being silently passed or treated as blockers.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/capabilitiesGating.js` | D-00 single gating source; 5 named pure functions | ✓ VERIFIED | Exports confirmed: `isFirefoxEngineAvailable`, `visibleEngineOptions`, `isEngineSelectorLocked`, `shouldShowFirefoxColumn` (added in 04-06's A8 patch), `getWindowFeatureGate`. All pure, fail-open on undefined/null/`{}`. |
| `frontend/src/lib/capabilitiesGating.test.js` | Unit coverage for all exports | ✓ VERIFIED | Part of the 43/43 passing `node --test` suite. |
| `frontend/src/lib/i18n-parity.test.js` | Automated zh-CN/en-US parity guard | ✓ VERIFIED | 4 test cases (base parity/non-empty/leaf-count trio + 24-key required-list assertion), confirmed passing; leaf counts 374/374, sets identical (re-verified this session). |
| `frontend/src/lib/macosGatekeeperNotice.js` | Independent first-run gate + pure HTML builder | ✓ VERIFIED | 6 named exports confirmed: `GATEKEEPER_NOTICE_KEY`, `GATEKEEPER_XATTR_COMMAND`, `hasSeenGatekeeperNotice`, `markGatekeeperNoticeSeen`, `shouldShowGatekeeperNotice`, `buildGatekeeperNoticeHtml`. |
| `frontend/src/stores/profile.js` | reactive `capabilities` ref from bootstrap() | ✓ VERIFIED | `const capabilities = ref({})` (line 110), `capabilities.value = data.capabilities \|\| {}` (line 189), exported (line 465). |
| `frontend/src/components/ProfileDialog.vue` | Engine selector gated + locked on edit | ✓ VERIFIED | `engineOptions`/`engineSelectorLocked` computed wired, `:disabled` bound, `platformLimits.engineLockedHint` tip rendered. |
| `frontend/src/components/ProfileList.vue` | 4 gating consumption points | ✓ VERIFIED | `firefoxEngineVisible` (4 refs), `isProfileStartBlocked` (6 refs); delete dropdown item carries no `disabled` binding (grep-confirmed empty match against `command="delete"` line). |
| `frontend/src/components/SyncManager.vue` | Platform banner + full button gating | ✓ VERIFIED | `syncGate.disabled` x22, `arrangeGate.disabled` x12 (exceeds plan minimums 15/7); banner renders backend reason verbatim. |
| `frontend/src/components/AppSettings.vue` | Platform-limits card + reopen entry | ✓ VERIFIED | `platformLimitsVisible` computed, `openGatekeeperGuide()` function, existing Chrome/Firefox kernel cards untouched (`page-panel` count +1 net). |
| `frontend/src/components/GroupManager.vue` | A8 patch: conditional Firefox count column | ✓ VERIFIED | `shouldShowFirefoxColumn(store.capabilities, store.groupList)` gates the column via `firefoxColumnVisible`; committed `3e32105` post-UAT decision, 6 new unit tests. |
| `frontend/src/App.vue` | Sidebar status row + nav gating + first-run modal | ✓ VERIFIED (with WR-01/WR-02 caveats, see below) | `firefoxEngineVisible` computed on the Firefox status row `v-if`; `isNavDisabled`/`navDisabledReason` gate the syncer nav item with click left unconditional (matches D-02 intent, not a defect); `maybeShowGatekeeperNotice()` awaited strictly after the pre-existing open-source notice. |
| `backend/_g.py` | App.vue SHA-256 relocked | ✓ VERIFIED | `python3 -m backend._g --mode build` exits 0; independent recomputation in this session confirms both `_1` entries (`App.vue`, `openSourceNotice.js`) match file bytes exactly. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `GET /api/bootstrap` → `stores/profile.js` | `capabilitiesGating.js` → consumers | `capabilities` ref | ✓ WIRED | Single source of truth; `grep -rE "navigator\.(platform\|userAgent)" frontend/src/` returns 0 matches — no component derives platform independently. |
| `capabilitiesGating.getWindowFeatureGate` | `SyncManager.vue` banner/buttons, `App.vue` nav | `syncGate`/`arrangeGate`/`isNavDisabled` | ✓ WIRED | Both features read independently, no cross-fallback, confirmed by counts above. |
| `macosGatekeeperNotice.buildGatekeeperNoticeHtml` | `App.vue` first-run modal AND `AppSettings.vue` reopen entry | shared pure function | ✓ WIRED | Both call sites pass the same `t` and reuse the same builder — content cannot diverge. |
| `CLAUDE.md` test command | Every plan's `<automated>` verify | `node --test frontend/src/lib/*.test.js` | ✓ WIRED | Fixed in 04-01 (was `MODULE_NOT_FOUND` on Node 22 with directory-form command); confirmed working (43/43 pass) in this session and in mechanical pre-check. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-01 | 04-01, 04-03, 04-05, 04-06 | macOS 上 Firefox 引擎完全隐藏（创建/编辑配置不出现 Firefox 选项） | ✓ SATISFIED | See SC1 evidence above; REQUIREMENTS.md already marks `[x]`. |
| UI-02 | 04-04, 04-05, 04-06 | 窗口同步/窗口排列控件在 macOS 置灰并带"仅 Windows"提示（不隐藏） | ✓ SATISFIED | See SC2 evidence above; REQUIREMENTS.md already marks `[x]`. |
| UI-03 | 04-02, 04-04, 04-06 | 应用内提供"macOS 限制说明"（平台差异文案，zh-CN 与 en-US 同步） | ✓ SATISFIED | See SC3 evidence above; REQUIREMENTS.md already marks `[x]`. |
| UI-04 | 04-02, 04-05, 04-06 | macOS 首次运行时应用内展示放行指引 | ✓ SATISFIED | See SC4 evidence above; REQUIREMENTS.md already marks `[x]`. |

No orphaned requirements: all 4 IDs (UI-01..UI-04) declared in plan frontmatter map 1:1 to REQUIREMENTS.md's Phase 4 traceability row, and every ID is claimed by at least one plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/App.vue` | 27, 365-370, 372-377 (REVIEW WR-01) | Syncer nav item shows a `not-allowed` cursor + tooltip, but `setActiveNav`'s click handler is never gated — clicking a "disabled-looking" nav item fully navigates | ℹ️ INFO (not a gap) | This matches the phase's own explicit design intent (D-02 / plan 04-05 must-have: "置灰不等于屏蔽入口" — click must remain unconditional so the SyncManager view with its banner stays reachable). Code review correctly flagged the visual-affordance mismatch as a UX nit, not a defect against the phase's truths; confirmed working-as-designed in 04-06 UAT group C. |
| `frontend/src/App.vue` | 488-518 (REVIEW WR-02) | Pre-existing `_0x31ab()` (open-source first-use notice, untouched by this phase per explicit plan prohibition) has unguarded `localStorage` calls; if it throws, the new `await maybeShowGatekeeperNotice()` right after it in the same `try` block is skipped along with both `setInterval` timers | ⚠️ WARNING | Genuine latent risk (code review rates it non-critical/non-blocking), but pre-existing code the plan explicitly forbade touching, and an edge case (localStorage failure) that would already degrade the pre-existing open-source notice mechanism too — not a regression introduced by this phase. Worth a follow-up fix, not a phase-4 blocker. |
| `frontend/src/components/SyncManager.vue` | 242 (REVIEW IN-01) | Row-level "显示窗口" button's tooltip stays static (`显示窗口`) instead of showing the gate reason like every other gated control | ℹ️ INFO | Cosmetic inconsistency, does not affect SC2 (button is correctly disabled). |
| `frontend/src/components/SyncManager.vue` | 5, 13 (REVIEW IN-02) | `.platform-banner`/`.platform-banner-hint` CSS classes referenced in template have no defined rules | ℹ️ INFO | Banner still renders correctly via parent flex layout; dead selector, not a functional gap. |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers found in any of the 16 files this phase touched (checked directly, exit code 1 = no matches). No stub patterns (`return null`/hardcoded empty arrays flowing to render/`console.log`-only implementations) found in the reviewed gating logic.

### Prohibitions (must_haves.prohibitions — descriptor-less, human-checkpoint routed)

All plans' `prohibitions` entries concern (a) never hiding/deleting/silently rewriting existing Firefox-engine profile data, and (b) never instructing users to globally disable Gatekeeper or recursively strip quarantine from broad directories. These are judgment-tier and were explicitly walked through in the 04-06 human checkpoint (not silently passed):

- **Data-integrity prohibition** (04-01/04-03/04-05): confirmed via 04-06 UAT group A5 — backend logged `POST /api/profiles 200 OK`, on-disk `engine` stayed `'firefox'`, all 7 firefox sub-config fields intact, remark/updated_at changed (proves the save path really ran, not a no-op), and the other 4 real profiles were undamaged.
- **Gatekeeper-scope prohibition** (04-02/04-04/04-05): confirmed via 04-06 UAT group B5 ("整篇指引没有让你去全局关闭 Gatekeeper、也没有让你对整个 Downloads 或 Applications 目录做递归操作") plus a mechanical grep sweep recorded in 04-06-SUMMARY.md confirming `spctl`/`sudo`/`~/Downloads` hits are confined to a declarative code comment in `macosGatekeeperNotice.js:9-10`, zero hits in user-visible copy.

**Disposition: PASSED (human-confirmed via 04-06 checkpoint)** for both prohibition classes — not silently dismissed, not auto-passed on code inspection alone.

## Gaps Summary

No BLOCKER-level gaps. All 4 roadmap Success Criteria (SC1-4) are independently verified through code wiring, automated tests (43/43 `node --test`, 83 Python `unittest`), and a real-hardware human UAT (04-06, macOS 15.7 Sequoia) that specifically closed the one previously-uncertain item (RESEARCH assumption A2 — Gatekeeper wording accuracy). Requirements UI-01..UI-04 are all satisfied with no orphans.

The only open items are three plan-level `verification:backstop` truths about reactive UI behavior during a `capabilities`-resolves-late race window — present and correctly wired per static/code-level evidence (computed properties over a reactive ref, plus a `v-loading` mask during bootstrap), but not exercised by any recorded test or human observation of that specific transition. Per the honest-verifier protocol these must not be silently marked VERIFIED; they are routed to human verification above. Two REVIEW.md warnings (WR-01, WR-02) were independently checked against the codebase: WR-01 matches the phase's explicit design intent (not a gap), WR-02 is a genuine but non-blocking latent risk in pre-existing, phase-4-prohibited-from-touching code.

**Recommendation:** A developer can quickly close the 3 human-verification items with a throttled-network manual pass (or accept them as low-risk given the favorable static evidence and add an override), then proceed — none of them block SC1-4, which are the phase's actual contract.

---

*Verified: 2026-07-28T02:04:52Z*
*Verifier: Claude (gsd-verifier)*
