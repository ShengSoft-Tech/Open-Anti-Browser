# Open-Anti-Browser

## What This Is

本地桌面端指纹浏览器管理器:Python (FastAPI + PySide6) 后端 + Vue 3 前端,管理两套指纹内核(fingerprint-chromium 149 和 firefox-fingerprintBrowser 151)的配置、代理、扩展、批量启动和窗口同步。面向需要多账号环境隔离的个人和小团队用户,已发布 Windows 版(v0.1.15,Inno Setup 安装包,CI 自动发版)。

## Core Value

一键创建并启动相互隔离、指纹可信的浏览器环境——配置即用,无需用户理解指纹参数细节。

## Requirements

### Validated

<!-- 已在 Windows 版 v0.1.x 发布并验证 -->

- ✓ 浏览器配置 CRUD(chrome/firefox 双引擎设置共存,engine 字段切换)— v0.1
- ✓ fingerprint-chromium 内核启动(指纹 seed 命令行参数、独立用户数据目录)— v0.1
- ✓ Firefox 内核启动(user.js 偏好 + fpfile + marionette 端口)— v0.1
- ✓ 代理管理:规范化、bypass 规则、本地代理桥(认证代理转发)、连通性测试 — v0.1
- ✓ 按出口 IP 解析地理信息(语言/时区自动匹配)— v0.1
- ✓ 扩展上传与安装 — v0.1
- ✓ 批量启动 + 运行时会话跟踪(psutil 检活)— v0.1
- ✓ 窗口同步器(主控注入 JS,CDP/Marionette 重放到跟随窗口)— v0.1(仅 Windows)
- ✓ win32 窗口排列(显示/统一大小/网格)— v0.1(仅 Windows)
- ✓ 对外自动化 API(/open-api,X-API-Key 鉴权)+ 纯后端模式 — v0.1
- ✓ CI 自动发版:推 v* tag → Windows runner 打包 PyInstaller + Inno Setup → GitHub Release — v0.1
- ✓ 开源声明完整性校验(backend/_g.py 哈希锁定)— v0.1

### Active

<!-- 里程碑 v0.2:macOS 支持(仅 Chrome 内核) -->

- [ ] macOS 内核:从 ../fingerprint-chromium(149.0.7827.114)构建 arm64 与 Intel x64 两个内核并上传 kernel release
- [ ] 后端跨平台适配:pywin32 条件依赖、window_manager 条件导入、config.py 平台分支路径、runtime_control creationflags 修复
- [ ] macOS 核心功能可用:配置管理、指纹启动、代理、扩展、批量启动(Chrome 引擎)
- [ ] macOS 上窗口排列/窗口同步禁用并明确提示"仅 Windows";Firefox 引擎在 macOS 隐藏
- [ ] CI 增加 macOS job:PyInstaller .app + 内核打包,产出 arm64/x64 两个 dmg 挂到 release
- [ ] release 说明包含未签名应用首次打开的放行步骤

### Out of Scope

- macOS 版 Firefox 内核 — 用户只需要 Chrome 内核;Firefox 内核(ruyipage)无 macOS 构建
- macOS 窗口排列/窗口同步 — 依赖 win32;CDP 同步理论可行但验证成本高,留待后续里程碑
- Apple 代码签名与公证 — 需要 Apple Developer 账号($99/年),本里程碑用"右键打开"放行方式替代
- Linux 支持 — 无用户需求
- universal binary(单包双架构)— Chromium universal 构建复杂,采用 arm64/x64 分开出包

## Context

- 运行目标平台原本仅 Windows:引擎是 .exe、窗口管理依赖 pywin32、打包用 PyInstaller + Inno Setup。
- Chrome 内核源码在兄弟项目 `../fingerprint-chromium`(ungoogled-chromium + 指纹补丁,版本 149.0.7827.114),已有 `flags.macos.gn` 和 `downloads-macos-arm64.ini`,具备 macOS arm64 构建基础;x64 需补 downloads 配置。
- Chromium 构建无法在 GitHub Actions 完成(时长/磁盘限制),内核在本地 Mac 构建一次,作为资产上传到 kernel release(`kernel-149.0.7827.114`),应用 CI 只负责下载打包。
- 现有 CI(.github/workflows/build-release.yml)从 backend/config.py 读 CHROME_ENGINE_ZIP_URL(单一事实来源),macOS job 沿用此模式。
- backend/_g.py 完整性校验在启动时运行,macOS 打包不得破坏它。

## Constraints

- **兼容性**: Windows 现有功能零回归 — macOS 适配全部走平台条件分支,不改变 Windows 行为
- **依赖**: pywin32 仅 Windows 可装 — requirements.txt 必须用环境标记(sys_platform)
- **构建**: Chromium 内核只在本地 Mac 构建 — CI 无法承担,构建产物以 release 资产分发
- **分发**: dmg 不签名 — 首次打开需用户手动放行,文档必须写清步骤
- **架构**: arm64 与 Intel x64 分开构建、分开出 dmg — 不做 universal binary

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| macOS 仅支持 Chrome 引擎 | 用户需求明确;Firefox 内核无 macOS 构建 | — Pending |
| 内核打包进 dmg(非首启下载) | 安装即用、完全离线,与 Windows engines 打包方式一致 | — Pending |
| 窗口排列/同步在 macOS 禁用 | win32 不可移植;CDP 同步验证成本高,核心功能优先出货 | — Pending |
| 不做签名/公证 | 无 Apple Developer 账号,放行步骤可接受 | — Pending |
| arm64 + x64 双内核双 dmg | 覆盖 Intel 老 Mac 用户,不做 universal 降低构建复杂度 | — Pending |

## Current Milestone: v0.2 macOS 支持(仅 Chrome 内核)

**Goal:** 让 Open-Anti-Browser 在 macOS(arm64 + Intel x64)上开箱可用——GitHub release 附带 dmg,安装后自带 mac 版 fingerprint-chromium 内核。

**Target features:**
- macOS arm64/x64 双内核构建并上传 kernel release
- 后端跨平台适配(Chrome-only,窗口功能禁用)
- CI macOS job 产出两个 dmg 并挂到 release

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-23 after starting milestone v0.2*
