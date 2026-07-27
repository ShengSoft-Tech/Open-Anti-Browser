# Phase 3: macOS Chrome 启动与能力 API - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

让 macOS 用户完整走通"创建 Chrome 配置 → 启动指纹 Chrome → 用代理/扩展/批量启动 → 停止"核心链路,并让后端暴露平台能力(capabilities)供前端(Phase 4)门控消费。覆盖需求 LAUNCH-01、LAUNCH-02、LAUNCH-03、XPLAT-05。

**关键事实(勘察确认):** 启动链路代码 `backend/services/chrome.py:launch_chrome_profile` 已是跨平台写法——直接 `Popen` 由 `bundled_engine_executable("chrome")` 解析出的 `Chromium.app/Contents/MacOS/Chromium`(Phase 1 D-06 已锁定路径),不经 `open -a`;`kill_process_tree`(network.py)走 psutil 递归子进程(跨平台);`get_engine_statuses()` 已返回 per-engine `installed`/`capability_ok`,`bootstrap()` 已聚合 engines。因此本 phase 的实际工作 = **在 macOS 上验证并补齐这条链路的边角(进程终止/quarantine)+ 新增能力 API**,而非从零实现启动。

**已锁定继承项(不再讨论):** 启动机制 = 直接 Popen 嵌套二进制(ROADMAP SC1 + Phase 1 D-06);Chrome 可执行路径 = `Chromium.app/Contents/MacOS/Chromium`;Firefox 在 macOS 保留于 `ENGINE_METADATA`、天然不可用,"隐藏"归 Phase 4(Phase 1 D-08);联调至少需一份本机内核——Phase 2 已发布 arm64/x64 到 `kernel-149.0.7827.114`。

**不在本 phase:** 前端隐藏 Firefox / 置灰窗口功能 / 平台说明 / 首次运行放行指引(Phase 4);CI dmg 打包(Phase 5);发布文档与真机端到端 Intel 原生验证(Phase 6);macOS 窗口排列/同步(里程碑外)。

</domain>

<decisions>
## Implementation Decisions

### 能力 API(capabilities API,XPLAT-05)
- **D-01:** 新增 `GET /api/capabilities` **独立端点**,并把同一 capabilities 块**并入 `bootstrap()`** 返回。前端启动时经 bootstrap 一次拿到(bootstrap 已聚合 engines/settings/profiles/downloads),运行时也可单独查询该端点。选此形态以对齐 ROADMAP SC4 明确写的 `GET /api/capabilities` 措辞,同时避免前端为门控额外多发一次请求。 — **Reversibility:** costly — capabilities 契约被 Phase 4 前端门控直接消费(读布尔字段),字段名/语义一旦定型,Phase 4 UI-01/UI-02 在其上叠加;改动需前后端同步。
- **D-02:** capabilities 字段粒度用**显式布尔**表达,让前端直接读、无需按平台名自行推断:
  - **per-engine `available`** —— 表示"当前平台是否支持该引擎",与现有 `installed`/`capability_ok`(= 内核路径是否存在)**正交**。Firefox 在 macOS `available=false`(即使 `ENGINE_METADATA` 仍保留其条目、Phase 1 D-08);Chrome 在 macOS `available=true`(是否 `installed` 另说)。这是 Phase 4 UI-01「完全隐藏 Firefox」的依据。
  - **窗口功能 `arrange` / `sync`** —— 各给 `available` 布尔 + `reason` 文案(如"窗口排列仅在 Windows 上可用")。这是 Phase 4 UI-02「置灰并显示『仅 Windows』提示」的依据,状态来源为 window_manager 的平台门控事实。
  - 窗口功能的 `reason` 文案应与 Phase 1 已确立的错误文案风格一致(指向具体功能,不让用户误读为整个应用不支持 mac,见 01-CONTEXT specifics)。

### 启动链路验证(LAUNCH-01/02/03)
- **D-03:** 验收方式 = **真机(用户 arm64 Mac)手动冒烟为 LAUNCH 主验收手段** + 新增 **mock Popen/psutil 的跨平台单测**锁回归(不依赖真内核,可在 CI macOS 子集与 Windows 全量同时跑)。沿用 Phase 1 D-11/D-12 已确立的"真机手动 + CI 子集持续保障"组合。
- **D-04:** 验证深度 = **逐项实测**(非仅"能拉起不报错"):真实代理(含账号代理走 `LocalHttpProxyBridge` 本地桥)、真实安装一个扩展、经代理解析 geo(时区/语言匹配出口 IP)、批量启 2-3 个配置验证相互隔离;每项肉眼确认生效。注:Intel x64 **原生**启动验证仍推迟到 Phase 6(用户仅有 arm64 Mac;x64 冒烟走 Rosetta 已在 Phase 2 覆盖到内核层)。

### 进程树终止(LAUNCH-03)
- **D-05:** macOS 上停止配置/退出应用采用**优雅终止**:先对整棵进程树发 **SIGTERM** 并给宽限窗口(约 3-5s)让 Chromium 干净退出/落盘,超时未退再 **SIGKILL**。避免现状的立即 SIGKILL 残留 `SingletonLock` / 损坏 profile。 — **Reversibility:** reversible — 局部改 `kill_process_tree` 行为即可回退。
- **D-06:** 捕获机制**沿用** `kill_process_tree` 现有的 psutil `children(recursive=True)` 遍历(跨平台一致),**不**引入 `start_new_session` + `os.killpg` 的平台分叉——直接 Popen 嵌套二进制时 Chromium Helper 为其子进程,可被递归捕获。SIGTERM 宽限建议用 psutil `terminate()` → `wait_procs(timeout)` → `kill()` 实现;**注意** psutil 在 Windows 上 `terminate()` 等同 `TerminateProcess`(与现即时 `kill()` 等价),故该改动可做成统一路径而非 macOS-only 分支,Windows 行为实质不变(planner 定夺分支 vs 统一)。

### Claude's Discretion
- **D-07(内核 quarantine 处理,LAUNCH-01 landmine):** 用户把 quarantine 策略与剥离时机**都交由 Claude 裁量**。默认倾向,供 researcher/planner 起步:
  1. **先研究实证** —— 确认 CLI `Popen`/`execve` 启动一份带 `com.apple.quarantine`、ad-hoc 签名的 Chromium 内核是否真会被 Gatekeeper 拦(CLI exec 通常不弹 GUI 门禁,但需在 arm64 Mac 上以真实下载内核实测,不能空想)。
  2. **若确需处理** —— 默认在**内核落地时**(下载/解压/安装内核后)`xattr -dr com.apple.quarantine` 剥离一次,并在**启动路径保留防御性兜底**(应对用户手动替换内核带回 quarantine);两者是否都做由实测结论决定。
  - 边界:应用**自身** bundle 的放行(Gatekeeper「仍要打开」/ UI-04 应用内指引)不在本 phase,归 Phase 4/6;本 D-07 只谈**内核**。 — **Reversibility:** reversible。
- **其余裁量:** capabilities 字段的具体命名与嵌套结构(在满足 D-02 语义前提下);SIGTERM 宽限秒数的确切取值;是否把 capabilities 也暴露到 `/open-api`(自动化面,非本次讨论项,planner 可按需决定,不属新 scope)。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与范围(本仓库)
- `.planning/ROADMAP.md` — Phase 3 目标与 4 条成功标准(SC1「直接 Popen 嵌套二进制,不经 open -a」;SC4 明确写 `GET /api/capabilities`)
- `.planning/REQUIREMENTS.md` — LAUNCH-01 / LAUNCH-02 / LAUNCH-03 / XPLAT-05 验收条件
- `.planning/PROJECT.md` — v0.2 约束(零回归、平台条件分支)与 Key Decisions
- `.planning/phases/01-backend-cross-platform/01-CONTEXT.md` — D-06(Chrome 路径 = `Chromium.app/Contents/MacOS/Chromium`)、D-08(Firefox 保留 metadata、天然不可用、隐藏归 Phase 4)、D-03(同步器/窗口功能 macOS 门控现状,capabilities 的窗口功能状态源)、窗口功能错误文案风格(specifics)
- `.planning/phases/02-macos/02-CONTEXT.md` — Phase 2 已发布 arm64/x64 内核到 `kernel-149.0.7827.114`(本 phase 联调依赖),config.py macOS 内核 URL 已回填

### 工程约定(本仓库)
- `CLAUDE.md` — 测试环境约束(纯 unittest + mock.patch,从仓库根运行;`browser_manager` 在 macOS 已可导入)、commit message 约定、`backend/_g.py` 完整性校验(本 phase 不触碰 openSourceNotice.js / App.vue,无哈希更新需求)

### 关键代码落点(勘察确认,full path + 行号)
- `backend/services/chrome.py:26-142` — `launch_chrome_profile`:已跨平台 Popen 嵌套二进制;`creationflags=CREATE_NEW_PROCESS_GROUP`(line 22/124,POSIX 上 =0 无害);env 注入 LANG/LANGUAGE;返回 process / remote_debugging_port / proxy_bridge / geo_profile
- `backend/config.py` — `bundled_engine_executable("chrome")` 解析 macOS Chrome 二进制路径(Phase 1 D-06)
- `backend/browser_manager.py:173-283` — `start_profile`(记录 `RuntimeSession`、pid)/ `stop_profile`(→ `kill_process_tree`);`:602-623` `get_engine_statuses`(现有 `installed`/`capability_ok`,D-02 新增 `available` 维度的落点);`:68-74` `bootstrap`(D-01 并入 capabilities 的落点);`:831-856` `_refresh_runtime_sessions`(psutil `pid_exists`/zombie 检活)
- `backend/services/network.py:839-854` — `kill_process_tree`(现全树立即 `process.kill()`;D-05/D-06 改动主体);`LocalHttpProxyBridge`(账号代理本地桥,D-04 实测对象);`resolve_geo_profile`(geo 解析)
- `backend/main.py:84-86` — `/api/bootstrap`(D-01 并入点);`:403-405` `/api/engines`(能力端点相邻放置参考);新增 `/api/capabilities` 路由落点;`open_api` 为自动化面
- `backend/services/window_manager.py:6` — `sys.platform == "win32"` 平台门控(capabilities 的窗口功能 `available`/`reason` 事实源)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **启动链路本身可直接复用**:`launch_chrome_profile` 无 Windows 硬编码,macOS 上应能开箱工作;本 phase 更多是"验证 + 补边角"而非重写。
- **`get_engine_statuses()` + `bootstrap()`** 已有 per-engine 状态聚合结构,D-01/D-02 在其上叠加 `available` 与 capabilities 块,复用现成序列化路径。
- **`kill_process_tree`** 已用 psutil 递归子进程,D-05 只需把"立即 kill"改为"terminate→宽限→kill",不改捕获逻辑(D-06)。
- **`LocalHttpProxyBridge`** 是账号代理转发现成机制,D-04 的账号代理实测直接用它。

### Established Patterns
- 平台分支/路径常量统一收敛在 `backend/config.py`(唯一来源);capabilities 里若需平台判定,沿用 `sys.platform` 现有约定(config.py:25/35/86、window_manager.py:6)。
- 测试为纯 unittest + `unittest.mock.patch`(参考 `tests/test_sync_regressions.py` FakeSyncClient 模式);D-03 的 mock Popen/psutil 单测沿此模式,不依赖真内核,可两平台跑。
- `installed`/`capability_ok` 现语义 = "内核路径存在";D-02 的 `available` 是新增的"平台级是否支持"维度,二者正交,勿混用同一字段。

### Integration Points
- **capabilities API → Phase 4 前端门控**:`engine.available=false`(Firefox/macOS)→ UI-01 完全隐藏;窗口功能 `available=false` + `reason` → UI-02 置灰并显示提示。字段契约是 Phase 3→4 的硬接口(D-01 标 costly 即因此)。
- **内核可下载/已安装 → 启动链路**:联调依赖 Phase 2 发布的 `kernel-149.0.7827.114` 内核(arm64 本机、x64 走 Rosetta)。
- **stop_profile / 退出应用 → 进程树终止**:D-05/D-06 决定 macOS 上"无残留"(LAUNCH-03)是否达成。

</code_context>

<specifics>
## Specific Ideas

- ROADMAP SC4 原文用 `GET /api/capabilities`——D-01 的端点命名以此为准。
- `available` vs `installed` 的正交示例:Firefox 在 macOS `available=false`;Chrome 在 macOS `available=true` 但未下载内核时 `installed=false`。前端门控读 `available`,安装提示读 `installed`。
- SIGTERM 宽限窗口示例 3-5s(D-05,确切值 Claude 裁量)。
- `kill_process_tree` 现状:`children(recursive=True)` 后全树 `process.kill()`(SIGKILL)立即终止(network.py:845-851)——D-05 改为先 `terminate()` 再宽限。
- 窗口功能 `reason` 文案沿用 01-CONTEXT 已定风格:「窗口排列仅在 Windows 上可用」/「窗口同步仅在 Windows 上可用」(指向具体功能,避免误读为整个应用)。

</specifics>

<deferred>
## Deferred Ideas

None — 讨论未越界。

**跨 phase 备忘(非新增 scope,仅提示 planner):**
- capabilities 是否也暴露到 `/open-api`(自动化面):本次未讨论,planner 可按需决定,属实现裁量而非新 capability。
- Intel x64 **原生**启动验证明确推迟到 Phase 6(D-04);本 phase 只在 arm64 Mac 上原生验证。
- 应用自身 bundle 的 Gatekeeper 放行(内核之外)归 Phase 4(UI-04 应用内指引)/ Phase 6(release 文档),不与本 phase 的内核 quarantine 处理(D-07)混淆。

</deferred>

---

*Phase: 3-macOS Chrome 启动与能力 API*
*Context gathered: 2026-07-27*
