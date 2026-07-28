---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: macOS 支持(仅 Chrome 内核)
current_phase: 05
current_phase_name: ci
status: executing
stopped_at: Completed 05-04-PLAN.md
last_updated: "2026-07-28T20:49:32.716Z"
last_activity: 2026-07-28
last_activity_desc: Phase 05 execution started
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 23
  completed_plans: 21
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-23)

**Core value:** 一键创建并启动相互隔离、指纹可信的浏览器环境——配置即用,无需用户理解指纹参数细节。
**Current focus:** Phase 05 — ci

## Current Position

Phase: 05 (ci) — EXECUTING
Plan: 5 of 6
Status: Ready to execute
Last activity: 2026-07-28 — Phase 05 execution started

Progress: [█████████░] 91%

## Performance Metrics

**Velocity:**

- Total plans completed: 17
- Average duration: — min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |
| 02 | 4 | - | - |
| 03 | 3 | - | - |
| 04 | 6 | - | - |

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
| Phase 03 P02 | 15min | 2 tasks | 2 files |
| Phase 04 P01 | 20min | 3 tasks | 7 files |
| Phase 04 P02 | 25min | 3 tasks | 5 files |
| Phase 04 P03 | 15min | 2 tasks | 1 files |
| Phase 04 P04 | 20min | 2 tasks | 2 files |
| Phase 04 P05 | 25min | 3 tasks | 3 files |
| Phase 04 P06 | 35min | 1 tasks | 3 files |
| Phase 05 P01 | 10min | 2 tasks | 3 files |
| Phase 05 P02 | 15min | 2 tasks | 2 files |
| Phase 05 P03 | 50min | 2 tasks | 2 files |
| Phase 05 P04 | 105min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v0.2 scope: macOS 仅支持 Chrome 引擎(Firefox 无 macOS 内核)
- v0.2 scope: 内核打包进 dmg,非首启下载;窗口排列/同步在 macOS 禁用(置灰提示);不做签名/公证;**v0.2 仅 arm64 dmg(x64 2026-07-27 移出里程碑、暂时先不支持;x64 内核资产已备,待后续里程碑再启)**
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
- [Phase ?]: kill_process_tree refactored to unified terminate->wait_procs->kill (D-05/D-06); grace_period keyword-defaulted (DEFAULT_TERMINATION_GRACE_PERIOD=3.0) for zero call-site changes
- [Phase 3]: 03-03 D-07 真机实证:新鲜浏览器下载的 ad-hoc arm64 内核带 quarantine 时裸 exec 被 AMFI kill(exit 137,非 Gatekeeper 弹窗),剥离后正常。chrome.py quarantine 剥离钩子是【启动必需】,且必须剥整个 .app bundle(framework dylib/helper 也带 quarantine);原钩子只剥主二进制不足,已修 fbac808
- [Milestone v0.2]: 2026-07-27 x64(Intel)从 v0.2 移除、暂时先不支持;PROJECT.md(Goal/Out-of-Scope/Key Decisions/里程碑)与 ROADMAP Phase 5 已注记 arm64-only,x64 待后续里程碑
- [Phase ?]: 04-01: capabilitiesGating.js established as D-00 single source of truth (isFirefoxEngineAvailable/visibleEngineOptions/isEngineSelectorLocked/getWindowFeatureGate); edit-mode retains firefox selection but locks control to reconcile SC1 with D-01 no-data-loss
- [Phase ?]: 04-01: CLAUDE.md frontend test command corrected to node --test frontend/src/lib/*.test.js (directory form threw MODULE_NOT_FOUND on Node 22)
- [Phase ?]: [Phase 4] 04-02: i18n-parity.test.js 建立递归 key-set 差集守护（顺序无关），24 条 Phase 4 必备 key 集中收敛在同一测试文件的清单里，供 04-03/04-04/04-05 消费
- [Phase ?]: [Phase 4] 04-02: macosGatekeeperNotice.js 独立 localStorage key (oab:macos-gatekeeper-notice:v1)，shouldShowGatekeeperNotice 用 platform === 'darwin' 正向判定（不是 !== 'win32'），避免 pre-bootstrap 状态误触发弹窗；GATEKEEPER_XATTR_COMMAND 作为模块常量而非 i18n 文案，保证中英命令逐字一致且限定单个 .app bundle
- [Phase ?]: ProfileList's four gating consumption points (filter dropdown, row tag, start disable/tooltip, batch-start filter) share firefoxEngineVisible computed and isProfileStartBlocked(row) — single D-00 predicate, no independent re-derivation
- [Phase ?]: Duplicate action disabled for platform-blocked firefox rows (duplicating would recreate the SC1-forbidden case); delete and stop remain fully unconditioned per D-01
- [Phase ?]: [Phase 4] 04-04: SyncManager.vue 首次引入 useI18n；syncGate/arrangeGate 各自独立读 capabilities.window.sync/arrange，横幅与4个最显眼按钮的 tooltip 直接绑定后端 reason 原文（不经 t()），其余22+按钮只加 :disabled 不加提示；文件其余上千行硬编码中文保持不动（范围守住）
- [Phase ?]: [Phase 4] 04-04: AppSettings.vue 新增 macOS-only 平台限制说明卡片（platformLimitsVisible = capabilities.platform 存在且非 win32），openGatekeeperGuide() 复用 04-02 的 buildGatekeeperNoticeHtml(t)，保证设置页重看入口与 04-05 首启弹窗文案永不分叉；Firefox 内核卡片保留，仅追加「仅 Windows」标签
- [Phase ?]: [Phase 4] 04-05: App.vue 侧栏 firefoxEngineVisible 隐藏 Firefox 状态行,同步器导航项经 el-tooltip + isNavDisabled/navDisabledReason 置灰但点击不拦截(D-02);GroupManager 分组内 Firefox 计数不隐藏(既有数据构成,D-01)
- [Phase ?]: [Phase 4] 04-05: App.vue onMounted 新增 maybeShowGatekeeperNotice(),严格排在既有开源声明首启提示(_0x31ab)之后、复用同一 try 块;backend/_g.py 的 App.vue SHA-256 在全部编辑定稿后重算写回(31871ec3...),仅改一行,openSourceNotice.js 条目/package.json 钩子零改动
- [Phase ?]: [Phase 4] 04-06: A8 用户拍板推翻 04-05 原建议——GroupManager Firefox 计数列由无条件保留改为按需显示(新增 shouldShowFirefoxColumn 纯函数,D-00 合规),commit 3e32105
- [Phase ?]: [Phase 4] 04-06: RESEARCH 假设 A2(Gatekeeper 放行指引措辞)已在 macOS 15.7(Sequoia, build 24G222)真机逐字核对通过,与系统实际菜单/按钮一致
- [Phase ?]: 05-01: assets/app.icns (D-06) 与 assets/dmg-background.png+@2x (D-10) 已入仓;icon_512x512@2x 档位实测为真 512x512(非 1024)并记录;背景图放行文案逐字核对不含全局停用 Gatekeeper 指令;PKG-02/PKG-04 因与 05-02/05-03/05-04/05-06 共享未全部标记完成(requirements.ready-ids 确认阻塞)
- [Phase ?]: 05-02: Cmd+Q intercepted via QObject event filter on qt_app (parented to avoid GC), delegating to existing force_exit() — no parallel shutdown path (D-07)
- [Phase ?]: 05-02: quarantine self-strip failure notice worded as expected first-launch phenomenon (QMessageBox.information, not critical) per D-12a; command always resolves to canonical /Applications install path when bundle is None or translocated, verbatim-locked against frontend GATEKEEPER_XATTR_COMMAND
- [Phase ?]: 05-03: build-macos job proven twice on real workflow_dispatch (30393410452, 30394320282); A2/A3/A4 RESEARCH assumptions resolved with real-machine evidence, LSMinimumSystemVersion measured at 13.0 (not the 12.0 placeholder, carry-forward to 05-04)
- [Phase ?]: 05-04: check_version_consistency.py placed in scripts/release/ (Phase 2 D-11 precedent), normalize_tag uses removeprefix not lstrip (RESEARCH's own example had the lstrip bug)
- [Phase ?]: 05-04: A3 final resolution — true LSMinimumSystemVersion floor is 15.0 (Sequoia), set by PySide6/shiboken6's own compiled Python-binding libraries (not the Qt frameworks, which remain 13.0); materially more restrictive than 05-03's carried-forward 13.0 measurement, flagged as a product decision for the milestone owner

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

Last session: 2026-07-28T20:49:32.705Z
Stopped at: Completed 05-04-PLAN.md
Resume file: None
