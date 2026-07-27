# Phase 4: 前端平台门控 - Pattern Map

**Mapped:** 2026-07-27
**Files analyzed:** 9 (4 modified existing, 3 new, 2 i18n files modified)
**Analogs found:** 9 / 9 (all in-repo; no external analogs needed — every touch point already has a same-file existing pattern to extend)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/stores/profile.js` (modify `bootstrap()`) | store | request-response (fetch + assign to reactive ref) | same file, `bootstrap()` lines 180-194 (self-analog: settings/engines/downloads wiring) | exact |
| `frontend/src/components/ProfileDialog.vue` (`engineOptions`) | component (form) | transform (static array → computed) | same file, `proxyTypeOptions` computed (line 537) | exact |
| `frontend/src/components/ProfileList.vue` (filter dropdown + row rendering) | component (list/table) | CRUD (read-only render + disable actions) | same file, existing `filterEngine`/`el-table-column` engine rendering (lines 20-28, 96-101) | exact |
| `frontend/src/App.vue` (`navItems`, header badges, engine status, first-run mount) | component (shell/layout) | event-driven (nav click) + request-response (bootstrap) | same file, `_0x31ab()` first-use-notice flow (lines 459-489) + `navItems`/`setActiveNav` (lines 203-212, 351-356) | exact |
| `frontend/src/components/SyncManager.vue` (banner + disabled controls) | component (view) | request-response | same file, existing `:disabled="!selectedRunningIds.length"` button pattern (lines 145, 149, 280-283) + `el-tooltip` pattern (lines 217-226) | exact |
| `frontend/src/components/AppSettings.vue` (new platform-limits card) | component (settings) | request-response | same file, existing `page-panel` card pattern (lines 23-41, the Firefox/Chrome engine cards) | exact |
| `frontend/src/lib/macosGatekeeperNotice.js` (new) | utility | event-driven (localStorage gate) | `frontend/src/lib/openSourceNotice.js` (shape/idiom only — **do not copy its base64 obfuscation**, it's a `_g.py` anti-tamper mechanism, not a general pattern) | role-match |
| `frontend/src/i18n/zh-CN.js` / `en-US.js` (new keys) | config (i18n dictionary) | transform | same files, existing nested key groups (`sidebar`, `settings`, `engine`, etc.) | exact |
| `frontend/src/lib/capabilitiesGating.test.js` / `i18n-parity.test.js` (new tests) | test | transform (pure function assertions) | `frontend/src/lib/proxyBypass.test.js` (full file — extraction-from-.vue-source idiom + `node:test`/`node:assert/strict` style) | exact |

## Pattern Assignments

### `frontend/src/stores/profile.js` (store, request-response)

**Analog:** same file, `bootstrap()` (lines 180-194)

**Current code** (lines 180-194):
```javascript
async function bootstrap() {
  loading.value = true
  try {
    const data = await api.get('/api/bootstrap')
    settings.value = data.settings
    profiles.value = data.profiles
    engines.value = data.engines
    downloads.value = data.downloads || {}
    await refreshApiInfo()
    await refreshSynchronizer()
    return data
  } finally {
    loading.value = false
  }
}
```

**Pattern to copy:** Add a new top-level `ref` next to the existing `settings`/`engines`/`downloads` refs (they're declared earlier in the same `setup()`-style store function, alongside line ~108's `engines` ref — read that neighborhood to match declaration style exactly), then assign it in `bootstrap()` the same way `downloads.value = data.downloads || {}` does (note the `|| {}` fallback — replicate that exact defensive-default idiom for `capabilities.value = data.capabilities || {}`, since components will do optional chaining like `store.capabilities?.engines?.firefox?.available` before the first bootstrap resolves). Must be exposed in the store's returned object (grep the `return { ... }` object at the bottom of `useProfileStore` to add `capabilities` alongside `settings`, `engines`, `downloads`).

**Error handling:** Same `try/finally` wrapping `loading.value` toggling — no separate error handling needed for this one field; if `api.get` throws, the whole `bootstrap()` call rejects as it already does for `settings`/`engines`.

---

### `frontend/src/components/ProfileDialog.vue` (component, engineOptions gating)

**Analog:** same file, `proxyTypeOptions` computed (line 537) — already shows the "static array → computed, gated by external state" idiom used elsewhere in this exact file.

**Current code to replace** (lines 532-535):
```javascript
const engineOptions = [
  { label: 'Chrome', value: 'chrome' },
  { label: 'Firefox', value: 'firefox' },
]
```

**Template usage (unchanged binding, line 27-30):**
```vue
<el-segmented
  v-model="form.engine"
  :options="engineOptions"
/>
```

**Core pattern (from RESEARCH.md Pattern 2, verified against store shape):**
```javascript
const engineOptions = computed(() => {
  const options = [{ label: 'Chrome', value: 'chrome' }]
  if (store.capabilities?.engines?.firefox?.available !== false) {
    options.push({ label: 'Firefox', value: 'firefox' })
  }
  return options
})
```

**Pitfall (see RESEARCH.md Pitfall 3 — must handle):** when editing an existing profile whose `form.engine === 'firefox'` but firefox is unavailable, `el-segmented`'s bound value won't be in `:options`. Recommended fix (RESEARCH.md's stated default): disable the entire `el-segmented` control in that specific edit-mode case rather than conditionally re-including `'firefox'` in the options array. `store` is already imported/available in this file (used elsewhere for settings/defaults) — confirm via existing `useProfileStore()` call at file top.

**Extractable-helper convention (for testability):** Since `proxyBypass.test.js` demonstrates the project's only existing frontend-test pattern — regex-extracting `function xxx(` declarations out of `<script setup>` — if the planner wants `engineOptions`'-equivalent logic unit-tested the same way, it must be written as a `function` declaration (not `const x = () =>`), OR (preferred per RESEARCH.md Wave 0 gap) extracted into a new plain module `frontend/src/lib/capabilitiesGating.js` with named exports, which is directly importable/testable without the extraction trick.

---

### `frontend/src/components/ProfileList.vue` (component, filter + row disable)

**Analog:** same file — filter dropdown (lines 20-28) and engine table-column rendering (lines 96-101).

**Current filter dropdown** (lines 20-28):
```vue
<el-select
  v-model="store.filterEngine"
  clearable
  :placeholder="t('profile.allEngines')"
  style="width: 140px"
>
  <el-option label="Chrome" value="chrome" />
  <el-option label="Firefox" value="firefox" />
</el-select>
```
**Pattern to copy:** Wrap the Firefox `<el-option>` in `v-if="store.capabilities?.engines?.firefox?.available !== false"`, mirroring the `engineOptions` computed's same-signed guard for consistency.

**Current row engine badge** (lines 96-101):
```vue
<el-table-column :label="t('profile.columns.engine')" width="110">
  <template #default="{ row }">
    <el-tag :type="row.engine === 'chrome' ? 'primary' : 'warning'" effect="plain" size="small">
      {{ row.engine === 'chrome' ? 'Chrome' : 'Firefox' }}
    </el-tag>
  </template>
</el-table-column>
```
**Pattern for D-01's "仅 Windows" tag:** Add a second, conditional `<el-tag type="info" size="small" v-if="row.engine === 'firefox' && store.capabilities?.engines?.firefox?.available === false">仅 Windows</el-tag>` (i18n-keyed) next to the existing engine tag — same `el-tag` idiom, no new component needed. Locate the row's Start-button and batch-start filter (per RESEARCH.md Pitfall 4, ~line 382 batch filter and the per-row start action) and add the same `capabilities.engines.firefox.available` gate to both, matching the existing `:disabled="..."` boolean-expression style already used for other row actions in this file.

**Imports pattern** (lines 235-236, unchanged, for context — chrome/firefox icon imports already exist and stay as-is since existing firefox profiles must still render their icon):
```javascript
import chromeIcon from '../assets/chrome.svg'
import firefoxIcon from '../assets/firefox.png'
```

---

### `frontend/src/App.vue` (component, nav gating + header/status + first-run modal)

**Analog:** same file — `navItems` array + `setActiveNav` (lines 203-212, 351-356), and the existing first-use-notice flow `_0x31ab()` (lines 459-489) as the shape template for the new Gatekeeper modal (different file/key, same idiom).

**⚠ CRITICAL:** `frontend/src/App.vue` is SHA-256 hash-locked in `backend/_g.py:16-19` (key `_1[b64("frontend/src/App.vue")] = "cfa6427a..."`). Any edit here (near-certain: navItems disabling, header Firefox badge/count removal, engine status text, first-run modal mount) **must** be followed by recomputing the file's SHA-256 and updating that exact dict entry in `_g.py`, or `npm run build` and `launch_app.main`'s `_7("runtime")` call will hard-fail. Do NOT touch the sibling locked entry for `openSourceNotice.js` (`_g.py:16`) at all.

**Current navItems** (lines 203-212):
```javascript
const navItems = [
  { key: 'profiles', icon: Monitor },
  { key: 'syncer', icon: Operation },
  { key: 'groups', icon: FolderOpened },
  { key: 'proxies', icon: Connection },
  { key: 'extensions', icon: Files },
  { key: 'apiAccess', icon: Link },
  { key: 'apiDocs', icon: Document },
  { key: 'settings', icon: Setting },
]
```
Current nav rendering (lines 16-27) has no disabled-state class today — `global.css` only defines `.nav-item`, `.nav-item:hover`, `.nav-item.active`. New `.nav-item.disabled` CSS rule needed there.

**Core disabling pattern (from RESEARCH.md Pattern 3, aligned to this file's actual template):**
```vue
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
    @click="setActiveNav(item.key)"
  >
    <el-icon><component :is="item.icon" /></el-icon>
    <span>{{ t(`nav.${item.key}`) }}</span>
  </div>
</el-tooltip>
```
`isNavDisabled('syncer')` → `store.capabilities?.window?.sync?.available === false`; `navDisabledReason('syncer')` → `store.capabilities?.window?.sync?.reason || ''` (read verbatim, do not re-wrap in `t()` — D-02 locked). **Do not block the click** — navigation into `SyncManager.vue` must still work so the view-level banner (D-02's second layer) is reachable.

**Header/status gating (Firefox hiding, UI-01), current code** (lines 71-76, sidebar status card):
```vue
<div class="status-row">
  <span>Firefox</span>
  <el-tag :type="engineTagType('firefox')" size="small">
    {{ engineStatusText('firefox') }}
  </el-tag>
</div>
```
**Pattern:** wrap this whole `<div class="status-row">` in `v-if="store.capabilities?.engines?.firefox?.available !== false"`.

**Existing engine helper functions** (lines 428-441, keep logic, just gate their call sites in template):
```javascript
function engineStatusText(engine) {
  const item = store.engines?.[engine]
  if (!item) return t('engine.unknown')
  if (!item.installed) return t('engine.notInstalled')
  if (engine === 'firefox' && !item.capability_ok) return t('engine.needFingerprintBuild')
  return t('engine.ready')
}

function engineTagType(engine) {
  const item = store.engines?.[engine]
  if (!item?.installed) return 'danger'
  if (engine === 'firefox' && !item.capability_ok) return 'warning'
  return 'success'
}
```
These do not need modification — only their firefox-row template call site needs the `v-if` guard above.

**First-run modal pattern to imitate (NOT to reuse directly)** — current `_0x31ab()` (lines 459-489):
```javascript
const _0x5c10 = 'oab:first-use-notice:v2'
// ...
async function _0x31ab() {
  if (localStorage.getItem(_0x5c10) === '1') {
    return
  }
  const notice = _0x91f3(languageCode.value)
  const html = `...`
  await ElMessageBox.alert(html, notice.title, {
    confirmButtonText: notice.confirmText,
    dangerouslyUseHTMLString: true,
    closeOnClickModal: false,
    closeOnPressEscape: false,
    showClose: false,
    customClass: 'first-use-notice-box',
  })
  localStorage.setItem(_0x5c10, '1')
}
```
Called in `onMounted` at line 295: `await _0x31ab()`, right after `await store.getBackendModeStatus()` and right before setting up polling timers. **New Gatekeeper modal must be a separate function reading a separate key** (`frontend/src/lib/macosGatekeeperNotice.js`, see below), invoked from `onMounted` immediately after `await _0x31ab()` so the two modals never overlap (per RESEARCH.md/CONTEXT.md discretion — open-source notice first, then Gatekeeper). Additionally gate on `store.capabilities?.platform !== 'win32'` (raw `sys.platform` string, confirmed present in backend response at `browser_manager.py:632`).

**Error handling:** the whole `onMounted` body is wrapped in one `try { ... } catch (error) { ElMessage.error(...) }` (lines 280-317) — the new modal call should sit inside that same try block, not add its own.

---

### `frontend/src/components/SyncManager.vue` (view, banner + disabled controls)

**Analog:** same file, existing disabled-button idiom (lines 145, 149, 272-274, 280-283) and `el-tooltip` idiom (lines 217, 222).

**Current disabled-button pattern** (line 12, hero action row):
```vue
<el-button type="primary" :disabled="selectedRunningIds.length < 2" :loading="submitting" @click="startSync">
  <el-icon><VideoPlay /></el-icon>
  启动同步
</el-button>
```
**Pattern to copy for UI-02:** OR the existing disable condition with the new capability gate, e.g. `:disabled="selectedRunningIds.length < 2 || store.capabilities?.window?.sync?.available === false"` — applied uniformly to `startSync`/`restartSync`/`stopSync`/`showWindows`/`uniformSize`/`arrangeWindows` buttons (lines 12-23, 145-151, 272-283, 303-304). Same treatment for the `arrange`-specific controls should read `store.capabilities?.window?.arrange?.available` where the action is arrangement-specific (`arrangeWindows`, "一键排列") vs. `window.sync.available` for sync-specific actions (`startSync`/`restartSync`/`stopSync`) — **do not conflate the two gates**, they are independent booleans in the capabilities contract.

**Existing tooltip idiom to imitate for the new banner's inline hints** (lines 217, 222):
```vue
<el-tooltip content="设为主控">
  <el-button circle text class="row-action" @click="setMaster(row.id)">
    <el-icon><Monitor /></el-icon>
  </el-button>
</el-tooltip>
```

**New banner (no existing analog in this file — new markup, first in file to use `useI18n`):** Add a top-of-view `<el-alert>` (Element Plus, not yet used elsewhere in this file but standard in the kit) shown `v-if="store.capabilities?.window?.sync?.available === false"`, with `:closable="false"` and content combining a new bilingual heading (`t('syncer.macNotAvailable')`) plus the raw backend reason string rendered verbatim (`{{ store.capabilities?.window?.sync?.reason }}`) — per D-02, do not wrap the reason itself in `t()`.

**Pitfall to flag:** This file has zero existing `useI18n`/`t()` usage (verified: no `useI18n` import). Adding `t()` calls for only the new banner/wrapper copy is expected and intentional (RESEARCH.md Pitfall 2) — it produces a mixed hardcoded-Chinese + new-i18n file, which is correct, not a regression to "fix" wholesale.

---

### `frontend/src/components/AppSettings.vue` (component, new platform-limits card)

**Analog:** same file, existing `page-panel` card structure (lines 33-41, the Firefox engine-status card).

**Current card pattern to copy** (lines 33-41):
```vue
<div class="page-panel">
  <div class="panel-title-row">
    <div>
      <h3>{{ t('settings.firefoxTitle') }}</h3>
      <p class="panel-desc">{{ t('settings.firefoxDesc') }}</p>
    </div>
    <el-tag :type="engineTag(store.engines.firefox)">{{ engineLabel(store.engines.firefox) }}</el-tag>
  </div>
</div>
```
**Pattern for the new "平台限制 / macOS 说明" card (UI-03):** Add a new sibling `<div class="page-panel">` with the same `panel-title-row` → `h3` + `panel-desc` structure, `v-if="store.capabilities?.platform !== 'win32'"` (or unconditional per the open discretion item — default macOS-only per CONTEXT.md D-03), listing the concrete restrictions (Firefox unavailable, window sync/arrange unavailable) using new i18n keys under a `settings.platformLimits*` or similar namespace, following the exact `t('settings.xxxTitle')` / `t('settings.xxxDesc')` naming convention already used for `chromeTitle`/`chromeDesc`/`firefoxTitle`/`firefoxDesc`.

**Imports/setup (unchanged, already present):**
```javascript
import { useI18n } from 'vue-i18n'
import { useProfileStore } from '../stores/profile.js'
const { t } = useI18n()
const store = useProfileStore()
```

---

### `frontend/src/lib/macosGatekeeperNotice.js` (new utility, event-driven localStorage gate)

**Analog (shape only, NOT content):** `frontend/src/lib/openSourceNotice.js` first-use-notice idiom (localStorage key + guard), as consumed from `App.vue`'s `_0x31ab()`. **Do not copy the base64/obfuscation mechanism** — that exists solely to satisfy `_g.py`'s SHA-256 anti-tamper lock and is irrelevant to this new, unlocked file. Write plain, readable strings.

**Recommended pattern (from RESEARCH.md Pattern 4, directly actionable):**
```javascript
// frontend/src/lib/macosGatekeeperNotice.js — new file, NOT hash-locked, safe to create/edit
const GATEKEEPER_NOTICE_KEY = 'oab:macos-gatekeeper-notice:v1'

export function hasSeenGatekeeperNotice() {
  return localStorage.getItem(GATEKEEPER_NOTICE_KEY) === '1'
}

export function markGatekeeperNoticeSeen() {
  localStorage.setItem(GATEKEEPER_NOTICE_KEY, '1')
}
```
Plain named-function exports (not arrow consts) keep this consistent with the project's one existing test-extraction convention, though since this is a standalone `.js` module (not embedded in a `.vue` `<script setup>`), it can be imported and tested directly — no regex extraction needed, unlike `proxyBypass.test.js`'s approach for in-SFC helpers.

**Consumed from `App.vue`'s `onMounted`,** using the same `ElMessageBox.alert(html, title, { dangerouslyUseHTMLString: true, ... })` shape as `_0x31ab()` (see App.vue section above) but with new, independent bilingual Gatekeeper copy (Sequoia-era "System Settings → Privacy & Security → Open Anyway" flow + `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app`-style command), gated by `hasSeenGatekeeperNotice()` / `markGatekeeperNoticeSeen()` instead of the raw `localStorage` calls the existing notice uses directly.

---

### `frontend/src/i18n/zh-CN.js` / `frontend/src/i18n/en-US.js` (config, new keys)

**Analog:** same files, existing nested-object key groups (e.g. `common`, `sidebar`, `settings`, `engine` — see `zh-CN.js` lines 1-40 for the exact nesting/naming style: camelCase leaf keys grouped under a lowercase section object).

**Pattern:** Add new keys under existing sections where semantically appropriate (`nav.*` already likely has a `syncer` entry — extend, don't duplicate), plus new sections as needed, e.g. `settings.platformLimitsTitle`, `settings.platformLimitsDesc`, `syncer.macNotAvailable`, `gatekeeper.title`, `gatekeeper.step1`, etc. — mirror exact structure 1:1 between the two files (this is what the new `i18n-parity.test.js` will assert). zh-CN is the default/reference locale per CLAUDE.md.

---

### `frontend/src/lib/*.test.js` (new tests)

**Analog:** `frontend/src/lib/proxyBypass.test.js` (full file, already read above) — demonstrates:
- `node:test` + `node:assert/strict` imports, no framework config
- For logic embedded in a `.vue` `<script setup>`: regex-extract `function xxx(` blocks via `extractFunction()` helper and `vm.runInNewContext`
- For logic in plain `.js` modules (preferred for new code per RESEARCH.md Wave 0 gap): standard ESM `import`, no extraction needed
- Test naming: descriptive full-sentence `test('...', () => { ... })` titles

**New test files to create, following this exact idiom:**
- `frontend/src/lib/capabilitiesGating.test.js` — tests for `isFirefoxOptionVisible(capabilities, currentEngine)` / `getWindowFeatureGate(capabilities, feature)` if extracted into `frontend/src/lib/capabilitiesGating.js`
- `frontend/src/lib/macosGatekeeperNotice.test.js` — tests for `hasSeenGatekeeperNotice()`/`markGatekeeperNoticeSeen()` (mock `localStorage` the way `proxyBypass.test.js` mocks nothing external — this new test will need a minimal `globalThis.localStorage` stub since Node's `node:test` has no browser `localStorage` by default)
- `frontend/src/lib/i18n-parity.test.js` — deep-compares `Object.keys` (recursively) of `zh-CN.js` default export vs `en-US.js` default export

**Run command (per CLAUDE.md):** `node --test frontend/src/lib/`

## Shared Patterns

### Capabilities single source of truth (D-00)
**Source:** `frontend/src/stores/profile.js` `bootstrap()` (new `capabilities` ref, to be added per this document's first section)
**Apply to:** `ProfileDialog.vue`, `ProfileList.vue`, `App.vue`, `SyncManager.vue`, `AppSettings.vue` — every gating decision reads `store.capabilities?.<path>`, always optional-chained (capabilities is `{}` before first bootstrap resolves), never `navigator.platform` / `sys.platform` re-derivation on the client.
```javascript
// safe-read idiom, apply everywhere:
store.capabilities?.engines?.firefox?.available   // !== false to show, === false to hide/disable
store.capabilities?.window?.sync?.available        // === false to disable
store.capabilities?.window?.sync?.reason            // render verbatim, no t() wrapping
store.capabilities?.window?.arrange?.available      // independent from .sync
store.capabilities?.platform                        // raw sys.platform string, e.g. 'darwin'/'win32'
```

### Backend contract (read-only, already shipped — do not modify)
**Source:** `backend/browser_manager.py:627-641`
```python
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
Already merged into `GET /api/bootstrap` at `browser_manager.py:75` (`"capabilities": self.get_platform_capabilities()`). No backend change needed this phase.

### `_g.py` hash-lock relock procedure (mandatory for every plan touching App.vue)
**Source:** `backend/_g.py:14-18`
```python
def _0(v: str) -> str:
    return base64.b64decode(v).decode("utf-8")

_1 = {
    _0("ZnJvbnRlbmQvc3JjL2xpYi9vcGVuU291cmNlTm90aWNlLmpz"): "2a766eeea1648831555dd1f5d00896ac507f6441a0b0e86cf9326617f14e4eff",
    _0("ZnJvbnRlbmQvc3JjL0FwcC52dWU="): "cfa6427a0c0f17357a41888128ed7d391c2efde62214304d9654027250886104",
}
```
**Apply to:** any plan/task editing `frontend/src/App.vue`. Last step of that task must be: compute `hashlib.sha256(Path('frontend/src/App.vue').read_bytes()).hexdigest()` and replace the value for the `frontend/src/App.vue` key in this dict (the first key, `openSourceNotice.js`, must remain untouched — no plan in this phase edits that file). Verify with `python -m backend._g` (or `npm run build`) before marking the task done.

### i18n bilingual parity (CLAUDE.md hard rule)
**Source:** `frontend/src/i18n/zh-CN.js` + `frontend/src/i18n/en-US.js`
**Apply to:** every new user-visible string in `App.vue` (nav tooltip wrapper text — NOT the raw `reason` field), `SyncManager.vue` banner, `AppSettings.vue` new card, and the new Gatekeeper modal component. zh-CN is the default/reference locale — add keys there first, then mirror in en-US.

### Disabled-control + reason hint (`el-tooltip` / native `disabled`)
**Source:** `frontend/src/components/SyncManager.vue:145,149,217,222` (already-established idiom in this codebase)
**Apply to:** `App.vue` nav item (new), `SyncManager.vue` action buttons (extend existing `:disabled` expressions), `ProfileList.vue` Start button for legacy firefox rows.

## No Analog Found

None. Every file in scope for this phase has a directly analogous existing pattern in the same file (or, for the two genuinely new files — `macosGatekeeperNotice.js` and the test files — a same-shape sibling file in `frontend/src/lib/`) to extend. This is expected: RESEARCH.md's "Key insight" notes this phase is pure conditional-rendering work with zero new architecture.

## Metadata

**Analog search scope:** `frontend/src/{stores,components,lib,i18n}/`, `backend/browser_manager.py`, `backend/_g.py`
**Files scanned:** `stores/profile.js`, `components/{App,ProfileDialog,ProfileList,SyncManager,AppSettings}.vue`, `lib/openSourceNotice.js`, `lib/proxyBypass.test.js`, `i18n/zh-CN.js`, `backend/browser_manager.py`, `backend/_g.py`
**Pattern extraction date:** 2026-07-27
