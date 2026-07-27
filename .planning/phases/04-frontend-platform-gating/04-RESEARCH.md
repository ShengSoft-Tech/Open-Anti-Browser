# Phase 4: 前端平台门控 - Research

**Researched:** 2026-07-27
**Domain:** Vue 3 SPA conditional rendering / platform capability gating / bilingual UX copy / integrity-hash-locked files
**Confidence:** HIGH (backend contract and all touch-point files were read directly from this repo; only the Gatekeeper copy content relies on external, CITED sources)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**门控信号源(基础决策,贯穿 UI-01/02)**
- **D-00:** 前端门控统一消费 capabilities API(经 bootstrap 返回的 `data.capabilities`),不在前端硬编码 `sys.platform` / `navigator.platform` 判断。当前 `stores/profile.js:180 bootstrap()` 只取了 settings/profiles/engines/downloads,未取 capabilities——需新增一个响应式 `capabilities` ref 并在 bootstrap 里赋值,作为所有门控组件的单一事实源。Reversibility: costly.

**Firefox 隐藏范围(UI-01)**
- **D-01:** macOS 上采取入口全隐 + 既有配置禁用保留:
  - 入口全部隐藏 Firefox——ProfileDialog 引擎选择器(`engineOptions`)、ProfileList 列表筛选 Tab 的 Firefox 选项、App.vue 顶部引擎状态徽章/计数中的 Firefox 项,在 `capabilities.engines.firefox.available===false` 时全部隐藏。
  - 既有 firefox-engine 配置不删不藏——从 Windows 迁移来、profiles.json 里已存在的 firefox 配置(Phase 1 D-08 要求它们在 macOS 能加载)仍显示在列表中,带「仅 Windows」类标记,禁用启动(编辑/复制是否一并禁由 planner 定),但保留可见与可删除,不静默丢数据。
  - 判定依据:UI-01 验收只要求"创建/编辑配置界面完全不出现 Firefox 选项",列表里显示一个禁用的既有 firefox 配置不违反该验收。Reversibility: reversible。

**窗口同步/排列置灰(UI-02)**
- **D-02:** 侧栏置灰 + 视图内横幅双层呈现(Roadmap 明确要求"置灰+提示,不隐藏"):
  - 导航层:App.vue `navItems` 里的 `syncer` 项在 macOS 置灰,hover tooltip 直接用 `capabilities.window.sync.reason`(「窗口同步仅在 Windows 上可用」)。
  - 视图层:进入 SyncManager 视图后,顶部一条 banner 说明"仅 Windows 可用",视图内的同步/排列控件全部禁用。
  - reason 文案读 capabilities 字段,不在前端另写(后端已固定「窗口排列仅在 Windows 上可用」/「窗口同步仅在 Windows 上可用」)。Reversibility: reversible。

**macOS 限制说明承载(UI-03)**
- **D-03:** 说明内容放在设置页(AppSettings.vue)新增一张「平台限制 / macOS 说明」卡片,不新增侧栏导航项。该卡片是限制说明的"永久家":UI-02 的置灰 banner 和 UI-04 的首启放行弹窗都可指向它随时回查。文案 zh-CN + en-US 双份。是否在 Windows 上也显示该卡片(macOS-only vs 平台自适应说明)由 planner 定,默认至少 macOS 上有内容。Reversibility: reversible。

**首次运行放行指引(UI-04)**
- **D-04:** 首启模态弹窗 + 独立 localStorage key:
  - macOS 首次运行时弹一次模态,内容 = Gatekeeper「仍要打开」分步指引 + `xattr -dr com.apple.quarantine` 终端命令。
  - 用新的独立 localStorage key(建议 `oab:macos-gatekeeper-notice:v1`)记忆"已看过",复用现有首启弹窗模式但不碰被 `_g.py` 锁定的 `openSourceNotice.js`——另起独立组件/key。
  - 看过之后可从 UI-03 的设置卡片随时再查。
  - 与 Phase 6 的 release notes 放行说明是两处不同载体(本 phase = 应用内提示;Phase 6 = 发布文档),不混淆。Reversibility: reversible。

### Claude's Discretion
- 各处新增文案的确切措辞(zh-CN / en-US);UI-04 localStorage key 的最终命名。
- 既有 firefox 配置"禁用"的确切范围(启动必禁、删除必留;编辑/复制/导出是否禁 planner 定夺)。
- 门控在前端的落地形式(store computed getter / 组件内读 capabilities),只要满足 D-00 的"单一事实源、不硬编码平台"。
- macOS 首启若同时命中开源声明首启提示(现有 `oab:first-use-notice:v2`)与放行弹窗时的先后/叠加顺序。
- SyncManager 视图内 banner 与控件禁用的具体组件写法。

### Deferred Ideas (OUT OF SCOPE)
None — 讨论未越界。

跨 phase 备忘(非新增 scope,仅提示 planner):
- CI dmg 打包(Phase 5)、release notes 放行说明 DOCS-01/02(Phase 6)不在本 phase。UI-04 的应用内放行弹窗与 Phase 6 的发布文档放行说明是两处不同载体,内容可相互呼应但不合并。
- 是否把限制说明卡片在 Windows 上也显示为"平台差异总览":默认 macOS-only,planner 可按需扩展,属实现裁量而非新 capability。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | macOS 上 Firefox 引擎完全隐藏(创建/编辑配置不出现 Firefox 选项) | Pattern 2 (`engineOptions` → computed); exact touch points identified: `ProfileDialog.vue:532-535`, `ProfileList.vue:26-27` (filterEngine dropdown), `App.vue:71-76` (sidebar status Firefox row) + `:428-441` (`engineStatusText`/`engineTagType`); Pitfall 3 (edit-mode existing firefox profile) and Pitfall 4 (batch/group start) cover the edge cases the literal requirement text doesn't spell out. |
| UI-02 | 窗口同步/窗口排列控件在 macOS 置灰并带"仅 Windows"提示(不隐藏) | Pattern 3 (disabled nav item + tooltip); `capabilities.window.{arrange,sync}.{available,reason}` contract confirmed verbatim in Code Examples section; Pitfall 2 documents the Chinese-only reason string / SyncManager's no-i18n-today baseline so the planner scopes new copy correctly. |
| UI-03 | 应用内提供"macOS 限制说明"(平台差异文案,zh-CN 与 en-US 同步) | `AppSettings.vue` already uses `useI18n`/`t()` consistently (confirmed by read) — new card follows that exact existing pattern; Wave 0 gap identifies a new i18n-parity test to enforce zh/en sync automatically. |
| UI-04 | macOS 首次运行时应用内展示放行指引(Gatekeeper "仍要打开"步骤 + `xattr -dr com.apple.quarantine` 命令,zh-CN 与 en-US 同步) | Pattern 4 (independent localStorage key + new non-hash-locked file); State of the Art section gives CITED, current (post-Sequoia) Gatekeeper step wording; Code Examples section clarifies the xattr command targets the outer .app bundle, distinct from the kernel-quarantine-strip already implemented server-side. |
</phase_requirements>

## Summary

This is a **pure frontend** phase. The backend contract it consumes (`capabilities` block in `GET /api/bootstrap`, also standalone at `GET /api/capabilities`) is already implemented and tested (`backend/browser_manager.py:627-641`, `tests/test_capabilities_api.py`) — confirmed by direct read, not assumption. The store (`frontend/src/stores/profile.js`) does not yet consume it: `bootstrap()` (line 180) destructures `settings`, `profiles`, `engines`, `downloads` from the response but drops `data.capabilities` even though the backend already returns it (`browser_manager.py:75`). Wiring that up is the D-00 foundation every other task in this phase depends on.

The remaining work is four narrow, well-located UI edits (hide Firefox entry points, grey out sync/arrange with a reason tooltip, add a settings-page explainer card, add a first-run Gatekeeper modal) plus the i18n pairs CLAUDE.md mandates for all new copy. The single highest-risk item in the whole phase is **not** logic complexity — it's `backend/_g.py`'s SHA-256 lock on `frontend/src/App.vue` (and a separate, do-not-touch lock on `frontend/src/lib/openSourceNotice.js`). Any edit to App.vue that isn't followed by regenerating its hash in `_g.py:18` will hard-fail `npm run build` and desktop app startup.

A second non-obvious finding: the backend's `reason` strings (`"窗口排列仅在 Windows 上可用"` / `"窗口同步仅在 Windows 上可用"`) are **Chinese-only, hardcoded, no locale parameter** (`browser_manager.py:629-630`). CONTEXT.md's D-02 locks the decision to read these verbatim rather than rewrite them — meaning en-US users will still see a Chinese sentence inside the tooltip/banner for this one specific string. This is an accepted, deliberate tradeoff (not a bug to "fix"), but the planner must not let a verification step treat it as an i18n gap, and should scope any *additional* wrapper copy (headings, links) to be properly bilingual.

**Primary recommendation:** Do the store wiring (D-00) as its own first task/wave, expose it as a single Pinia `computed` (e.g. `store.capabilities`), and make every other task (Firefox hiding, sync/arrange greying, settings card, first-run modal) read only from that computed — never re-derive platform from `navigator.platform` or similar. Handle the App.vue hash relock as an explicit, separate step at the very end of any plan/task that touches App.vue.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Capabilities single source of truth (D-00) | Browser/Client (Pinia store) | API/Backend (already returns `capabilities` in bootstrap, Phase 3, done) | Store is the only place that should read `data.capabilities`; every component below reads the store, never the API directly and never `navigator.platform`. |
| Firefox entry hiding (UI-01) | Browser/Client (Vue components: ProfileDialog, ProfileList, App.vue) | — | Pure conditional rendering keyed off `capabilities.engines.firefox.available`; no backend change. |
| Window sync/arrange greying (UI-02) | Browser/Client (App.vue nav, SyncManager.vue) | API/Backend (supplies `available`/`reason` strings, done) | Disabled-state + reason text are UI concerns; the boolean and its Chinese reason string are backend-owned and already shipped. |
| macOS 限制说明 (UI-03) | Browser/Client (AppSettings.vue + i18n files) | — | Static content page; no backend involvement, no new state. |
| Gatekeeper 首启指引 (UI-04) | Browser/Client (new component + localStorage + i18n files) | — | Client-only modal + client-only persistence key; explicitly must NOT touch the existing `_g.py`-locked first-use-notice component. |

## Standard Stack

No new packages are required for this phase. All primitives already exist as project dependencies and are already used elsewhere in this exact codebase:

| Library | Version (installed) | Purpose in this phase | Why standard here |
|---------|---------|---------|--------------|
| element-plus | ^2.9.1 [VERIFIED: codebase grep, frontend/package.json] | `el-tooltip` (grey+reason for sync/arrange), `el-tag`/`el-button disabled` (Firefox/legacy-config disabling), `el-dialog`/`ElMessageBox.alert` (first-run modal) | Already the UI kit for the whole app; `el-tooltip` is already used in `SyncManager.vue:217,222` for other hints. |
| vue-i18n | ^11.3.2 [VERIFIED: codebase grep] | `useI18n()` / `t()` for all new zh-CN/en-US copy | Existing i18n mechanism (`frontend/src/i18n/{zh-CN,en-US}.js` + `i18n/index.js`), used by every component except `SyncManager.vue` (see Pitfall 2). |
| pinia | ^2.3.0 [VERIFIED: codebase grep] | `computed` getter for `capabilities` on `useProfileStore` | Store already holds `settings`/`engines`/etc. the same way. |

**Installation:** none — no `npm install` needed for this phase.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reading `capabilities` from the Pinia store | Hardcoding `navigator.platform` / `import.meta.env` platform checks in each component | Explicitly forbidden by D-00 (locked decision) — would decouple UI from the backend contract and break the moment SYNC-01 (future CDP cross-platform sync) ships. |
| `el-tooltip` for the "仅 Windows" reason | Custom CSS `title` attribute | `el-tooltip` matches existing pattern (`SyncManager.vue`), gets consistent styling/positioning for free. |

## Package Legitimacy Audit

**Not applicable.** This phase installs zero new packages (frontend or backend). No `npm install`/`pip install` occurs. Skip the legitimacy gate.

## Architecture Patterns

### System Architecture Diagram

```
GET /api/bootstrap  ──────────────────────────────────────────────┐
(backend, already returns                                          │
 data.capabilities = {                                             │
   engines: { chrome:{available}, firefox:{available} },           │
   window: { arrange:{available,reason}, sync:{available,reason} } │
 })                                                                 │
                                                                     ▼
                                            stores/profile.js bootstrap()
                                            [MISSING TODAY — must add]
                                            capabilities.value = data.capabilities
                                                                     │
                              ┌──────────────────────────────────────┼───────────────────────────────┐
                              ▼                                      ▼                                ▼
                 ProfileDialog.vue                         App.vue (navItems,                SyncManager.vue
                 engineOptions computed                     header-badges, engine            (view-level banner +
                 (drop 'firefox' when                        status text/tag)                 disabled controls)
                 !capabilities.engines                       + syncer nav item                 reads capabilities.
                 .firefox.available)                          disabled + tooltip               window.{arrange,sync}
                              │                               reason=capabilities.
                              ▼                               window.sync.reason
                 ProfileList.vue
                 (filterEngine dropdown option;
                  existing firefox-engine rows:
                  visible + "仅 Windows" tag +
                  disabled Start button;
                  batch-start must skip them)

AppSettings.vue                              new GatekeeperNotice.vue (or similar)
"平台限制 / macOS 说明" card                   first-run modal, gated by NEW localStorage
(zh-CN + en-US copy,                          key (e.g. oab:macos-gatekeeper-notice:v1),
always reachable from                          mounted from App.vue onMounted() alongside
settings nav — permanent home)                 (not inside) the existing first-use-notice flow
      ▲                                                    │
      └──────────── both link/point back to ───────────────┘
        (UI-02 banner "了解更多" and UI-04 modal footer can
         both reference the AppSettings card as the permanent home)
```

### Recommended Project Structure
No new directories needed. Touch points, all pre-existing:
```
frontend/src/
├── stores/profile.js          # add `capabilities` ref + expose in bootstrap() return
├── components/
│   ├── ProfileDialog.vue      # engineOptions -> computed, gated (UI-01)
│   ├── ProfileList.vue        # filterEngine dropdown option + row rendering/disable (UI-01)
│   ├── App.vue                # navItems syncer disabled+tooltip (UI-02); header badges/engineStatusText (UI-01);
│   │                          # ⚠ SHA-256 locked by backend/_g.py:18 — MUST relock after edit
│   ├── SyncManager.vue        # view-level banner + control disabling (UI-02)
│   ├── AppSettings.vue        # new "平台限制 / macOS 说明" card (UI-03)
│   └── <NewComponent>.vue     # first-run Gatekeeper modal (UI-04) — new file, independent of openSourceNotice.js
├── i18n/
│   ├── zh-CN.js                # new keys for all of the above, zh-CN is default locale
│   └── en-US.js                # matching keys, 1:1 with zh-CN
└── lib/
    └── openSourceNotice.js     # ⚠ SHA-256 locked by backend/_g.py:17 — DO NOT MODIFY (UI-04 must not touch this)
```

### Pattern 1: Capabilities as a single Pinia computed
**What:** Add `const capabilities = ref({})` to `useProfileStore`, set it in `bootstrap()` from `data.capabilities`, and expose it in the returned object (same idiom already used for `settings`, `engines`, `downloads`).
**When to use:** Any component that needs to know whether Firefox / window arrange / window sync is available on the current platform.
**Example:**
```javascript
// Source: frontend/src/stores/profile.js:180-194 (existing bootstrap pattern, extended)
async function bootstrap() {
  loading.value = true
  try {
    const data = await api.get('/api/bootstrap')
    settings.value = data.settings
    profiles.value = data.profiles
    engines.value = data.engines
    downloads.value = data.downloads || {}
    capabilities.value = data.capabilities || {}   // <-- currently missing, add this line
    await refreshApiInfo()
    await refreshSynchronizer()
    return data
  } finally {
    loading.value = false
  }
}
```
Consumers then do e.g. `store.capabilities?.engines?.firefox?.available` — always optional-chained, since `capabilities` is `{}` until bootstrap resolves (avoids a flash of Firefox options before the first API round-trip completes).

### Pattern 2: Gating a static options array with a computed
**What:** `ProfileDialog.vue`'s `engineOptions` is currently a plain top-level `const` array (line 532-535), not reactive. Convert to `computed`.
**Example:**
```javascript
// Source: frontend/src/components/ProfileDialog.vue:532-535 (current, non-reactive)
const engineOptions = [
  { label: 'Chrome', value: 'chrome' },
  { label: 'Firefox', value: 'firefox' },
]
// Recommended replacement pattern:
const engineOptions = computed(() => {
  const options = [{ label: 'Chrome', value: 'chrome' }]
  if (store.capabilities?.engines?.firefox?.available !== false) {
    options.push({ label: 'Firefox', value: 'firefox' })
  }
  return options
})
```
Note the `!== false` guard (not `=== true`): before bootstrap resolves, `capabilities` is `{}` and the field is `undefined` — defaulting to "show Firefox" until data arrives is safer than a flash-hide/flash-show flicker in the common (Windows) case, and macOS will correct within one tick once bootstrap resolves. Confirm this tradeoff with the planner; the alternative (defaulting to hidden) avoids ever showing Firefox to a macOS user even for one frame, at the cost of a flash-hide for Windows users on slow loads.

### Pattern 3: Disabled nav item with reason tooltip
**What:** `App.vue`'s `navItems` is a flat array (`{ key, icon }`, lines 203-212) rendered via `v-for` with a plain `@click`. No disabled-state styling exists today (`global.css` only has `.nav-item`, `.nav-item:hover`, `.nav-item.active` — no `.disabled` variant).
**When to use:** UI-02's nav-level greying for `syncer`.
**Example approach:**
```vue
<!-- Source: frontend/src/App.vue:16-27, extended -->
<el-tooltip
  v-for="item in navItems"
  :key="item.key"
  :disabled="!isNavDisabled(item.key)"
  :content="navDisabledReason(item.key)"
  placement="right"
>
  <div
    class="nav-item"
    :class="{ active: activeNav === item.key, disabled: isNavDisabled(item.key) }"
    @click="!isNavDisabled(item.key) && setActiveNav(item.key)"
  >
    <el-icon><component :is="item.icon" /></el-icon>
    <span>{{ t(`nav.${item.key}`) }}</span>
  </div>
</el-tooltip>
```
`isNavDisabled('syncer')` reads `store.capabilities?.window?.sync?.available === false`; `navDisabledReason('syncer')` returns `store.capabilities?.window?.sync?.reason || ''`. A new `.nav-item.disabled` CSS rule (reduced opacity, `cursor: not-allowed`, no hover highlight) needs to be added to `global.css`. **Decide during planning**: does clicking a disabled nav item still navigate to `SyncManager.vue` (which then shows its own banner + fully disabled controls, per D-02's "视图层" requirement), or does it block navigation entirely? CONTEXT.md's D-02 explicitly requires **both** layers (nav tooltip AND in-view banner + disabled controls), which implies navigation into the view must still be allowed — do not block the click.

### Pattern 4: First-run modal with independent localStorage key (reusing existing idiom, new file)
**What:** `App.vue` already has a first-run modal pattern at lines 187, 280-295 (`_0x31ab()` invoked in `onMounted`), gated by `localStorage.getItem('oab:first-use-notice:v2')`. UI-04 needs the same *shape* of logic (check key → show `ElMessageBox.alert` with HTML content → set key) but must NOT reuse or modify `openSourceNotice.js` (hash-locked) or its key.
**Example (new, independent):**
```javascript
// New file, e.g. frontend/src/lib/macosGatekeeperNotice.js (NOT hash-locked, safe to create/edit)
const GATEKEEPER_NOTICE_KEY = 'oab:macos-gatekeeper-notice:v1'

export function hasSeenGatekeeperNotice() {
  return localStorage.getItem(GATEKEEPER_NOTICE_KEY) === '1'
}

export function markGatekeeperNoticeSeen() {
  localStorage.setItem(GATEKEEPER_NOTICE_KEY, '1')
}
```
Call this from `App.vue`'s `onMounted()`, gated additionally on `store.capabilities?.platform !== 'win32'` (the capabilities payload already includes a raw `platform` field per `browser_manager.py:632` — `sys.platform`, e.g. `'darwin'` on macOS), and sequence it **after** the existing open-source notice await (`await _0x31ab()`) so the two modals never overlap (Claude's Discretion item in CONTEXT.md — this ordering is the simplest safe default: open-source notice first, then Gatekeeper guidance).

### Anti-Patterns to Avoid
- **Re-deriving platform in the frontend:** Do not add any `navigator.platform` / `userAgent` sniffing. `capabilities.platform` (raw `sys.platform` string) and the per-feature `available` booleans are the only sanctioned signal (D-00, locked).
- **Rewriting backend reason strings:** Do not translate, reformat, or template `capabilities.window.arrange.reason` / `.sync.reason` in the frontend — D-02 explicitly locks "读字段,不在前端另写".
- **Silently dropping existing Firefox profiles:** D-01 explicitly forbids hiding/deleting pre-existing firefox-engine profiles in the list; only new-creation Firefox entry points are hidden.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Disabled control + reason hint | Custom overlay div + `title` attribute | `el-tooltip` + native `disabled` prop on `el-button`/form controls | Already the established pattern in this codebase (`SyncManager.vue:217,222`); free a11y/positioning. |
| First-run "seen" tracking | New generic "notices" framework/registry | A second flat localStorage boolean key, mirroring the exact idiom already in `App.vue` for the open-source notice | The existing pattern is a single string key + `'1'` sentinel; a whole notification framework is over-engineering for two total notices. |
| i18n key-parity checking | Manual eyeballing of two files during review | A small node:test script asserting `Object.keys` (deep) match between `zh-CN.js` and `en-US.js` | No such test exists today (verified — grep found zero i18n-parity tests); SC3/SC4 explicitly require zh/en sync, so an automated check is cheap insurance and fits the existing `node --test frontend/src/lib/` test convention. |

**Key insight:** Nothing in this phase requires new architecture — it is entirely "read one already-shipped boolean/string field, conditionally render." The complexity is in *coverage* (finding every Firefox-facing surface) and *process* (the `_g.py` hash relock), not in design.

## Common Pitfalls

### Pitfall 1: `backend/_g.py` SHA-256 lock on App.vue silently breaks build/startup
**What goes wrong:** Any edit to `frontend/src/App.vue` (near-certain in this phase — UI-01 header badges/engine text, UI-02 navItems, UI-04 modal mount) changes its SHA-256, but `_1` dict in `backend/_g.py:18` still has the old hash. `npm run build`'s `prebuild`/`postbuild` hooks run `python -m backend._g --mode build|runtime`, and desktop startup calls `_7("runtime")` — both raise `RuntimeError("资源完整性校验失败...")` and hard-fail.
**Why it happens:** The hash check (`_5()` in `_g.py`) is an anti-tamper mechanism protecting the open-source notice; it does not distinguish "legitimate feature edit" from "notice removal attempt."
**How to avoid:** After finishing all App.vue edits for a task/plan, compute `sha256sum frontend/src/App.vue` (or the Python equivalent used by `_3()`: `hashlib.sha256(path.read_bytes()).hexdigest()`) and update the value at `backend/_g.py:18` for the `frontend/src/App.vue` key. Do this as the **last** edit to App.vue in a given task, and re-verify by running `npm run build` (or `python -m backend._g --mode runtime`) before considering the task done. Do NOT touch `_1`'s key for `openSourceNotice.js` (`_g.py:17`) at all — no task in this phase should edit that file.
**Warning signs:** `npm run build` failing with `资源完整性校验失败，已停止构建` after an otherwise-correct App.vue diff; desktop app refusing to start with the runtime variant of the same message.

### Pitfall 2: Backend `reason` strings are Chinese-only; SyncManager.vue has no i18n today
**What goes wrong:** `capabilities.window.sync.reason` / `.arrange.reason` come from `browser_manager.py:629-630` as bare Chinese strings with no locale parameter. Meanwhile `SyncManager.vue` (1387 lines) has **zero** `useI18n`/`t()` usage — every existing string in that file is hardcoded Chinese (verified by grep: no `useI18n` import found). A planner unfamiliar with this could either (a) wrongly "fix" the reason string by wrapping it in `t()` with a translation key that doesn't exist on the backend, or (b) assume the whole component needs an i18n migration as part of this phase (out of scope — SC2 does not require en-US parity for the *banner*, only SC3/SC4 explicitly require zh/en sync).
**Why it happens:** D-02 (locked) intentionally scopes "read the reason field verbatim" — this was a discussed and accepted tradeoff, not an oversight.
**How to avoid:** For the *reason text itself*, render `store.capabilities.window.sync.reason` directly, unwrapped, exactly as CONTEXT.md's D-02 specifies. For any *new wrapper copy* the planner authors around it (a banner heading like "同步器在当前平台不可用", a "查看说明" link label, etc.), add proper `t()` keys to both `i18n/zh-CN.js` and `i18n/en-US.js` per CLAUDE.md's hard rule — do not hardcode those new strings the way the rest of `SyncManager.vue` does. This means `SyncManager.vue` will end up with a **mixed** i18n pattern (old hardcoded Chinese + new `t()`-driven UI-02 strings) — that's expected and acceptable, not a regression to "fix" wholesale.
**Warning signs:** A verification step failing "en-US shows Chinese text" against the reason string specifically (expected, not a bug) vs. against newly-authored wrapper copy (actual bug, must fix).

### Pitfall 3: Editing an existing (Windows-origin) Firefox profile on macOS via a Firefox-less engine selector
**What goes wrong:** `ProfileDialog.vue`'s engine field is an `el-segmented` control bound to `engineOptions` (line 27-30, options at line 532). If `engineOptions` is filtered to `[Chrome]` only on macOS (per Pattern 2), opening the **edit** dialog for a pre-existing profile whose `engine === 'firefox'` (migrated from Windows, per Phase 1 D-08 — these must still load) will bind `el-segmented`'s `v-model` to a value (`'firefox'`) that isn't in its own `:options` list. Element Plus's `el-segmented` behavior for an out-of-options bound value is undefined/inconsistent across versions, and a naive save could silently coerce/overwrite `engine` to `'chrome'`, corrupting the stored profile.
**Why it happens:** UI-01's hiding logic was designed around profile *creation* (new profiles can only be Chrome), but CONTEXT.md's D-01 separately requires existing firefox profiles to remain **editable or not** ("planner 定夺") — the two requirements intersect at exactly this control.
**How to avoid:** When `mode === 'edit'` and `form.engine === 'firefox'` and `!capabilities.engines.firefox.available`, either (a) disable the entire engine `el-segmented` (read-only, show current value even though it's not a selectable option — confirm this is visually supported, may need `:disabled="true"` on the whole field rather than filtering options), or (b) keep `'firefox'` in `engineOptions` *only* when it's the profile's current value in edit mode, additionally tagged "仅 Windows / 不可切换". Document whichever choice is made — this is exactly the "既有 firefox 配置'禁用'的确切范围" question CONTEXT.md defers to the planner, and this specific control is where the decision has to land concretely.
**Warning signs:** A firefox-engine profile edited on macOS silently becomes a chrome-engine profile after save; or the segmented control renders with no option highlighted/selected.

### Pitfall 4: Batch-start / group-start don't know about disabled Firefox rows
**What goes wrong:** `ProfileList.vue`'s batch-start filter (`.filter(item => item.status === 'stopped' && !store.isProfileStarting(item.id))`, ~line 382) and `store.startGroup()` do not exclude firefox-engine profiles on macOS. If UI-01 only disables the **row-level** Start button but batch/group start bypasses that same guard, a "启动全部" action could still attempt to start an un-launchable Firefox profile and surface a raw backend error instead of the intended "此配置仅 Windows 支持" UX.
**Why it happens:** The Start-button disabling (row level) and the batch/group start code paths are separate call sites; disabling one doesn't touch the other.
**How to avoid:** Apply the same `capabilities.engines.firefox.available` gate to whatever helper computes "startable" profiles for batch/group actions, not just the single-row button's `:disabled` binding.
**Warning signs:** Clicking "启动全部" on macOS with a mixed chrome/firefox profile list produces a generic error toast for the firefox rows instead of them being silently skipped (or a clear pre-flight message).

### Pitfall 5: `AppSettings.vue`'s existing Firefox kernel-management card is out of D-01's enumerated scope
**What goes wrong:** CONTEXT.md's D-01 explicitly lists three hiding locations (ProfileDialog engineOptions, ProfileList filterEngine, App.vue header badges/counts) but does **not** mention `AppSettings.vue`'s existing "Firefox 内核" card (lines 33-41: title, description, install/download status tag) — this card is unrelated to profile creation/editing (SC1's literal scope: "创建/编辑配置界面") and continues to reference the Firefox kernel management flow (executable path, installer URL, download) that Phase 1 D-08 keeps functional metadata-wise even on macOS.
**Why it happens:** SC1's wording is scoped narrowly to the create/edit dialog; the settings-page kernel card is a distinct surface not covered by the discussed decisions.
**How to avoid:** Treat this as an **open question** rather than silently deciding either way — flag it to the user/planner: leave the AppSettings Firefox kernel card as-is (matches literal SC1 wording, and Phase 1 already made firefox metadata retrievable/downloadable cross-platform) unless the user wants it hidden/annotated too. Do not expand scope unilaterally during planning without a decision.
**Warning signs:** UAT reviewer navigates to Settings on macOS and finds a fully-interactive "download Firefox kernel" button, which — while consistent with locked decisions — may look inconsistent next to a Firefox-free profile creation flow. Worth a one-line callout when planning, not necessarily a code change.

## Code Examples

### Reading capabilities safely (optional chaining, no throw before bootstrap resolves)
```javascript
// Source: pattern consistent with existing store getters, frontend/src/stores/profile.js
const firefoxAvailable = computed(() => store.capabilities?.engines?.firefox?.available !== false)
const syncGate = computed(() => ({
  disabled: store.capabilities?.window?.sync?.available === false,
  reason: store.capabilities?.window?.sync?.reason || '',
}))
```

### Backend contract, verified verbatim (do not modify — Phase 3 already shipped and tested)
```python
# Source: backend/browser_manager.py:627-641 (read directly from this repo)
def get_platform_capabilities(self) -> dict[str, Any]:
    is_windows = sys.platform == "win32"
    arrange_reason = None if is_windows else "窗口排列仅在 Windows 上可用"
    sync_reason = None if is_windows else "窗口同步仅在 Windows 上可用"
    return {
        "platform": sys.platform,
        "engines": {
            "chrome": {"available": True},
            "firefox": {"available": is_windows},
        },
        "window": {
            "arrange": {"available": is_windows, "reason": arrange_reason},
            "sync": {"available": is_windows, "reason": sync_reason},
        },
    }
```

### xattr command already used server-side for the *kernel* bundle (for cross-reference only — UI-04's user-facing command targets the outer .app, not this)
```python
# Source: backend/services/chrome.py:157-168 (read directly from this repo)
# xattr -dr com.apple.quarantine <kernel .app bundle path>  — this strips quarantine
# from the bundled Chromium kernel automatically at launch time (Phase 3 D-07).
# UI-04's Gatekeeper guide is about a DIFFERENT quarantine flag: the one macOS puts
# on the downloaded Open-Anti-Browser.app itself (the outer app is unsigned/ad-hoc-signed
# per PKG-03, no Developer ID per DIST-01-deferred). The user-facing command should be
# framed around /Applications/Open-Anti-Browser.app (or wherever the user installs it),
# not the kernel path — do not conflate the two in UI-04's copy.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Right-click app icon → "Open" → confirm, to bypass "unidentified developer" Gatekeeper block | Must open the app once (gets blocked) → System Settings → Privacy & Security → Security section → **"Open Anyway"** → authenticate with password | macOS Sequoia (2024) removed the right-click bypass path for apps blocked as being from an unidentified developer [CITED: iboysoft.com/tips/allow-apps-to-run-sequoia.html, mackeeper.com/blog] | UI-04's copy must describe the **System Settings → Privacy & Security → Open Anyway** flow, not the older "right-click → Open" instruction, since it will read as broken/wrong on any Mac running Sequoia or later. |

**Deprecated/outdated:** The classic "control-click the app, choose Open, click Open again" instruction is no longer reliable as the *primary* path starting with macOS Sequoia for apps that are unsigned/not from an identified developer — Apple's own current guide (support.apple.com/guide/mac-help/mh40616/mac) frames the flow as: trigger the block once, then go through System Settings > Privacy & Security > Open Anyway [CITED: support.apple.com/guide/mac-help/mh40616/mac]. Recommend the planner have the UI-04 copy present **both** steps in sequence (open once to trigger the block, then go to System Settings) rather than only the old right-click shortcut.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Defaulting `engineOptions`/gating computeds to "available" (not hidden) when `capabilities` is still `{}` (pre-bootstrap) is the safer default vs. defaulting to hidden | Pattern 2 | Low — only affects a single render tick before bootstrap resolves; wrong choice causes a brief flicker, not a functional bug either way. Confirm preference with planner/user. |
| A2 | The exact current (post-Sequoia) Gatekeeper "Open Anyway" wording/flow, sourced from WebSearch summaries and one WebFetch of Apple's guide page (partial fetch) | State of the Art / UI-04 copy | Medium — if Apple has since changed the exact button/menu labels again (macOS updates roughly yearly), the in-app instructions could describe stale UI. Recommend the planner have a human on a real Mac confirm the exact current wording before finalizing zh-CN/en-US copy, and revisit at Phase 6 (release docs) time. |

**If this table is empty:** N/A — see above; both entries are low/medium risk and don't block planning, but A2 in particular should get a quick human sanity-check against a real Mac before the copy is considered final (not before this phase can be planned/executed).

## Open Questions (RESOLVED)

1. **RESOLVED: Should `AppSettings.vue`'s existing Firefox kernel-management card be hidden/annotated on macOS too?**
   - **Resolution (plan-phase):** annotate, do not hide — followed by `04-05`, whose objective records the same call for `GroupManager.vue:36`'s per-group Firefox count (hiding would break group arithmetic and contradict D-01's「不删不藏」). Final sign-off deferred to the `04-06` human checkpoint.
   - What we know: SC1 and D-01 scope Firefox-hiding to the create/edit dialog, list filter, and App.vue badges/counts — not this settings card.
   - What's unclear: Whether leaving a fully-functional "download Firefox kernel" control visible on macOS settings is acceptable UX, or should get at least a "仅 Windows 支持" annotation matching the rest of the phase's spirit.
   - Recommendation: Default to leaving it untouched (matches locked decisions literally); planner may add a one-line annotation as low-cost discretion, but should not silently hide it (that would exceed CONTEXT.md's discussed scope without a decision record).

2. **RESOLVED: Exact edit-mode behavior for pre-existing Firefox profiles' engine field (Pitfall 3).**
   - **Resolution (plan-phase):** fully disable the engine control and retain the original value — implemented by `04-01` Task 2. Filtering the option out instead would leave `el-segmented` bound to a value absent from its options, and a naive save would silently rewrite `engine` to `chrome`, corrupting migrated Windows profiles.
   - What we know: D-01 requires such profiles stay visible + deletable + start-disabled; editing/duplicating is explicitly left to planner discretion.
   - What's unclear: Whether the engine `el-segmented` should be fully disabled in this case, or keep `'firefox'` conditionally in its options list.
   - Recommendation: Fully disable the engine control when editing a profile whose current engine is unavailable on this platform (simplest, least error-prone; avoids the "unselected/undefined value" render risk entirely).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Node built-in `node:test` (frontend); no framework config file exists — invoked directly [VERIFIED: codebase grep, frontend/package.json has no "test" script] |
| Config file | none — `node --test frontend/src/lib/` per CLAUDE.md |
| Quick run command | `node --test frontend/src/lib/` |
| Full suite command | `node --test frontend/src/lib/` (same — no separate "full" tier exists today) |

**Important existing constraint (from CLAUDE.md, verified against `frontend/src/lib/proxyBypass.test.js`):** the one existing frontend test does not import Vue/compile SFCs — it regex-extracts plain `function xxx(` declarations out of a `.vue` file's `<script setup>` block and runs them in a sandboxed `vm` context. Any new pure-logic helper this phase introduces (e.g. `hasSeenGatekeeperNotice`) should either live in a plain `.js` file under `frontend/src/lib/` (directly testable, no extraction needed — preferred) or, if it must live inside a `.vue` file's `<script setup>`, be declared with `function xxx(` (not `const xxx = () =>`) to stay extractable by this pattern.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Firefox hidden from create/edit engine selector & list filter when `capabilities.engines.firefox.available === false` | unit (pure logic, e.g. extracted `engineOptions`-equivalent helper) | `node --test frontend/src/lib/` | ❌ Wave 0 |
| UI-01 | Pre-existing firefox-engine profile row stays visible/deletable/start-disabled | manual-only (requires seeded profile fixture + rendered table; no component-mount test harness in this repo) | — | N/A — document manual UAT step |
| UI-02 | Sync/arrange nav+view controls disabled with reason text when `available === false` | unit (pure logic: `isNavDisabled`/`syncGate`-style helpers) | `node --test frontend/src/lib/` | ❌ Wave 0 |
| UI-03 | Settings card content present, zh-CN/en-US key parity | unit (i18n key-parity check) | `node --test frontend/src/lib/i18n-parity.test.js` (new) | ❌ Wave 0 |
| UI-04 | First-run modal shown once, gated by new independent localStorage key, zh-CN/en-US key parity | unit (localStorage gating helper logic) + same i18n-parity test as UI-03 | `node --test frontend/src/lib/` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `node --test frontend/src/lib/` (fast, < 5s given current suite size)
- **Per wave merge:** same command — no heavier "full suite" tier exists for frontend in this repo
- **Phase gate:** Full command green before `/gsd-verify-work`; UI-01's "existing firefox profile row" behavior and the actual Gatekeeper modal copy/flow are inherently visual/manual and should be covered by conversational UAT (`/gsd-verify-work`), not automated tests

### Wave 0 Gaps
- [ ] `frontend/src/lib/capabilitiesGating.js` (new, suggested name) — pure functions: `isFirefoxOptionVisible(capabilities, currentEngine)`, `getWindowFeatureGate(capabilities, feature)` — extracted from/backing the component logic, directly unit-testable without the extraction-regex trick
- [ ] `frontend/src/lib/macosGatekeeperNotice.js` (new) — `hasSeenGatekeeperNotice()` / `markGatekeeperNoticeSeen()`, directly testable
- [ ] `frontend/src/lib/i18n-parity.test.js` (new) — deep-compares `Object.keys` of `zh-CN.js` vs `en-US.js` default exports, catching missing-translation regressions for UI-03/UI-04 and any future i18n addition
- [ ] No pytest/unittest gap on the backend side — this phase makes zero backend changes; `tests/test_capabilities_api.py` already covers the contract this phase depends on

## Security Domain

**`security_enforcement`:** absent from `.planning/config.json` → treated as enabled per protocol, but this phase introduces no new trust boundary, no new user input, no secrets, and no authentication/session surface. It conditionally renders existing UI based on a read-only, already-authenticated-by-nothing (local-only `/api/*`, no auth per CLAUDE.md) capabilities flag. ASVS categories are assessed but largely not applicable:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No new auth surface; `/api/*` remains unauthenticated local API per existing architecture. |
| V3 Session Management | No | No session state introduced. |
| V4 Access Control | No | Gating is a UX affordance, not an access-control boundary — the backend already independently rejects window-arrange/sync calls on non-Windows (`XPLAT-02`, Phase 1, tested). Frontend hiding must not be treated as the enforcement point; it already isn't (verified: backend gate exists independently in `window_manager.py`/`synchronizer.py`). |
| V5 Input Validation | Marginal | The only "input" this phase adds is reading `localStorage` keys it itself writes — no external/untrusted input parsing. No new validation library needed. |
| V6 Cryptography | No | Not applicable. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via `dangerouslyUseHTMLString` in the new Gatekeeper `ElMessageBox.alert` (mirroring the existing open-source notice's HTML string pattern, `App.vue:480-487`) | Tampering/Elevation (of DOM content) | Content is 100%-static, developer-authored i18n copy (no user/API-sourced text interpolated into the HTML string) — same safety property the existing notice already relies on. Keep it that way: do not interpolate any dynamic/user-controlled value into the modal's HTML string. |

## Sources

### Primary (HIGH confidence)
- Direct file reads, this repository: `backend/browser_manager.py` (bootstrap, get_platform_capabilities, get_engine_statuses), `backend/main.py` (bootstrap/capabilities routes), `backend/_g.py` (integrity hash mechanism), `backend/services/chrome.py` (quarantine-strip precedent), `frontend/src/stores/profile.js`, `frontend/src/components/{App,ProfileDialog,ProfileList,SyncManager,AppSettings}.vue`, `frontend/src/lib/openSourceNotice.js`, `frontend/src/assets/global.css`, `frontend/src/i18n/{zh-CN,en-US}.js`, `frontend/src/lib/proxyBypass.test.js`, `tests/test_capabilities_api.py`, `frontend/package.json`, `.planning/config.json`
- `.planning/phases/04-frontend-platform-gating/04-CONTEXT.md` — locked decisions D-00 through D-04 and canonical code-location references (cross-verified against actual line numbers above; mostly accurate, minor drift noted where App.vue's "header-badges" label maps to the sidebar status-card in current code)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` (Phase 4 section)

### Secondary (MEDIUM confidence)
- [Open a Mac app from an unknown developer — Apple Support Guide](https://support.apple.com/guide/mac-help/mh40616/mac) [CITED] — current System Settings > Privacy & Security > Open Anyway flow, fetched via WebFetch summary
- [Allow Apps from Anywhere on macOS Sequoia — iBoysoft](https://iboysoft.com/tips/allow-apps-to-run-sequoia.html) [CITED] — confirms Sequoia removed the right-click bypass for unidentified-developer blocks
- [Cannot Be Opened Because It Is from an Unidentified Developer — MacKeeper](https://mackeeper.com/blog/cannot-be-opened-because-it-is-from-an-unidentified-developer/) [CITED] — corroborating secondary source on the System Settings flow and "available for about an hour" detail

### Tertiary (LOW confidence)
- None used as a basis for any claim in this document beyond what's cited above.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all patterns verified directly against this codebase.
- Architecture: HIGH — every file/line reference in this document was read directly this session, not assumed from CONTEXT.md alone.
- Pitfalls: HIGH for Pitfalls 1/2/3/4 (all derived from direct code inspection); MEDIUM for the exact wording of Pitfall/State-of-the-Art's Gatekeeper flow (CITED, not independently verified on a physical Mac this session).

**Research date:** 2026-07-27
**Valid until:** 30 days for the codebase-internal findings (stable, phase is about to be planned/executed); the Gatekeeper macOS-version-specific UI wording (State of the Art section) should be re-confirmed against a real Mac before Phase 6 (release docs) if more than ~2 months elapse, since Apple's Gatekeeper UX has shifted roughly yearly.
