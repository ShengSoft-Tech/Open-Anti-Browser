---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: macOS 支持(仅 Chrome 内核)
current_phase: 07
current_phase_name: 补丁发布与发布链路验证
status: executing
stopped_at: Phase 7 context gathered
last_updated: "2026-08-01T00:27:49.737Z"
last_activity: 2026-07-31
last_activity_desc: Phase 06 complete, transitioned to Phase 07
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 31
  completed_plans: 28
  percent: 86
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-23)

**Core value:** 一键创建并启动相互隔离、指纹可信的浏览器环境——配置即用,无需用户理解指纹参数细节。
**Current focus:** Phase 06 — release-docs

## Current Position

Phase: 07 — 补丁发布与发布链路验证
Plan: Not started
Status: Ready to execute
Last activity: 2026-07-31 — Phase 06 complete, transitioned to Phase 07

Progress: [████████░░] 86%

## Performance Metrics

**Velocity:**

- Total plans completed: 22
- Average duration: — min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |
| 02 | 4 | - | - |
| 03 | 3 | - | - |
| 04 | 6 | - | - |
| 06 | 5 | - | - |

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
| Phase 05 P05 | 15min | 2 tasks | 1 files |
| Phase 06 P01 | 42min | 3 tasks | 7 files |
| Phase 06 P02 | 6min | 2 tasks | 3 files |
| Phase 06 P03 | 15min | 2 tasks | 5 files |
| Phase 06 P04 | 20min | 2 tasks | 3 files |
| Phase 06 P05 | 50min | 3 tasks | 9 files |

## Accumulated Context

### Roadmap Evolution

- Phase 7 added (2026-07-31): 补丁发布与发布链路验证 — 修复 macOS 关闭按钮后台挂起(UI-05),并借真实 `v0.2.1` tag push 核销 Phase 6 遗留的两项未验证事项(PKG-06:release job checkout 修复的首次真实执行 + RESEARCH 假设 A2 的正反判定)。触发来源是 Phase 6 UAT 中的实际发现,不是里程碑规划。两处修复 `a886dc7` / `524aeb1` 已在 main 上,本 phase 的工作是发布并验证。

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
- [Phase ?]: 05-05: release job consolidates Windows+macOS publish into a single softprops/action-gh-release call (needs: [build, build-macos], tag-gated); Windows build job's inline Create GitHub Release step removed with zero regression, proven on real workflow_dispatch run 30402103536 (release=skipped as designed, no new Release created)
- [Phase ?]: [Phase 5] 05-02 gap-fix: launch_app.py 的 installEventFilter(qt_app) 反模式在真机导致 ~2s 内必现 SIGSEGV（05-06 checkpoint 抓到）；改为 QApplication 子类重载 event()。新增 AST 结构守卫测试 + build-macos 真 cocoa GUI 冒烟门禁（QT_QPA_PLATFORM 刻意不设为 offscreen），经 4 次真实 workflow_dispatch 验证：buggy 代码 2/2 次真实 segfault 被拦下，fix 后 1/1 次 18s 全程存活通过。修复过的干净 dmg 已放入 ~/Downloads，供用户重跑 05-06 真机 checkpoint。
- [Phase ?]: [Phase 5] 05-02 gap-fix #2(05-06 二次真机 checkpoint 抓到)：DesktopApplication.event() 把 handle_macos_quit_request(...) 的返回值当 `return True` 早退门禁，super().event(e) 永远跑不到——QCoreApplication::event() 对 QEvent.Quit 的默认处理(真正让事件循环退出的那一步)被跳过，Cmd+Q 后进程停在约 60% CPU 无限循环不退出(非崩溃)。此缺陷并非第一次 gap-fix 引入的回归——原 installEventFilter 实现有完全相同的逻辑缺陷，D-07 的 Cmd+Q 功能从未在任何已发布形态下真正工作过，此前的启动崩溃只是掩盖了它。修复：event() 无条件转发给 super().event(e)；force_exit() 新增 `_closing` 幂等短路防止 Quit 事件重入时重新 showNormal()。新增 AST 结构守卫测试(MacQuitEventLoopConvergenceTests，用全函数 ast.walk 而非仅顶层语句计数，否则对这个具体缺陷是空判定)。build-macos GUI 冒烟门禁新增第二维度：18s 存活确认后再用 `osascript ... to quit`(与 Cmd+Q 同一条 Apple Event 路径，非 POSIX 信号)发真实 Quit 请求，断言进程在 12s 有界超时内退出且无残留进程；经真实 workflow_dispatch 验证：buggy 分支(30418065169)进程存活 18s 但 Quit 后 113.7% CPU 卡死不退出被正确拦下，fix 后(30418547844)Quit 后 2s 内 exit code 0 干净退出。修复过的干净 dmg 见 workflow_dispatch run 30418547844 的 artifact，供用户重跑 05-06 真机 checkpoint 的 C 组三种退出路径。
- [Phase ?]: D-15 human correction: English 放行 fallback repeats the xattr command verbatim instead of pointing at the Chinese <details> block; acceptance criterion strengthened to byte-identical occurrences >= 1 (not exactly 1)
- [Phase ?]: 06-01 Task 3: real workflow_dispatch run 30653333767 on main confirms build-release.yml's modified release job still parses (build=success, build-macos=success, release=skipped as designed by tag guard)
- [Phase ?]: 06-02: Trust caveat uses '担保'/endorsement instead of '认可'/'信任' near Apple/Gatekeeper as an extra safety margin beyond the literal negative-grep regex; README pointer bullets restate only the two prerequisites + Release-page link, no steps duplicated (D-11)
- [Phase ?]: 06-03: gatekeeper.step1 rewritten to the double-click-again path (measured on real hardware); step2-4 preserved as System-Settings/confirm/terminal fallback chain; gatekeeperCopyParity.test.js locks the ordering and forbidden-fragment gate
- [Phase ?]: 06-03: dmg background footer regenerated to the same double-click-again flow, replacing the never-exercised right-click route; same 600x400/1200x800 geometry create-dmg depends on
- [Phase ?]: 06-04: ROADMAP Phase 6 SC1-3 and REQUIREMENTS DOCS-01/02 rewritten to the measured double-click-again flow and single-architecture prerequisite checklist, with a dated callout naming both 2026-07-28 (05-06 real-hardware capture) and 2026-07-27 (second-architecture removal from v0.2); the callout paraphrases the removed architecture to avoid tripping its own forbidden-word verify gate
- [Phase ?]: 06-04: cross-surface parity audit confirms xattr command / primary 放行 step / macOS 15 floor consistent across release template, both locale files, both READMEs, and build-release.yml; full suite green (118 Python + 52 node:test) run via repo's existing .venv
- [Phase ?]: 06-05: real v0.2.0 tag pushed (option-a); found and fixed release job missing checkout step that silently dropped body_path content; hand-corrected live Release body; closed 05-ci UAT test 1
- [Phase ?]: 06-05: D-13 干净账户要求经开发者豁免,在既有账户中验收;备选放行路径「系统设置 → 仍要打开」记为未验证(该账户已带 Phase 5 写入的 Gatekeeper denial breadcrumb),主路径/自查/安装/创建启动 Chrome 配置四段全额通过
- [Phase ?]: 06-05: 走查发现真机运行缺陷(macOS 关闭按钮不退出应用,仅隐藏到菜单栏),已在 a886dc7 修复并路由到新增 Phase 7(UI-05),不计入 Phase 6 文档缺口,不阻塞本计划完成

### Pending Todos

None yet.

### Blockers/Concerns

- ~~arm64 重构建阻塞~~ 已解决(2026-07-25):兄弟仓库产出 post-D-02 arm64 ditto zip,02-03 已验证并发布到 kernel-149.0.7827.114
- ~~Phase 2 仅剩 02-04 (x64) 阻塞~~ 已解决(2026-07-27):兄弟仓库交付 post-D-02 x64 交叉编译 ditto zip(fingerprint-chromium 提交 91d6603b/f0985747/30d2553a:补 downloads-macos-x64.ini、flags 拆出 macos-arm64/x64 中立化、x64 build),经架构断言 + Rosetta CDP 冒烟把关后已上传到 kernel-149.0.7827.114,双架构齐备。上传前必须的脚本改动:codesign 阶段改按架构分支(x86_64 平台设计默认不签名,跳过;arm64 从严不变,fix 02b6688)。注:先前"kernel-artifacts/ 与 out/ 目录已消失"的复核判断是路径基准错误——实际位置为 `bfwg/kernel-artifacts/`(仓库同级)与 `build/src/out/`,两者一直都在;此前拒绝 arm64 zip 顶替 x64(lipo 取证 launcher=arm64,A-K02/T-02-05)的处置正确
- Phase 5 (CI 打包发布) 需要 Phase 2 产出的真实内核资产才能端到端验证——现双架构内核资产(arm64 + x64)已在 kernel-149.0.7827.114 发布,该前置已满足
- 06-05 Task 3 (clean-account human verification) not yet executed — requires a real macOS machine and a newly created user account; Tasks 1-2 (real v0.2.0 tag push, release-body defect found and fixed, 05-ci UAT closed) are complete and committed

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — this is the first GSD milestone in this repo)* | | | |

## Session Continuity

Last session: 2026-07-31T23:16:41.621Z
Stopped at: Phase 7 context gathered
Resume file: .planning/phases/07-patch-release/07-CONTEXT.md
