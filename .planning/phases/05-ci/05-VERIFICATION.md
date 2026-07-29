---
phase: 05-ci
verified: 2026-07-29T00:00:00Z
status: human_needed
score: 4/5 must-haves verified
behavior_unverified: 1
overrides_applied: 0
gaps: []
deferred:
  - truth: "dmg 背景图放行提示应描述真实首启体验(拦截一次 → 应用退出 → 再次双击即可用),而不是'右键→打开'"
    addressed_in: "Phase 6"
    evidence: "Phase 6 Success Criteria 1: 'Release notes 提供分步放行说明(启动被拦 → 系统设置 → 隐私与安全性 → 仍要打开)'; 05-06-SUMMARY Open Item 2 明确写为 'NEEDS FIXING (Phase 6 scope)'，plan 明文声明 PKG/DOCS 分工不在本 phase 执行。"
  - truth: "首次启动系统对话框的完整标题/按钮文案(B1)"
    addressed_in: "Phase 6"
    evidence: "05-06-SUMMARY Open Item 1: 'Phase 6 will need this wording to write user-facing release documentation, and will perform a real install anyway. Carried forward as a Phase 6 input.'"
behavior_unverified_items:
  - truth: "推送真实 v* tag 后,build → build-macos → release 全链路端到端跑通,Windows 安装包与 macOS arm64 dmg 被 release job 用同一次 softprops/action-gh-release 调用发布到同一个 GitHub Release"
    test: "推送一个真实的 v* tag(例如 Phase 6 完成后正式发版时的 v0.2.0),观察 build-macos 与 build 两个 job success 后 release job 是否被触发(而非 workflow_dispatch 下的 skipped)，并确认 GitHub Release 页面上同时出现 Open-Anti-Browser-Setup.exe 与 Open-Anti-Browser-*-arm64.dmg"
    expected: "release job 结论为 success(不是 skipped),GitHub Release 页面出现两个文件,tag 版本号与两个文件的版本号、应用内显示版本号一致"
    why_human: "这是唯一让 `if: startsWith(github.ref, 'refs/tags/')` 条件为真、`release` job 真正执行的触发方式;workflow_dispatch(本 phase 全部 8 次真实 CI 验证所用的触发方式)在设计上会跳过这个 job(D-04)。GitHub Actions 无法在不推真实 tag 的前提下模拟这条路径,任何静态断言都只能验证 job 的结构(needs/if/单一 softprops 调用/资产齐备性检查),验证不了它在真实 tag 事件下确实被调度并成功执行。"
human_verification:
  - test: "推送一个真实的 v* tag,确认 release job 从 skipped 变为 success,GitHub Release 上同时挂载 Windows 安装包与 macOS arm64 dmg"
    expected: "单次 tag push 后,同一个 GitHub Release 页面上出现两份产物,文件名版本号与 tag 一致"
    why_human: "本 phase 全部 8 次真实 CI 验证均以 workflow_dispatch 触发(按 D-04 设计,此时 release job 结构性跳过);ROADMAP SC1(『推送 v* tag 后 CI 并行触发』)与 SC4/PKG-05 前半句(『与 Windows 安装包一并挂到同一 GitHub Release』)所描述的触发路径,只能在真实 tag push 时才会执行,目前仍是 05-05-SUMMARY 明确记录在案的已知残余风险,而非本报告新发现的问题。"
---

# Phase 5: CI 打包发布 Verification Report

**Phase Goal:** 推送 v* tag 后 CI 自动产出 macOS arm64 签名 dmg,并与 Windows 安装包一并挂到同一 GitHub Release
**Verified:** 2026-07-29
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, arm64-only scope per 2026-07-27 变更)

| # | Truth (SC) | Status | Evidence |
|---|---|---|---|
| SC1 | 推送 v* tag 后 CI 并行触发 macOS job(arm64),与既有 Windows job 互不影响 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (触发部分) / ✓ VERIFIED (并行部分) | 工作流顶部 `on: push: tags: 'v*'` 未改动(`git diff` 对 :1-11 为空,多个 plan 的 acceptance criteria 已断言);`build`/`build-macos` 两个 job 无 `if` 条件,GitHub Actions 对同一 `on:` 触发一视同仁地并行调度,与触发方式(tag push / workflow_dispatch)无关——这一点已被 05-05 Task 2 用真实 run 的 `startedAt` 时间戳重叠证实(两 job 并行)。但「tag push 这一事件本身」从未被真实触发过(全部 8 次验证 CI 均为 `workflow_dispatch`),见下方 behavior_unverified_items。 |
| SC2 | CI 产出真正的 `.app` bundle:菜单栏/Dock 显示正确应用名与图标,Cmd+Q 可正常退出 | ✓ VERIFIED | 05-06 真机 checkpoint Group C(4/4 PASS,`ps`/`lsof` 实测)、Group D(3/3 PASS,`Info.plist` 实测值 `CFBundleName=Open-Anti-Browser`)。Cmd+Q 曾两次在真机上失败(SIGSEGV、无限循环不退出),均已 root-cause 修复并留下双层 CI 回归门禁(`GUI launch smoke test`),已用真实 CI 反证(`30418065169` 故意失败、`30418547844` 修复后成功)。 |
| SC3 | 内核经 ditto 注入 `.app` 后整体做 ad-hoc 重签,`codesign --verify --deep --strict` 作为 CI 硬门禁,校验失败即中止发布 | ✓ VERIFIED | `.github/workflows/build-release.yml` 内 `codesign --verify --deep --strict` 出现 4 次(签名后外层+内层、dmg 挂载后外层+内层),`--deep --sign`/`continue-on-error`/`if: always()` 均为 0 次(本地 grep 复核)。多次真实 CI 绿跑证实门禁通过。 |
| SC4 | dmg(arm64,x64 已按 2026-07-27 scope 变更移出)含 `.app` + Applications 别名 + 拖拽背景图,版本+架构命名,与 Windows 安装包一起出现在同一 GitHub Release | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (「同一 Release」部分) / ✓ VERIFIED (dmg 内容与命名部分) | dmg 内容(`.app`/Applications 别名/`.background`)与命名(`Open-Anti-Browser-{version}-arm64.dmg`)已在真机与 CI 双重验证(05-06 Group A 5/5 PASS;CI `Verify dmg contents` 步骤断言三项存在)。但「与 Windows 安装包一起出现在同一 GitHub Release」这一最终产出,只在结构层面被验证(全文件 `softprops/action-gh-release` 恰好 1 次、`needs: [build, build-macos]`、release-assets 齐备性检查、tag 守门条件),从未在真实 tag push 下端到端跑过一次——见下方 behavior_unverified_items。 |
| SC5 | `backend/_g.py` 开源声明完整性校验在 macOS 构建与启动过程中保持有效,不因打包流程被破坏 | ✓ VERIFIED | `git diff` 对 `backend/_g.py`、`frontend/src/App.vue`、`frontend/src/lib/openSourceNotice.js` 三个哈希锁定文件,在整个 phase(`382c6e2`..`acfcc9a`,15 个 commit)范围内为空。CI 内独立结构断言(`Contents/Resources/frontend/dist/index.html` 存在、递归文件数非零、`Contents/Frameworks/frontend` 符号链接正确)覆盖了「dist 缺失时 `_g.py` 校验静默跳过」这一已知漏洞;`--backend-only` 冒烟测试在真实 CI 上多次通过,证明 `launch_app.main` 开头的运行时校验没有拒绝启动。 |

**Score:** 4/5 truths verified(1 present + wired, behavior 未被真实 tag push 事件覆盖)

### Deferred Items

Phase 5 本身已完成的工作中发现两处文案缺口,均已被 05-06-SUMMARY 明确记录为 Phase 6(发布文档)范围内的待办,不作为本 phase 的 gap:

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | dmg 背景图放行提示("右键→打开")与真机实测的真实首启路径("拦截一次 → 应用退出 → 再次双击即可用")不符 | Phase 6 | Phase 6 Success Criteria 1 明确要求"分步放行说明";05-06-SUMMARY Open Item 2 标注为"NEEDS FIXING (Phase 6 scope)"并说明 PKG/DOCS 分工已在 plan 中固定 |
| 2 | 首次启动系统 Gatekeeper 对话框的完整标题/按钮文案(B1)未被捕获,仅有客观的决策时间序列(来自 `log stream`) | Phase 6 | 05-06-SUMMARY Open Item 1:"Phase 6 will need this wording to write user-facing release documentation, and will perform a real install anyway. Carried forward as a Phase 6 input." |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `assets/app.icns` | 合法 Mac OS X icon,5 档位+@2x | ✓ VERIFIED | `file` 确认 `Mac OS X icon`(`ic12` type,200074 bytes),`iconutil` 可回读。05-06 真机确认 9 档,`icon_512x512@2x`(1024 档)缺失(512 顶格),用户目视判定 ACCEPTABLE,记为已知取舍,非本 phase 的阻断项。 |
| `assets/dmg-background.png` / `@2x` | 600×400 / 1200×800,含放行提示 | ✓ VERIFIED | `sips` 实测尺寸精确匹配。文案逐字核对无 `spctl`/`sudo`/`--master-disable`/`~/Downloads` 等越权指令。 |
| `launch_app.py` | macOS Cmd+Q 接管 + 首启 quarantine 自剥离与兜底提示 | ✓ VERIFIED | `should_intercept_quit_event`/`handle_macos_quit_request`/`is_macos_frozen_runtime`/`resolve_app_bundle_root`/`is_translocated_path`/`strip_quarantine_from_bundle`/`quarantine_command_target`/`build_quarantine_failure_message`/`maybe_strip_quarantine`/`DesktopApplication` 全部存在且已接线(源码直读确认,行号 27-467)。`build_quarantine_failure_message(None)` 实际输出与 `macosGatekeeperNotice.js` 的 `GATEKEEPER_XATTR_COMMAND` 逐字一致(本地实测复核)。 |
| `tests/test_macos_desktop_runtime.py` | Cmd+Q / quarantine 回归锁 | ✓ VERIFIED | 25 个测试全部通过(含 AST 结构守卫 `QApplicationEventFilterGuardTests`、`MacQuitEventLoopConvergenceTests`)。 |
| `scripts/release/check_version_consistency.py` | 三方版本一致性判定 | ✓ VERIFIED | `main false` 输出 `0.1.16`(与 `frontend/package.json`、`backend/main.py` 一致);`v9.9.9 true` 正确非零退出并打印三方值。 |
| `.github/workflows/build-release.yml` | `build-macos` + `release` job 全流程 | ✓ VERIFIED | 逐行读取确认:内核下载(读 `CHROME_ENGINE_ZIP_URL_MACOS_ARM64`)→ pyinstaller `.app` → `plutil` 补 plist → 内核注入 → 逐层签名 → 双层验证 → 架构/dist/minOS 断言 → `--backend-only` 冒烟 → GUI 冒烟(崩溃+Cmd+Q 双维度)→ dmg → 内容验证 → upload-artifact → release job(needs 两个 build job,tag 守门,单一 softprops 调用)。windows `build` job 除移除 `Create GitHub Release` 步骤外逐字未动(`git diff` 验证)。 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `assets/app.icns` | `build-macos`(pyinstaller `--icon`) | `--icon "assets/app.icns"` | ✓ WIRED | 工作流 :228 行确认 |
| `assets/dmg-background.png`+@2x | `build-macos`(create-dmg) | `tiffutil -cathidpicheck` 合成 retina tiff | ✓ WIRED | 工作流 :711 行确认 |
| `build-macos`(Resolve version) | `scripts/release/check_version_consistency.py` | 捕获 stdout 写入 `$GITHUB_ENV` | ✓ WIRED | 工作流 :159 行调用,非零退出中止(:160-165) |
| `build-macos`(GUI 冒烟) | `launch_app.py:DesktopApplication.event` | 真实 cocoa 事件循环启动 + osascript Quit | ✓ WIRED | 工作流 :531-697 行,两个真实 CI 运行(失败/成功)反证有效 |
| 两个 build job 的 artifact | `release` job | `actions/download-artifact@v4` `pattern`+`merge-multiple` | ✓ WIRED(结构) / ⚠️ 未经真实 tag 触发验证 | 工作流 :791-813 行结构正确,但该 job 从未在真实 tag push 下执行过一次 |

### Data-Flow Trace (Level 4)

不适用——本 phase 无渲染动态数据的前端组件,CI 工作流与 Python 运行时函数不涉及此层。

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 版本一致性脚本对当前仓库判定为一致 | `python3 scripts/release/check_version_consistency.py main false` | stdout `0.1.16`,exit 0 | ✓ PASS |
| 版本一致性脚本对故意错误 tag 判定为不一致 | `python3 scripts/release/check_version_consistency.py v9.9.9 true` | stderr 含 `9.9.9`/`package.json`/`main.py`,exit 1 | ✓ PASS |
| `build_quarantine_failure_message(None)` 与前端常量逐字一致 | `python3 -c "import launch_app; print(...)"` | 命令行 `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app` 完全匹配 `GATEKEEPER_XATTR_COMMAND` | ✓ PASS |
| 全量单测(含 `test_macos_desktop_runtime`、`test_version_consistency`) | `.venv/bin/python -m unittest discover -s tests -v` | 118 tests, OK (skipped=2, 均为 Windows-only 用例) | ✓ PASS |
| 真实 CI 门禁存在且非摆设 | `gh run view 30418065169`(scratch 分支,故意保留缺陷代码) | conclusion=`failure`,GUI 冒烟按 Cmd+Q 维度正确失败 | ✓ PASS |
| 真实 CI 最终绿跑 | `gh run view 30418547844`(main @ `acfcc9a`) | conclusion=`success`,`build`/`build-macos` 均 success,`release` 按设计 skipped | ✓ PASS |

### Probe Execution

不适用——本 phase 无 `scripts/*/tests/probe-*.sh` 形式的探针脚本;打包/签名/dmg 链路的"探针"等价物是真实 `workflow_dispatch` CI 运行,已在上表与下方逐项覆盖(8 次真实运行,run id 见下)。

**真实 CI 运行核对表(通过 `gh run list`/`gh run view` 独立复核,非转述 SUMMARY)：**

| Run ID | 结论 | 触发事件 | headSha | 备注 |
|---|---|---|---|---|
| 30394320282 | success | workflow_dispatch | 28f7388 | 05-03 A2/A3 诊断修复后 |
| 30396059257 | failure | workflow_dispatch | e5fc1cf | 05-04 门禁验证,故意/中途失败(LSMinimumSystemVersion 定稿迭代) |
| 30396920074 | success | workflow_dispatch | 7aced9b | 05-04 门禁修复后绿跑 |
| 30402103536 | success | workflow_dispatch | e1a4ea9 | 05-05 release job 落地后绿跑 |
| 30408031397 / 30408314357 | cancelled | workflow_dispatch | — | gap-fix 1 CI 脚本调试迭代 |
| 30408617294 | failure | workflow_dispatch | d6403dc | gap-fix 1 反证:GUI 冒烟正确捕获 SIGSEGV |
| 30408816656 | success | workflow_dispatch | 26190e7 | gap-fix 1 修复后绿跑 |
| 30418065169 | failure | workflow_dispatch | d525e6d | gap-fix 2 反证:GUI 冒烟正确捕获 Cmd+Q 无限循环 |
| 30418547844 | success | workflow_dispatch | acfcc9a | gap-fix 2 修复后最终绿跑,05-06 checkpoint 用的就是这次产出 |

以上全部通过 `gh run list --workflow=build-release.yml` 与 `gh run view <id> --json conclusion,event,headSha,jobs` 独立查询确认,与各 SUMMARY 的记录完全一致,无夸大或选择性引用。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| PKG-01 | 05-03, 05-05 | tag push 触发并行 macOS job | ⚠️ 部分证据(behavior 未验证) | 结构(no matrix, macos-15)与并行性(startedAt 重叠)已验证;tag push 事件本身未真实触发 |
| PKG-02 | 05-01, 05-02, 05-03, 05-04, 05-06 | `.app` bundle + Cmd+Q | ✓ SATISFIED | 05-06 真机 Group C/D 全 PASS,两处真实缺陷已修复并有 CI 回归门禁 |
| PKG-03 | 05-02, 05-03, 05-06 | 逐层签名 + 双层硬门禁 | ✓ SATISFIED | CI 门禁结构正确且真实通过;真机确认 quarantine/AMFI/ASP 行为符合预期(自剥离成功,内核 AMFI adhoc 校验通过、无 ASP 拦截) |
| PKG-04 | 05-01, 05-03, 05-06 | dmg 内容与命名 | ✓ SATISFIED | 05-06 真机 Group A 全 PASS,CI `Verify dmg contents` 步骤断言三项存在 |
| PKG-05 | 05-04, 05-05 | `_g.py` 校验有效 + 两 dmg(现为一 dmg)与 Windows 同 Release | ⚠️ 部分证据(behavior 未验证) | `_g.py` 前提断言(dist 进包+运行时冒烟)已验证;"同一 Release"半句未经真实 tag push 验证 |

**ORPHANED requirements:** 无。REQUIREMENTS.md 对 Phase 5 的映射(PKG-01~05)与六份 PLAN 的 `requirements:` 字段完全对应,无遗漏、无多余。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | 无 TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER 匹配 | — | 对 `launch_app.py`、`.github/workflows/build-release.yml`、`scripts/release/check_version_consistency.py`、两份新测试文件全量 grep,零命中 |
| — | — | 无 `continue-on-error`/`if: always()`/`--deep --sign` | — | 工作流全文 grep 计数均为 0,签名门禁未被削弱 |

无 Blocker、无 Warning 级反模式。

### Human Verification Required

1. **推送真实 v* tag,确认 release job 真正执行并产出统一 Release**
   - **Test:** 推一个真实的 `v*` tag(自然会在 Phase 6 完成、正式发版 v0.2.0 时发生),观察 `release` job 从此前 8 次验证中的 `skipped` 变为 `success`
   - **Expected:** GitHub Release 页面上同时出现 `Open-Anti-Browser-Setup.exe` 与 `Open-Anti-Browser-{version}-arm64.dmg`,二者版本号与 tag 一致
   - **Why human:** 这是本 phase 全部自动化验证(8 次真实 CI 运行)刻意未覆盖的唯一路径——按 D-04 设计,调试通道全部走 `workflow_dispatch`,该事件下 `release` job 的 `if: startsWith(github.ref, 'refs/tags/')` 恒为假,job 结构性跳过。这不是遗漏,而是 05-05-SUMMARY 明确记录在案的已知残余风险("real tag push" 是唯一能验证这条路径的方式,且发版本身就是这个验证)。

### Gaps Summary

本 phase 无 `gaps_found` 级别的问题。所有六份 plan 的 `must_haves`(truths / artifacts / key_links / prohibitions)逐条核对代码库后均成立,包括两个由 05-06 真机 checkpoint 发现、且已在 gap-fix 与 gap-fix-2 中 root-cause 修复并留下真实 CI 反证的阻断性缺陷(macOS 双击后 ~2s SIGSEGV;Cmd+Q 后进程无限循环不退出)。

唯一未达到 `passed` 的原因是一个**行为未验证**(而非失败或缺失)的真相:ROADMAP SC1 与 SC4/PKG-05 都描述的"推送 v* tag → CI 触发 → 与 Windows 安装包一并挂到同一 GitHub Release"这条端到端路径,其触发条件(真实 tag push)从未在本 phase 的任何一次验证中被真正满足过——全部 8 次真实 CI 运行都是 `workflow_dispatch`,而这正是 `release` job 被设计为跳过的场景(D-04)。工作流的结构性证据(单一 `softprops/action-gh-release` 调用、`needs: [build, build-macos]`、tag 守门条件、资产齐备性断言、windows job 逐字未改)全部到位且经代码直读复核,但"结构正确"与"真实 tag 事件下确实按预期执行一次"是两件事,后者只有真正发版才能证实。这与 x64 缺失(已按 2026-07-27 scope 变更明确排除)是两类不同性质的事情——不是被移出范围,而是留待发版那一刻自然发生的验证。

---

*Verified: 2026-07-29*
*Verifier: Claude (gsd-verifier)*
