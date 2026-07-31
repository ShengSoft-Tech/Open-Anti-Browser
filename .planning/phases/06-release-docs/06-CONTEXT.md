# Phase 6: 发布文档与端到端验证 - Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

macOS 用户拿到未签名的 dmg 后，**无需开发者协助**即可自行完成放行、安装并开始使用。

交付物是**文档**（Release notes 模板 + README 前置要求 + 三处放行文案统一），加上一次「用户仅凭文档能否自助走完全程」的**真实端到端验证**。

不在本 phase：任何新功能、任何运行时行为变更（唯一例外是 D-04 修 code review WR-01 的命令转义，因为它与文档文案由单测锁定必须同改）。

</domain>

<decisions>
## Implementation Decisions

### 放行路径写哪一条

**背景（必读，决定了下面四条）：** Phase 5 的 05-06 真机 checkpoint 用带毫秒时间戳的 `syspolicyd` 日志证明，**放行不是靠系统设置成功的**：

```
22:32:20.606  启动#1 App ready，Python 开始跑
     ↓        这 12 秒内 maybe_strip_quarantine() 成功摘掉 quarantine
22:32:31.034  syspolicyd: Prompt shown (6, 0), waiting for response
22:32:32.911  syspolicyd: Adding Gatekeeper denial breadcrumb (open)   ← 被拒
22:32:32.924  kernel ASP: Security policy would not allow process: 35736
22:32:35.818  启动#2 → 无弹框、直接可用（此时 .app 上已无 quarantine）
```

`spctl --assess` 至今仍报 `rejected` —— 系统里从未产生过针对本应用的放行记录。

- **D-01:** Release notes 的放行说明**以 Phase 5 实测路径为主路径**：双击 → 看到拦截提示就关掉 → **再双击一次**即可用。系统设置与 `xattr` 命令降为备选。ROADMAP SC1 与 REQUIREMENTS DOCS-01 现文写的「系统设置 → 隐私与安全性 → 仍要打开」是在 Phase 5 出结果**之前**写的，与实测不符，需一并改写。

- **D-02:** **三个消费面全部改成一致**，不允许再有第二种说法：
  1. Release notes 模板（新建）
  2. `assets/dmg-background.png` + `@2x` —— 现在教「右键点图标 →「打开」」，**连实测路径都不是**，需重生成两张 png
  3. Phase 4 已交付的应用内提示四步文案（`frontend/src/i18n/zh-CN.js` 与 `en-US.js` 的 `gatekeeper.step1`–`step4`）
  — **Reversibility:** costly — 动的是 Phase 4 已验收交付物与 Phase 5 的二进制资产。回退需重跑 Phase 4 的 i18n/notice 单测并再次重生成 png；文案本身可改，但「已验收交付物被后续 phase 改动」这件事需要 verifier 重新核对 Phase 4 的 UI-04 验收仍然成立。

- **D-03:** 放行说明写成**递进三步**给兼容退路：
  1. 「再双击一次」（正常情况读者只需看这一步）
  2. 「仍打不开 → 系统设置 → 隐私与安全性 → 仍要打开」
  3. `xattr` 命令
  理由：自剥离只在**一台** macOS 15.7 arm64 上验证成功，其他机器上未必同样成立（用户可能装到非 `/Applications` 位置，或真的触发 App Translocation）。只写主路径的话，一旦自剥离失败用户会彻底卡死、无从下手。

- **D-04:** `xattr` 命令用**加引号的固定路径**：`xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"`。同步修 `05-REVIEW.md` 的 **WR-01**（应用内 `GATEKEEPER_XATTR_COMMAND` 目前是裸路径无引号，路径含空格会拼错）。两处由单测锁定逐字一致，**必须同改**。

### 硬件/系统门槛怎么讲

- **D-05:** REQUIREMENTS 的 **DOCS-02 原文「双架构下载选择指引」已失效** —— x64 于 2026-07-27 移出 v0.2，没有第二个包可选。重写为「**前置要求清单**」：下载前确认 **Apple Silicon + macOS 15 或更新**。不假装有选择，直接说清能不能跑。
  注意 DOCS-02 现文只覆盖了架构，**完全没提 macOS 15 下限** —— 那是 Phase 5 实测 PySide6/shiboken6 绑定库 `minos=15.0` 得出的硬门槛，比架构更容易把人挡在外面（macOS 15 是 2024 年 9 月才发布的）。

- **D-06:** 自查方法 **GUI 为主、命令作补**。主写「左上角苹果图标 → 关于本机」看「芯片」一行是否 Apple M×、看系统版本号是否 ≥ 15；后附 `uname -m && sw_vers -productVersion` 给习惯终端的人。目标读者大概率不懂命令行 —— 本 phase 的目标就是「无需开发者协助」。

- **D-07:** 不符合门槛时**只写文档预期表现，本 phase 不加任何运行时代码检查**。加运行时代码会扰动已验收的 Phase 5 产物，且 macOS < 15 根本跑不到那行代码（`LSMinimumSystemVersion` 先拦）。

- **D-08:** 两句失败表现（macOS < 15 会被系统拒绝打开、Intel Mac 无法运行 arm64 包）**目前无人实测**，仅由 `LSMinimumSystemVersion` 语义推断得出。文档用**保守措辞**（「系统会拒绝打开」而不是逐字引用某个弹框文案），并把「未实测」记为已知假设。
  理由：Phase 5 刚刚吃过一次亏 —— `05-RESEARCH.md` 靠推断得出「App Translocation 必然发生、自剥离必然失败」，真机三次全部证伪。不要重蹈覆辙地把推断写成事实。

### Release notes 怎么落地

- **D-09:** **机械前提**：`release` job 当前只有 `generate_release_notes: true`，**没有 `body` / `body_path`**，手写的放行说明**无处可插**。新增仓内模板（如 `.github/RELEASE_NOTES_TEMPLATE.md`），给 gh-release 步骤加 `body_path` 指向它；**保留 `generate_release_notes: true`** —— 自动生成的 changelog 会追加在手写正文之后。
  — **Reversibility:** costly — 改的是 Phase 5 刚验收、且**真实发布路径从未执行过**的 `release` job。它第一次真正跑起来会是推 `v*` tag 那一刻，改错要到发版时才暴露。改动必须走 `workflow_dispatch` 回归（届时 release job 仍会 skipped，只能验 YAML 合法性与 job 结构，无法验 body_path 实际渲染）。

- **D-10:** **一份模板双语并列**（中文在上、English 在下，或用 `<details>` 折叠英文）。GitHub Release 只有一个正文、无语言切换机制，想让两类读者都看懂只能并列。项目有 `README_EN.md` 与 `en-US.js`，说明确实有英文读者。

- **D-11:** **README / README_EN 的下载章节只加两行前置要求 + 链到 Release 页**，放行步骤不重复写。单一事实源在模板里，避免三处文案漂移。
  （现状：两份 README 的「下载」章节只有三个链接，零 macOS 内容。）

- **D-12:** 新增单测断言**模板里的 `xattr` 命令与 `macosGatekeeperNotice.js` 的 `GATEKEEPER_XATTR_COMMAND` 逐字一致**。照搬 05-02 已有的跨语言逐字比对先例。现在是三处文案要同步，不锁必漂 —— Phase 5 的两个阻塞缺陷都证明了「注释提醒」拦不住东西。

### 端到端验证在哪验

- **D-13:** **在同一台 Mac 上新建一个干净的系统用户账户**跑完整验证。`LSQuarantineEventsV2` 数据库与 Gatekeeper 放行记录按用户隔离，但 `/Applications` 全局共享 —— **需先卸载**现有安装。

  > **2026-07-31 OVERRIDE(开发者决定,记录于此不改原文):** 干净账户要求经开发者明确选择后豁免，改为在现有账户中验收。承接的后果:该账户已有 Phase 5 写入的 Gatekeeper denial breadcrumb，备选放行路径「系统设置 → 隐私与安全性 → 仍要打开」的界面状态不代表新用户所见，该步骤记为**未验证**、不计入通过。主路径与其余四段仍按 D-15 全额验收。ROADMAP SC3 已同步收窄(见其 2026-07-31 澄清)。
  背景：开发者当前账户已被 Phase 5 的验收污染（有 `Adding Gatekeeper denial breadcrumb` 记录、多条 LSQuarantine 行、应用仍装着），不满足 SC3 的「从未安装过本应用的 Mac」。

- **D-14:** **改写 ROADMAP SC2/SC3 与 REQUIREMENTS DOCS-02 为 arm64-only**，并记录依据（x64 于 2026-07-27 移出 v0.2，`PROJECT.md` Out of Scope 已录）。不留永远无法满足的验收条目。
  SC3 现文要求「arm64 与 x64 分别原生验证，不借助 Rosetta」—— 没有 x64 包，这一半做不了。
  — **Reversibility:** reversible — 纯文档改动；x64 回归时改回即可，且 x64 内核资产已在 `kernel-149.0.7827.114` 备好。

- **D-15:** 验收判据：**全程只准看 Release notes/README，不准用文档里没写的知识** —— 不准凭记忆去系统设置、不准凭记忆敲命令。一旦发现自己在用文档外的知识才能过去，即**记为文档缺口并补文档**，而不是「反正我过去了就算过」。
  理由：验证者同时是开发者，天然带前置知识，这是本 phase 最大的验证盲区。

### Claude's Discretion

- 模板文件的具体路径与命名（`.github/RELEASE_NOTES_TEMPLATE.md` 只是建议）
- 双语并列的具体排版（上下并列 vs `<details>` 折叠）
- 一致性单测放在 Python 侧还是 node:test 侧（模板是 markdown，两边都能读）
- dmg 背景图重生成的具体文案排版与配图手法（05-01 已建立用仓库自带 headless Chromium 截图的流程，零新增依赖）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

ROADMAP.md 未为 Phase 6 声明 Canonical refs，以下为本次讨论累积。

### Phase 5 的实测证据（本 phase 全部文案的事实基础）
- `.planning/phases/05-ci/05-06-SUMMARY.md` — 真机验收 23 项逐条结论；**B1 的首启决策序列时间线**（D-01/D-03 的依据）、B3/B4 的 quarantine 与 translocation 实测、Open Items 第 2 条明确把「dmg 背景图指引与实测路径不符」**指名交给 Phase 6**
- `.planning/phases/05-ci/05-REVIEW.md` — **WR-01/WR-02**（`xattr` 命令未做 shell 转义、translocated 场景下命令目标错）是 D-04 的直接来源
- `.planning/phases/05-ci/05-04-SUMMARY.md` — `LSMinimumSystemVersion=15.0` 的测量依据（18 个 PySide6/shiboken6 绑定库 `minos=15.0`），D-05 的事实基础
- `.planning/phases/05-ci/05-05-SUMMARY.md` — `release` job 结构与**「真实发布路径从未执行过」的残余风险**，D-09 的风险背景
- `.planning/phases/05-ci/05-UAT.md` — Phase 5 遗留的人工验收项（推真实 `v*` tag）。**与本 phase 有天然耦合**：Phase 6 的端到端验证若基于真实 Release 产物，会顺带核销它

### 要改动的文案载体
- `frontend/src/lib/macosGatekeeperNotice.js` — `GATEKEEPER_XATTR_COMMAND` 常量（D-04 要改）；注释里写明它与 `_g.py` 哈希锁定的 `openSourceNotice.js` 刻意独立
- `frontend/src/i18n/zh-CN.js` § `gatekeeper` — `step1`–`step4` 四步文案（D-02 要改）
- `frontend/src/i18n/en-US.js` § `gatekeeper` — 同上英文
- `README.md` § 下载 — 现只有三个链接（D-11 要加前置要求）
- `README_EN.md` § Download — 同上
- `.github/workflows/build-release.yml` § `release` job — 加 `body_path`（D-09）
- `assets/dmg-background.png` / `assets/dmg-background@2x.png` — 需重生成（D-02）

### 范围与约束的权威来源
- `.planning/PROJECT.md` § Out of Scope — **x64 于 2026-07-27 移出 v0.2**（D-14 的依据）；§ Constraints「dmg 不签名 — 首次打开需用户手动放行，文档必须写清步骤」
- `.planning/ROADMAP.md` § Phase 6 — SC1/SC2/SC3 原文（D-01/D-05/D-14 均要求改写）
- `.planning/REQUIREMENTS.md` § DOCS — DOCS-01/DOCS-02 原文（同上）
- `CLAUDE.md` — 用户可见文案用中文、commit message 用英文；`backend/_g.py` 哈希锁定 `openSourceNotice.js` 与 `App.vue`，**不得触碰**

### Phase 4 的既有交付（被 D-02 改动的对象）
- `.planning/phases/04-frontend-platform-gating/04-CONTEXT.md` — UI-04 首启放行提示的原始决策与 D-04 约束（文案安全边界：不含 `spctl`、不含 `sudo`、不对宽目录递归）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/macosGatekeeperNotice.js`：纯逻辑模块，无 Vue/UI 依赖，可被 `node:test` 直接 import。`buildGatekeeperNoticeHtml(t)` 已把四步文案抽成 i18n key，改文案**只需动 i18n 文件**，不必动逻辑
- 05-01 建立的资产生成流程：用仓库自带的 headless `engines/chrome/Chromium.app` 截图 HTML 生成 png，**零新增依赖**。重生成 dmg 背景图照搬即可
- 05-02 建立的跨语言逐字比对单测先例（Python 侧 `build_quarantine_failure_message` ↔ JS 侧 `GATEKEEPER_XATTR_COMMAND`），D-12 的一致性锁照搬这个模式

### Established Patterns
- **文案单一事实源 + 单测锁**：Phase 5 已验证有效。本 phase 会把它扩展到第三处（Release notes 模板）
- **保守措辞记录未实测项**：Phase 5 的 SUMMARY 明确区分「实测」与「推断」，D-08 沿用
- **i18n 双语必须同步**：`CLAUDE.md` 明文要求新增文案同时更新 `zh-CN.js` 与 `en-US.js`

### Integration Points
- `release` job 的 gh-release 步骤（`build-release.yml` 末段）——`body_path` 注入点
- `assets/dmg-background*.png` 被 `build-macos` job 的 `create-dmg` 步骤消费，重生成后需确认 create-dmg 的图标坐标仍对齐
- Phase 4 的 i18n 改动会触发 `frontend/src/lib/*.test.js`（含 `i18n-parity.test.js` 中英键对齐断言）与 `macosGatekeeperNotice.test.js`

</code_context>

<specifics>
## Specific Ideas

- 放行说明的措辞基调：把「被拦截」讲成**预期现象**而非故障。Phase 4 的 `gatekeeper.intro`（「这是预期行为，并不代表程序有问题」）与 dmg 背景图（「首次打开若被拦截属正常现象」）已经是这个基调，新文案保持一致
- 递进三步的信息层次：正常读者**只需读第一步就够**，后两步是异常兵。排版上要让这一点一眼可见，不要三步等权重并列
- `spctl` 仍报 `rejected` 这件事值得在文档里点一句 —— 应用能跑是因为**不再被隔离**，不是因为被 Gatekeeper 信任。避免用户误以为「装上了就等于被系统认可了」

</specifics>

<deferred>
## Deferred Ideas

- **B1 首启对话框的逐字措辞采集** — Phase 5 的 05-06 只拿到日志层面的决策序列（`Prompt shown` → `denial breadcrumb`），弹框的标题与按钮文字未采集，用户明确选择接受该缺口。Phase 6 的端到端验证会做一次真实全新安装，**顺带把这个补上**（不是新能力，是本 phase 验证的自然副产品）
- **macOS 14 / Intel Mac 上的实际失败表现实测** — D-08 决定只写推断。若将来有条件拿到这两类机器，可回补实测并收紧文档措辞
- **x64 双架构下载指引** — x64 回归时（内核资产已在 `kernel-149.0.7827.114` 备好）需要重新引入「如何判断自己是 Apple Silicon 还是 Intel」的选择指引，即 DOCS-02 的原始形态
- **端到端验证是否基于真实 `v*` tag 产出的 Release** — 讨论中提出但未展开。Phase 5 遗留的 UAT 需要一次真实 tag push；若 Phase 6 的验证基于真实 Release 产物则可一并核销。留给 plan-phase 定，注意推 `v*` tag 会触发**对用户可见的真实发版**

</deferred>

---

*Phase: 6-发布文档与端到端验证*
*Context gathered: 2026-07-30*
