# Phase 7: 补丁发布与发布链路验证 - Research

**Researched:** 2026-07-31
**Domain:** GitHub Actions 发布链路实证(`softprops/action-gh-release` 正文渲染顺序)、发布把关脚本扩展(`check_version_consistency.py`)、macOS 真机 GUI 回归验证的 CI 可行性边界(TCC/Accessibility)、发版/回退操作流程
**Confidence:** HIGH for 代码可读部分(check_version_consistency.py、build-release.yml、launch_app.py 现状全部直接读源码得出);MEDIUM for `softprops/action-gh-release` 正文渲染顺序(官方 README 逐字确认,但仓库自己从未真实验证过,A2 仍待本 phase 的真实 tag push 核销);MEDIUM-LOW for macOS Accessibility/TCC 在 GitHub-hosted runner 上的行为边界(来自公开 issue 与文档交叉印证,不是本仓库直接实测)

## Summary

Phase 7 没有新技术栈——它是一次「发布并观测」的操作型 phase,唯一的新代码是给 `scripts/release/check_version_consistency.py` 加一个模板版本号读取分支(D-02),外加 `.github/RELEASE_NOTES_TEMPLATE.md` 顶部一段手写的双语「本次更新」内容(D-01/D-03/D-04)。`launch_app.py` 的关闭按钮修复(`a886dc7`)与 `build-release.yml` 的 `release` job checkout 修复(`524aeb1`)都已经在 main 上,本 phase **不写这两处的实现代码**,只写「验证脚手架」——版本号一致性门禁的模板扩展,以及触发一次真实 `v0.2.1` tag push 后对三条 success criteria 的实证记录。

三个关键研究结论:(1)官方文档明确 `body_path` 内容会被 pre-pended(前置)于 `generate_release_notes: true` 产出的自动 changelog 之前——这与 `06-RESEARCH.md` 假设 A2 的方向一致,但该结论从未在本仓库被真实验证过(v0.2.0 的正文是手工贴的,不是流水线渲染的证据),SC3 存在的意义就是让这次 v0.2.1 成为第一个真实观测样本。(2)Claude's Discretion 里「给 build-macos 的 GUI 冒烟门禁加第三维度(AppleScript 点关闭按钮)」在 GitHub-hosted macOS runner 上**技术上不可行**——现有的 `osascript ... to quit` 之所以能在无人值守的 CI 里工作,是因为它是发给目标 App 的标准 `NSApplication` 终止 Apple Event,不经过任何需要 Accessibility 权限的 UI 元素遍历;而「点击某个具体窗口的关闭按钮」必须通过 `System Events` 做 UI Scripting,这类操作被 macOS 的 `kTCCServiceAccessibility` 严格网关,GitHub-hosted runner 的 SIP 保持开启、无法非交互式授权,已有多个 `actions/runner-images` 上的公开 issue 印证这条路无法在无人值守 CI 里打通。这意味着 SC1 的关闭按钮回归护栏只能是本次的真机人工验证,不可能升级成自动化门禁——planner 应当把这一点作为「Claude's Discretion」条目的明确结论写进计划,而不是留白。(3)prior 两次真机缺陷(05-02 SIGSEGV、05-06 Quit 死循环)都只在 PyInstaller 冻结的 `.app` bundle 里复现,从未在 `python launch_app.py` 源码直跑时出现过——即便关闭按钮修复本身的代码路径只按 `sys.platform` 分支、不按 `sys.frozen` 分支,冻结态与源码态在 Qt 平台插件加载、bundle 身份注册(LaunchServices)、Dock 图标行为等方面存在本质差异,因此 SC1 的真机验证载体**必须**是冻结的 `.app`(推荐用真实 Release 里的 dmg,而非 `workflow_dispatch` 产出的临时 artifact),不能用源码跑当作等价证据。

**Primary recommendation:** 把本 phase 的工作切成两条独立但共享同一次 tag push 的轨道——(a)一次性的门禁与文案改动(D-01~D-04,可提前在 `workflow_dispatch` 下把 YAML/脚本正确性验证到位),(b)真正的「发布并观测」动作(版本号 bump → 落 main → 打 `v0.2.1` tag → 推送 → 在真实 Release 页面上核对 SC1/SC2/SC3 三件事)。不要把 (b) 拆成多次发布,ROADMAP 已经明确约束了这一点。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 版本号一致性门禁(tag/package.json/main.py/模板四方比对) | CI / 发布脚本(`scripts/release/check_version_consistency.py`) | — | 单一事实源已经是这个脚本,D-02 只是扩展它的比对范围,不引入新组件 |
| Release 正文渲染(手写「本次更新」+ 自动 changelog) | CI / `release` job(`softprops/action-gh-release`) | 发布制品(`.github/RELEASE_NOTES_TEMPLATE.md`) | 渲染动作发生在 CI(action 消费 `body_path`),但内容的单一事实源在仓库内的模板文件 |
| macOS 关闭按钮退出行为 | Desktop 运行时(`launch_app.py` 的 Qt 事件层) | — | 纯前端(Qt/Cocoa 事件循环)问题,不涉及 backend/API |
| 关闭按钮回归护栏 | 人工验证(真机) | CI(仅覆盖 Cmd+Q,不覆盖关闭按钮) | Accessibility/TCC 网关使得「点击窗口关闭按钮」这一操作无法在 GitHub-hosted macOS runner 上被无人值守地自动化 |
| 发版触发与产物聚合 | CI(`build`/`build-macos`/`release` 三个 job 的 `needs` 图) | — | 已在 Phase 5/6 建成,本 phase 不改动其结构,只观测其输出 |

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Release 正文的「本次更新」章节**

背景(决定了下面四条,必读):讨论中实测确认了两个此前无人记录的事实:

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
- **关闭按钮实测的载体与覆盖范围** — 冻结的 `.app` vs 源码跑 `launch_app.py`(注:05-02 与 05-06 两次缺陷都只在冻结包里暴露);只测关闭按钮 vs 关闭按钮 / Cmd+Q / 菜单栏图标退出三条路径全跑;要不要给 `build-macos` 的 GUI 冒烟门禁加第三维度(AppleScript 点关闭按钮并断言进程退出),让这条路径有回归护栏而不只有 AST 断言。**本研究的结论:第三维度在 GitHub-hosted macOS runner 上不可行,见下方 Common Pitfalls #3 与 Open Questions。**
- **失败回退策略与 A2 判定处置** — v0.2.1 正文若仍未渲染,允不允许再用 `gh release edit` 手工补救;A2 被推翻(自动 changelog 排在手写正文之前)时,本 phase 就地调模板排版还是只记录判定。
- 「本次更新」新章节的**双语排布与具体位置**(中英各自跟随所在语言区块之首 vs 两段紧挨着放整篇顶部)、措辞基调、模板里版本号的**具体书写形式**(直接影响 D-02 的门禁用什么方式抓取)。**本研究建议见 Architecture Patterns Pattern 1。**
- 版本号 bump(`frontend/package.json` + `backend/main.py` 两处 `version=`)、模板改动、门禁扩展三者的 commit 切分与 tag 时机。注意 `check_version_consistency.py` 在 tag 模式下要求 `tag == package.json == main.py`,所以 0.2.1 必须先落到 main、tag 再指向那个 commit。

### Deferred Ideas (OUT OF SCOPE)

- **模板顶部的版本无关平台导语**(「Windows 用户下载 Setup.exe 即可,以下说明仅适用于 macOS」)— D-03 选择用按平台分条替代。若将来「本次更新」章节被移除或平台数量增加,可回补这个导语
- **Windows 侧的完整发布文档**(模板目前 107 行零 Windows 内容)— 属于 DOCS 范畴(Phase 6 的地盘),不在 UI-05/PKG-06 的 requirement 覆盖内。若将来 Windows 侧也有需要文档化的安装/放行环节,应另开 phase
- **v0.2.0 Release 页面加指向 v0.2.1 的说明** — D-04 否决(会再引入一次手工 `gh release edit`)。若将来 v0.2.0 被发现有影响使用的问题,再单独处理
</user_constraints>

## Phase Requirements

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-05 | macOS 上点窗口关闭按钮直接退出应用,不再隐藏到菜单栏(Windows/Linux 最小化到托盘行为不变) | `a886dc7` 已在 main;`launch_app.py:69-92` 的 `should_intercept_quit_event`/`should_close_to_tray`/`handle_macos_quit_request` 是修复本体;`tests/test_macos_desktop_runtime.py` 的 `MacQuitInterceptionTests`/`MacCloseToTrayTests`/`MacQuitEventLoopConvergenceTests` 是既有单测+AST 断言;本 phase 的任务是补上真机实证——见 Common Pitfalls #3/#4、Open Questions #1 |
| PKG-06 | 推送 v* tag 后 Release 正文由流水线自动渲染,手写正文与自动 changelog 的先后顺序被记录在案 | `524aeb1` 已在 main(`build-release.yml:818-824` 的 `release` job 已含 `actions/checkout` + `body_path`);`softprops/action-gh-release` 官方 README 确认 body_path 前置于自动 changelog(见 Sources);D-01~D-04 是本 phase 要新增的模板内容,D-02 是要扩展的门禁 |
</phase_requirements>

## Standard Stack

没有新工具链。本 phase 复用 Phase 5/6 已经建立的一切:

### Core
| Tool/Format | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `softprops/action-gh-release` | `v2`(已固定在 `build-release.yml:819`) | 发布 GitHub Release、渲染正文 | Phase 5 已选定,本 phase 不升级(见下方版本核查说明) |
| Python `unittest` / Node `node:test` | 已在仓库(122 Python + 52 node,均可跑通,2 skip 为 Windows-only) | 版本一致性门禁的单测、模板内容的 node 侧断言 | CLAUDE.md 文档化的测试命令,`scripts/release/check_version_consistency.py` 与 `frontend/src/lib/releaseNotesTemplate.test.js` 已建立好可扩展的模式 |
| Markdown + HTML 注释 | — | `.github/RELEASE_NOTES_TEMPLATE.md` 的内容格式与版本号锚点(建议) | GitHub Release 正文按 GFM 渲染,HTML 注释不会显示但对脚本可解析,见 Pattern 1 |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `gh` CLI | 2.88.1(开发机已安装) | 推 tag 后核查 Release、必要时执行回退(delete release/tag) | 见 Common Pitfalls #5(回退操作) |
| `git` | 2.54.0(开发机已安装) | tag 创建/删除/推送 | 同上 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 用 HTML 注释锚点(`<!-- RELEASE_VERSION: 0.2.1 -->`)承载版本号供脚本解析 | 直接正则抓标题里的数字(如 `## 本次更新 (v0.2.1)`) | 标题正则会与「Claude's Discretion」里悬而未决的措辞/排布耦合——排布一改正则就碎;注释锚点把「给读者看的措辞」与「给脚本读的版本号」彻底解耦,读者侧改标题不影响门禁,是本研究给 D-02 的具体建议(见 Pattern 1) |
| 保持 `softprops/action-gh-release@v2` | 升级到 `v3`(Node 24,官方推荐,`v2.6.2` 是最终 v2 版本且已停止维护) | v3 是不相关的独立可回退决策,混进本 phase 会给「真实发布路径首次执行」再引入一个新变量,与 `06-RESEARCH.md` 同一结论——不在本 phase 范围内 |
| 门禁逻辑放进 `check_version_consistency.py`(Python,D-02 明文指定) | 放进 `frontend/src/lib/releaseNotesTemplate.test.js`(node,已存在同类断言) | D-02 是锁定决策,必须扩展 Python 脚本本身(它是 CI 里唯一会真正**拦截构建**的调用点,`build-release.yml:159` 的退出码直接决定 tag 能不能发出去);node 侧测试只在本地/`node --test` 时跑,不在 `build-macos` job 的 gating 路径上,可以作为**额外**的第二层断言但不能替代 D-02 要求的门禁 |

**Installation:** 无新依赖(见下方 Package Legitimacy Audit)。

**版本核查:** `softprops/action-gh-release@v2` 固定在 `build-release.yml:819`,当前指向 `v2.6.2`(官方最终 v2 版本,已停止维护,Node 20 runtime 已被 GitHub Actions 标记淘汰,官方建议升级到跑 Node 24 的 `v3`)。本 phase **不需要**升级它——升级是独立、可单独回退的决策,不要顺手夹带进这次「首次真实发布」。

## Package Legitimacy Audit

**本 phase 不安装任何新的外部包。** 所有改动都落在仓库已有文件(`scripts/release/check_version_consistency.py`、`.github/RELEASE_NOTES_TEMPLATE.md`、`frontend/package.json`、`backend/main.py`)或新增的纯文本/测试文件上。Package Legitimacy Gate 协议不适用——跳过 `gsd-tools query package-legitimacy check` 步骤。

## Architecture Patterns

### System Architecture Diagram

```
                 ┌──────────────────────────────────────────────┐
                 │ 版本号三/四方一致性(D-02 扩展对象)              │
                 │                                                │
                 │  frontend/package.json  "version": "0.2.1"     │
                 │  backend/main.py        version="0.2.1" ×2     │
                 │  .github/RELEASE_NOTES_TEMPLATE.md              │
                 │    <!-- RELEASE_VERSION: 0.2.1 --> (建议锚点)    │
                 │  git tag v0.2.1  ── 仅 tag 模式下参与比对        │
                 └───────────────────┬────────────────────────────┘
                                     │ 全部读取自
                                     ▼
                 scripts/release/check_version_consistency.py
                 (read_package_version / read_main_versions /
                  NEW: read_template_version)
                                     │
                                     │ build-release.yml:159
                                     │ (build-macos job,Resolve version 步骤)
                                     ▼
                 一致 → APP_VERSION 写入 $GITHUB_ENV,继续构建
                 不一致 → 非零退出码 → build-macos 失败 → release job
                          因 needs:[build, build-macos] 也不会跑
                          (tag 发不出去,这正是 D-02 要的拦截效果)


                 ┌──────────────────────────────────────────────┐
                 │ Release 正文渲染(SC2/SC3 观测对象,原则上不改)   │
                 │                                                │
                 │ .github/workflows/build-release.yml § release  │
                 │  body_path: .github/RELEASE_NOTES_TEMPLATE.md   │
                 │  generate_release_notes: true                   │
                 │                                                │
                 │  softprops/action-gh-release@v2 的合成顺序      │
                 │  (官方 README 确认): body_path 内容 → PREPENDED │
                 │  → 自动生成的 changelog(本仓库场景下只有一行     │
                 │     **Full Changelog**: compare 链接,因为直推   │
                 │     main、无 PR)                                │
                 └───────────────────┬────────────────────────────┘
                                     │ push v0.2.1 tag(唯一能触发
                                     │ release job 的动作;
                                     │ workflow_dispatch 下 release
                                     │ 恒被 if 条件 skip)
                                     ▼
                 真实 GitHub Release 页面
                 → SC2:正文是否含手写「本次更新」内容(无需 gh release edit)
                 → SC3:观测手写内容与自动 changelog 的实际先后顺序,
                        核销或推翻 06-RESEARCH.md 假设 A2


                 ┌──────────────────────────────────────────────┐
                 │ macOS 关闭按钮退出(SC1,人工真机验证)             │
                 │                                                │
                 │ launch_app.py should_close_to_tray() /          │
                 │ should_intercept_quit_event() /                 │
                 │ handle_macos_quit_request() / closeEvent() /    │
                 │ DesktopApplication.event()   (a886dc7,已在 main) │
                 │                                                │
                 │ CI 侧已有的自动回归护栏(build-macos job):        │
                 │  维度一:18s 存活(防 05-02 SIGSEGV 回归)          │
                 │  维度二:osascript "tell app to quit" 有界退出   │
                 │         (防 05-06 Quit 死循环回归,走 AppleEvent, │
                 │          不需要 Accessibility 权限)              │
                 │  维度三(关闭按钮点击):技术上不可行,见 Pitfall #3  │
                 │                                                │
                 │ → SC1 只能由人在真机上,对**冻结的 .app**(建议    │
                 │   来自真实 Release 的 dmg)点关闭按钮,ps/活动     │
                 │   监视器确认进程真正消失                          │
                 └──────────────────────────────────────────────┘
```

### Recommended Project Structure
```
.github/
├── RELEASE_NOTES_TEMPLATE.md        # MODIFIED — D-01/D-03/D-04,顶部新增双语「本次更新」
└── workflows/
    └── build-release.yml            # 不改动 release job(SC2/SC3 观测对象);
                                      # Resolve version 步骤(约 148-171 行)不必改,
                                      # 因为它只是调用脚本 + 捕获 stdout,脚本内部签名不变

scripts/release/
└── check_version_consistency.py     # MODIFIED — D-02,新增 read_template_version()
                                      # 分支,纳入 check_version_consistency() 的比对

tests/
└── test_version_consistency.py      # MODIFIED — 为 D-02 新增的模板版本号分支补单测,
                                      # 照搬现有 _write_package_json/_write_main_py 的
                                      # tmp-dir 夹具模式

frontend/
├── package.json                     # MODIFIED — version bump 三处之一
└── src/lib/
    └── releaseNotesTemplate.test.js # 可选 MODIFIED — 已存在的 D-12 模板一致性测试文件,
                                      # 可加一条「模板版本号锚点存在且是 semver 形状」的
                                      # 轻量断言(非阻断性,阻断性门禁必须在 Python 侧)

backend/
└── main.py                          # MODIFIED — version bump 两处 FastAPI version= 字段

.planning/phases/07-patch-release/
└── 07-*-SUMMARY.md                  # 真机验证记录(SC1)+ Release 正文实测记录(SC2/SC3)
```

### Pattern 1: 版本号锚点与展示文案解耦(给 D-02 的具体建议)

**What:** 在模板文件里放一个 HTML 注释锚点(如 `<!-- RELEASE_VERSION: 0.2.1 -->`)承载版本号,`check_version_consistency.py` 只解析这个锚点,不解析任何双语标题的措辞。

**When to use:** 当「读者可见的文案排布/措辞」被明确列为 Claude's Discretion(可能反复调整),但同时又需要一个稳定、可编程解析的版本号来源时。

**Why(避免的坑):** 如果正则直接抓标题文本(例如 `## 本次更新 (v0.2.1)` 或 `## What's Changed (v0.2.1)`),排布方案一旦从「中英各自跟随语言区块之首」改成「两段紧挨着放顶部」,或者措辞从「本次更新」改成别的说法,正则就要跟着改,而且中英文两处都要抓、都要一致,规则会变复杂且脆弱。用一个不渲染的注释锚点,读者体验(措辞/排布/中英是否对称)与门禁(版本号必须四方一致)完全解耦,复用现成的 `_SEMVER_VERSION_RE` 语义(三段数字 + 可选 prerelease/build 后缀)即可安全解析。

**Example:**
```python
# Source: scripts/release/check_version_consistency.py (现有文件,建议新增)
DEFAULT_TEMPLATE_PATH = REPO_ROOT / ".github" / "RELEASE_NOTES_TEMPLATE.md"

_TEMPLATE_VERSION_RE = re.compile(
    r'<!--\s*RELEASE_VERSION:\s*(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\s*-->'
)


def read_template_version(path: "Path | None" = None) -> str:
    """读取 RELEASE_NOTES_TEMPLATE.md 里的 RELEASE_VERSION 注释锚点。"""
    template_path = path or DEFAULT_TEMPLATE_PATH
    text = template_path.read_text(encoding="utf-8")
    match = _TEMPLATE_VERSION_RE.search(text)
    if match is None:
        raise VersionMismatch(
            "RELEASE_NOTES_TEMPLATE.md 中未找到 <!-- RELEASE_VERSION: X.Y.Z --> 锚点，"
            "D-01 引入的「本次更新」章节每次发版前必须同步更新此锚点。"
        )
    return match.group(1)
```
```markdown
<!-- .github/RELEASE_NOTES_TEMPLATE.md 顶部,建议形态(注释本身不会出现在渲染后的 Release 正文里) -->
<!-- RELEASE_VERSION: 0.2.1 -->
## 本次更新
- macOS: 修复点关闭按钮后应用仍在后台运行的问题
- Windows: 本版本无功能变更

## What's Changed
- macOS: fixed the app staying alive in the background after clicking the window close button
- Windows: no functional changes in this release
```
再把 `check_version_consistency()` 的等式扩展为四方比对(tag 模式)/三方比对(非 tag 模式,忽略 tag),复用已有的 `VersionMismatch` 抛出路径,`main()` 的 CLI 签名(`<ref_name> <is_tag>`,stdout 只打印版本号)完全不需要变。

### Pattern 2: 「发布并观测」而非「实现」的任务形态

**What:** 本 phase 大部分「任务」不是写代码,而是按顺序执行一次真实操作并记录观测结果——这与常规 phase 的「写代码 → 写测试 → 跑通」形态不同。

**When to use:** 任何要点是「证明已有修复在真实环境下生效」而不是「实现新行为」的 phase。

**Example(推荐的 phase 内排序,对应 Claude's Discretion 里的「发版与验证的先后排序」):**
1. Wave 0:D-01~D-04 的模板与脚本改动,在**分支**上完成,用 `workflow_dispatch` 验证 `build`/`build-macos` 两个 job 仍能跑通(`release` job 因 `if: startsWith(github.ref, 'refs/tags/')` 恒被 skip,这一步只验证 YAML 合法性与门禁脚本本身逻辑正确,不验证 body_path 实际渲染,也不构成 SC1 的证据)。
2. 版本号 bump(`frontend/package.json` + `backend/main.py` 两处)与模板改动一起落 main(必须在打 tag **之前**,`check_version_consistency.py` 的 tag 模式要求三/四方全等)。
3. 打 `v0.2.1` tag 并推送——这是本 phase 唯一一次触发 `release` job 的动作,也是 SC2/SC3 的唯一观测窗口。
4. SC1 的真机验证:等 Release 产出后,下载 Release 页面上真实的 dmg(而非 `workflow_dispatch` 的 artifact),在真机上点关闭按钮,`ps`/活动监视器确认进程消失。
5. 观测记录:SC2(正文是否需要 `gh release edit`)、SC3(手写内容与自动 changelog 的实际先后顺序,核销或推翻 A2)。

### Anti-Patterns to Avoid
- **把三条 SC 拆到不同 wave 分别发版：** ROADMAP 已经显式约束「三条标准共享同一个验证动作,不应拆到不同 wave 分别发版」——这不只是效率考虑,而是因为多次发版会制造多个 Release 页面,污染「这是不是第一次真实执行」的证据链。
- **用 `workflow_dispatch` 的产物当 SC1/SC2/SC3 的证据：** `release` job 在 `workflow_dispatch` 下恒被 skip(`if: startsWith(github.ref, 'refs/tags/')`),SC2/SC3 天然无法用这条路径验证;SC1 虽然理论上可以用 `workflow_dispatch` 产出的 dmg,但这与「验的是最终发布产物」的语义有出入,属于 Claude's Discretion 里需要 planner 显式决策的一条。
- **给 `check_version_consistency.py` 的模板版本号解析引入对措辞/排布的依赖：** 见 Pattern 1——用固定的注释锚点,不要正则抓中英文标题里的自然语言文本。
- **试图给 build-macos 的 GUI 冒烟门禁加「点击关闭按钮」的第三维度：** 见 Common Pitfalls #3,GitHub-hosted macOS runner 上无法非交互式获取 Accessibility 权限,这条路走不通,不要花时间尝试。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 模板版本号一致性校验 | 一个独立的新脚本或 GitHub Action 步骤 | 扩展 `scripts/release/check_version_consistency.py` 现有的纯函数(D-02 明文要求) | 脚本已经是清晰的纯函数结构(`read_package_version`/`read_main_versions`/`check_version_consistency`),有单测覆盖,`main()` 的 CLI 契约已被 `build-release.yml:159` 消费,新增一个并行脚本会制造第二套一致性校验逻辑 |
| 让「点击窗口关闭按钮」这类 UI 事件在 CI 里自动化重放 | 尝试用 `osascript`/`System Events` 的 `click button 1 of window 1` 或第三方 UI 自动化框架在 GitHub-hosted runner 上跑 | 保留现状(18s 存活 + `osascript ... to quit` 两维度自动化 + 人工点关闭按钮的真机验证) | Accessibility(`kTCCServiceAccessibility`)网关无法在无 SIP 关闭权限、无交互授权渠道的托管 runner 上打通,详见 Common Pitfalls #3;这不是「暂时没做」,是这类 runner 的架构性限制 |
| Release 正文的双语拼接逻辑 | 在 `release` job 里加一个脚本步骤拼接中英文/自动 changelog | `softprops/action-gh-release` 自带的 `body_path` + `generate_release_notes: true` 组合(action 已经处理 pre-pend 逻辑) | Phase 6 已经验证过这个组合能工作(YAML 层面),本 phase 只是让它第一次真的跑一次 tag push;新增拼接步骤等于重新发明 action 已经做的事,还会改动 SC2/SC3 的观测对象本身 |

**Key insight:** 本 phase 每一个「不要手搓」的结论都指向同一件事——机制已经存在(仓库自己的脚本,或已固定的 GitHub Action,或 macOS 系统本身的权限模型),phase 的实际工作是「让机制第一次被真实触发并观测结果」,而不是新建机制。

## Runtime State Inventory

本 phase 涉及版本号字符串(`0.2.0` → `0.2.1`)在多处的同步,属于「重命名/迁移」的邻近类别,按 D-05/06 的方法逐项确认:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 无——版本号不作为任何数据库/存储的 key、user_id 或 collection 名称使用 | 无 |
| Live service config | GitHub Release 页面本身是「活的服务配置」,但 v0.2.0 的 Release 页面按 D-04/CONTEXT.md 明确保持原样不再手工编辑——本 phase 只新增 v0.2.1,不回填/修改 v0.2.0 | 无需迁移;仅需在 SUMMARY 中明确记录「v0.2.0 页面未被触碰」这一事实,防止未来误解 |
| OS-registered state | 无——版本号不出现在任何 Windows Task Scheduler / launchd / pm2 类注册信息里;Info.plist 的 `CFBundleShortVersionString`/`CFBundleVersion` 由 CI 的 `Patch Info.plist` 步骤在构建时用 `$APP_VERSION`(来自门禁脚本 stdout)动态写入,不需要手改仓库内文件 | 无 |
| Secrets/env vars | 无——版本号不是任何密钥/env var 的名字或值的一部分 | 无 |
| Build artifacts | `check_version_consistency.py` 若被本 phase 修改了函数签名/新增强制性分支,任何缓存的 `.pyc`(`tests/__pycache__/test_version_consistency.cpython-*.pyc`)理论上会被 Python 自动失效重编译,不需要手动清理 | 无需人工干预,Python 的 mtime 校验会自动处理 |

**Nothing found beyond the above** — 已核对 `check_version_consistency.py`、`build-release.yml`、`launch_app.py` 全文,版本号与本 phase 涉及的两处修复均无隐藏的运行时状态残留。

## Common Pitfalls

### Pitfall 1: 把 `workflow_dispatch` 的绿色结果误当作 `body_path` 渲染已验证
**What goes wrong:** `release` job 的 `if: startsWith(github.ref, 'refs/tags/')` 使得它在 `workflow_dispatch`(分支 ref)下恒被 `skipped`。一个绿色的 `workflow_dispatch` 跑只能证明 `build`/`build-macos` 两个 job 的 YAML/逻辑没有语法或结构性错误,**不能**证明 `body_path` 的内容真的会被正确渲染进 Release 正文。
**Why it happens:** `release` job 依赖 `needs: [build, build-macos]` 且被 tag 门控,`workflow_dispatch` 触发时 `github.ref` 是分支 ref 不是 tag ref,job 图会正常求值但 `release` 这个 job 节点直接被跳过,不会报错也不会警告。
**How to avoid:** 只把 `workflow_dispatch` 当作 Wave 0 的「语法/脚本正确性」冒烟测试,SC2/SC3 的实证结论必须来自真实 `v0.2.1` tag push 后的 Release 页面观测。
**Warning signs:** 计划或验证报告里出现「`workflow_dispatch` 跑通,SC2 已验证」这类表述——这是 05-05/06-05 已经反复踩过、又反复被文档化警示的坑(见 `06-RESEARCH.md` Pitfall 5)。

### Pitfall 2: `check_version_consistency.py` 的 CLI 契约不能破坏
**What goes wrong:** 脚本的 stdout **只能**打印版本号本身(`build-release.yml:159` 用 `$(...)` 命令替换直接捕获 stdout 赋给 `APP_VERSION`)。如果 D-02 的扩展在 `main()` 里不小心多打印了诊断信息到 stdout(而不是 stderr),`APP_VERSION` 会被污染成一个非法字符串,后续 `plutil -replace CFBundleShortVersionString -string "$APP_VERSION"` 这类步骤会静默写入错误值。
**Why it happens:** 脚本现有约定是「诊断信息 → stderr,版本号 → stdout」,新增的模板版本号读取分支如果照抄这个约定没问题,但如果开发者图省事在 `read_template_version()` 里加了 `print()` 调试语句忘记删,或者把错误信息打到 stdout 而非 stderr,就会破坏这个契约。
**How to avoid:** 新增的 `read_template_version()` 只应该 `raise VersionMismatch(...)` 或返回字符串,不应该有任何 `print()` 副作用;`main()` 里唯一允许打到 stdout 的位置(第 131 行 `print(version)`)保持不变。
**Warning signs:** 本地手跑 `python3 scripts/release/check_version_consistency.py v0.2.1 true` 后,stdout 不是干净的单行版本号。

### Pitfall 3: 给 build-macos GUI 冒烟门禁加「关闭按钮点击」第三维度在 GitHub-hosted runner 上不可行
**What goes wrong:** 现有的两个自动化维度(18s 存活 + `osascript "tell application ... to quit"`)之所以能在无人值守的 CI 里工作,是因为它们都不需要 macOS 的 Accessibility(`kTCCServiceAccessibility`)权限——18s 存活只是 `kill -0` 轮询进程是否还在,`tell application "X" to quit` 是发给目标 App 本身的标准 `NSApplication` 终止 Apple Event(属于应用默认响应的标准事件,不经过 UI 元素遍历)。但「点击某个具体窗口的关闭按钮」在 AppleScript 里必须通过 `tell application "System Events" to click button 1 of window 1 of process "..."` 这种 UI Scripting 语法完成,这类操作会触发 macOS 对**发起进程**(`osascript`/`bash`)的 Accessibility 权限检查。GitHub-hosted macOS runner 镜像默认不预先授予这项权限,而且 SIP(System Integrity Protection)在这些 runner 上保持开启,导致连「直接改写 `TCC.db` 强行插入授权记录」这条常见的本地 CI 变通方案都走不通(TCC.db 受 SIP 保护,只有具备特定 entitlement 的进程才能写)。
**Why it happens:** Apple 把「读取/操纵其他应用的 UI 元素」(Accessibility)和「向应用发送该应用主动声明会响应的标准生命周期事件」(如 Quit)视为两类风险完全不同的能力,前者被划入需要用户交互式授权、且不可编程绕过的强隔离权限。
**How to avoid:** 不要在 `build-macos` job 里尝试添加「点击关闭按钮」的第三维度。SC1 的关闭按钮回归验证只能停留在人工真机检查,现有的两维度自动化门禁(防 SIGSEGV 回归 + 防 Quit 死循环回归)已经是 CI 侧能做到的上限。
**Warning signs:** 计划里出现「给 GUI 冒烟门禁加第三维度断言」这类任务且预期在 CI 里跑通——会在实现阶段撞上超时/权限拒绝且无法在托管 runner 上修复。

### Pitfall 4: 用源码跑 `python launch_app.py` 冒充冻结态 `.app` 的关闭按钮验证证据
**What goes wrong:** `should_close_to_tray()`/`should_intercept_quit_event()` 的判定只按 `sys.platform == "darwin"` 分支,不检查 `sys.frozen`,理论上源码直跑也会走到同一段代码。但 05-02(SIGSEGV)与 05-06(Quit 死循环)这两次真机缺陷,从 Phase 5 到 Phase 6 的多轮真机验证,**从未在源码直跑(`python launch_app.py`)时复现过,只在 PyInstaller 冻结的 `.app` bundle 里复现**。这意味着触发这两个缺陷的必要条件不完全是「代码路径被执行」,还牵涉冻结态特有的运行时差异——PyInstaller 打包的 Qt/PySide6 二进制版本与本地 `.venv` 里的版本可能不完全一致、`.app` bundle 通过 Finder/LaunchServices 双击启动 vs 终端直接跑 Python 解释器在 NSApplication 的激活策略/进程注册上存在系统性差异、bundle 身份(`CFBundleIdentifier`/Info.plist)只有冻结态才具备。
**Why it happens:** 这两个 bug 的根因(SIGSEGV 出在 PySide 包装层对某些事件目标的空 vtable/d_ptr 访问;Quit 死循环出在 Cocoa 终止协议与 Qt 事件循环的交互时序)都与「Qt/Cocoa 层面的事件分发时机」强相关,而这个时机受进程如何被启动、Qt 平台插件如何加载影响,不是纯 Python 逻辑分支能完全代表的。
**How to avoid:** SC1 的真机验证必须针对**冻结的 `.app`**,且优先使用真实 Release 产出的 dmg(而非临时 `workflow_dispatch` artifact),不接受源码直跑作为等价证据。
**Warning signs:** SUMMARY/验证记录里写「用 `python launch_app.py` 跑源码验证了关闭按钮行为」——这不满足 SC1 对「真机实测」的要求。

### Pitfall 5: 发版失败后的回退操作有多种选项,且互不等价
**What goes wrong:** 如果 `v0.2.1` 推送后 Release 正文没有正确渲染(SC2 未达成),团队可能条件反射式地用 `gh release edit` 手工补救——但这恰恰是本 phase 要证明「不再需要」的操作,若真的用了,PKG-06 的核心验收目标就没达成,只是又制造了一个「手工补全」的 Release,和 v0.2.0 一样。
**Why it happens:** `gh release edit` 是最快的止损手段,压力下容易被当作默认选项,而不是被当作「验收失败」的信号。
**How to avoid:** 在执行 tag push 之前,明确本 phase 的三种可能回退路径并写进计划(不是留到出问题时再决定):(a) 保留失败状态,记录 SC2 未达成 + `gh release edit` 手工补救(承认这次没通过,但仍然是有效的观测——A2 判定依然成立,只是走了手工路径);(b) `git push origin :refs/tags/v0.2.1` 删除远程 tag + `gh release delete v0.2.1 --yes` 删除 Release,修复问题后重新打同一个 `v0.2.1` tag 再推送(需注意:删除后重新创建同名 tag 并推送,会作为一次新的 ref 创建事件重新触发 `on: push: tags:`,这是 GitHub Actions 的标准行为,但**未在本仓库实测**,标记为 `[ASSUMED]`);(c) 放弃 v0.2.1,烧一个 `v0.2.2` 版本号重新走一遍完整流程(不删除/重推 tag,规避「已发布 tag 被重写」对已拉取用户的影响,但需要再走一次 D-02 门禁与三处版本号 bump)。这三条路径的抉择权 CONTEXT.md 已经明确留给 planner,不是研究能替 planner 做的决定,但 planner 落子前必须知道选项的完整代价。
**Warning signs:** 计划里对「万一失败怎么办」只字未提,或者隐含假设「肯定一次成功」。

## Code Examples

### D-02: 扩展 `check_version_consistency()` 纳入模板版本号(四方比对)

```python
# Source: scripts/release/check_version_consistency.py(现有文件,建议扩展形态)
def check_version_consistency(
    ref_name: str,
    is_tag: bool,
    package_path: "Path | None" = None,
    main_path: "Path | None" = None,
    template_path: "Path | None" = None,   # 新增
) -> str:
    main_versions = read_main_versions(main_path)
    if len(main_versions) < 2:
        raise VersionMismatch(...)  # 逻辑不变
    if len(set(main_versions)) != 1:
        raise VersionMismatch(...)  # 逻辑不变
    main_version = main_versions[0]

    package_version = read_package_version(package_path)
    template_version = read_template_version(template_path)  # 新增

    if is_tag:
        expected_version = normalize_tag(ref_name)
        if expected_version == package_version == main_version == template_version:
            return expected_version
        raise VersionMismatch(
            "版本不一致: "
            f"tag={expected_version} package.json={package_version} "
            f"main.py={main_version} template={template_version}"
        )

    # 非 tag 模式:忽略 ref_name,三方(package/main/template)必须一致
    if package_version == main_version == template_version:
        return package_version
    raise VersionMismatch(
        "版本不一致(非 tag 模式,忽略分支名): "
        f"package.json={package_version} main.py={main_version} template={template_version}"
    )
```
`main()` 的 CLI 契约(`<ref_name> <is_tag>`,stdout 只打印版本号)完全不需要改动——`read_template_version()` 内部用 `DEFAULT_TEMPLATE_PATH` 的默认参数照抄现有的 `read_package_version`/`read_main_versions` 模式即可。

### D-02: 单测(照抄现有夹具模式)

```python
# Source: tests/test_version_consistency.py(现有文件,建议新增的测试类形态)
def _write_template(dir_path: Path, version: str) -> Path:
    path = dir_path / "RELEASE_NOTES_TEMPLATE.md"
    path.write_text(f"<!-- RELEASE_VERSION: {version} -->\n## 本次更新\n...\n", encoding="utf-8")
    return path


class CheckVersionConsistencyTemplateTests(unittest.TestCase):
    def test_tag_mode_requires_template_version_too(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "1.2.3")
            main_path = _write_main_py(tmp_path, ["1.2.3", "1.2.3"])
            template_path = _write_template(tmp_path, "1.2.2")  # 故意漏改
            with self.assertRaises(vc.VersionMismatch) as ctx:
                vc.check_version_consistency(
                    "v1.2.3", True,
                    package_path=package_path, main_path=main_path,
                    template_path=template_path,
                )
            self.assertIn("template=1.2.2", str(ctx.exception))

    def test_missing_template_anchor_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "RELEASE_NOTES_TEMPLATE.md"
            template_path.write_text("## 本次更新\n(忘了加锚点)\n", encoding="utf-8")
            with self.assertRaises(vc.VersionMismatch):
                vc.read_template_version(template_path)
```

### D-01/D-03/D-04: 模板顶部新增章节的内容形态(不含具体排布,排布留给 planner)

```markdown
<!-- Source: .github/RELEASE_NOTES_TEMPLATE.md,建议在现有 107 行最前面新增,
     具体是「中英各自跟随语言区块之首」还是「两段紧挨着放顶部」是 Claude's Discretion,
     以下只演示内容与措辞基调,不代表最终排布决定 -->

<!-- RELEASE_VERSION: 0.2.1 -->
## 本次更新

- **macOS：** 修复点击窗口关闭按钮后应用仍在后台运行的问题——现在点关闭按钮会直接退出应用
- **Windows：** 本版本无功能变更

## What's Changed

- **macOS:** Fixed the app staying alive in the background after clicking the window close
  button — clicking it now quits the app directly
- **Windows:** No functional changes in this release
```
措辞延续 Phase 6 的基调(讲用户能感知的现象,不讲实现细节),`524aeb1` 的 CI 修复按 D-04 不出现在这里。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.github/RELEASE_NOTES_TEMPLATE.md` 版本无关、零维护 | 顶部新增每次发版必改的「本次更新」章节,由 `check_version_consistency.py` 门禁强制同步 | 本 phase(D-01/D-02) | 模板从「写一次、长期不变」变成「发布流程的一部分」,后续每次发版都要记得改这一段——这是 D-01 的 Reversibility 被标记为 costly 的原因 |
| `release` job 的 checkout 缺失,`body_path` 被静默丢弃(v0.2.0 首发实际发生的情况) | `524aeb1` 已修复(`build-release.yml:791-792` 有 `actions/checkout@v4`) | 06-05(2026-07-31 之前),已在 main | 本 phase 是这个修复**第一次**真实执行(v0.2.0 的成功正文是手工贴的,不算数) |

**Deprecated/outdated:**
- `softprops/action-gh-release@v2` — 官方标记 `v2.6.2` 为最终 v2 版本,已停止维护,推荐升级 `v3`(Node 24 runtime)。本 phase 不处理这个升级,留给未来独立的里程碑/phase。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `body_path` 内容会被 `softprops/action-gh-release` pre-pended(前置)于 `generate_release_notes: true` 产出的自动 changelog 之前 | Architecture Patterns(System Diagram)、Phase Requirements | 这是官方 README 逐字确认的行为(`[CITED: raw.githubusercontent.com/softprops/action-gh-release/master/README.md]`),但从未在本仓库被真实验证——这正是本 phase SC3 存在的意义:若真实观测与文档不符,SC3 的判定结论应以真实观测为准,推翻本条假设 |
| A2 | 删除远程 tag(`git push origin :refs/tags/v0.2.1`)后重新创建并推送同名 tag,会作为一次新的 ref 创建事件重新触发 `on: push: tags:` workflow | Common Pitfalls #5(回退策略) | 这是 GitHub Actions 的标准公开行为(训练知识,未在本仓库或本次会话中用工具验证),风险极低但若不成立,选择路径(b)的回退方案会失效,需要改用路径(c)(烧新版本号) |
| A3 | Accessibility(`kTCCServiceAccessibility`)权限在 GitHub-hosted macOS runner 上无法被非交互式、编程方式授予(SIP 保持开启,阻止直接改写 TCC.db) | Common Pitfalls #3、Architecture Patterns Pattern 2 | 基于多个 `actions/runner-images` 公开 issue 与社区文章交叉印证(`[CITED: 见 Sources]`),但不是本仓库直接实测。若判断错误(例如 GitHub 后续更新了 runner 镜像的预授权策略),SC1 的「第三维度自动化不可行」结论需要重新评估——建议 planner 在实现前用一次快速的 `workflow_dispatch` 冒烟(尝试最小化的 `click button` AppleScript,观察是否超时/报错)复核这条假设,而不是直接采信本研究 |
| A4 | 05-02(SIGSEGV)与 05-06(Quit 死循环)两次真机缺陷只在冻结 `.app` 复现、从未在源码直跑复现,这一差异是「冻结态特有运行时因素」导致而非偶然 | Common Pitfalls #4 | 基于 STATE.md 记录的历史事实(缺陷确实只在冻结态被抓到)做出的因果推断,推断本身未被专门验证过。若推断错误(即源码直跑其实也能复现,只是没人试过),放宽 SC1 验证载体到源码跑也许是可以接受的——但风险不对称:错误地采信「源码跑等价」可能让一个只在冻结态出现的真实回归被漏检,而错误地坚持「只能用冻结态」的代价只是多花一点验证时间,故本研究建议保守处理 |

## Open Questions

1. **发版与验证的先后排序应该选哪一个?**
   - What we know:CONTEXT.md 已经把这条列为 Claude's Discretion,并列出了两个选项的权衡(先验后发验的不是最终产物;先发后验一旦失败要再发 v0.2.2)。
   - What's unclear:哪个选项更符合项目当前的风险偏好——SC2/SC3 天然要求真实 tag push,SC1 理论上可以在 tag push 前用 `workflow_dispatch` 产出的 dmg 先验证。
   - Recommendation:鉴于 ROADMAP 已明确「三条标准共享同一次真实 tag push,不应拆到不同 wave」,且 SC1 的验证载体本身已经要求「冻结态 `.app`」(Pitfall 4),建议 SC1 也使用 tag push 后 Release 页面上的真实 dmg 进行验证(而不是 tag push 前的 `workflow_dispatch` 产物)——这样三条 SC 共享同一个验证时间点和同一份产物,证据链最干净;代价是如果 SC1 验证失败,回退成本与 Pitfall 5 讨论的一致。这是 planner 需要在计划里显式落盘的决策,不是本研究能替 planner 拍板的。

2. **失败回退策略(A2 被推翻,或正文未渲染)时,是否允许 `gh release edit`?**
   - What we know:D-04 的动机是「证明不再需要手工补救」;若真的失败,`gh release edit` 能止损但会削弱本 phase 的验收结论。
   - What's unclear:CONTEXT.md 明确把这条留给 planner。
   - Recommendation:参见 Pitfall 5 列出的三条路径(接受失败+手工补救 / 删除重推 tag / 烧新版本号)。建议 planner 在计划中预先声明「如果验证失败,采用路径 X」,而不是等失败发生时再临场决定——这本身也是本 phase「操作型」性质的一部分,应该被当作 verification 步骤的一部分提前设计。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | tag 创建与推送 | ✓ | 2.54.0(开发机已安装) | — |
| `gh` CLI | Release 观测、必要时的回退操作(delete release/tag) | ✓ | 2.88.1(开发机已安装) | GitHub Web UI 可替代大部分操作 |
| Python `.venv`(仓库自带) | 跑通 `check_version_consistency.py` 相关单测 | ✓ | 已验证可跑通(122 个测试,2 skip) | 系统 `python3` 缺少依赖(`websocket` 等),不能直接用,必须用 `.venv/bin/python` |
| Node.js(`node --test`) | 跑 `frontend/src/lib/*.test.js`(52 个,含 `releaseNotesTemplate.test.js`) | ✓ | 已验证可跑通(52/52 通过) | — |
| 真实 macOS 硬件(Apple Silicon, macOS 15.7) | SC1 的关闭按钮真机验证 | ✓(开发机本身即 macOS 15.7 Apple Silicon) | 24G222 | 无替代——D-13/D-15 的同类要求(Phase 6)已确认无自动化替代 |
| GitHub push 权限(推 `v*` tag 的权限) | 触发一次真实 `v0.2.1` 发布(SC2/SC3 的唯一证据来源) | 假定可用(项目维护者本人执行) | — | 若不可用,SC2/SC3 无法在本 phase 内闭环,需要升级为阻塞项 |

**Missing dependencies with no fallback:**
- 无——本 phase 所需的全部工具/权限在当前开发机上均已确认可用。

**Missing dependencies with fallback:**
- 无。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest`(`scripts/release/check_version_consistency.py` 的扩展) + Node `node:test`(`frontend/src/lib/releaseNotesTemplate.test.js` 的可选补充断言) |
| Config file | 无——沿用 CLAUDE.md 文档化的命令 |
| Quick run command | `.venv/bin/python -m unittest tests.test_version_consistency -v`(版本号门禁改动)或 `node --test frontend/src/lib/*.test.js`(模板/前端改动) |
| Full suite command | `.venv/bin/python -m unittest discover -s tests -v`(当前基线:122 个测试,2 skip,均为 Windows-only 分支,在 macOS 上预期跳过) + `node --test frontend/src/lib/*.test.js`(当前基线:52/52 通过) |

### Phase Requirement → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PKG-06 | 模板版本号锚点存在、格式为 semver、且与 tag/package.json/main.py 一致(D-02) | unit | `.venv/bin/python -m unittest tests.test_version_consistency.CheckVersionConsistencyTemplateTests -v`(新增类,命名建议见 Code Examples) | ❌ Wave 0(新增) |
| PKG-06 | 漏改模板版本号时门禁正确拒绝(负向用例) | unit | 同上,`test_tag_mode_requires_template_version_too` | ❌ Wave 0(新增) |
| PKG-06 | Release 正文由流水线自动渲染、无需 `gh release edit`,以及手写正文与自动 changelog 的实际先后顺序 | manual_procedural | 真实 `v0.2.1` tag push 后人工检视 Release 页面(无自动化等价物——这正是 SC2/SC3 本身) | ❌ Wave 0(本 phase 的核心产出,非既有缺口) |
| UI-05 | macOS 关闭按钮点击后进程真正消失(`ps`/活动监视器确认) | manual_procedural | 人工真机操作(无自动化等价物,见 Common Pitfalls #3) | ❌ Wave 0(本 phase 的核心产出) |
| UI-05(既有回归护栏,非本 phase 新增) | CI 侧两维度自动化(18s 存活防 SIGSEGV 回归 + `osascript quit` 防死循环回归) | integration(CI) | `build-macos` job 的 "GUI launch smoke test" 步骤(已存在,`build-release.yml:531-697`) | ✅(已存在,05-02/05-06 已建成) |

### Sampling Rate
- **Per task commit:** 版本号门禁改动跑 `.venv/bin/python -m unittest tests.test_version_consistency -v`;模板改动跑 `node --test frontend/src/lib/*.test.js`
- **Per wave merge:** 全套 `.venv/bin/python -m unittest discover -s tests -v` + `node --test frontend/src/lib/*.test.js`
- **Phase gate:** 全套测试绿灯 + 真实 `v0.2.1` tag push 完成 + SC1 人工真机检查通过 + SC2/SC3 观测记录落盘,才能进 `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `scripts/release/check_version_consistency.py` 新增 `read_template_version()` 与四方/三方比对扩展(D-02)
- [ ] `tests/test_version_consistency.py` 新增覆盖模板版本号分支的测试类(正向一致 + 负向漏改 + 缺失锚点三种场景)
- [ ] `.github/RELEASE_NOTES_TEMPLATE.md` 顶部新增 `<!-- RELEASE_VERSION: X.Y.Z -->` 锚点 + 双语「本次更新」章节(D-01/D-03/D-04)
- [ ] 无需新装测试框架——`unittest`/`node:test` 均已在仓库可用,`.venv` 已验证可跑通全套

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 不涉及任何鉴权面 |
| V3 Session Management | no | 不适用 |
| V4 Access Control | no | 不适用 |
| V5 Input Validation | 否(窄) | 版本号解析(`read_template_version`)是从仓库内自有文件读取固定形状的字符串,不是外部/用户输入;沿用现有 `_SEMVER_VERSION_RE` 的严格 semver 形状约束即可,不需要额外的输入校验设计 |
| V6 Cryptography | no | 不适用 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 发布流程被绕过(tag 指向未经版本号门禁校验的 commit) | Tampering | `check_version_consistency.py` 已经是 `build-macos` job 里的硬阻断步骤(非零退出码即失败,`release` job 因 `needs:[build, build-macos]` 连带不跑),D-02 只是扩展比对范围,不改变阻断机制本身 |
| 发布正文包含误导性/危险指令(如 `sudo`、`spctl --master-disable`) | Tampering(误导用户执行危险命令) | Phase 6 已经建立 `releaseNotesTemplate.test.js` 里的 `FORBIDDEN_FRAGMENTS` 黑名单测试(`sudo`/`spctl`/`--master-disable`/`~/Downloads`/`csrutil`),D-01 新增的「本次更新」章节内容纯文字描述,不含任何命令,天然不会触碰这条边界,但若模板改动扩大范围,应重跑该测试确认未新增违禁片段 |

## Sources

### Primary (HIGH confidence)
- 直接读取仓库文件:`scripts/release/check_version_consistency.py`、`.github/workflows/build-release.yml`、`launch_app.py`(第 55-190 行区间)、`tests/test_macos_desktop_runtime.py`(第 253-430 行区间)、`tests/test_version_consistency.py`、`frontend/src/lib/macosGatekeeperNotice.js`、`frontend/src/lib/releaseNotesTemplate.test.js`、`.github/RELEASE_NOTES_TEMPLATE.md`
- `git log`/`git tag`/`git status` 直接查询本仓库历史(确认 `a886dc7`/`524aeb1` 已在 main,`v0.2.0` tag 存在,当前 `frontend/package.json`/`backend/main.py` 均为 `0.2.0`)
- 本地实跑 `.venv/bin/python -m unittest discover -s tests -v`(122 测试,2 skip)与 `node --test frontend/src/lib/*.test.js`(52/52 通过),作为本 phase 的回归测试基线
- `.planning/phases/06-release-docs/06-RESEARCH.md`(A2 假设原文、`softprops/action-gh-release` 相关既有结论)、`.planning/phases/06-release-docs/06-05-SUMMARY.md`(v0.2.0 真实 tag push 实测记录、checkout 缺陷发现经过)、`.planning/STATE.md`(05-02/05-06 两次真机缺陷的完整成因记录)

### Secondary (MEDIUM confidence)
- `raw.githubusercontent.com/softprops/action-gh-release/master/README.md`(WebFetch 直接抓取,`[CITED]`)——确认 `body_path` 内容 pre-pended 于自动生成 notes 之前,以及 `v2.6.2` 是最终 v2 版本、推荐升级 v3
- GitHub `actions/runner-images` 相关公开 issue 与社区文章(WebSearch,`[CITED]`,多篇交叉印证)——确认 GitHub-hosted macOS runner 上 Accessibility/TCC 权限无法非交互式授予、UI Scripting 类 AppleScript 在无人值守 CI 下会因权限阻挡而超时/失败

### Tertiary (LOW confidence)
- 删除远程 tag 后重新推送同名 tag 会重新触发 `on: push: tags:` workflow——训练知识,`[ASSUMED]`,未在本仓库或本次会话中用工具验证(见 Assumptions Log A2)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 无新工具,全部复用仓库既有的、已直接读源码确认的机制
- Architecture: HIGH — 版本号门禁扩展模式直接复用脚本自身已有的纯函数结构;发布正文渲染路径已被官方文档确认(MEDIUM,因未在本仓库实测)
- Pitfalls: MEDIUM — Accessibility/TCC 相关结论(Pitfall 3)基于公开 issue 交叉印证而非本仓库直接实测,标记为 `[ASSUMED]`/`[CITED]` 并在 Open Questions 中建议 planner 用一次快速冒烟复核

**Research date:** 2026-07-31
**Valid until:** 与本次真实 `v0.2.1` tag push 的结果强绑定——一旦 tag 推送完成,SC2/SC3 的观测结论(A1)应以实测结果为准更新本文档或直接体现在 SUMMARY 里,不应继续依赖本研究里的官方文档推断。Accessibility/TCC 相关结论(A3)在 GitHub 更新 runner 镜像策略前应保持有效,无固定过期时间。
