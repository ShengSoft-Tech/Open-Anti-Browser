# Phase 6: 发布文档与端到端验证 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-30
**Phase:** 6-发布文档与端到端验证
**Areas discussed:** 放行路径写哪一条, 硬件/系统门槛怎么讲, Release notes 怎么落地, 端到端验证在哪验

**开场提出的核心矛盾：** Phase 6 的三条 Success Criteria 写在 Phase 5 出结果之前，与实测冲突 —— SC1 描述的「系统设置 → 仍要打开」路径实测从未被执行过；SC2/SC3 的「双架构」在 x64 于 2026-07-27 移出 v0.2 后已无对象。用户选择讨论全部四个区域。

---

## 放行路径写哪一条

### Q1: Release notes 里的放行说明，以哪条路径为主？

| Option | Description | Selected |
|--------|-------------|----------|
| 写实测路径 | 主路径「双击 → 看到拦截提示就关掉 → 再双击一次」，系统设置与 xattr 降为备选。步数最少、与实测一致；但只在一台 macOS 15.7 上验过 | ✓ |
| 写系统设置路径 | 继续照 SC1/DOCS-01 写。官方路径、与 Phase 4 应用内提示一致；但本 phase 从未验证过，且对多数用户是多余步骤 | |
| 两条都写，实测优先 | 「再双击」为步骤 1，「系统设置」为步骤 2。覆盖两种结局但文档变长 | |

**User's choice:** 写实测路径
**Notes:** 决策依据是 05-06 的 syspolicyd 日志时间线 —— 放行不是靠系统设置成功的，是应用自剥离摘掉 quarantine 后第二次双击畅通；`spctl` 至今仍报 `rejected`。

### Q2: 除 Release notes 外，另两个面要不要一起改成实测路径？

| Option | Description | Selected |
|--------|-------------|----------|
| 三面全改 | Release notes + dmg 背景图 + Phase 4 应用内提示。需重生成两张 png、改两份 i18n，动了 Phase 4 已验收交付物 | ✓ |
| 只改 Release notes + dmg 背景 | 应用内提示不动 —— 它只在应用已跑起来时才看得到 | |
| 只改 Release notes | 改动面最小、不碰二进制资产与既有交付物 | |

**User's choice:** 三面全改
**Notes:** dmg 背景图现教「右键 → 打开」，是第三种说法，连实测路径都不是 —— 而它恰是用户最先看到的一屏。

### Q3: 自剥离只在一台机器上验过。文档要不要给「万一再双击也不行」兜底？

| Option | Description | Selected |
|--------|-------------|----------|
| 给，写成递进三步 | 再双击 → 系统设置 → xattr。正常读者只需看第一步 | ✓ |
| 不给，只写主路径 | 保持极简；风险是自剥离失败时用户彻底卡死 | |
| 给，但折叠/另页 | 主文只写第一步，备选放 `<details>` 或 README 另一节 | |

**User's choice:** 给，写成递进三步

### Q4: 文档里的 xattr 命令写成什么形式？

| Option | Description | Selected |
|--------|-------------|----------|
| 加引号固定路径 | `xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"`，同步修 code review WR-01 | ✓ |
| 教用户拖拽生成路径 | 从根上消除路径拼错，但不能整条复制粘贴 | |
| 两种都给 | 覆盖面最全，文案略长 | |

**User's choice:** 加引号固定路径
**Notes:** 直接对应 05-REVIEW.md 的 WR-01 —— 应用内那条目前是裸路径无引号。两处有单测锁定逐字一致，必须同改。

---

## 硬件/系统门槛怎么讲

### Q1: DOCS-02 现文已失效（无双架构可选）。重写成什么？

| Option | Description | Selected |
|--------|-------------|----------|
| 前置要求清单 | 「下载前确认 Apple Silicon + macOS 15 或更新」并给自查方法，不假装有选择 | ✓ |
| 保留双架构框架 | Intel 分支写「暂不支持，后续里程碑供应」，为 x64 回归预留位置 | |
| 担保式开头 | 文档顶部一行大字声明支持范围 | |

**User's choice:** 前置要求清单
**Notes:** DOCS-02 现文只覆盖架构，完全没提 macOS 15 下限 —— 而后者是 Phase 5 实测得出、更容易把人挡在外面的门槛。

### Q2: 自查方法给哪种？（读者大概率不懂命令行）

| Option | Description | Selected |
|--------|-------------|----------|
| GUI 为主，命令作补 | 主写「关于本机」看芯片与版本号，后附 `uname -m && sw_vers -productVersion` | ✓ |
| 只给 GUI 路径 | 文档最短、对普通用户零门槛 | |
| 只给命令 | 精确无歧义，但不懂命令行的用户会卡住 | |

**User's choice:** GUI 为主，命令作补

### Q3: 不符合门槛的用户若硬装了会怎样？要不要管？

| Option | Description | Selected |
|--------|-------------|----------|
| 只写文档预期表现 | 本 phase 不改任何代码 | ✓ |
| 加启动时友好报错 | 体验最好，但要动已验收的 Phase 5 产物，且 macOS < 15 跑不到那行代码 | |
| 不写也不改 | 最简；用户碰上陌生报错时对不上号 | |

**User's choice:** 只写文档预期表现

### Q4: 「macOS < 15 会弹什么」「Intel Mac 上会怎样」要不要先实测再写？

| Option | Description | Selected |
|--------|-------------|----------|
| 写成推断并标注未实测 | 文档用保守措辞，CONTEXT 里记为已知假设 | ✓ |
| 实测后再写 | 文档精确，但需要额外硬件，可能直接阻塞本 phase | |
| 不写失败表现 | 最诚实但用户对不上号 | |

**User's choice:** 写成推断并标注未实测
**Notes:** Phase 5 刚吃过一次亏 —— RESEARCH 靠推断得出「App Translocation 必然发生、自剥离必然失败」，真机三次全部证伪。

---

## Release notes 怎么落地

**技术约束先行说明：** `release` job 当前只有 `generate_release_notes: true`，无 `body`/`body_path`，手写放行说明无处可插。`softprops/action-gh-release@v2` 支持 `body_path` 与 `generate_release_notes` 共存。

### Q1: 放行说明怎么进 Release 正文？

| Option | Description | Selected |
|--------|-------------|----------|
| body_path 指仓内模板 | 放行说明进版本控制、每次发版自动带上、不靠人工补 | ✓ |
| 写进 README 用链接引 | 单一事实源，改文案不用发新版；但用户在最焦虑时刻多一次跳转 | |
| 两者兼顾 | 覆盖面最全，两处文案需保持同步、有漂移风险 | |

**User's choice:** body_path 指仓内模板

### Q2: Release notes 模板的语言怎么安排？

| Option | Description | Selected |
|--------|-------------|----------|
| 一份模板双语并列 | GitHub Release 只有一个正文、无语言切换，想让两类读者都看懂只能并列 | ✓ |
| 只写中文 | 最短；但项目有 README_EN 与 en-US i18n，说明确有英文读者 | |
| 中文为主 + 英文链接 | 正文简短，英文读者多一跳 | |

**User's choice:** 一份模板双语并列

### Q3: README / README_EN 里要不要也写 macOS 安装说明？

| Option | Description | Selected |
|--------|-------------|----------|
| README 只放前置要求 + 链接 | 避免下了 355MB 才发现不能跑；放行步骤不重复写，单一事实源在模板 | ✓ |
| README 写完整一份 | 从仓库页进来的人不用跳转；但三个文件要同步改 | |
| README 不动 | 最简；但先看仓库首页再决定下不下载的人拿不到任何 macOS 信息 | |

**User's choice:** README 只放前置要求 + 链接

### Q4: 模板里的 xattr 命令与应用内 GATEKEEPER_XATTR_COMMAND 要不要加一致性断言？

| Option | Description | Selected |
|--------|-------------|----------|
| 加，用单测锁 | 照搬 05-02 已有的跨语言逐字比对先例。三处文案要同步，不锁必漂 | ✓ |
| 只靠人工注意 | 不增测试；但 Phase 5 已证明「注释提醒」拦不住东西 | |
| 连放行步骤一起锁 | 最严；但 dmg 背景图是 png，文案无法自动比对 | |

**User's choice:** 加，用单测锁

---

## 端到端验证在哪验

**开场说明的两个障碍：** ① 开发者当前账户已被 Phase 5 验收污染（Gatekeeper denial breadcrumb、多条 LSQuarantine 记录、应用仍装着）；② SC3 要求的 x64 原生验证无包可做。

### Q1: 「从未安装过的 Mac」这个条件怎么满足？

| Option | Description | Selected |
|--------|-------------|----------|
| 新建系统用户账户 | LSQuarantine 与放行记录按用户隔离；/Applications 全局共享需先卸载。无需额外硬件 | ✓ |
| 重置当前用户的痕迹 | 无需切账户；但改动日常账户安全状态，且很难确认真的清干净——清不干净会假阴性地「验过了」 | |
| 借一台真实干净机器 | 最接近真实用户；但需要硬件，可能阻塞本 phase | |

**User's choice:** 新建系统用户账户

### Q2: SC3 里「x64 原生验证」那一半怎么处置？

| Option | Description | Selected |
|--------|-------------|----------|
| 改写 SC 并记录依据 | ROADMAP SC2/SC3 与 DOCS-02 改为 arm64-only，验收标准与现实对齐 | ✓ |
| 保留 SC 但标为 deferred | 历史文本不动；但 Phase 6 永远无法完整 pass，每次 verify 都要重新解释 | |
| 只改 DOCS-02，SC 不动 | 两处矛盾，下游 verifier 会拿 SC 当权威而报 gap | |

**User's choice:** 改写 SC 并记录依据

### Q3: 「仅凭文档即可完成」怎么算验过？

| Option | Description | Selected |
|--------|-------------|----------|
| 只准看文档，卡住即失败 | 不准用文档外知识；发现用了就记为文档缺口并补文档 | ✓ |
| 全程录屏/截图取证 | 证据更硬（Phase 5 的日志捕获就推翻过回忆）；多一道手续 | |
| 找个不懂技术的人跑 | 真正消除开发者盲区；但需要协调人，可能阻塞 | |

**User's choice:** 只准看文档，卡住即失败
**Notes:** 验证者同时是开发者，天然带前置知识 —— 这是本 phase 最大的验证盲区。

---

## Claude's Discretion

- 模板文件的具体路径与命名（`.github/RELEASE_NOTES_TEMPLATE.md` 只是建议）
- 双语并列的具体排版（上下并列 vs `<details>` 折叠）
- 一致性单测放在 Python 侧还是 node:test 侧
- dmg 背景图重生成的具体文案排版与配图手法

## Deferred Ideas

- **B1 首启对话框的逐字措辞采集** — Phase 5 未采集到，用户明确接受该缺口；Phase 6 的真实全新安装会顺带补上
- **macOS 14 / Intel Mac 上的实际失败表现实测** — 本次决定只写推断，将来有硬件可回补
- **x64 双架构下载指引** — x64 回归时需重新引入 DOCS-02 的原始形态
- **端到端验证是否基于真实 `v*` tag 产出的 Release** — 讨论中提出但未展开，留给 plan-phase 定；注意推 tag 会触发对用户可见的真实发版
