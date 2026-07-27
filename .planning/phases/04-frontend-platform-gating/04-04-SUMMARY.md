---
phase: 04-frontend-platform-gating
plan: 04
subsystem: ui
tags: [vue3, i18n, capabilities-contract, platform-gating, element-plus]

# Dependency graph
requires:
  - phase: 04-frontend-platform-gating (plan 01)
    provides: "capabilitiesGating.js — getWindowFeatureGate(capabilities, feature) as the D-00 single source of truth for sync/arrange gating"
  - phase: 04-frontend-platform-gating (plan 02)
    provides: "24 bilingual i18n leaf keys (platformLimits.*, syncer.*, gatekeeper.*) and macosGatekeeperNotice.js's buildGatekeeperNoticeHtml(t) / GATEKEEPER_XATTR_COMMAND"
provides:
  - "SyncManager.vue: syncGate/arrangeGate computed, top platform banner (el-alert, non-closable) rendering backend reason verbatim, all sync-replayed and win32 window-management actions individually gated"
  - "AppSettings.vue: macOS-only platform-limits card (platformLimitsVisible) listing three concrete unavailable features with the verbatim xattr command, openGatekeeperGuide() re-view entry shared with the future first-run modal, Firefox card 'Windows only' badge"
affects: [04-05, 04-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SyncManager.vue's first Vue-i18n usage: useI18n() introduced alongside two purpose-built computed (syncGate/arrangeGate) as the file's only platform-gating entry points; the rest of the file's ~1400 lines of hardcoded Chinese are intentionally left untouched (scope boundary, not a regression)"
    - "Backend capabilities.window.*.reason strings are bound verbatim (never wrapped in t()); only the surrounding banner/tooltip chrome and the empty-reason fallback (platformLimits.windowsOnlyFallback) go through i18n"
    - "AppSettings.vue's platform-limits card and Firefox-card badge share one computed (platformLimitsVisible) so both react to the same capabilities.platform !== 'win32' condition with zero duplication"

key-files:
  created: []
  modified:
    - frontend/src/components/SyncManager.vue
    - frontend/src/components/AppSettings.vue

key-decisions:
  - "syncGate/arrangeGate are independent computed, each calling getWindowFeatureGate(store.capabilities, 'sync'|'arrange') exactly once — no cross-fallback between the two features, matching the backend's independent booleans (browser_manager.py get_platform_capabilities)"
  - "Banner de-duplicates by comparing the two gates' raw .reason strings (not the fallback-resolved display text) before deciding whether to render a second line — this naturally collapses to one line when both reasons are empty (both fall back to the same generic text) while still showing two distinct lines when the backend supplies two different real reasons"
  - "Only 4 buttons get an explicit reason-carrying el-tooltip (the 3 hero sync buttons + the dedicated 一键排列 button in the windows-management card) per the plan's explicit scope; every other gated control relies on the banner for explanation, avoiding a tooltip on every one of the 26 gated controls"
  - "AppSettings.vue's platform-limits card is macOS-only by design (platformLimitsVisible requires capabilities.platform to be truthy AND !== 'win32') — Windows users never see an empty 'no limitations' card, and the card stays hidden during the pre-bootstrap window before capabilities resolves"
  - "openGatekeeperGuide() calls buildGatekeeperNoticeHtml(t) with zero additional dynamic interpolation, reusing 04-02's HTML builder verbatim so the settings re-view path and 04-05's future first-run modal can never diverge in copy"
  - "The gatekeeper command is rendered through Vue text interpolation ({{ GATEKEEPER_XATTR_COMMAND }}) inside a <code> element, not v-html — the command string comes from a hardcoded module constant, not from any dynamic/API source, so no escaping is bypassed"

patterns-established:
  - "Any future feature-gated Vue file should follow the same shape: one computed per capability wired straight to getWindowFeatureGate, banner/tooltip binds the raw .reason with an i18n fallback for the empty case, and the rest of the file's existing content is left untouched unless it is itself part of the gated surface"

requirements-completed: [UI-02, UI-03]

coverage:
  - id: D1
    description: "Synchronizer view stays fully enterable on a machine where capabilities.window.sync.available === false: no v-if hides any existing button/panel/form item, only :disabled is added; a non-closable top banner explains the limitation using the backend's verbatim reason string."
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "node --input-type=module inline check from PLAN.md verify block — printed 'SyncManager gating OK sync=22 arrange=12'"
        status: pass
      - kind: other
        ref: "git diff frontend/src/components/SyncManager.vue | grep '^+.*v-if' — all 3 new v-if occurrences are inside the new el-alert banner block only; grep -c 'const syncGate = computed(' / 'const arrangeGate = computed(' both = 1; getWindowFeatureGate(store.capabilities, 'sync'|'arrange') each = 1"
        status: pass
    human_judgment: true
    rationale: "The plan's acceptance criteria explicitly call for a macOS-machine visual/interaction pass (orange banner rendering the exact backend string, buttons visibly greyed, group filter/settings popover still interactive) — this was not screenshot-verified in this non-interactive execution session; the underlying computed/template wiring is fully unit- and grep-asserted."
  - id: D2
    description: "syncGate and arrangeGate read capabilities.window.sync / capabilities.window.arrange independently with no cross-fallback; sync-replayed actions (start/restart/stop sync, text actions, tab actions, batch open URLs) are gated by syncGate, win32 window-management actions (show windows, uniform size, arrange) are gated by arrangeGate, and purely local-state controls (group filter, master selection, sync-settings popover toggles/inputs, panel segmented control, compact-panel switch) are left ungated."
    requirement: "UI-02"
    verification:
      - kind: unit
        ref: "node --input-type=module inline check counting syncGate.disabled (>=15, actual 22) and arrangeGate.disabled (>=7, actual 12) occurrences"
        status: pass
    human_judgment: false
  - id: D3
    description: "AppSettings.vue gains a macOS-only 'platform limits' card (3 concrete bullet items: Firefox kernel, window arrange/sync, Gatekeeper first-open) with the xattr command rendered verbatim via text interpolation, and a 'reopen Gatekeeper guide' button reusing buildGatekeeperNoticeHtml(t); the existing Chrome and Firefox kernel cards remain fully present and unhidden, with the Firefox card gaining only a non-destructive 'Windows only' info tag."
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "node --input-type=module inline check from PLAN.md verify block — printed 'AppSettings card OK' (asserts all required symbols/i18n keys present, no v-html, existing firefox/chrome titles still present)"
        status: pass
      - kind: other
        ref: "grep -c 'page-panel' frontend/src/components/AppSettings.vue: 3 -> 4 (net +1, exactly the new card); grep -c \"t('settings.firefoxTitle')\" = 1 with no v-if on that page-panel's root div; grep -c 'function openGatekeeperGuide(' = 1"
        status: pass
    human_judgment: true
    rationale: "The plan requires a bilingual (zh-CN + en-US) visual pass confirming the terminal command renders character-for-character (no HTML-entity escaping, no smart-quote substitution) and that clicking 'reopen guide' shows the same modal as the future first-run flow — this is a rendering/typography check that needs an actual browser, not performed in this non-interactive session."

duration: 20min
completed: 2026-07-27
status: complete
---

# Phase 4 Plan 4: Sync/Arrange View Gating and Platform Limits Card Summary

**SyncManager.vue's sync and window-arrange actions are individually disabled via two independent capability computed (syncGate/arrangeGate) behind a non-closable top banner rendering the backend's verbatim reason string, and AppSettings.vue gains a macOS-only "platform limits" card plus a Gatekeeper re-view entry that reuses 04-02's HTML builder verbatim.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-27
- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 2

## Accomplishments
- `SyncManager.vue`: introduced its first-ever `useI18n()` usage plus `syncGate`/`arrangeGate` computed (each a single call to `getWindowFeatureGate(store.capabilities, 'sync'|'arrange')`), then wired `|| syncGate.disabled` / `|| arrangeGate.disabled` into 26 existing button `:disabled` expressions across the hero, console, compact panel, text panel, tabs panel, and batch-open-urls sections — without hiding any existing button, panel, or form item.
- Added a non-closable `el-alert` banner (`v-if="syncGate.disabled || arrangeGate.disabled"`) at the top of `sync-page`, rendering the backend's raw `reason` string(s) verbatim (never passed through `t()`), de-duplicated when both gates carry the same reason, with a local i18n fallback (`platformLimits.windowsOnlyFallback`) for the empty-reason case so the banner is never empty.
- Wrapped the 4 most prominent entry points (hero's 启动同步/重启同步/停止同步 + the dedicated windows-panel 一键排列 button) in `el-tooltip`s that show the same verbatim reason when their gate is disabled.
- `AppSettings.vue`: added a `platformLimitsVisible` computed (`capabilities.platform` truthy and `!== 'win32'`) gating a new "平台限制说明" card that lists 3 concrete unavailable features and renders the `GATEKEEPER_XATTR_COMMAND` module constant via text interpolation inside a `<code>` element (no `v-html`).
- Added `openGatekeeperGuide()`, calling `ElMessageBox.alert(buildGatekeeperNoticeHtml(t), ...)` — the exact same HTML builder 04-05's first-run modal will use, guaranteeing the two surfaces never diverge in copy.
- Existing Chrome and Firefox kernel cards left completely untouched structurally; Firefox card gained only a `v-if="platformLimitsVisible"` "仅 Windows 可用" info tag next to its existing status tag.

## Task Commits

Each task was committed atomically:

1. **Task 1: 同步器视图的平台横幅与全量动作按钮门控** - `2d20977` (feat)
2. **Task 2: 设置页新增平台限制说明卡片与放行指引重看入口** - `1192da8` (feat)

## Files Created/Modified
- `frontend/src/components/SyncManager.vue` - `useI18n`/`t` introduced; `syncGate`/`arrangeGate` computed; top platform banner; 26 button `:disabled` expressions extended; 4 tooltips added
- `frontend/src/components/AppSettings.vue` - `platformLimitsVisible` computed; `openGatekeeperGuide()`; new platform-limits `page-panel` card; Firefox card "Windows only" badge; scoped `<style>` block added (file previously had none) for `.panel-tag-group` / `.platform-limits-list` / `.platform-limits-command`

## Final Button Dispatch List (SyncManager.vue)

**Gated by `syncGate.disabled`** (sync-replayed actions, 17 controls):
1. Hero 启动同步 (`startSync`)
2. Hero 重启同步 (`restartSync`)
3. Hero 停止同步 (`stopSync`)
4. Console 启动同步 (`startSync`)
5. Console 重启同步 (`restartSync`)
6. Console 停止同步 (`stopSync`)
7. Compact panel 关闭空白页 (`close_blank`)
8. Text panel 清空内容 (`clear`)
9. Text panel 相同内容 quick action (`same`)
10. Text panel 输入随机数字 (`random`)
11. Text panel "相同文本" 输入 button (`same`)
12. Text panel 执行输入 (`designated`)
13. Tabs panel 统一标签页 (`unify_tabs`)
14. Tabs panel 关闭其他 (`close_others`)
15. Tabs panel 关闭当前 (`close_current`)
16. Tabs panel 关闭空白页 (`close_blank`)
17. 批量打开 (`openUrls`)

**Gated by `arrangeGate.disabled`** (win32 window-management actions, 9 controls):
1. List head 显示窗口 (`showWindows`)
2. List head 统一大小 (`uniformSize`)
3. Per-row inline 显示窗口 tooltip button (`showWindows([row.id])`)
4. Compact panel 显示窗口
5. Compact panel 统一大小
6. Compact panel 一键排列 (`arrangeWindows`)
7. Windows-panel quick actions 显示窗口
8. Windows-panel quick actions 统一大小
9. Windows-panel dedicated 一键排列 (`arrangeWindows`, wrapped in `el-tooltip`)

**Not gated** (local-only state, per plan's explicit exclusion — disabling would violate D-02 "don't hide, don't block reading"):
- 分组筛选下拉 (`groupFilter` select)
- 设为主控 (`setMaster`)
- 同步设置弹层（`el-popover`）里的全部开关、延迟输入框、快捷键输入框
- `activePanel` 分段器 (windows/text/tabs)
- `compactPanel` switch
- 相同文本/批量网址的文本输入框本身，以及"首个网址在当前标签页打开" switch
- 指定文本组的"添加文本组"/"删除"按钮（纯本地状态操作）

## Platform Limits Card — Final Copy (for 04-06 human wording check)

**zh-CN:**
- 标题: `平台限制说明`
- 描述: `当前系统上，部分功能暂不可用，具体见下方列表`
- 条目 1 (Firefox): `Firefox 指纹内核暂无 macOS 构建，新建配置仅提供 Chrome；已有的 Firefox 配置会保留，但无法在当前系统启动`
- 条目 2 (窗口): `窗口排列与窗口同步依赖 Windows 专有接口，在当前系统不可用`
- 条目 3 (Gatekeeper): `本应用未经 Apple 签名，首次打开需要手动放行` + 逐字命令 `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app`
- 按钮: `重新查看放行指引`
- Firefox 卡片标签: `仅 Windows 可用`
- 横幅标题 (`syncer.platformBannerTitle`): `同步器在当前系统不可用`
- 横幅提示 (`syncer.platformBannerHint`): `可到「设置 → 平台限制说明」查看详情`
- 空 reason 兜底 (`platformLimits.windowsOnlyFallback`): `该功能仅在 Windows 上可用`

**en-US:**
- Title: `Platform Limitations`
- Description: `Some features are unavailable on the current system. See the list below.`
- Item 1 (Firefox): `The Firefox fingerprint engine has no macOS build. New profiles only offer Chrome; existing Firefox profiles are kept but cannot be launched on the current system.`
- Item 2 (Window): `Window arrangement and window sync rely on Windows-only interfaces and are unavailable on the current system.`
- Item 3 (Gatekeeper): `This app is not signed by Apple. The first launch requires manual approval.` + verbatim command `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app`
- Button: `View Gatekeeper Guide Again`
- Firefox card tag: `Windows only`
- Banner title: `Synchronizer is unavailable on the current system`
- Banner hint: `See Settings → Platform Limitations for details.`
- Empty-reason fallback: `This feature is only available on Windows.`

All copy above names the specific unavailable feature (Firefox kernel, window arrange/sync, first-open approval) — none of it states or implies the app doesn't support macOS as a whole, satisfying the plan's prohibition.

## Decisions Made
- Chose the windows-panel's dedicated `一键排列` button (not the compact-panel one) as the 4th tooltip-wrapped "most prominent" entry, since it sits inside a dedicated `type="primary"` card specifically about window arrangement, matching the plan's framing of "四个最显眼的入口" alongside the 3 hero buttons.
- Added a minimal `<style scoped>` block to `AppSettings.vue` (the file previously had none) for `.panel-tag-group` (flex row so the new "Windows only" tag sits cleanly beside the existing engine-status tag instead of being spread apart by `panel-title-row`'s `justify-content: space-between`), `.platform-limits-list`, and `.platform-limits-command` — all new classes scoped to this file, no existing selectors touched.
- Both new computed properties (`syncGate`/`arrangeGate` in SyncManager.vue, `platformLimitsVisible` in AppSettings.vue) read exclusively from `store.capabilities`, never from `navigator.platform`/`navigator.userAgent`, preserving D-00's single-source-of-truth contract (verified via grep, 0 matches in both files).

## Deviations from Plan

None - plan executed exactly as written. The one open question in the plan's `<action>` text — "统一打开网址区域的同步打开与同步主标签页当前网址按钮" — was resolved by gating the one concrete button that exists in that section (`批量打开` / `openUrls`); no second button by that description exists in the current file, and the plan's own line-numbered enumeration elsewhere in the same task matched the file exactly, so no architectural question arose. This did not require a Rule 4 checkpoint since the acceptance criteria's `sd >= 15` threshold was already satisfied by the concrete, unambiguous button list (actual: 22, 26 gated controls total).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 04-05 (App.vue nav gating + first-run modal mount) can now safely wire `shouldShowGatekeeperNotice`/`markGatekeeperNoticeSeen` in `App.vue`'s `onMounted`, calling the same `buildGatekeeperNoticeHtml(t)` this plan's `openGatekeeperGuide()` already uses — the two surfaces are guaranteed to render identical copy.
- 04-06's human wording pass has the exact final zh-CN/en-US card copy captured above (no need to re-open the files to extract it).
- Both `.disabled` grep counts (22 sync, 12 arrange) exceed the plan's minimum thresholds (15/7) comfortably, leaving headroom if 04-05 or a future plan needs to add one more gated control without re-auditing the whole file.
- `backend/_g.py`'s integrity check (`python3 -m backend._g --mode build`) still exits 0 — `App.vue` and `openSourceNotice.js` were never touched by this plan.

---
*Phase: 04-frontend-platform-gating*
*Completed: 2026-07-27*

## Self-Check: PASSED

All 3 files (`SyncManager.vue`, `AppSettings.vue`, this SUMMARY) and both task commit hashes (`2d20977`, `1192da8`) verified present.
