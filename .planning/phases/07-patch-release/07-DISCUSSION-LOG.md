# Phase 7: 补丁发布与发布链路验证 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-31
**Phase:** 7-补丁发布与发布链路验证
**Areas discussed:** 正文内容与版本号

---

## 灰区选择

呈现了四个灰区,用户只选了「正文内容与版本号」:

| 灰区 | 描述 | Selected |
|------|------|----------|
| 发版排序与门禁 | SC1 的关闭按钮真机实测放在推 tag 之前(workflow_dispatch 产出的 dmg)还是之后(Release 里的 dmg) | |
| 关闭按钮实测口径 | 冻结 .app vs 源码;只测关闭按钮 vs 三条退出路径全跑;要不要给 build-macos GUI 冒烟门禁加第三维度 | |
| 正文内容与版本号 | v0.2.1 三处版本号同步;RELEASE_NOTES_TEMPLATE.md 要不要加「本次更新」章节 | ✓ |
| 失败回退与 A2 判定 | 正文仍未渲染时允不允许手工 gh release edit;A2 被推翻时就地调模板还是只记录 | |

**Notes:** 未选的三项在 CONTEXT.md 的 § Claude's Discretion 中原样保留,交给 planner 定夺,不丢失。

---

## 正文内容与版本号

### Q1 — v0.2.1 的「本次修了什么」怎么告诉用户?

| Option | Description | Selected |
|--------|-------------|----------|
| 模板顶部加手写章节(推荐) | 在 RELEASE_NOTES_TEMPLATE.md 顶部新增「本次更新 / What's Changed」双语章节,发版前手改。理由:自动 changelog 在本仓库只产出一行 compare 链接。代价:模板从「版本无关」变成「每次发版必改」 | ✓ |
| 不加,只留 compare 链接 | 模板保持版本无关、零维护。代价:点进去看到 14 条 commit,其中 12 条是 GSD 规划 docs | |
| 另开一个版本段文件 | 另维护 .github/RELEASE_HIGHLIGHTS.md 由流水线拼接。代价:要改 build-release.yml 的 release job,而那正是本 phase 要实证的那段 | |

**User's choice:** 模板顶部加手写章节
**Notes:** 讨论中实测确认了两个此前未记录的事实,直接支撑了这个选择——(1) `generate_release_notes: true` 在本仓库(直推 main、无 PR)只产出一行 `**Full Changelog**: compare/...`;(2) v0.2.0 线上那份完整正文是 `gh release edit` 手工贴的,不是流水线渲染的证据,因此不能当作 A2 的观测样本。

---

### Q2 — 「本次更新」章节漏改怎么拦?

| Option | Description | Selected |
|--------|-------------|----------|
| 扩展已有版本一致性门禁(推荐) | 让 check_version_consistency.py 多比一处:模板版本号必须与 tag / package.json / main.py 一致,漏改即构建失败 | ✓ |
| 只写人工 checklist | 在 PLAN / 发版步骤里写一条「发版前改模板」。零新增代码。代价:Phase 5 的两个阻塞缺陷都证明了「注释/提醒拦不住东西」 | |
| 章节不写版本号 | 写成「最近更新」而不写 v0.2.1。弱化后果而非拦截,下一个版本的读者会看到上一个版本的修复说明 | |

**User's choice:** 扩展已有版本一致性门禁
**Notes:** 与 Phase 6 建立的「单一事实源 + 单测锁」模式一致,是该模式的第三次应用。

---

### Q3 — 模板 107 行全是 macOS 内容,但同一 Release 还挂着 Setup.exe,Windows 读者怎么办?

| Option | Description | Selected |
|--------|-------------|----------|
| 在「本次更新」里按平台分条(推荐) | 写成「macOS: 修复关闭按钮…… / Windows: 本版本无功能变更」。零额外章节,顺带告诉 Windows 用户「下面那大篇不是给你的」 | ✓ |
| 另加一句版本无关导语 | 模板最顶部加「Windows 用户下载 Setup.exe 即可;以下说明仅适用于 macOS」。更显眼,但多一个需要维护的段落 | |
| 不动,记为 deferred | 本 phase 只做 UI-05 / PKG-06,Windows 文案属于 DOCS 范畴(Phase 6 的地盘) | |

**User's choice:** 在「本次更新」里按平台分条
**Notes:** 导语方案转入 CONTEXT.md 的 Deferred Ideas,若将来「本次更新」章节被移除或平台数量增加可回补。

---

### Q4 — `524aeb1` 的流水线修复要不要写进面向用户的「本次更新」?

| Option | Description | Selected |
|--------|-------------|----------|
| 不提,只讲关闭按钮(推荐) | 正文只写用户能感知的变化;流水线修复的证据落在 SUMMARY / UAT 供 PKG-06 核销,不污染发布说明 | ✓ |
| 提一句作为交代 | 写「v0.2.0 的发布说明因发布流程问题未能完整显示,已修复」。但 v0.2.0 的正文已手工补全,现在看到的人已经是完整版本 | |
| 不提,但处理 v0.2.0 页面 | 正文不提 CI 修复,另外去 v0.2.0 页面加一句指向 v0.2.1。代价:又一次手工 gh release edit,而本 phase 的目标正是证明不再需要手工补救 | |

**User's choice:** 不提,只讲关闭按钮

---

### 收尾确认

| Option | Description | Selected |
|--------|-------------|----------|
| 可以写 CONTEXT 了 | 其余灰区交给 planner 定,写入 Claude's Discretion | ✓ |
| 再聊聊正文内容 | 双语排布与位置、措辞基调、模板里版本号的具体写法 | |
| 去聊其他灰区 | 发版排序与门禁 / 关闭按钮实测口径 / 失败回退与 A2 判定 | |

---

## Claude's Discretion

- 发版与验证的先后排序(SC1 先验后发 vs 先发后验)——planner 应显式落盘,不要隐式选一个
- 关闭按钮实测的载体(冻结 .app vs 源码)与覆盖范围(一条路径 vs 三条),以及要不要给 `build-macos` 的 GUI 冒烟门禁加第三维度
- 失败回退策略(允不允许再手工 `gh release edit`)与 A2 被推翻时的处置(就地调模板 vs 只记录判定)
- 「本次更新」新章节的双语排布与具体位置、措辞基调、模板里版本号的具体书写形式(直接影响 D-02 门禁怎么抓取)
- 版本号 bump、模板改动、门禁扩展三者的 commit 切分与 tag 时机

## Deferred Ideas

- 模板顶部的版本无关平台导语(D-03 用按平台分条替代)
- Windows 侧的完整发布文档(模板目前零 Windows 内容,属 DOCS 范畴,不在 UI-05/PKG-06 覆盖内)
- v0.2.0 Release 页面加指向 v0.2.1 的说明(D-04 否决,会再引入一次手工编辑)
