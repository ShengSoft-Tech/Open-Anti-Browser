# Phase 4: 前端平台门控 - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

让 macOS 用户在界面上只看到与当前平台能力匹配的选项,并获得清晰的平台差异说明与首次运行放行指引。覆盖需求 UI-01、UI-02、UI-03、UI-04。

**门控信号源(已就绪,前端只需消费):** Phase 3 已把 capabilities 块并入 `GET /api/bootstrap`(也有独立 `GET /api/capabilities`),形状固定:
- `capabilities.engines.chrome.available` / `capabilities.engines.firefox.available`(macOS 上 firefox=false,与 `installed`/`capability_ok` 正交)
- `capabilities.window.arrange.{available,reason}` / `capabilities.window.sync.{available,reason}`(macOS 上 available=false,reason 已含中文文案)

本 phase 是**纯前端工作**:读 capabilities 做门控 + 新增说明/放行文案。后端契约不动。

**不在本 phase:** 后端 capabilities 实现(Phase 3 已完成);CI dmg 打包(Phase 5);release 放行说明文档 DOCS-01/02(Phase 6);macOS 窗口排列/同步的实际实现(里程碑外)。

</domain>

<decisions>
## Implementation Decisions

### 门控信号源(基础决策,贯穿 UI-01/02)
- **D-00:** 前端门控**统一消费 capabilities API**(经 bootstrap 返回的 `data.capabilities`),不在前端硬编码 `sys.platform` / `navigator.platform` 判断。当前 `stores/profile.js:180 bootstrap()` 只取了 settings/profiles/engines/downloads,**未取 capabilities**——需新增一个响应式 `capabilities` ref 并在 bootstrap 里赋值,作为所有门控组件的单一事实源。 — **Reversibility:** costly — capabilities 是 Phase 3→4 的硬接口,UI-01/UI-02 都读它的布尔字段;若改成硬编码平台判断,后续 CDP-only 跨平台同步(SYNC-01)放开时需逐处改回。

### Firefox 隐藏范围(UI-01)
- **D-01:** macOS 上采取**入口全隐 + 既有配置禁用保留**:
  - **入口全部隐藏 Firefox**——ProfileDialog 引擎选择器(`engineOptions`)、ProfileList 列表筛选 Tab 的 Firefox 选项、App.vue 顶部引擎状态徽章/计数中的 Firefox 项,在 `capabilities.engines.firefox.available===false` 时全部隐藏。
  - **既有 firefox-engine 配置不删不藏**——从 Windows 迁移来、profiles.json 里已存在的 firefox 配置(Phase 1 D-08 要求它们在 macOS 能加载)**仍显示在列表中**,带「仅 Windows」类标记,**禁用启动**(编辑/复制是否一并禁由 planner 定),但**保留可见与可删除**,不静默丢数据。
  - 判定依据:UI-01 验收只要求"创建/编辑配置界面完全不出现 Firefox 选项",列表里显示一个禁用的既有 firefox 配置不违反该验收。 — **Reversibility:** reversible — 纯前端条件渲染。

### 窗口同步/排列置灰(UI-02)
- **D-02:** **侧栏置灰 + 视图内横幅**双层呈现(Roadmap 明确要求"置灰+提示,不隐藏"):
  - **导航层**:App.vue `navItems` 里的 `syncer` 项在 macOS 置灰,hover tooltip 直接用 `capabilities.window.sync.reason`(「窗口同步仅在 Windows 上可用」)。
  - **视图层**:进入 SyncManager 视图后,顶部一条 banner 说明"仅 Windows 可用",视图内的同步/排列控件全部禁用。
  - reason 文案**读 capabilities 字段,不在前端另写**(后端已固定「窗口排列仅在 Windows 上可用」/「窗口同步仅在 Windows 上可用」)。 — **Reversibility:** reversible。

### macOS 限制说明承载(UI-03)
- **D-03:** 说明内容放在**设置页(AppSettings.vue)新增一张「平台限制 / macOS 说明」卡片**,不新增侧栏导航项。该卡片是限制说明的"永久家":UI-02 的置灰 banner 和 UI-04 的首启放行弹窗都可指向它随时回查。文案 zh-CN + en-US 双份。是否在 Windows 上也显示该卡片(macOS-only vs 平台自适应说明)由 planner 定,默认至少 macOS 上有内容。 — **Reversibility:** reversible。

### 首次运行放行指引(UI-04)
- **D-04:** **首启模态弹窗 + 独立 localStorage key**:
  - macOS 首次运行时弹一次模态,内容 = Gatekeeper「仍要打开」分步指引 + `xattr -dr com.apple.quarantine` 终端命令。
  - 用**新的独立 localStorage key**(建议 `oab:macos-gatekeeper-notice:v1`)记忆"已看过",**复用现有首启弹窗模式但不碰被 `_g.py` 锁定的 `openSourceNotice.js`**——另起独立组件/key。
  - 看过之后可从 UI-03 的设置卡片随时再查。
  - 与 Phase 6 的 release notes 放行说明是**两处不同载体**(本 phase = 应用内提示;Phase 6 = 发布文档),不混淆。 — **Reversibility:** reversible。

### Claude's Discretion
- 各处新增文案的确切措辞(zh-CN / en-US);UI-04 localStorage key 的最终命名。
- 既有 firefox 配置"禁用"的确切范围(启动必禁、删除必留;编辑/复制/导出是否禁 planner 定夺)。
- 门控在前端的落地形式(store computed getter / 组件内读 capabilities),只要满足 D-00 的"单一事实源、不硬编码平台"。
- macOS 首启若同时命中开源声明首启提示(现有 `oab:first-use-notice:v2`)与放行弹窗时的先后/叠加顺序。
- SyncManager 视图内 banner 与控件禁用的具体组件写法。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与范围(本仓库)
- `.planning/ROADMAP.md` — Phase 4 目标与 4 条成功标准(SC1 完全不出现 Firefox;SC2 置灰+「仅 Windows」提示不隐藏;SC3 应用内限制说明 zh/en 同步;SC4 首启 Gatekeeper 放行指引 zh/en 同步)
- `.planning/REQUIREMENTS.md` — UI-01 / UI-02 / UI-03 / UI-04 验收条件
- `.planning/PROJECT.md` — v0.2 约束(Windows 零回归、平台条件分支)与 Key Decisions

### 上游契约与决策(本仓库)
- `.planning/phases/03-macos-chrome-api/03-CONTEXT.md` — **capabilities API 契约**(D-01/D-02):端点形状、`available` 与 `installed`/`capability_ok` 正交、per-engine `available`、window `arrange/sync` 的 `available`+`reason`。这是本 phase 门控读取的硬接口。
- `.planning/phases/01-backend-cross-platform/01-CONTEXT.md` — D-08(firefox 在 macOS 保留于 ENGINE_METADATA、天然不可用、"隐藏"归前端);窗口功能错误文案风格(specifics:指向具体功能,勿让用户误读为整个应用不支持 mac)

### 工程约定(本仓库)
- `CLAUDE.md` — 前端约定(Element Plus unplugin 自动导入、Pinia、**新增用户可见文案必须同步 `i18n/zh-CN.js` 与 `i18n/en-US.js`,zh-CN 为默认**);**⚠ `backend/_g.py` 完整性校验:`frontend/src/App.vue` 与 `frontend/src/lib/openSourceNotice.js` 被 SHA-256 哈希锁定**(见 code_context landmine)

### 关键代码落点(勘察确认,full path + 行号)
- `backend/browser_manager.py:627-641` — `get_platform_capabilities`(契约源);`:75` `bootstrap()` 并入 capabilities 的位置
- `frontend/src/stores/profile.js:180-193` — `bootstrap()`(需新增 `capabilities` 消费);`:108` `engines` ref 附近;`:153-154,174-175` chrome/firefox 计数
- `frontend/src/components/ProfileDialog.vue:532` — `engineOptions`(引擎选择器,UI-01 隐藏点);`:281-307` Firefox 指纹面板(随引擎隐藏天然不触发)
- `frontend/src/components/ProfileList.vue:21-27` — `filterEngine` 下拉的 Firefox option(UI-01);`:82,99` 行内 firefox 图标/标签(既有 firefox 配置的禁用呈现落点)
- `frontend/src/App.vue:203-211` — `navItems`(syncer 置灰,UI-02);`:72-74` header-badges Firefox 状态徽章(UI-01);`:432,439` `engineStatusText`/`engineTagType` firefox 分支;首启弹窗挂载点(UI-04)。**⚠ 被 `_g.py:18` 哈希锁定**
- `frontend/src/components/SyncManager.vue` — 整个 syncer 视图(UI-02 banner + 控件禁用)
- `frontend/src/components/AppSettings.vue` — UI-03 平台限制卡片落点
- `frontend/src/lib/openSourceNotice.js` — 现有首启弹窗模式参考(**⚠ 被 `_g.py:17` 哈希锁定,勿改**;UI-04 另起独立组件/key)
- `frontend/src/i18n/zh-CN.js` / `frontend/src/i18n/en-US.js` — 所有新增文案必须双份

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **capabilities 已在 bootstrap 返回**:`browser_manager.py:75` 已把 `get_platform_capabilities()`(:627-641)聚合进 bootstrap,前端只需在 `stores/profile.js` 里读 `data.capabilities`,无需新增后端请求。
- **首启弹窗模式已存在**:`openSourceNotice.js` + App.vue 挂载 + localStorage key `oab:first-use-notice:v2`(见 `_g.py:26` 解码)。UI-04 **复用这套"首启一次 + localStorage 记忆"模式**,但用**新独立组件 + 新 key**,不改被锁的 openSourceNotice.js。
- **Firefox 表面已定位齐全**:ProfileList 的 `filterEngine` 下拉、engine 列渲染;App.vue 的 header-badges 引擎状态、`engineStatusText`/`engineTagType`;store 的 chrome/firefox 计数——都是 UI-01 的隐藏落点。

### Established Patterns
- **用户可见文案双语**:`i18n/zh-CN.js` + `i18n/en-US.js`(zh-CN 默认),UI-02/03/04 新增文案必须两份齐全(SC3/SC4 明确要求 zh/en 同步)。
- **门控单一事实源**:capabilities 应集中读取(store getter),避免各组件散落 `platform` 判断——契合 D-00 与 Windows 零回归(Windows 上 capabilities 布尔全为可用,行为不变)。
- 窗口功能 `reason` 文案由后端提供,前端**读字段而非重写**,与 Phase 1/3 文案风格保持一致。

### Integration Points
- **⚠⚠ `_g.py` 哈希锁定 landmine(最高优先级)**:`frontend/src/App.vue` 被 `backend/_g.py:18` SHA-256 锁定。UI-01(header badges/计数)、UI-02(navItems syncer 置灰)、UI-04(首启弹窗挂载)**几乎必然改 App.vue** → planner/executor **必须**在改完 App.vue 后重算其 SHA-256 并更新 `_g.py:18` 的哈希值,否则 `npm run build`(prebuild/postbuild 钩子 `python -m backend._g`)与桌面启动(`launch_app.main` 调 `_7("runtime")`)都会失败。**且严禁移除开源声明本身**(首次使用提示是反商业滥用机制)。`openSourceNotice.js` 同样被锁——UI-04 不要动它。
- **store bootstrap 需接线 capabilities**:`stores/profile.js:180` 的 `bootstrap()` 目前不取 `data.capabilities`,需新增 `capabilities` ref 并赋值,作为门控源(D-00)。
- **capabilities 契约字段**:门控读 `capabilities.engines.firefox.available`(UI-01)、`capabilities.window.arrange.{available,reason}` 与 `capabilities.window.sync.{available,reason}`(UI-02)。

</code_context>

<specifics>
## Specific Ideas

- 窗口 tooltip/banner **直接复用 capabilities 的 reason 文案**:「窗口排列仅在 Windows 上可用」/「窗口同步仅在 Windows 上可用」(后端已给,前端读 `reason`,不另写死)。
- UI-04 建议 localStorage key:`oab:macos-gatekeeper-notice:v1`,与现有 `oab:first-use-notice:v2` 并列、互不干扰。
- 既有 firefox 配置在 macOS 的呈现:列表可见 + 「仅 Windows」标记 + 禁用启动,**保留删除能力**(不静默丢数据)。
- UI-03 设置卡片是限制说明的"永久家";UI-02 置灰 banner、UI-04 首启弹窗都链接过去。
- Firefox 隐藏基于 `capabilities.engines.firefox.available`,而非 `installed`/`capability_ok`(后者=内核路径是否存在,语义不同,勿混用)。

</specifics>

<deferred>
## Deferred Ideas

None — 讨论未越界。

**跨 phase 备忘(非新增 scope,仅提示 planner):**
- CI dmg 打包(Phase 5)、release notes 放行说明 DOCS-01/02(Phase 6)不在本 phase。UI-04 的**应用内**放行弹窗与 Phase 6 的**发布文档**放行说明是两处不同载体,内容可相互呼应但不合并。
- 是否把限制说明卡片在 Windows 上也显示为"平台差异总览":默认 macOS-only,planner 可按需扩展,属实现裁量而非新 capability。

</deferred>

---

*Phase: 4-前端平台门控*
*Context gathered: 2026-07-27*
