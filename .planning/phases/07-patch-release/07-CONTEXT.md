# Phase 7: 补丁发布与发布链路验证 - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

用**一次真实的 `v0.2.1` tag push**,把三件「已修好但从未被真实验证过」的事同时兑现:

1. macOS 关闭按钮真机退出实证(`a886dc7`,至今只有单测 + AST 结构断言)
2. Release 正文由流水线自动渲染实证(`524aeb1`,release job 补 `actions/checkout` 后首次真实执行)
3. `06-RESEARCH.md` 假设 A2(`body_path` 内容前置于自动 changelog)的正反判定

**两处代码修复都已在 main 上,本 phase 的工作是「发布并验证」,不是重新实现。**

本次讨论只覆盖了**发布正文内容与版本号**这一个灰区(用户主动收窄)。其余三个识别出的灰区——发版与验证的先后排序、关闭按钮实测的载体与覆盖范围、失败回退与 A2 判定处置——用户明确交给 planner 定夺,见 § Claude's Discretion。

不在本 phase:任何新功能;应用侧任何超出 `a886dc7` 已有修复的行为变更。

</domain>

<decisions>
## Implementation Decisions

### Release 正文的「本次更新」章节

**背景(决定了下面四条,必读):** 讨论中实测确认了两个此前无人记录的事实:

1. `.github/RELEASE_NOTES_TEMPLATE.md` 现为 107 行、**版本无关**(中文全篇 1–51 行 + English 全篇 55–107 行的并列结构),内容全部是「系统要求 / 签名信任说明 / Gatekeeper 放行指引」,**零「本次更新」章节**。
2. `generate_release_notes: true` 在本仓库**只产出一行 `**Full Changelog**: compare/...` 链接**——GitHub 的自动 notes 是从 PR 生成的,本仓库直推 main、无 PR。v0.2.0 线上那份完整正文是 `gh release edit` 手工贴的,**不是流水线渲染的证据**(这一点对 SC3/A2 的判定很关键:v0.2.0 不能当作 A2 的观测样本)。
3. `v0.2.0..HEAD` 共 14 个 commit,其中 **12 个是 GSD 规划 `docs(...)`**,真正的修复只有 `a886dc7` 与 `524aeb1` 两个。

- **D-01:** 在 `.github/RELEASE_NOTES_TEMPLATE.md` **顶部新增手写的「本次更新 / What's Changed」章节**,每次发版前手改。
  理由:自动 changelog 在本仓库只有一行 compare 链接,不写就等于不告诉用户修了什么;而点进 compare 看到的是 14 条 commit、其中 12 条是 GSD 规划文档,真正的修复埋在里面。
  被否决的备选:(a) 不加、只留 compare 链接;(b) 另开 `.github/RELEASE_HIGHLIGHTS.md` 由流水线拼接——(b) 需要改 `build-release.yml` 的 release job,**而那正是本 phase 要实证的那段**,改它会把 SC2 的验证对象一并改掉。
  — **Reversibility:** costly — 模板从此由「版本无关、零维护」变成「每次发版必改」,这个属性由 D-02 的门禁固化后就成了发版流程的硬约束;回退需同时撤掉门禁扩展与其测试。

- **D-02:** **扩展已有的 `scripts/release/check_version_consistency.py` 门禁**,把模板里的版本号纳入一致性比对:模板版本号必须与 tag / `frontend/package.json` / `backend/main.py` 一致,漏改即构建失败、tag 发不出去。
  理由:D-01 引入的「每次发版必改」不能靠人记。Phase 5 的两个阻塞缺陷(05-02 SIGSEGV、05-06 Quit 死循环)都证明了「注释/提醒拦不住东西」;Phase 6 建立的「单一事实源 + 单测锁」模式在这里直接复用。
  被否决的备选:(a) 只写人工 checklist;(b) 章节不写版本号(只写「最近更新」)——(b) 把漏改的后果从「自相矛盾」弱化成「内容过时」,是弱化后果而非拦截,下一个版本的读者会看到上一个版本的修复说明。
  — **Reversibility:** reversible — 局部改动,现有脚本已有清晰的 `VersionMismatch` 抛出路径与单测覆盖。

- **D-03:** 「本次更新」章节**按平台分条**——`macOS: 修复点关闭按钮后应用仍在后台运行的问题` / `Windows: 本版本无功能变更`。不另加版本无关的导语段落。
  理由:模板 107 行全是 macOS 内容,但同一个 Release 还挂着 `Open-Anti-Browser-Setup.exe`,Windows 读者打开会以为整篇都跟自己有关。按平台分条零额外章节成本,顺带告诉 Windows 用户「下面那大篇不是给你的」。
  被否决的备选:(a) 顶部另加一句「Windows 用户下载 Setup.exe 即可,以下说明仅适用于 macOS」——更显眼但多一个需要维护的段落;(b) 不动、记为 deferred。

- **D-04:** `524aeb1` 的**流水线修复不写进面向用户的正文**。正文只写用户能感知的变化(macOS 关闭按钮)。
  理由:用户不关心 CI 内部缺陷;而且 v0.2.0 的正文已经手工补全,现在点进去的人看到的已经是完整版本,「已修复显示问题」的交代对他们没有对应物。PKG-06 的核销证据落在 SUMMARY / UAT 文档里,不污染发布说明。
  被否决的备选:(a) 提一句作为交代;(b) 正文不提但另外去 v0.2.0 页面加一句指向 v0.2.1——(b) 又是一次手工 `gh release edit`,**而本 phase 的目标正是证明不再需要手工补救**。

### Claude's Discretion

用户明确把以下交给 planner/researcher 定夺(讨论中列出但主动未选):

- **发版与验证的先后排序(影响 SC1/SC2 的验证门禁)** — SC1 的关闭按钮真机实测放在推 tag 之前(用 `workflow_dispatch` 产出的 dmg)还是之后(用 Release 里的 dmg)。权衡:先发后验,一旦失败就得对用户可见地再发 v0.2.2;先验后发,验的不是最终发布产物。**planner 应当把这一条当作 phase 级排序决策显式落盘,而不是隐式选一个。**
- **关闭按钮实测的载体与覆盖范围** — 冻结的 `.app` vs 源码跑 `launch_app.py`(注:05-02 与 05-06 两次缺陷都只在冻结包里暴露);只测关闭按钮 vs 关闭按钮 / Cmd+Q / 菜单栏图标退出三条路径全跑;要不要给 `build-macos` 的 GUI 冒烟门禁加第三维度(AppleScript 点关闭按钮并断言进程退出),让这条路径有回归护栏而不只有 AST 断言。
- **失败回退策略与 A2 判定处置** — v0.2.1 正文若仍未渲染,允不允许再用 `gh release edit` 手工补救;A2 被推翻(自动 changelog 排在手写正文之前)时,本 phase 就地调模板排版还是只记录判定。
- 「本次更新」新章节的**双语排布与具体位置**(中英各自跟随所在语言区块之首 vs 两段紧挨着放整篇顶部)、措辞基调、模板里版本号的**具体书写形式**(直接影响 D-02 的门禁用什么方式抓取)。
- 版本号 bump(`frontend/package.json` + `backend/main.py` 两处 `version=`)、模板改动、门禁扩展三者的 commit 切分与 tag 时机。注意 `check_version_consistency.py` 在 tag 模式下要求 `tag == package.json == main.py`,所以 0.2.1 必须先落到 main、tag 再指向那个 commit。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

ROADMAP.md 未为 Phase 7 声明 Canonical refs,以下为本次讨论累积。

### 本 phase 要验证的两处修复(已在 main,不要重新实现)
- `launch_app.py` §`should_close_to_tray()` / `should_intercept_quit_event()` / `handle_macos_quit_request()` / `closeEvent()` — `a886dc7` 的修复本体。**函数上方的注释记录了 05-02 与 05-06 两次真机缺陷的成因,是 SC1 为什么必须真机实测的直接依据**
- `tests/test_macos_desktop_runtime.py` — `a886dc7` 附带的单测与 AST 结构断言(SC1 明确指出「至今只有单测和结构断言,没有真机证据」)
- `.github/workflows/build-release.yml` §`release` job — `524aeb1` 补上的 `actions/checkout` 步骤 + `body_path: .github/RELEASE_NOTES_TEMPLATE.md`。**这段是 SC2 的验证对象,除非有充分理由否则不要改动它**
- `.github/workflows/build-release.yml` §`build-macos` job 的 GUI 冒烟门禁 — 现有两维度(18s 存活 + `osascript quit` 有界退出),是 Claude's Discretion 里「要不要加第三维度」的现状基线

### 本 phase 要改动的文案与门禁载体
- `.github/RELEASE_NOTES_TEMPLATE.md` — 107 行,中文全篇 1–51 / English 全篇 55–107。D-01/D-03/D-04 的改动对象
- `scripts/release/check_version_consistency.py` — D-02 的扩展对象。现读 `frontend/package.json` 与 `backend/main.py`(要求后者恰有 ≥2 个 semver 形状的 `version=` 且彼此一致);`normalize_tag()` 用 `removeprefix` 而非 `lstrip`
- `frontend/package.json` §`version` 与 `backend/main.py` 两处 FastAPI `version=` — 版本号 bump 的三个落点(`CLAUDE.md` 明文约定三处一起改)

### 验证口径与历史证据(SC1/SC2/SC3 的事实基础)
- `.planning/phases/06-release-docs/06-RESEARCH.md` §Assumptions 表 **A2 行** — SC3 要判定/推翻的那条假设的原文与置信度说明
- `.planning/phases/06-release-docs/06-05-SUMMARY.md` §「Release Body 实测」 — v0.2.0 真实 tag push 的观测记录 + checkout 缺陷的发现经过
- `.planning/phases/05-ci/05-UAT.md` — 测试 1 已于 2026-07-31 由 v0.2.0 核销(pass);本 phase 不重复核销该项
- `.planning/phases/05-ci/05-05-SUMMARY.md` — release job 结构与「真实发布路径从未执行过」的残余风险原始记录
- `.planning/phases/06-release-docs/06-CONTEXT.md` §D-09/D-10/D-12 — Release notes 落地的原始决策(`body_path` + 保留 `generate_release_notes`、一份模板双语并列、模板与 `GATEKEEPER_XATTR_COMMAND` 逐字一致的单测锁)。**D-12 的逐字一致锁仍然有效,改模板时不得破坏**

### 范围与约束的权威来源
- `.planning/ROADMAP.md` §Phase 7 — SC1/SC2/SC3 原文,含「三条标准共享同一个验证动作(一次真实 v0.2.1 tag push),不应拆到不同 wave 分别发版」的显式约束
- `.planning/REQUIREMENTS.md` — UI-05(第 52 行)、PKG-06(第 53 行)原文
- `CLAUDE.md` — 用户可见文案用中文、commit message 用英文;版本号三处同改;`backend/_g.py` 哈希锁定 `openSourceNotice.js` 与 `App.vue`,**不得触碰**

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/release/check_version_consistency.py`:已是独立可测的纯函数结构(`read_package_version` / `read_main_versions` / `check_version_consistency`),D-02 的扩展照搬 `read_main_versions` 的正则抽取 + `VersionMismatch` 抛出模式即可,无需新建脚本
- `build-macos` job 的 GUI 冒烟门禁:已建立「真 cocoa GUI(刻意不设 `QT_QPA_PLATFORM=offscreen`)+ 有界超时断言 + 残留进程检查」的完整套路,若采纳「加第三维度」则直接在该步骤内扩展
- Phase 6 建立的跨文件逐字一致单测(模板 `xattr` 命令 ↔ `GATEKEEPER_XATTR_COMMAND`):D-02 的版本号一致性锁是同一模式的第二次应用

### Established Patterns
- **单一事实源 + 门禁锁**:Phase 5/6 反复验证有效,D-02 是它的第三次应用(前两次:版本号跨 `package.json`/`main.py`、放行命令跨模板/前端常量)
- **区分「实测」与「推断」**:Phase 5/6 的 SUMMARY 明确标注两者。SC1/SC3 都要求实测证据(`ps`/活动监视器、Release 正文实际渲染顺序),本 phase 的产出必须守住这条线——注意 v0.2.0 的线上正文是**手工贴的**,不能当作 A2 的观测样本
- **CI 门禁失败即发版失败**:`check_version_consistency.py` 已在 `build` job 中以退出码方式阻断,D-02 沿用同一阻断路径

### Integration Points
- `build-release.yml` 第 148–163 行附近:`check_version_consistency.py` 的调用点,D-02 的扩展若改变脚本入参/输出需同步此处
- `release` job 的 `softprops/action-gh-release` 步骤:`body_path` 注入点,**SC2/SC3 的观测点,本 phase 原则上只观测不改动**
- 模板改动会触发 Phase 6 建立的模板一致性测试(`xattr` 命令逐字比对),改模板后需跑全套(118 Python + 52 node:test,用仓库既有 `.venv`)

</code_context>

<specifics>
## Specific Ideas

- 「本次更新」章节的措辞基调延续 Phase 6:讲用户能感知的现象,不讲内部机制。macOS 那条建议写成用户视角的症状描述(「点关闭按钮后应用仍在后台运行」),而不是实现描述(「closeEvent 不再走托盘分支」)
- Windows 那条即使是「无功能变更」也要显式写出来,不能省略——省略等于让 Windows 用户继续以为整篇 macOS 说明与自己有关,这正是 D-03 要解决的问题
- v0.2.0 的 Release 页面**保持原样不再手工编辑**。它的正文已由 `gh release edit` 补全,再动一次就与本 phase「证明不再需要手工补救」的目标自相矛盾

</specifics>

<deferred>
## Deferred Ideas

- **模板顶部的版本无关平台导语**(「Windows 用户下载 Setup.exe 即可,以下说明仅适用于 macOS」)— D-03 选择用按平台分条替代。若将来「本次更新」章节被移除或平台数量增加,可回补这个导语
- **Windows 侧的完整发布文档**(模板目前 107 行零 Windows 内容)— 属于 DOCS 范畴(Phase 6 的地盘),不在 UI-05/PKG-06 的 requirement 覆盖内。若将来 Windows 侧也有需要文档化的安装/放行环节,应另开 phase
- **v0.2.0 Release 页面加指向 v0.2.1 的说明** — D-04 否决(会再引入一次手工 `gh release edit`)。若将来 v0.2.0 被发现有影响使用的问题,再单独处理

</deferred>

---

*Phase: 7-补丁发布与发布链路验证*
*Context gathered: 2026-07-31*
