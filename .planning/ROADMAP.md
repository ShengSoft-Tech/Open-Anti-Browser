# Roadmap: Open-Anti-Browser — v0.2 macOS 支持(仅 Chrome 内核)

## Overview

这是 Open-Anti-Browser 在本仓库中的第一个 GSD 里程碑(v0.1 已在 GSD 引入前发布)。目标是让应用在 macOS(arm64 + Intel x64)上开箱可用:先让后端在 macOS 上能装、能跑、路径正确;与此并行,在兄弟仓库本地构建两个架构的 fingerprint-chromium 内核并发布为 kernel release 资产;随后打通 macOS 上指纹 Chrome 的实际启动链路并暴露平台能力 API;再让前端根据能力 API 隐藏 Firefox、对窗口同步/排列置灰提示;最后把这一切装进 CI,产出签名 dmg 并挂上 Release,配上放行文档完成端到端验证。窗口排列/同步与 Firefox 在 macOS 上明确排除在外,签名与公证留待后续里程碑。

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: 后端跨平台基础适配** - pip 安装、导入、启动、路径解析在 macOS 上全部跑通,Windows 行为零回归 (completed 2026-07-24)
- [x] **Phase 2: macOS 内核构建与发布** - 本地构建 arm64/x64 两个 fingerprint-chromium 内核并发布为 kernel release 资产 (completed 2026-07-26)
- [x] **Phase 3: macOS Chrome 启动与能力 API** - macOS 用户可一键启动指纹 Chrome 配置,后端暴露平台能力供前端门控 (completed 2026-07-27)
- [ ] **Phase 4: 前端平台门控** - macOS 上 Firefox 隐藏、窗口同步/排列置灰提示、平台说明与放行指引上线
- [ ] **Phase 5: CI 打包发布** - CI 新增 macOS job,产出签名 dmg(arm64+x64)并与 Windows 安装包挂到同一 Release
- [ ] **Phase 6: 发布文档与端到端验证** - Release notes 放行说明齐全,真机端到端验证通过

## Phase Details

### Phase 1: 后端跨平台基础适配

**Goal**: 后端在 macOS 上可以正常安装依赖、导入并启动(含纯后端模式),路径全部解析到 macOS 约定位置,同时 Windows 现行为字节级不变
**Depends on**: Nothing (first phase)
**Requirements**: XPLAT-01, XPLAT-02, XPLAT-03, XPLAT-04
**Success Criteria** (what must be TRUE):

  1. macOS 上执行 `pip install -r requirements.txt` 直接成功,不因 pywin32 等 Windows-only 依赖报错(`sys_platform` 环境标记生效)
  2. 后端在 macOS 上可以正常导入与启动,不再因 `window_manager` 顶层 `import win32api` 崩溃;调用窗口排列相关 API 时返回"仅 Windows 支持"的错误提示
  3. macOS 冻结态下应用数据写入 `~/Library/Application Support/Open-Anti-Browser/`,Chrome 引擎默认可执行文件路径解析到 `Chromium.app/Contents/MacOS/Chromium`
  4. `--backend-only` 纯后端模式可在 macOS 上派生、通过 psutil 检活、并正常停止(`creationflags` 平台条件化,不再向 POSIX 传入 Windows 专属参数)
  5. Windows 上以上路径/导入/启动相关的现有行为与既有 unittest 套件保持字节级不变

**Plans**: 4/4 plans executed
**Wave 1**

- [x] 01-01-PLAN.md — macOS 可安装/可导入/可派生纵切(requirements 标记 + window_manager 条件导入 + runtime_control creationflags)[XPLAT-01/02/04]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — config.py 平台感知路径解析(macOS 可写根 + Chrome 引擎路径 + firefox 条目保留)[XPLAT-03]
- [x] 01-03-PLAN.md — 同步器启动平台门禁 + main.py os.startfile 核销 [XPLAT-02]

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — 双 runner CI 测试 workflow(windows-latest 全量 + macos 实测范围)[XPLAT-01/02/03/04]

### Phase 2: macOS 内核构建与发布

**Goal**: fingerprint-chromium 149.0.7827.114 的 macOS arm64 与 Intel x64 两个内核已在本地(`../fingerprint-chromium`)构建完成,并作为 kernel release 资产可供下载
**Depends on**: Nothing (independent/parallel track — 本地构建发生在兄弟仓库,不阻塞 Phase 1)
**Requirements**: KERNEL-01, KERNEL-02, KERNEL-03
**Success Criteria** (what must be TRUE):

  1. macOS arm64 内核可从 kernel release(如 `kernel-149.0.7827.114`)下载,产物经 ditto 打包保留符号链接并附带 ad-hoc 签名
  2. 兄弟仓库已补齐 `downloads-macos-x64.ini`,Intel x64 内核在 arm64 Mac 上交叉编译产出,同样可从同一 kernel release 下载
  3. 两个内核资产在上传前都通过 file/lipo 架构验证(确认各自架构匹配)与本机启动冒烟测试,文件名包含明确架构标识(如 `-arm64`/`-x64`)

*(边界收窄:讨论 D-03/D-05 已澄清 Chromium 构建/交叉编译/lipo/冒烟归兄弟仓库 `../fingerprint-chromium`;本仓库职责 = 上传前二次把关 + gh 发布 + config.py URL 回填。verifier 以此口径校验。)*

**Plans**: 4/4 plans executed

**Wave 1** *(可并行,无文件重叠)*

- [x] 02-01-PLAN.md — 上传前把关+发布脚本 verify_and_upload_macos_kernel.sh(tracer:arm64 verify 流水线端到端 + x64 Rosetta 冒烟分支 + gh 上传)[KERNEL-01/02/03]
- [x] 02-02-PLAN.md — config.py 回填 macOS arm64/x64 内核 URL 常量 + test_config_platform 断言 [KERNEL-01/02]

**Wave 2** *(depends on Wave 1;人工把关,受兄弟仓库产物阻塞)*

- [x] 02-03-PLAN.md — arm64 内核真实把关并发布到 kernel release(gated on 兄弟仓库 post-D-02 arm64 zip)[KERNEL-01/03]
- [x] 02-04-PLAN.md — x64 内核真实把关(含 Rosetta 冒烟)并发布(gated on 兄弟仓库 x64 交叉编译产物)[KERNEL-02/03]

### Phase 3: macOS Chrome 启动与能力 API

**Goal**: macOS 用户可以完整走通"创建配置 → 启动指纹 Chrome → 使用代理/扩展/批量启动 → 停止"的核心链路,后端同时暴露平台能力供前端消费
**Depends on**: Phase 1 (config/路径分支基础); Phase 2 (需要至少一份本机内核用于联调验证)
**Requirements**: LAUNCH-01, LAUNCH-02, LAUNCH-03, XPLAT-05
**Success Criteria** (what must be TRUE):

  1. macOS 用户创建 Chrome 引擎配置后可一键启动,指纹参数、独立用户数据目录、CDP 调试端口、psutil 会话跟踪均正常工作(直接 `Popen` 嵌套 `.app` 内二进制,不经 `open -a`)
  2. 代理(含本地代理桥)、扩展安装、按 IP 地理解析、批量启动在 macOS 上的 Chrome 配置中均验证可用
  3. 停止单个配置或退出应用能正确终止 macOS 上的 Chrome 进程树,不留残留进程
  4. 请求平台能力接口(如 `GET /api/capabilities`)可获知当前平台可用引擎与窗口功能状态,为前端门控提供依据

**Plans**: 3/3 plans executed

**Wave 1** *(可并行,无文件重叠)*

- [x] 03-01-PLAN.md — capabilities API(tracer:get_platform_capabilities + GET /api/capabilities + bootstrap;含 D-01 契约决策门)[XPLAT-05]
- [x] 03-02-PLAN.md — kill_process_tree 优雅终止统一路径(SIGTERM→宽限→SIGKILL)+ 跨平台单测 + 零回归门禁 [LAUNCH-03]

**Wave 2** *(depends on Wave 1;含真机主验收)*

- [x] 03-03-PLAN.md — chrome.py quarantine 防御钩子 + arm64 真机端到端冒烟(启动/代理/扩展/geo/批量/停止无残留 + D-07 实证)[LAUNCH-01/02/03]

### Phase 4: 前端平台门控

**Goal**: macOS 用户在界面上只看到与当前平台能力匹配的选项,并获得清晰的平台差异说明与首次运行放行指引
**Depends on**: Phase 3 (依赖 capabilities API)
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):

  1. macOS 上创建/编辑配置界面完全不出现 Firefox 引擎选项
  2. macOS 上窗口同步/窗口排列控件呈置灰状态并显示"仅 Windows 支持"提示,而非直接隐藏
  3. 应用内可查看"macOS 限制说明"内容,zh-CN 与 en-US 文案同步
  4. macOS 首次运行时应用内展示 Gatekeeper 放行指引("仍要打开"步骤 + `xattr -dr com.apple.quarantine` 命令),zh-CN 与 en-US 文案同步

**Plans**: 2/6 plans executed
**UI hint**: yes

**Wave 1**

- [x] 04-01-PLAN.md — tracer:capabilities 事实源接线 + capabilitiesGating 纯函数模块 + ProfileDialog 引擎选择器门控与编辑态锁定 [UI-01]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — i18n parity 自动守护 + 本 phase 全部中英双语文案(23 条)+ Gatekeeper 首启逻辑模块 [UI-03/UI-04]

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 04-03-PLAN.md — ProfileList:筛选下拉隐藏 Firefox、既有配置「仅 Windows」标记、单行/批量启动统一门控 [UI-01]
- [ ] 04-04-PLAN.md — SyncManager 平台横幅与动作按钮门控 + AppSettings 平台限制说明卡片与指引复看入口 [UI-02/UI-03]

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 04-05-PLAN.md — App.vue 侧栏状态行/导航置灰/首启放行弹窗 + `backend/_g.py` 摘要重算(哈希锁定 landmine)[UI-01/UI-02/UI-04]

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 04-06-PLAN.md — macOS 真机人工验收 checkpoint:既有 Firefox 配置能力矩阵 / Gatekeeper 指引真实性 / 双语可读性 [UI-01..UI-04]

### Phase 5: CI 打包发布

**Goal**: 推送 v* tag 后 CI 自动产出 macOS arm64 签名 dmg,并与 Windows 安装包一并挂到同一 GitHub Release
> ⚠ **2026-07-27 scope 变更:x64(Intel)从 v0.2 移除、暂时先不支持。** 本 phase 规划/执行时仅做 **arm64**;下述所有 x64 相关标准(matrix x64=macos-15-intel、第二个 dmg、双架构下载文档、x64 原生验证等)一律暂缓,待后续里程碑再启。x64 内核资产已在 kernel-149.0.7827.114 备好,恢复成本低。详见 PROJECT.md Out of Scope / Key Decisions。
**Depends on**: Phase 1 (跨平台后端代码需已就绪); Phase 2 (需要可下载的内核资产); Phase 3 (Chrome 启动链路需已验证)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):

  1. 推送 v* tag 后 CI 并行触发 macOS job(matrix:arm64=macos-15、x64=macos-15-intel),与既有 Windows job 互不影响
  2. CI 产出真正的 `.app` bundle(正确 Info.plist、.icns 图标):菜单栏/Dock 显示正确应用名与图标,Cmd+Q 可正常退出
  3. 内核经 ditto 注入 `.app` 后整体做 ad-hoc 重签,`codesign --verify --deep --strict` 作为 CI 硬门禁,校验失败即中止发布
  4. 两个 dmg(含 `.app` + Applications 别名 + 拖拽安装背景图)以版本+架构命名(如 `Open-Anti-Browser-0.2.0-arm64.dmg`)并与 Windows 安装包一起出现在同一 GitHub Release
  5. `backend/_g.py` 开源声明完整性校验在 macOS 构建与启动过程中保持有效,不因打包流程被破坏

**Plans**: TBD

### Phase 6: 发布文档与端到端验证

**Goal**: macOS 用户拿到未签名的 dmg 后,无需开发者协助即可自行完成放行、安装并开始使用
**Depends on**: Phase 5 (需要真实 CI 产出的 dmg 才能验证)
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):

  1. Release notes 提供分步放行说明(启动被拦 → 系统设置 → 隐私与安全性 → 仍要打开),并附 `xattr -dr com.apple.quarantine` 终端替代方案
  2. Release notes/README 提供双架构下载选择指引,帮助用户判断自己的 Mac 是 Apple Silicon 还是 Intel
  3. 在一台从未安装过本应用的 Mac 上(arm64 与 x64 分别原生验证,不借助 Rosetta),用户仅依据发布文档即可完成下载、放行、安装、创建配置并启动 Chrome 配置的完整流程

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6
(Phase 2 内核构建可与 Phase 1 并行开展,但 Phase 5 打包前必须等待 Phase 2 产出内核资产)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 后端跨平台基础适配 | 4/4 | Complete    | 2026-07-24 |
| 2. macOS 内核构建与发布 | 4/4 | Complete    | 2026-07-26 |
| 3. macOS Chrome 启动与能力 API | 3/3 | Complete    | 2026-07-27 |
| 4. 前端平台门控 | 2/6 | In Progress|  |
| 5. CI 打包发布 | 0/TBD | Not started | - |
| 6. 发布文档与端到端验证 | 0/TBD | Not started | - |
