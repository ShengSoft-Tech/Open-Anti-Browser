---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: macOS 支持(仅 Chrome 内核)
current_phase: 03
current_phase_name: macos-chrome-api
status: executing
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-07-27T17:52:46.868Z"
last_activity: 2026-07-27
last_activity_desc: Phase 03 execution started
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 11
  completed_plans: 9
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-23)

**Core value:** 一键创建并启动相互隔离、指纹可信的浏览器环境——配置即用,无需用户理解指纹参数细节。
**Current focus:** Phase 03 — macos-chrome-api

## Current Position

Phase: 03 (macos-chrome-api) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-07-27 — Phase 03 execution started

Progress: [████████░░] 82%

## Performance Metrics

**Velocity:**

- Total plans completed: 8
- Average duration: — min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |
| 02 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 20min | 2 tasks | 5 files |
| Phase 01 P02 | 12min | 1 tasks | 2 files |
| Phase 01 P03 | 12min | 2 tasks | 2 files |
| Phase 01 P04 | 12min | 2 tasks | 2 files |
| Phase 02 P01 | 20min | 2 tasks | 1 files |
| Phase 02 P02 | 8min | 2 tasks | 2 files |
| Phase 02 P03 | 35min | 3 tasks | 0 files |
| Phase 03 P01 | 15min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v0.2 scope: macOS 仅支持 Chrome 引擎(Firefox 无 macOS 内核)
- v0.2 scope: 内核打包进 dmg,非首启下载;窗口排列/同步在 macOS 禁用(置灰提示);不做签名/公证,arm64+x64 双内核双 dmg
- [Phase ?]: D-01: window_manager.py Windows branch moved verbatim into if sys.platform == "win32" block; non-Windows branch exports identically-named/signed stub functions raising RuntimeError — zero browser_manager.py changes needed
- [Phase ?]: D-09/D-10: requirements.txt uses PEP 508 sys_platform == "win32" markers on pywin32/ruyipage (versions unchanged); no requirements-build.txt split
- [Phase ?]: config.py 路径解析平台化(D-05/06/07/08):macOS 冻结态可写根锁定 Application Support,Chrome 路径锁定 .app bundle 内二进制,ENGINE_METADATA 保留 firefox 条目,Windows 路径值逐字不变
- [Phase ?]: D-03: Synchronizer start gate lives inside BrowserSynchronizer.start (not main.py route or browser_manager) — same convention as window_manager.py's per-function win32 gate
- [Phase ?]: D-04: main.py open_system_url already cross-platform since initial commit — closed as verification-only, zero code change
- [Phase ?]: D-12: independent ci-tests.yml (push/PR/workflow_dispatch) added; build-release.yml (v* tag release) untouched
- [Phase ?]: macOS CI test range = full suite (72/72 pass after installer-test file-existence guard fix, no subset needed)
- [Phase ?]: Upload asset always re-staged to $SCRATCH/$ZIP_NAME (config.py-resolved name) before gh release upload, guaranteeing published asset name matches SSOT constant regardless of local artifact filename
- [Phase ?]: 02-02: 沿用 _CHROME_KERNEL_BASE f-string 模式回填 macOS arm64/x64 内核 URL 常量(-1.3 revision),不用 platform.machine() 运行时分支
- [Phase ?]: 02-03: arm64 内核经真实 verify+upload 脚本独立复核后发布到 kernel-149.0.7827.114,post-D-02 归属经人工 cross-repo handoff 确认(LOG(INFO) 无法静态检出)
- [Phase ?]: 03-01: capabilities 契约锁定 option-a(嵌套形状),available 与 installed/capability_ok 正交,不并入 open-api

### Pending Todos

None yet.

### Blockers/Concerns

- ~~arm64 重构建阻塞~~ 已解决(2026-07-25):兄弟仓库产出 post-D-02 arm64 ditto zip,02-03 已验证并发布到 kernel-149.0.7827.114
- ~~Phase 2 仅剩 02-04 (x64) 阻塞~~ 已解决(2026-07-27):兄弟仓库交付 post-D-02 x64 交叉编译 ditto zip(fingerprint-chromium 提交 91d6603b/f0985747/30d2553a:补 downloads-macos-x64.ini、flags 拆出 macos-arm64/x64 中立化、x64 build),经架构断言 + Rosetta CDP 冒烟把关后已上传到 kernel-149.0.7827.114,双架构齐备。上传前必须的脚本改动:codesign 阶段改按架构分支(x86_64 平台设计默认不签名,跳过;arm64 从严不变,fix 02b6688)。注:先前"kernel-artifacts/ 与 out/ 目录已消失"的复核判断是路径基准错误——实际位置为 `bfwg/kernel-artifacts/`(仓库同级)与 `build/src/out/`,两者一直都在;此前拒绝 arm64 zip 顶替 x64(lipo 取证 launcher=arm64,A-K02/T-02-05)的处置正确
- Phase 5 (CI 打包发布) 需要 Phase 2 产出的真实内核资产才能端到端验证——现双架构内核资产(arm64 + x64)已在 kernel-149.0.7827.114 发布,该前置已满足

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — this is the first GSD milestone in this repo)* | | | |

## Session Continuity

Last session: 2026-07-27T17:52:46.859Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
