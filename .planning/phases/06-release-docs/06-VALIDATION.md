---
phase: 6
slug: release-docs
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-30
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `06-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (`launch_app.py` 改动) + Node `node:test` (`frontend/src/lib/*.js` 改动) |
| **Config file** | none — 与 CLAUDE.md「常用命令」记录的测试命令一致 |
| **Quick run command** | `node --test frontend/src/lib/*.test.js`(前端改动)/ `python -m unittest tests.test_macos_desktop_runtime -v`(后端改动) |
| **Full suite command** | `python -m unittest discover -s tests -v` |
| **Estimated runtime** | ~30 秒(前端 node:test ~5s;Python 全量受 CLAUDE.md「测试环境」限制,含 macOS 门槛模块) |

**Caveat(来自 CLAUDE.md):** 凡导入 `backend.browser_manager` / `backend.main` / `launch_app` 的测试在非 Windows 上无法运行。本 phase 触及的 `launch_app.py` 属该类模块 —— 依赖它的断言必须在 Mac 本地跑通后再依赖,不能只看 CI。

---

## Sampling Rate

- **After every task commit:** 前端/i18n 改动跑 `node --test frontend/src/lib/*.test.js`;`launch_app.py` 改动跑 `python -m unittest tests.test_macos_desktop_runtime -v`
- **After every plan wave:** `python -m unittest discover -s tests -v`(注意上方 macOS-only import 说明)
- **Before `/gsd-verify-work`:** 全量绿 **且** D-13/D-15 人工端到端 checkpoint 通过
- **Max feedback latency:** 30 秒

---

## Per-Task Verification Map

> 由 `/gsd-plan-phase` 播种;task ID 与 Threat Ref 待 PLAN.md 产出后由 `/gsd-validate-phase` 或执行期回填。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01/Task1 (quote), 06-01/Task2 (lock), 06-04/Task2 (three-way check) | 06-01, 06-04 | Wave 1, Wave 3 | DOCS-01 | T-06-01 | `xattr` 命令在 JS 常量 / Python 渲染消息 / release notes 模板三处逐字一致(D-04/D-12) | unit | `node --test frontend/src/lib/macosGatekeeperNotice.test.js frontend/src/lib/releaseNotesTemplate.test.js` + `python -m unittest tests.test_macos_desktop_runtime.BuildQuarantineFailureMessageTests -v` + 06-04 Task2 内联三方比对断言(`python3 -c "..."`,见 06-04-SUMMARY) | ✅ | ✅ green |
| 06-03/Task1 | 06-03 | Wave 2 | DOCS-01 | T-06-06 | 改写 `gatekeeper.step1`–`step4` 后中英 key 仍对齐,且不含禁用片段 | unit | `node --test frontend/src/lib/i18n-parity.test.js frontend/src/lib/gatekeeperCopyParity.test.js` | ✅ | ✅ green |
| TBD | TBD | TBD | DOCS-01, DOCS-02 | T-06-12 | Release notes 渲染出带引号命令、递进三步、前置要求清单 | manual_procedural | 无自动化等价物 — D-13/D-15 干净 macOS 账户人工验证 | ❌ W0(这是本 phase 的验收标准本身) | ⬜ pending (owned by 06-05) |
| TBD | TBD | TBD | DOCS-02 | T-06-09 | dmg 背景图文案匹配实测首启流程,且不含 `spctl` / `sudo` / `--master-disable` / 宽目录递归 | manual_procedural | 源 HTML 禁用词 grep + 目视核对(照搬 05-01 的 Forbidden-phrase audit;06-03 已跑过一次针对 06-03 内容自身的 scratch HTML 审计,此行专指 06-05 挂载真实 dmg 后的目视图标对齐复核) | ❌ W0 | ⬜ pending (owned by 06-05) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] 新增跨文件一致性测试(D-12)—— 读取三处文案面(JS 常量、Python 渲染消息、release notes 模板)并断言 `xattr` 命令逐字一致。落点由 planner 决定:扩展 `tests/test_macos_desktop_runtime.py` 的 `BuildQuarantineFailureMessageTests`,或新建 `node:test` 文件(两侧都能把 Markdown 模板当纯文本读)
- [ ] 更新 `frontend/src/lib/macosGatekeeperNotice.test.js` 现有的无引号路径断言,改为匹配 D-04 的加引号格式
- [ ] 更新 `tests/test_macos_desktop_runtime.py` 的 `test_non_translocated_bundle_message_points_to_its_own_path` 与 `test_translocated_scenario_matches_frontend_constant` 字面量期望,纳入新引号
- [ ] 无需安装测试框架 —— `unittest` 与 `node:test` 均已按 CLAUDE.md 记录接通

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 用户仅凭 Release notes/README 即可完成下载 → 放行 → 安装 → 创建配置 → 启动 Chrome 配置 | DOCS-01, DOCS-02 | 「文档是否足以让人自助走完全程」本质上无法自动化 —— D-15 明确要求人工执行且全程不得使用文档外知识 | **2026-07-31 起改为现有账户执行**(D-13 干净账户要求经开发者决定豁免):先卸载 `/Applications` 中现有安装,再仅依据发布文档走完全程;凡是发现自己动用了文档外知识,记为文档缺口并补文档 |
| 备选放行路径「系统设置 → 隐私与安全性 → 仍要打开」 | DOCS-01 | 该路径的界面状态由 per-user 的 Gatekeeper denial breadcrumb 驱动,现有账户已被 Phase 5 写入过该记录 | **不验证**(2026-07-31 随 D-13 豁免一并收窄)。补验条件:在干净系统用户账户中重跑该步骤 |
| dmg 背景图重生成后 create-dmg 图标坐标仍对齐 | DOCS-01 | 视觉对齐无法由断言表达 | 本地 `create-dmg` 产出 dmg 后挂载目视核对图标与背景文字位置 |
| `release` job 的 `body_path` 实际渲染效果 | DOCS-01 | `release` job 由 tag 触发,`workflow_dispatch` 下恒为 skipped —— 只能验 YAML 合法性与 job 图,渲染必须真实推 `v*` tag | `workflow_dispatch` 回归验 YAML/job 结构;渲染效果待真实 tag push 后在 Release 页核对(planner 需决定是否在本 phase 内推 tag) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
