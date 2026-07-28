# Requirements: Open-Anti-Browser — v0.2 macOS 支持(仅 Chrome 内核)

**Defined:** 2026-07-23
**Core Value:** 一键创建并启动相互隔离、指纹可信的浏览器环境——配置即用,无需用户理解指纹参数细节。

## v0.2 Requirements

Requirements for the macOS support milestone. Each maps to roadmap phases.

### 内核构建与分发 (KERNEL)

- [x] **KERNEL-01**: macOS arm64 指纹内核可从 kernel release 下载(基于 ../fingerprint-chromium 149.0.7827.114 本地构建,ditto 打包保符号链接,含 ad-hoc 签名)
- [x] **KERNEL-02**: macOS Intel x64 指纹内核可从 kernel release 下载(先在兄弟项目补 downloads-macos-x64.ini,arm64 Mac 交叉编译)
- [x] **KERNEL-03**: 内核资产上传前通过架构验证(file/lipo)与本机启动冒烟测试,文件名含明确架构标识

### 后端跨平台 (XPLAT)

- [x] **XPLAT-01**: macOS 用户可以直接 `pip install -r requirements.txt` 成功(pywin32 等仅 Windows 依赖加 sys_platform 环境标记)
- [x] **XPLAT-02**: 后端在 macOS 可正常导入与启动(window_manager 条件导入;窗口排列 API 在 macOS 返回"仅 Windows 支持"错误,Windows 行为字节级不变)
- [x] **XPLAT-03**: config.py 平台分支生效:冻结态可写根为 `~/Library/Application Support/Open-Anti-Browser/`,Chrome 引擎路径为 `Chromium.app/Contents/MacOS/Chromium`
- [x] **XPLAT-04**: 纯后端模式(`--backend-only`)在 macOS 可派生、检活与停止(creationflags 平台条件化)
- [x] **XPLAT-05**: 后端暴露平台能力信息(如 capabilities 字段/端点),标明当前平台可用引擎与窗口功能

### macOS Chrome 启动 (LAUNCH)

- [x] **LAUNCH-01**: macOS 用户可以启动指纹 Chrome 配置(直接 Popen 嵌套 .app 内的 Chromium 二进制,指纹参数、独立用户数据目录、CDP 调试端口、psutil 会话跟踪全部正常)
- [x] **LAUNCH-02**: 代理(含本地代理桥)、扩展安装、按 IP 地理解析、批量启动在 macOS Chrome 上工作
- [x] **LAUNCH-03**: 停止配置与退出应用能正确终止 macOS 上的 Chrome 进程树,无残留进程

### 前端平台门控 (UI)

- [x] **UI-01**: macOS 上 Firefox 引擎完全隐藏(创建/编辑配置不出现 Firefox 选项)
- [x] **UI-02**: 窗口同步/窗口排列控件在 macOS 置灰并带"仅 Windows"提示(不隐藏)
- [x] **UI-03**: 应用内提供"macOS 限制说明"(平台差异文案,zh-CN 与 en-US 同步)
- [x] **UI-04**: macOS 首次运行时应用内展示放行指引(Gatekeeper "仍要打开"步骤 + `xattr -dr com.apple.quarantine` 命令,zh-CN 与 en-US 同步)

### CI 打包发布 (PKG)

- [ ] **PKG-01**: 推送 v* tag 触发 CI macOS job(matrix:arm64=macos-15,x64=macos-15-intel),与现有 Windows job 并行
- [x] **PKG-02**: PyInstaller 产出真正的 .app bundle(BUNDLE + Info.plist + .icns:菜单栏/Dock 显示正确应用名与图标,Cmd+Q 正常退出)
- [x] **PKG-03**: 内核经 ditto 注入 .app 后整体 ad-hoc 重签,CI 内 `codesign --verify --deep --strict` 作为硬门禁
- [ ] **PKG-04**: dmg 含 .app + Applications 别名 + 自定义拖拽安装背景图,文件名含版本与架构(如 `Open-Anti-Browser-0.2.0-arm64.dmg`)
- [ ] **PKG-05**: 两个 dmg 与 Windows 安装包挂到同一 GitHub Release;backend/_g.py 完整性校验在 macOS 构建与启动中保持有效

### 发布文档 (DOCS)

- [ ] **DOCS-01**: Release notes 提供分步放行说明(启动被拦 → 系统设置 → 隐私与安全性 → 仍要打开,附 xattr 终端替代方案)
- [ ] **DOCS-02**: Release notes/README 提供双架构下载选择指引(如何判断自己是 Apple Silicon 还是 Intel)

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### 分发增强

- **DIST-01**: Apple Developer ID 签名 + 公证(需 $99/年账号,消除放行流程)
- **DIST-02**: Sparkle 式应用内自动更新(依赖签名基础设施)

### 跨平台功能

- **SYNC-01**: CDP-only 跨平台窗口同步(不含排列;需专门里程碑验证可行性)

## Out of Scope

| Feature | Reason |
|---------|--------|
| macOS 版 Firefox 内核 | 用户只需 Chrome;Firefox 内核(ruyipage)无 macOS 构建 |
| macOS 窗口排列(显示/统一大小/网格) | win32 API 绑定,macOS 无等价原语(需 Accessibility/私有 API) |
| universal binary 单 dmg | Chromium universal 构建成本过高;双 dmg 明确命名即可 |
| CI 内构建 Chromium 内核 | GitHub Actions 时长/磁盘限制放不下;本地构建 + release 资产分发 |
| Linux 支持 | 无用户需求 |
| 签名/公证(本里程碑) | 无 Apple Developer 账号,放行文档 + 应用内提示替代 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| XPLAT-01 | Phase 1 | Complete |
| XPLAT-02 | Phase 1 | Complete |
| XPLAT-03 | Phase 1 | Complete |
| XPLAT-04 | Phase 1 | Complete |
| KERNEL-01 | Phase 2 | Complete |
| KERNEL-02 | Phase 2 | Complete |
| KERNEL-03 | Phase 2 | Complete |
| LAUNCH-01 | Phase 3 | Complete |
| LAUNCH-02 | Phase 3 | Complete |
| LAUNCH-03 | Phase 3 | Complete |
| XPLAT-05 | Phase 3 | Complete |
| UI-01 | Phase 4 | Complete |
| UI-02 | Phase 4 | Complete |
| UI-03 | Phase 4 | Complete |
| UI-04 | Phase 4 | Complete |
| PKG-01 | Phase 5 | Pending |
| PKG-02 | Phase 5 | Complete |
| PKG-03 | Phase 5 | Complete |
| PKG-04 | Phase 5 | Pending |
| PKG-05 | Phase 5 | Pending |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |

**Coverage:**

- v0.2 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

*Note: the "19 total" figure that appeared in the initial draft of this section undercounted XPLAT (5, not 2). The count above (22) was reconciled against the actual requirement list during roadmap creation on 2026-07-23.*

---
*Requirements defined: 2026-07-23*
*Last updated: 2026-07-23 after roadmap creation (traceability mapped, count reconciled 19→22)*
