---
phase: 04-frontend-platform-gating
plan: 06
subsystem: ui
tags: [macos-uat, vue3, i18n, gatekeeper, capabilities-contract]

# Dependency graph
requires:
  - phase: 04-frontend-platform-gating (plans 01-05)
    provides: "全部自动化门控代码(capabilitiesGating.js、i18n 24 条双语文案、ProfileList/SyncManager/AppSettings/App.vue 门控消费点、macosGatekeeperNotice.js 首启弹窗)"
provides:
  - "本 phase 三项人工核销结论(既有 Firefox 配置能力矩阵、Gatekeeper 放行指引在 macOS 15.7 真机的逐字核对、双语平台限制文案可读性)——RESEARCH 假设 A2 已在真机闭环"
  - "A8 讨论裁定:GroupManager Firefox 计数列改为按需显示(capabilitiesGating.js 新增 shouldShowFirefoxColumn 纯函数),推翻 04-05 SUMMARY 的原「不隐藏」建议"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "shouldShowFirefoxColumn(capabilities, groups) 延续 D-00:引擎可用时恒真(Windows 零回归),不可用时仅当分组内确有 firefox 配置才真——与 isFirefoxEngineAvailable/isEngineSelectorLocked/getWindowFeatureGate 同属 capabilitiesGating.js 的单一事实源"

key-files:
  created: []
  modified:
    - frontend/src/lib/capabilitiesGating.js
    - frontend/src/lib/capabilitiesGating.test.js
    - frontend/src/components/GroupManager.vue

key-decisions:
  - "A8(用户拍板,推翻 planner 原建议):GroupManager 的 Firefox 计数列从「无条件保留」改为「按需显示」——该列反映的是既有配置构成而非可创建引擎,不受 UI-01 隐藏约束,但对没有任何 firefox 配置的全新 macOS 用户是恒为 0 的噪音列;折中方案已在真机验证两个分支(有夹具时显示、删除夹具后消失且配置数与 Chrome 列对得上)"
  - "B2(RESEARCH 假设 A2 核销):Gatekeeper 指引文案的『系统设置 → 隐私与安全性 → 安全性 → 仍要打开』流程,在 macOS 15.7(Sequoia,build 24G222)真机逐字核对通过,与 Sequoia 移除右键绕过后的实际系统 UI 一致——这是本 phase 唯一「正确性不在代码库里」的交付物,现已闭环"
  - "CLAUDE.md 记录的前端开发后端端口(8000)与本次真机验收实测的 Vite 代理目标端口(18000)不一致,记录为 follow-up 文档漂移,不在本 plan 修正"

patterns-established: []

requirements-completed: [UI-01, UI-02, UI-03, UI-04]

coverage:
  - id: D1
    description: "既有 engine=firefox 配置(模拟 Windows 迁移)在 macOS 上的完整能力矩阵——可见+Firefox标签、仅Windows标记、启动禁用+悬停提示、复制禁用+删除可用、引擎选择器锁定且保存后 engine 未被静默改写、批量启动只跑 Chrome 无报错 toast、筛选下拉仅 Chrome——真机逐项通过,并额外做了后端日志+落盘复核确认保存链路真实执行(非空操作)且未损伤其余配置"
    requirement: "UI-01"
    verification:
      - kind: manual_procedural
        ref: "04-06 人工 UAT A 组 7 项 + A5 数据完整性专项复核(POST /api/profiles 200 OK,engine 落盘仍为 firefox,firefox/chrome 子配置字段完好,remark/updated_at 已更新证明保存链路真实执行,其余 4 条真实配置无附带损伤)"
        status: pass
    human_judgment: true
    rationale: "视觉/交互确认(标签渲染、气泡悬停、保存后落盘状态)需要真机人工执行,已在本次 UAT 完成,记录为既成事实而非待办。"
  - id: D2
    description: "A8 讨论裁定并已实现:GroupManager 的 Firefox 计数列由无条件保留改为按需显示,新增 shouldShowFirefoxColumn(capabilities, groups) 纯函数(D-00 合规,未自行推导平台),真机验证两个分支行为正确"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/capabilitiesGating.test.js — shouldShowFirefoxColumn 6 条新增用例(Windows 分支/迁移用户分支/全新用户分支/fail-open/畸形输入/纯函数不改入参),node --test frontend/src/lib/*.test.js → 43/43 pass"
        status: pass
      - kind: manual_procedural
        ref: "真机验证:有 firefox 夹具时列显示;删除夹具后列消失,且「配置数 = Chrome = 4」对得上"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gatekeeper 放行指引(UI-04)在 macOS 15.7 真机逐字核对——弹窗先后顺序不重叠、指引措辞与系统实际菜单/按钮文字一致(核销 RESEARCH 假设 A2)、xattr 命令可完整复制无转义、未引导关闭整个 Gatekeeper 或递归操作宽泛目录、确认后不再复现"
    requirement: "UI-04"
    verification:
      - kind: manual_procedural
        ref: "04-06 人工 UAT B 组 5 项,macOS 15.7 (build 24G222) 真机核对;安全底线机械复核 grep spctl/sudo/~/Downloads 命中全部限定在 macosGatekeeperNotice.js:9-10 的声明性注释内,用户可见文案零命中"
        status: pass
    human_judgment: true
    rationale: "Gatekeeper 措辞是否与当前 macOS 版本真实 UI 一致是文案正确性判断,RESEARCH 假设 A2 明确要求真机人工核销,任何 grep/单测无法覆盖;已在本次 UAT 完成。"
  - id: D4
    description: "双语平台限制说明卡片与置灰提示(UI-02/UI-03)的可读性——设置页卡片点名三项具体能力、中英来回切换全部跟随(唯一预期例外:后端 reason 原文字符串按 D-02 锁定决策保持中文)、文案不误导整体可用性、同步器导航置灰但点击仍可进入且视图内横幅/按钮禁用/分组筛选与设置弹层仍可用"
    requirement: "UI-02"
    verification:
      - kind: manual_procedural
        ref: "04-06 人工 UAT C 组 4 项,zh-CN/en-US 双语真机来回切换核对"
        status: pass
    human_judgment: true
    rationale: "文案是否读起来准确得体、是否会让用户误解为整个应用不支持 macOS,是主观阅读判断,任何自动化断言无法覆盖;已在本次 UAT 完成。"

duration: 35min
completed: 2026-07-27
status: complete
---

# Phase 4 Plan 6: macOS 真机人工验收 Summary

**Phase 4 全部三项无法自动断言的交付(既有 Firefox 配置能力矩阵、Gatekeeper 放行指引在 macOS 15.7 Sequoia 真机的逐字核对、双语平台限制文案可读性)已由真机人工验收全部通过,唯一发现的裁量分歧(GroupManager Firefox 计数列)已当场讨论裁定并实现为 `shouldShowFirefoxColumn()` 补丁(commit `3e32105`)。**

## Performance

- **Duration:** ~35 min（含真机 UAT 往返 + A8 补丁实现与验证）
- **Completed:** 2026-07-27
- **Tasks:** 1（checkpoint:human-verify）
- **Files modified:** 3（A8 补丁,由 orchestrator 在本 checkpoint 期间实现并提交,非本 plan 原计划的 `files_modified`）

## Accomplishments

- **A 组(UI-01,7 项全部通过)**：既有 `engine=firefox` 配置(模拟 Windows 迁移,夹具 `UAT-迁移自Windows-Firefox`)在 macOS 上：行可见带 Firefox 标签、「仅 Windows」标记、启动禁用+悬停气泡、复制禁用+删除可用、引擎选择器锁定、批量启动只跑 Chrome 无报错 toast、筛选下拉仅 Chrome。
- **A5 数据完整性专项复核**：编辑保存后端日志确认 `POST /api/profiles 200 OK`；落盘复核 `engine` 仍为 `'firefox'`(未被静默改写为 chrome)、firefox 子配置 7 个字段完好、chrome 子配置原样保留、`remark`/`updated_at` 已更新(证明走完了真实保存链路而非空操作)、其余 4 条真实配置无附带损伤。
- **A8 讨论裁定并已实现**：GroupManager 的 Firefox 计数列由 planner 原建议的「无条件保留」改为用户拍板的「按需显示」——`capabilitiesGating.js` 新增纯函数 `shouldShowFirefoxColumn(capabilities, groups)`(D-00 合规,不自行推导平台),`GroupManager.vue` 加 `v-if="firefoxColumnVisible"`。真机验证两个分支：有 firefox 夹具时列显示；删除夹具后列消失,且「配置数 = Chrome = 4」对得上。
- **B 组(UI-04,5 项全部通过,含 RESEARCH 假设 A2 核销)**：开源声明与 Gatekeeper 指引先后不重叠；指引措辞(「系统设置 → 隐私与安全性 → 安全性 → 仍要打开」)与 **macOS 15.7(Sequoia,build 24G222)** 真机逐字相符；`xattr -dr com.apple.quarantine …` 完整可复制无转义；未引导关闭整个 Gatekeeper 或递归操作宽泛目录(机械复核确认 `spctl`/`sudo`/`~/Downloads` 命中全部限定在代码注释内,用户可见文案零命中);确认后刷新不再弹出。
- **C 组(UI-02/UI-03,4 项全部通过)**：设置页「平台限制说明」卡片点名 Firefox 内核/窗口排列同步/首次运行放行三项具体能力；中英切换全部跟随(唯一预期例外:后端 `reason` 原文按 D-02 锁定决策保持中文);文案读作「这几个功能不可用」而非「应用不支持 macOS」；同步器导航置灰但点击仍可进入视图,视图内横幅+按钮禁用+分组筛选/同步设置弹层仍可用。
- 全部三组共 17+1 项(含 A8 裁量项)人工验收结论逐条记录,构成 `/gsd-verify-work` 对 UI-01..UI-04 的验收证据。

## Task Commits

本 plan 自身无独立任务提交(checkpoint 任务,`files_modified: []`)。UAT 过程中产生的唯一代码变更由 orchestrator 在 checkpoint 期间实现并提交：

1. **A8 补丁：GroupManager Firefox 计数列按需显示** - `3e32105`（feat，orchestrator 实现，非 executor）

**Plan metadata:** 见本 SUMMARY 提交（docs）

## Files Created/Modified

- `frontend/src/lib/capabilitiesGating.js` - 新增 `shouldShowFirefoxColumn(capabilities, groups)` 纯函数
- `frontend/src/lib/capabilitiesGating.test.js` - 新增 6 条测试用例(Windows 分支/迁移用户分支/全新用户分支/fail-open/畸形输入/纯函数不改入参)
- `frontend/src/components/GroupManager.vue` - Firefox 计数列加 `v-if="firefoxColumnVisible"`,新增 computed 调用 `shouldShowFirefoxColumn`

## Decisions Made

- **A8(用户拍板,推翻 04-05-SUMMARY 原建议)**：GroupManager 的 Firefox 计数列从「无条件保留」改为「按需显示」。理由：该列报告的是「现有配置构成」而非「可创建引擎」，不受 UI-01 约束；但对没有任何 firefox 配置的全新 macOS 用户，它是恒为 0、还挂着用不了的引擎名的噪音列。折中方案两边都满足——迁移用户仍能看到真实计数(不违反 D-01「不删不藏」)，全新用户不再看到噪音列。
- **B2(RESEARCH 假设 A2 正式核销)**：Gatekeeper 指引描述的「系统设置 → 隐私与安全性 → 安全性 → 仍要打开」流程,在真实的 macOS 15.7(Sequoia)系统上核对无误——这是 04-RESEARCH.md 明确标记为「仅有二手来源引用、需真机人工核实」的唯一条目，现已闭环，无需修改文案。
- **文档漂移记录(follow-up，非本 phase 缺陷)**：`CLAUDE.md` 记录的前端开发后端端口为 8000，但 `vite.config.js` 的 `/api` 代理实际指向 18000；`frontend/package.json` 的 prebuild/postbuild 钩子调用裸 `python`，macOS 上通常只有 `python3`，本次验收依赖临时 PATH shim 才跑通 `npm run build`。两项均记录为后续可修的文档/工程漂移，不在本 plan 修正。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - 架构/裁量决策，经用户裁定] GroupManager Firefox 计数列显示策略调整**
- **Found during:** Checkpoint 人工 UAT，A8 项
- **Issue:** 04-05-SUMMARY 记录的原有裁量是「无条件保留 Firefox 计数列」，理由是隐藏会导致分组合计对不上账；但真机验收时用户指出这对全新 macOS 用户(无任何 firefox 配置)是一列恒为 0 的噪音信息。
- **Fix:** 用户当场拍板改为「按需显示」——新增 `shouldShowFirefoxColumn(capabilities, groups)` 纯函数，Windows/有迁移配置时显示，全新 macOS 用户时隐藏；由 orchestrator 在 checkpoint 期间实现（非本 plan 常规任务流程内的 executor 提交）。
- **Files modified:** `frontend/src/lib/capabilitiesGating.js`、`frontend/src/lib/capabilitiesGating.test.js`、`frontend/src/components/GroupManager.vue`
- **Verification:** `node --test frontend/src/lib/*.test.js` → 43/43 pass；`python3 -m backend._g --mode build` → exit 0；完整 `npm run build` → exit 0；真机验证两个分支行为正确
- **Committed in:** `3e32105`

---

**Total deviations:** 1（Rule 4 架构/裁量类，经用户在 checkpoint 现场明确决策后落地，非自动裁定）
**Impact on plan:** 补丁范围极小（1 个纯函数 + 1 个 `v-if` + 6 条测试），不影响本 phase 其余任何已完成交付；未违反任何既有决策（D-00/D-01 均满足）。

## Issues Encountered

None — 三组验收全部一次通过，未发现需要修正的缺陷。

## User Setup Required

None - no external service configuration required.

## Follow-up Items (记录，不在本 phase 处理)

| Category | Item | Notes |
|----------|------|-------|
| 文档漂移 | `CLAUDE.md` 记录前端开发后端端口 8000，实际 `vite.config.js` 代理到 18000 | 建议后续 phase 或独立 docs 修正 CLAUDE.md |
| 工程健壮性 | `frontend/package.json` prebuild/postbuild 钩子调用裸 `python`，macOS 上通常只有 `python3` | 建议后续改为可配置或增加 `python3` 回退；本次验收靠临时 PATH shim 绕过 |

## Next Phase Readiness

- Phase 4 的四项需求 UI-01/UI-02/UI-03/UI-04 全部完成人工核销，可提交 `/gsd-verify-work` 或推进到 Phase 5。
- RESEARCH 假设 A2（Gatekeeper 措辞真机核实）已闭环，无需在 Phase 6（release notes）重新验证系统 UI 措辞本身，但 Phase 6 撰写发布文档时仍应参考本次 macOS 15.7 的核对结论。
- 两项 follow-up（CLAUDE.md 端口漂移、prebuild 钩子 python/python3）记录在案，供后续 phase 或独立 docs-update 处理，不阻塞 Phase 4 收尾。
- 无阻塞项。

---
*Phase: 04-frontend-platform-gating*
*Completed: 2026-07-27*

## Self-Check: PASSED

Verified: commit `3e32105` present in git log (`git log --oneline` confirms); `frontend/src/lib/capabilitiesGating.js`, `frontend/src/lib/capabilitiesGating.test.js`, `frontend/src/components/GroupManager.vue` diffs read directly and match description; `node --test frontend/src/lib/*.test.js` → 43/43 pass; `python3 -m backend._g --mode build` → exit 0.
