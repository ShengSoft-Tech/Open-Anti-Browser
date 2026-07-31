# Phase 6: 发布文档与端到端验证 - Research

**Researched:** 2026-07-30
**Domain:** Release documentation (GitHub Release notes, README), macOS Gatekeeper/quarantine UX writing, GitHub Actions `softprops/action-gh-release` body injection, cross-artifact consistency testing
**Confidence:** HIGH (this phase is almost entirely documentation work grounded in Phase 5's real-hardware evidence, which is already in the repo; the one code change — D-04's `shlex`/quoting fix — is a small, well-understood Python/JS change)

## Summary

Phase 6 has no new technology to evaluate. Its "stack" is: Markdown (Release notes template + README sections), a one-line `body_path` addition to an already-verified GitHub Actions workflow, two PNG assets regenerated with a process Phase 5 already established (headless Chromium screenshot, zero new dependencies), a small Python/JS text-and-quoting fix, and a cross-file verbatim-consistency unit test extending a pattern Phase 5 already built twice. The single hard constraint governing every piece of prose in this phase is: **write down what Phase 5 measured on real hardware, not what the code's comments assume.** `05-06-SUMMARY.md` is the primary source of truth for what actually happens on first launch (blocked once → app exits → double-click again → works), and it explicitly flags two things the current shipped assets get wrong (the dmg background's "right-click → Open" instruction, and the requirements docs' now-stale "DOCS-01 talks about System Settings as the primary path" framing).

The only genuinely technical risk in this phase is `release` job unrunnability: `softprops/action-gh-release`'s `release` job step is gated on `startsWith(github.ref, 'refs/tags/')` and has never executed for real (Phase 5's own review flagged this). Adding `body_path` to it can only be smoke-tested by YAML validity and a `workflow_dispatch` run where the step stays `skipped` — the actual rendering of `body_path` content can only be confirmed by pushing a real `v*` tag, which is a user-visible, irreversible action (CONTEXT.md's Deferred Ideas explicitly punts this decision to the planner).

**Primary recommendation:** Treat this phase as "update prose + one quoting fix + one workflow line + regenerate two PNGs + one cross-file unit test + one real end-to-end human checkpoint on a clean macOS user account." Do not introduce any new library, build tool, or CI action beyond what Phase 4/5 already use.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Release notes content (Gatekeeper steps, hardware/OS gating) | Docs / Release artifact (`.github/RELEASE_NOTES_TEMPLATE.md`) | CI (`release` job `body_path`) | Single source of truth lives in the template file; CI only injects it verbatim into the GitHub Release body |
| dmg first-run guidance | Build artifact (`assets/dmg-background*.png`) | — | Baked into the dmg at build time (05-03's `create-dmg --background`); regenerated via the same local headless-Chromium screenshot process, not CI |
| In-app first-launch notice | Frontend (`frontend/src/i18n/{zh-CN,en-US}.js` + `macosGatekeeperNotice.js`) | — | Already-shipped Phase 4 UI-04 deliverable; Phase 6 only edits copy, not the rendering logic |
| Fallback terminal command generation | Backend (`launch_app.py::build_quarantine_failure_message`) | Frontend (`GATEKEEPER_XATTR_COMMAND` constant) | Both sides must render byte-identical text; Python is the runtime fallback dialog, JS is the pre-first-run in-app notice — cross-checked by unit test, not by shared code |
| README download-section pointer | Docs (`README.md` / `README_EN.md`) | Release artifact (links to Release page) | README stays a thin pointer per D-11; the template is the only place with step-by-step detail |
| End-to-end acceptance | Human (real Mac, clean OS user account) | — | No tier below "a human following only the shipped docs" can validate DOCS-01/02 per D-15 |

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**放行路径写哪一条**

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

**硬件/系统门槛怎么讲**

- **D-05:** REQUIREMENTS 的 **DOCS-02 原文「双架构下载选择指引」已失效** —— x64 于 2026-07-27 移出 v0.2，没有第二个包可选。重写为「**前置要求清单**」：下载前确认 **Apple Silicon + macOS 15 或更新**。不假装有选择，直接说清能不能跑。
  注意 DOCS-02 现文只覆盖了架构，**完全没提 macOS 15 下限** —— 那是 Phase 5 实测 PySide6/shiboken6 绑定库 `minos=15.0` 得出的硬门槛，比架构更容易把人挡在外面（macOS 15 是 2024 年 9 月才发布的）。

- **D-06:** 自查方法 **GUI 为主、命令作补**。主写「左上角苹果图标 → 关于本机」看「芯片」一行是否 Apple M×、看系统版本号是否 ≥ 15；后附 `uname -m && sw_vers -productVersion` 给习惯终端的人。目标读者大概率不懂命令行 —— 本 phase 的目标就是「无需开发者协助」。

- **D-07:** 不符合门槛时**只写文档预期表现，本 phase 不加任何运行时代码检查**。加运行时代码会扰动已验收的 Phase 5 产物，且 macOS < 15 根本跑不到那行代码（`LSMinimumSystemVersion` 先拦）。

- **D-08:** 两句失败表现（macOS < 15 会被系统拒绝打开、Intel Mac 无法运行 arm64 包）**目前无人实测**，仅由 `LSMinimumSystemVersion` 语义推断得出。文档用**保守措辞**（「系统会拒绝打开」而不是逐字引用某个弹框文案），并把「未实测」记为已知假设。
  理由：Phase 5 刚刚吃过一次亏 —— `05-RESEARCH.md` 靠推断得出「App Translocation 必然发生、自剥离必然失败」，真机三次全部证伪。不要重蹈覆辙地把推断写成事实。

**Release notes 怎么落地**

- **D-09:** **机械前提**：`release` job 当前只有 `generate_release_notes: true`，**没有 `body` / `body_path`**，手写的放行说明**无处可插**。新增仓内模板（如 `.github/RELEASE_NOTES_TEMPLATE.md`），给 gh-release 步骤加 `body_path` 指向它；**保留 `generate_release_notes: true`** —— 自动生成的 changelog 会追加在手写正文之后。
  — **Reversibility:** costly — 改的是 Phase 5 刚验收、且**真实发布路径从未执行过**的 `release` job。它第一次真正跑起来会是推 `v*` tag 那一刻，改错要到发版时才暴露。改动必须走 `workflow_dispatch` 回归（届时 release job 仍会 skipped，只能验 YAML 合法性与 job 结构，无法验 body_path 实际渲染）。

- **D-10:** **一份模板双语并列**（中文在上、English 在下，或用 `<details>` 折叠英文）。GitHub Release 只有一个正文、无语言切换机制，想让两类读者都看懂只能并列。项目有 `README_EN.md` 与 `en-US.js`，说明确实有英文读者。

- **D-11:** **README / README_EN 的下载章节只加两行前置要求 + 链到 Release 页**，放行步骤不重复写。单一事实源在模板里，避免三处文案漂移。
  （现状：两份 README 的「下载」章节只有三个链接，零 macOS 内容。）

- **D-12:** 新增单测断言**模板里的 `xattr` 命令与 `macosGatekeeperNotice.js` 的 `GATEKEEPER_XATTR_COMMAND` 逐字一致**。照搬 05-02 已有的跨语言逐字比对先例。现在是三处文案要同步，不锁必漂 —— Phase 5 的两个阻塞缺陷都证明了「注释提醒」拦不住东西。

**端到端验证在哪验**

- **D-13:** **在同一台 Mac 上新建一个干净的系统用户账户**跑完整验证。`LSQuarantineEventsV2` 数据库与 Gatekeeper 放行记录按用户隔离，但 `/Applications` 全局共享 —— **需先卸载**现有安装。
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

### Deferred Ideas (OUT OF SCOPE)

- **B1 首启对话框的逐字措辞采集** — Phase 5 的 05-06 只拿到日志层面的决策序列（`Prompt shown` → `denial breadcrumb`），弹框的标题与按钮文字未采集，用户明确选择接受该缺口。Phase 6 的端到端验证会做一次真实全新安装，**顺带把这个补上**（不是新能力，是本 phase 验证的自然副产品）
- **macOS 14 / Intel Mac 上的实际失败表现实测** — D-08 决定只写推断。若将来有条件拿到这两类机器，可回补实测并收紧文档措辞
- **x64 双架构下载指引** — x64 回归时（内核资产已在 `kernel-149.0.7827.114` 备好）需要重新引入「如何判断自己是 Apple Silicon 还是 Intel」的选择指引，即 DOCS-02 的原始形态
- **端到端验证是否基于真实 `v*` tag 产出的 Release** — 讨论中提出但未展开。Phase 5 遗留的 UAT 需要一次真实 tag push；若 Phase 6 的验证基于真实 Release 产物则可一并核销。留给 plan-phase 定，注意推 `v*` tag 会触发**对用户可见的真实发版**
</user_constraints>

## Phase Requirements

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | Release notes 提供分步放行说明(启动被拦 → 再双击一次 → 仍不行则系统设置 → 隐私与安全性 → 仍要打开,并附 `xattr` 终端替代方案) — **rewritten per D-01/D-03**, original "系统设置 first" wording is superseded by Phase 5 measured evidence | `05-06-SUMMARY.md` Group B (B1–B8) gives the exact measured sequence and timestamps; `05-REVIEW.md` WR-01/WR-02 give the exact quoting defect to fix in the `xattr` fallback (D-04); see Common Pitfalls #1–#3 and Code Examples below |
| DOCS-02 | Release notes/README 提供**前置要求清单**(Apple Silicon + macOS 15 或更新) — **rewritten per D-05/D-14**, original "双架构下载选择指引" is stale (x64 out of scope since 2026-07-27) | `PROJECT.md` Out of Scope entry (x64 removed 2026-07-27); `05-04-SUMMARY.md`/`build-release.yml`'s `LSMinimumSystemVersion=15.0` full-enumeration measurement; see Architecture Patterns "Pattern 2" and Common Pitfalls #4 below |
</phase_requirements>

## Standard Stack

There is no new runtime stack for this phase — it reuses Phase 4/5's established toolchain exactly.

### Core
| Tool/Format | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `softprops/action-gh-release` | `v2` (pinned, already in `build-release.yml`) | Publishes the GitHub Release and its body text | Already the project's chosen release-publishing action (Phase 5); no reason to introduce an alternative |
| Markdown | — | Release notes template, README sections | GitHub Release bodies and README files are both rendered as GitHub-flavored Markdown; no templating engine needed |
| `node:test` / Python `unittest` | already in repo | Cross-file consistency lock (D-12) | Matches the existing 05-02 precedent (`BuildQuarantineFailureMessageTests` already cross-checks Python against the JS constant) |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Repo's own headless `engines/chrome/Chromium.app` | already vendored (149.0.7827.114) | Regenerate `assets/dmg-background.png` / `@2x` | Exact 05-01 process: scratch HTML → `--headless=new --disable-gpu --no-sandbox --hide-scrollbars --window-size=600,400 --screenshot=<out>.png`, `--force-device-scale-factor=1` for @1x / `=2` for @2x |
| `sips`, `tiffutil` | macOS built-in | Verify regenerated PNG dimensions; confirm they still combine into a retina TIFF before trusting `create-dmg` will accept them | Same verification commands 05-01 already used (`sips -g pixelWidth -g pixelHeight`, `tiffutil -cathidpicheck ... -out <tmp>.tiff`) |
| Python `shlex` | stdlib | Optional shell-quoting technique for the *dynamic* (non-canonical) bundle path branch of `build_quarantine_failure_message` — see Common Pitfalls #3 | Only if the planner extends D-04's fix beyond the fixed canonical-path case |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Baked-in `body_path` template committed to `.github/RELEASE_NOTES_TEMPLATE.md` | Inline heredoc `body:` string directly in the workflow YAML | Inline `body:` mixes long user-facing prose with CI config, harder to review/diff independently, and can't be unit-tested against `macosGatekeeperNotice.js` as a standalone file the way `body_path` can |
| Regenerating dmg background via headless Chromium screenshot (05-01's method) | Any GUI image editor / Figma export | Editor-based regeneration isn't reproducible from the repo alone and reintroduces a new dependency the project doesn't otherwise need; 05-01 already proved the headless-screenshot method works with zero new deps |
| `shlex.quote()`-based dynamic escaping for all target paths | Hardcoded double-quote wrap only for the fixed canonical path (D-04's literal instruction) | `shlex.quote` uses single-quote escaping and is a no-op for the canonical path (no shell metacharacters) — it would NOT reproduce the literal double-quoted string the cross-language test needs to lock against the JS constant. D-04 explicitly wants the simpler fixed double-quoted literal, not general-purpose escaping. See Common Pitfalls #3. |

**Installation:** none — no new packages for this phase (see Package Legitimacy Audit below).

**Version verification:** `softprops/action-gh-release@v2` is currently pinned in `.github/workflows/build-release.yml:816`. The action's own README states `v2.6.2` is the final `v2` release and no longer maintained/supported (deprecated Node 20 runtime); the maintainers recommend `v3` (Node 24). **This phase does not need to bump the pin** — D-09 only adds a `body_path:` input to the existing `v2` call, and `body_path` has been supported since early `v1`/`v2` releases. Bumping to `v3` is an unrelated, separately-reversible decision the planner should NOT bundle into this phase (it would add an unrelated variable to the "real publish path has never executed" risk D-09 already calls out as costly-to-revert). Flagged here only so the planner doesn't feel obligated to silently upgrade it.

## Package Legitimacy Audit

**No new external packages are installed in this phase.** All changes touch existing repo files (`launch_app.py`, `frontend/src/lib/macosGatekeeperNotice.js`, `frontend/src/i18n/*.js`, `README*.md`, `.github/workflows/build-release.yml`, `assets/dmg-background*.png`) or add new plain files (`.github/RELEASE_NOTES_TEMPLATE.md`, a consistency test). The Package Legitimacy Gate protocol is therefore not applicable — skip the `gsd-tools query package-legitimacy check` step during planning; there is nothing to check.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │  .github/RELEASE_NOTES_TEMPLATE.md       │
                    │  (single source of truth — new, D-09)    │
                    │  中文 gatekeeper steps + 前置要求          │
                    │  English gatekeeper steps + requirements │
                    └───────────────┬───────────────────────┬─┘
                                    │                         │
                     body_path: →   │                         │  verbatim xattr
                     (release job)  │                         │  command asserted
                                    ▼                         │  against ↓ (D-12)
              ┌────────────────────────────────┐              │
              │ softprops/action-gh-release@v2   │             │
              │ body_path prepended, then        │             │
              │ generate_release_notes: true      │             │
              │ appends auto changelog            │             │
              └───────────────┬────────────────┘              │
                               │                                │
                               ▼                                │
                    GitHub Release page (v* tag push only)      │
                    — the ONLY untested render path (D-09)      │
                                                                 │
   ┌─────────────────────────────────────────────────────────┐  │
   │ README.md / README_EN.md § 下载/Download                │  │
   │ (thin pointer, D-11: 2 lines + link to Release page)     │  │
   └─────────────────────────────────────────────────────────┘  │
                                                                 │
   ┌─────────────────────────────────────────────────────────┐  │
   │ assets/dmg-background.png / @2x                           │  │
   │ (regenerated, D-02: footer text must match measured path) │  │
   │ consumed by build-macos job's `create-dmg --background`   │  │
   └─────────────────────────────────────────────────────────┘  │
                                                                 │
   ┌─────────────────────────────────────────────────────────┐  │
   │ frontend/src/i18n/{zh-CN,en-US}.js § gatekeeper           │  │
   │ (Phase 4 UI-04 deliverable, edited in place for D-02)     │  │
   │ consumed by macosGatekeeperNotice.js::buildGatekeeperNoticeHtml
   └──────────────────────────┬────────────────────────────────┘  │
                              │ GATEKEEPER_XATTR_COMMAND constant  │
                              │ (D-04: add quotes around path) ────┴──►
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ launch_app.py::build_quarantine_failure_message           │
   │ (D-04: match quoting, cross-checked by                    │
   │  BuildQuarantineFailureMessageTests, extended for D-12)    │
   └─────────────────────────────────────────────────────────┘

   Human end-to-end path (D-13/D-15):
   clean macOS user account → download dmg from Release page (reading
   only the template's rendered text) → blocked once → double-click
   again → drag to /Applications → create Chrome profile → launch
```

### Recommended Project Structure
```
.github/
├── RELEASE_NOTES_TEMPLATE.md   # NEW — D-09/D-10, bilingual, single source of truth
└── workflows/
    └── build-release.yml       # MODIFIED — release job gains body_path: .github/RELEASE_NOTES_TEMPLATE.md

assets/
├── dmg-background.png          # REGENERATED — D-02, footer text matches measured path
└── dmg-background@2x.png       # REGENERATED — same content, 2x resolution

frontend/src/
├── lib/
│   ├── macosGatekeeperNotice.js       # MODIFIED — D-04, GATEKEEPER_XATTR_COMMAND gains quotes
│   └── macosGatekeeperNotice.test.js  # MODIFIED — existing literal-string assertions updated for new quoting
└── i18n/
    ├── zh-CN.js                # MODIFIED — gatekeeper.step1–step4 rewritten to D-01/D-03 progressive steps
    └── en-US.js                # MODIFIED — same, English

launch_app.py                   # MODIFIED — D-04, build_quarantine_failure_message quotes canonical path
tests/test_macos_desktop_runtime.py  # MODIFIED — BuildQuarantineFailureMessageTests literal updated

README.md / README_EN.md        # MODIFIED — D-11, 2-line prerequisite + link, no step duplication

.planning/ROADMAP.md            # MODIFIED — D-01/D-05/D-14, SC1/SC2/SC3 rewritten
.planning/REQUIREMENTS.md       # MODIFIED — D-01/D-05/D-14, DOCS-01/DOCS-02 text rewritten
```

### Pattern 1: Cross-file verbatim consistency lock (extend 05-02's precedent to three files)

**What:** A single literal string (the `xattr` command) must render byte-identical across three surfaces: the Release notes template, `macosGatekeeperNotice.js`'s `GATEKEEPER_XATTR_COMMAND`, and `launch_app.py`'s `build_quarantine_failure_message` output. Phase 5 already solved the two-file version of this exact problem.

**When to use:** Any time a fixed piece of user-facing text is duplicated across a JS constant and a Python function purely because they run in different processes (frontend pre-launch notice vs. backend post-launch-failure fallback) and now a third static Markdown file.

**Existing precedent (already in repo, read before writing the new test):**
```python
# Source: tests/test_macos_desktop_runtime.py (existing, D-12a precedent)
class BuildQuarantineFailureMessageTests(unittest.TestCase):
    def test_translocated_scenario_matches_frontend_constant(self) -> None:
        message = launch_app.build_quarantine_failure_message(None)
        js_source = GATEKEEPER_NOTICE_JS.read_text(encoding="utf-8")
        match = re.search(r"GATEKEEPER_XATTR_COMMAND\s*=\s*'([^']+)'", js_source)
        self.assertIsNotNone(match, "未能在 macosGatekeeperNotice.js 中找到 GATEKEEPER_XATTR_COMMAND")
        expected_command = match.group(1)
        self.assertIn(expected_command, message)
```
The D-12 test should follow the identical shape: regex the fixed command out of the JS constant, then regex/read the same literal out of `.github/RELEASE_NOTES_TEMPLATE.md`, and assert all three strings (JS constant, Python-rendered message, template's embedded command) are equal after the D-04 quoting change is applied everywhere.

### Pattern 2: Progressive-disclosure documentation ordering (D-03)

**What:** Present the common-case step first and visually de-emphasize the fallback steps, rather than three equally-weighted steps.
**When to use:** Any time real-hardware evidence shows one path resolves the overwhelming majority of cases (Phase 5's 05-06 checkpoint: self-strip succeeded 3/3 times across all installs) but a documented fallback must still exist for the untested minority case (custom install location, actual App Translocation).
**Example (Markdown structure, not code — this is what the template should look like):**
```markdown
## 首次打开被拦截？这是正常现象

1. **再次双击打开应用即可。** 首次双击 macOS 会短暂拦截，关闭提示后再双击一次通常就能正常打开
   （这是在真实硬件上实测得到的行为，不是假设）。

<details>
<summary>如果第二次双击仍然打不开</summary>

2. 打开"系统设置 → 隐私与安全性"，滚动到"安全性"区域，找到关于 Open-Anti-Browser 的提示，
   点击"仍要打开"。
3. 如果以上都不行，打开"终端"，粘贴执行：
   ```
   xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"
   ```
   （若安装在其他位置，请把引号内的路径换成实际安装路径）

</details>
```
This mirrors the CONTEXT.md decision (D-03) that "正常读者只需读第一步就够" — use a collapsed `<details>` block (GitHub Flavored Markdown renders this correctly in both Release bodies and README) so the two fallback steps are visually present but not competing for attention with step 1.

### Anti-Patterns to Avoid
- **Writing the release notes' Gatekeeper steps as fact-from-recall:** Phase 5's own `05-RESEARCH.md` predicted App Translocation would always occur; three real installs falsified it. Every claim in this phase's prose about *what actually happens* must trace to `05-06-SUMMARY.md`'s measured evidence, not to code comments describing intended behavior.
- **Duplicating the full Gatekeeper walkthrough in README:** D-11 explicitly forbids this — README gets a 2-line pointer, the template is the only full copy. Duplicating invites the exact "three drifted texts" failure Phase 5's WR-01/WR-02 already demonstrated is a real risk class in this codebase.
- **Claiming Gatekeeper "trusts" the app:** `spctl --assess --type execute` returned `rejected` throughout all of Phase 5's testing, even after the app became launchable. The docs must say the app runs because it's no longer quarantined, not because it was approved — conflating the two is factually wrong and could mislead users into thinking the developer has Apple trust it does not have (see CONTEXT.md's "Specific Ideas" section, third bullet).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Injecting a long, hand-written body into a GitHub Release created by `softprops/action-gh-release` | A custom `gh release create --notes-file` step run separately from/instead of the existing action | The existing action's `body_path:` input | The action already supports this exact use case (`body_path` is "attempted first, then falling back on `body`"); adding a second, parallel release-creation mechanism would fight the existing `needs: [build, build-macos]` + tag-gated `release` job Phase 5 already built and verified twice on real `workflow_dispatch` runs |
| Detecting Apple Silicon vs. Intel, or macOS version, for the reader | Any runtime code check, telemetry ping, or JS/Python detection embedded in the docs | Plain-language GUI instructions (Apple menu → About This Mac → look at "Chip" and macOS version number) plus the two terminal commands (`uname -m`, `sw_vers -productVersion`) as a documented fallback | D-07 explicitly forbids adding runtime code for this in this phase — a build with `LSMinimumSystemVersion=15.0` already refuses to launch on macOS < 15 at the OS level, so a redundant in-app check would never even execute on the failing case, and would only exist to serve a purely educational purpose that a doc sentence already covers |
| Retina dmg background image with two resolutions | Any image-editing tool, npm image-processing library, or new CI step to generate it | The exact 05-01 process: scratch HTML + headless `engines/chrome/Chromium.app` screenshot at `--force-device-scale-factor=1`/`2`, verified with `sips`/`tiffutil` | Zero new dependencies, reproducible from files already in the repo, and produces byte-for-byte the same kind of asset `create-dmg`'s `--background` step already consumes correctly (05-03 proved this works in real CI) |

**Key insight:** every "don't hand-roll" case in this phase resolves to "the mechanism already exists in this repo (or in the pinned GitHub Action) — the actual Phase 6 work is entirely about correct *content*, not new mechanism."

## Runtime State Inventory

Not applicable as a rename/refactor/migration phase in the literal sense, but D-13's clean-account requirement is materially the same class of problem (stale, per-account OS state that a code diff cannot detect), so it is documented here for the planner's benefit:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `LSQuarantineEventsV2` database (per-user, tracks Gatekeeper quarantine decisions) already has entries for the developer's current macOS account from Phase 5's real-hardware testing | Must run the D-13/D-15 end-to-end verification from a **newly created macOS user account** on the same machine, not the developer's existing account |
| Live service config | `spctl`/Gatekeeper "denial breadcrumb" record already exists for this app under the developer's account (per `05-06-SUMMARY.md`'s log capture) — this state is invisible to `git status` and cannot be reset by reinstalling the app | Same — new OS user account is the only way to get a truthful "never installed" state; `/Applications` itself is shared across accounts and must have any prior install removed first |
| OS-registered state | None found specific to this phase beyond the quarantine/Gatekeeper records above (no LaunchAgents, no Task Scheduler equivalent registered by this app) | None |
| Secrets/env vars | None — this phase touches no secrets | None |
| Build artifacts | None — no local package installs/builds are part of this phase's own work (CI still builds the app; this phase only edits the workflow's release body config) | None |

**Nothing else found in any category** — verified by inspecting `05-06-SUMMARY.md`'s "Test Environment" and "Open Items" sections, which are the authoritative record of what state Phase 5's real-hardware testing left behind.

## Common Pitfalls

### Pitfall 1: Writing DOCS-01/ROADMAP SC1 to match the *original* requirement text instead of the *measured* behavior
**What goes wrong:** REQUIREMENTS.md's current DOCS-01 text and ROADMAP's current SC1 text both describe "启动被拦 → 系统设置 → 隐私与安全性 → 仍要打开" as the primary flow. This was accurate *before* Phase 5 ran real hardware tests; it is not accurate now.
**Why it happens:** These lines were written during initial roadmap creation (2026-07-23), before any real installs had happened. Nobody has gone back to update them since 05-06's checkpoint (2026-07-28) produced contradicting evidence.
**How to avoid:** Per D-01, rewrite ROADMAP SC1 and REQUIREMENTS DOCS-01 as part of this phase's own work (not the release notes' work) — the requirement text itself is stale, not just the eventual doc prose.
**Warning signs:** Any planning artifact in this phase that describes the Gatekeeper flow starting with "System Settings" as the first step, rather than "double-click again," is working from the stale requirement text instead of `05-06-SUMMARY.md`'s Group B measurements.

### Pitfall 2: Trusting `05-04`'s `LSMinimumSystemVersion` value without re-checking which measurement superseded it
**What goes wrong:** Multiple historical values exist in the plan history for this constant: an initial `12.0` placeholder, then `13.0` measured from a 4-binary sample in 05-03, then `15.0` from a full Mach-O enumeration in 05-04/05-05. Only `15.0` is current and correct.
**Why it happens:** The value was revised twice as measurement methodology improved (sample → full enumeration). Anyone reading only an early Phase 5 summary would get the wrong (lower, less restrictive) number.
**How to avoid:** Cite `LSMinimumSystemVersion=15.0` (as currently hardcoded in `build-release.yml`'s "Patch Info.plist" step, line 258) as the authoritative value for this phase's documentation — it is what actually ships.
**Warning signs:** Any doc text saying "macOS 13" or "macOS 12" for the minimum is citing a superseded measurement.

### Pitfall 3: Applying `shlex.quote()` where D-04 wants a fixed, always-quoted literal
**What goes wrong:** WR-01's suggested fix in `05-REVIEW.md` was `shlex.quote(str(target))`. For the canonical path `/Applications/Open-Anti-Browser.app` (no spaces or shell metacharacters), Python's `shlex.quote` is a documented no-op — it returns the string completely unchanged, without adding any quotes. If the planner naively applies `shlex.quote()` expecting it to match D-04's example output (`xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"`), the produced string will NOT have quotes and will NOT match the JS constant if the JS constant is hand-written with literal double quotes.
**Why it happens:** `shlex.quote`'s quoting rule is "only quote if the string contains a character outside `[a-zA-Z0-9_@%+=:,./-]`" — and it uses single quotes (`'...'`), not double quotes, when it does quote.
**How to avoid:** For the fixed canonical-path branch, use an explicit `f'"{target}"'`-style wrap (or equivalently bake the quotes into the literal), matching D-04's exact specified output. Reserve `shlex.quote()` only if the planner separately decides to also harden the *dynamic*, non-canonical `str(bundle)` branch (the actual live install path when not translocated) — that branch is a different code path from the one the cross-language test (D-12) locks, and hardening it is a reasonable but separate improvement, not required by D-04's literal text.
**Warning signs:** The existing test `test_non_translocated_bundle_message_points_to_its_own_path` currently asserts the *unquoted* form (`f"xattr -dr com.apple.quarantine {bundle}"`) — this assertion must be updated in the same commit as the source change, or the test suite will fail after D-04's fix (this is by design: it's the existing regression guard that would otherwise silently drift).

### Pitfall 4: Treating `spctl --assess` "rejected" as a bug to explain away rather than a fact to state plainly
**What goes wrong:** A well-meaning docs pass might try to reassure users by implying the app becomes "trusted" once it launches successfully. It does not — `spctl --assess --type execute` returned `rejected` for the entire duration of Phase 5's testing, including after the app was working normally.
**Why it happens:** "It works now" is easy to misread as "it's approved now." These are different mechanisms (quarantine removal vs. Gatekeeper trust) and the app only ever achieves the former.
**How to avoid:** State this fact plainly in the Release notes (per CONTEXT.md's "Specific Ideas" — "应用能跑是因为不再被隔离，不是因为被 Gatekeeper 信任"), framed as expected/normal for an ad-hoc-signed, unsigned-by-Apple-Developer-ID app, not as a caveat or apology.
**Warning signs:** Docs language like "once approved" or "after Gatekeeper trusts the app" anywhere in the template.

### Pitfall 5: `release` job changes can only be smoke-tested, not fully verified, before a real tag push
**What goes wrong:** Assuming a green `workflow_dispatch` run proves the `body_path` addition renders correctly in a real Release body.
**Why it happens:** The `release` job's `if: startsWith(github.ref, 'refs/tags/')` guard means the job is always `skipped` on `workflow_dispatch` (branch ref, not a tag ref) — this has been true and observed since Phase 5 (`run 30402103536`, "release=skipped as designed"). A `workflow_dispatch` regression run can confirm the YAML parses and the job graph (`needs: [build, build-macos]`) is intact, but cannot confirm what the actual rendered GitHub Release body looks like.
**How to avoid:** Document this residual risk explicitly (as D-09's CONTEXT.md entry already does) rather than claiming full verification. If the planner chooses to fold Phase 5's outstanding UAT item (push a real `v*` tag) into this phase's end-to-end verification, that closes the gap for real — but it is a user-visible, irreversible action that must be called out, not silently assumed.
**Warning signs:** A plan or verification step that marks `body_path` rendering "verified" based only on a `workflow_dispatch` run.

## Code Examples

### D-04: quoting fix for `launch_app.py::build_quarantine_failure_message`
```python
# Source: launch_app.py (existing, to be modified per D-04 / WR-01)
# BEFORE (unquoted — breaks on paths with spaces, WR-01):
def build_quarantine_failure_message(bundle) -> str:
    target = quarantine_command_target(bundle)
    command = f"xattr -dr {QUARANTINE_ATTRIBUTE} {target}"
    ...

# AFTER (D-04's literal instruction — always double-quote the target):
def build_quarantine_failure_message(bundle) -> str:
    target = quarantine_command_target(bundle)
    command = f'xattr -dr {QUARANTINE_ATTRIBUTE} "{target}"'
    ...
```

### D-04: matching JS constant
```javascript
// Source: frontend/src/lib/macosGatekeeperNotice.js (existing, to be modified per D-04)
// BEFORE:
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app'

// AFTER:
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"'
```
Note: the existing test `macosGatekeeperNotice.test.js`'s assertion `assert.ok(targetPath.endsWith('.app'))` (after stripping the `xattr -dr com.apple.quarantine ` prefix) will need the trailing/leading quote character accounted for — either strip quotes before the `.app` suffix check, or assert on the full quoted literal.

### D-09: `body_path` addition to the release job
```yaml
# Source: .github/workflows/build-release.yml (existing `release` job, to be modified per D-09)
# Confirmed via softprops/action-gh-release's own README (raw.githubusercontent.com/softprops/action-gh-release/master/README.md):
#   "body_path: Path to load text communicating notable changes in this release"
#   "When providing a body and body_path at the same time, body_path will be attempted
#    first, then falling back on body if the path can not be read from."
#   "If body is specified, the body will be pre-pended to the automatically generated notes."
- name: Create GitHub Release
  uses: softprops/action-gh-release@v2
  with:
    files: release-assets/*
    body_path: .github/RELEASE_NOTES_TEMPLATE.md
    generate_release_notes: true
    name: "Open-Anti-Browser ${{ github.ref_name }}"
```
`generate_release_notes: true` is kept per D-09 — the auto-generated changelog appends after the template's hand-written content.

### Progressive-disclosure Gatekeeper steps (see Architecture Patterns Pattern 2 above for the full block)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DOCS-01/ROADMAP SC1: "System Settings → Privacy & Security → Open Anyway" as primary flow | "Double-click again" as primary flow, System Settings/xattr as fallback | 2026-07-28, per `05-06-SUMMARY.md`'s real-hardware first-launch decision-sequence capture | Every consumer of this text (release notes, dmg background, in-app notice) must be rewritten; the requirement/roadmap text itself must also be corrected, not just the eventual prose |
| `assets/dmg-background*.png` footer: "right-click the app icon → Open" | Must describe the measured "blocked once → double-click again" flow | Flagged as Open Item 2 in `05-06-SUMMARY.md`, explicitly deferred to Phase 6 | The current shipped assets (from 05-01, commits `382c6e2`/`8475af3`) are stale the moment 05-06's evidence came in; they were never wrong per Phase 5's own acceptance criteria (which only checked "no forbidden phrases"), but they are wrong relative to what actually happens |
| `LSMinimumSystemVersion` placeholder `12.0` → sampled `13.0` → fully-enumerated `15.0` | `15.0` is current and shipping | 05-04/05-05 (full Mach-O enumeration superseded the earlier 4-binary sample) | Documentation must cite macOS 15, not 12 or 13, as the floor |
| x64 dmg as a planned deliverable | x64 removed from v0.2 scope entirely | 2026-07-27 (`PROJECT.md` Key Decisions / Out of Scope) | DOCS-02's "双架构下载选择指引" framing no longer applies — rewrite as a single-architecture prerequisite check, not a choice |

**Deprecated/outdated:**
- ROADMAP SC3's "arm64 与 x64 分别原生验证" — half of this can never be satisfied without an x64 dmg; D-14 rewrites it to arm64-only.
- `softprops/action-gh-release@v2` — not deprecated for this phase's purposes (still functional, `body_path` fully supported), but the action's own maintainers have marked `v2.6.2` as the final `v2` release with no further support, recommending `v3`. Not in scope for this phase (see Standard Stack note above) — flagged for a future milestone.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "macOS < 15 会被系统拒绝打开" and "Intel Mac 无法运行 arm64 包" are accurate descriptions of what a user will actually see | User Constraints (D-08), Common Pitfalls #2 | If wrong (e.g., some other error surfaces, or the OS behavior differs from `LSMinimumSystemVersion`/architecture-mismatch semantics), users on unsupported hardware get confusing docs; D-08 already mandates conservative wording and explicit "not real-machine-tested" framing to bound this risk |
| A2 | `body_path` content is prepended before `generate_release_notes: true`'s auto-generated changelog, exactly as documented in `softprops/action-gh-release`'s README (cross-checked twice via WebFetch against the live README, MEDIUM confidence per this session's classify-confidence seam) | Code Examples (D-09 block), Common Pitfalls #5 | If the actual rendering order or interaction differs from the README's stated behavior, the hand-written Gatekeeper guidance could end up positioned oddly relative to the auto-changelog — but this can only be confirmed by a real tag push (Pitfall 5), which is out of this research's ability to test |
| A3 | The `.app` bundle path (`/Applications/Open-Anti-Browser.app`) never legitimately contains a double-quote character, so a naive `f'"{target}"'` wrap is sufficient without full shell-escaping | Code Examples (D-04 block), Common Pitfalls #3 | Extremely low probability (would require a user to rename the app or its parent folder to include a literal `"` character) — if it ever happened, the copy-pasted terminal command would silently fail; this is the same residual-risk class D-04 already accepts by choosing a fixed literal over full `shlex` escaping |

**Note:** All three assumptions above are LOW/MEDIUM risk and none contradicts a locked CONTEXT.md decision — they are refinements needed only because CONTEXT.md's decisions describe *what* to write, not the exact syntax of every code change.

## Open Questions

1. **Should the end-to-end verification (D-13/D-15) be performed against a real `v*` tag Release, or a `workflow_dispatch` artifact download?**
   - What we know: Phase 5 left an outstanding UAT item requiring a real tag push; a real tag push is the only way to exercise the `release` job's `body_path` rendering (Pitfall 5) and is also the only way to give the end-to-end verifier an authentic "download from the Release page" experience matching what a real user would see.
   - What's unclear: Pushing a `v*` tag triggers a real, user-visible release — CONTEXT.md's Deferred Ideas section explicitly flags this as "留给 plan-phase 定" (left to the planner).
   - Recommendation: The planner should treat this as a phase-level sequencing decision (likely: rewrite all docs/code first using a `workflow_dispatch` run only to validate YAML/job-graph integrity, then as a final gated step push the real tag once all prose is locked, use *that* Release for the human end-to-end checkpoint, and let it simultaneously close Phase 5's outstanding UAT item).

2. **Does the in-app Phase 4 notice's step count/structure need to match the progressive 3-step disclosure exactly, or can it stay 4 flat steps?**
   - What we know: The current `gatekeeper.step1`–`step4` are four flat, equally-weighted steps describing the (now-superseded) System-Settings-first flow. D-02 requires all three consumer surfaces to say the same thing; D-03 requires progressive disclosure with the primary path visually distinct from fallbacks.
   - What's unclear: Whether "same thing" means identical *content* (which double-click-first flow to describe) while allowing each surface to keep its own native structural idiom (the in-app notice is a modal dialog with an ordered list, not a collapsible Markdown block — `<details>` doesn't translate 1:1 into `buildGatekeeperNoticeHtml`'s DOM structure), or whether the in-app version must also visually de-emphasize the fallback steps (e.g., via a different CSS class or a "usually just this" annotation on step 1).
   - Recommendation: Content parity (all three describe "double-click again" as primary and same fallback order) is the D-02 requirement; the exact *rendering* mechanism (collapsible vs. plain ordered list) can differ per surface's native format — the planner should scope the in-app notice's task to "reorder/rewrite content to match the measured flow" without necessarily requiring a `<details>`-equivalent UI change, unless discuss-phase/planning decides the visual de-emphasis matters enough in the modal to warrant a small UI tweak.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `engines/chrome/Chromium.app` (headless screenshot capability) | Regenerating `assets/dmg-background.png`/`@2x` | ✓ (per 05-01, already vendored in repo tree during local dev) | 149.0.7827.114 (project's pinned fingerprint-chromium build) | None needed — this is a local-dev-only step, not required in CI |
| `sips`, `tiffutil`, `iconutil` | Verifying regenerated PNG dimensions and retina TIFF combination | ✓ (macOS built-in command-line tools) | OS-provided | None needed on macOS; not required on non-macOS dev machines since this step only runs when regenerating assets, which requires a Mac anyway |
| A second, clean macOS user account on real Apple Silicon hardware | D-13/D-15 end-to-end verification | Unconfirmed at research time — must be created by whoever executes the verification checkpoint | macOS 15.7 (matching 05-06's tested build, or newer per the 15.0 floor) | None — this is a hard requirement for DOCS-01/02's success criteria; no automated substitute exists (D-15 explicitly requires a human following only the shipped docs) |
| `gh` CLI or GitHub web UI access to push a `v*` tag and inspect the resulting Release | Open Question 1 (real end-to-end verification against a real Release) | Assumed available to whoever executes this phase (existing project maintainer with push access) | — | If tag-push access is unavailable to the executor, fall back to `workflow_dispatch`-only validation (YAML/job-graph correctness) and flag the `body_path` rendering as unverified, per Pitfall 5 |

**Missing dependencies with no fallback:**
- A genuinely clean macOS user account with no prior install of this app — this is a hard requirement of D-13/SC3 and has no automatable substitute.

**Missing dependencies with fallback:**
- Real `v*` tag push access — if unavailable, fall back to `workflow_dispatch`-only smoke testing of the `release` job's YAML/job-graph, with the `body_path` rendering explicitly documented as unverified (see Pitfall 5).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest` (backend/`launch_app.py` changes) + Node `node:test` (frontend `frontend/src/lib/*.js` changes) |
| Config file | none — matches CLAUDE.md's documented test commands exactly |
| Quick run command | `node --test frontend/src/lib/*.test.js` (frontend-only changes) or `python -m unittest tests.test_macos_desktop_runtime -v` (backend-only changes) |
| Full suite command | `python -m unittest discover -s tests -v` (note: most of this suite requires macOS-only imports per CLAUDE.md's "测试环境" section — the Python side of this phase's changes, `launch_app.py`, is one of the modules gated behind `pywin32`-free-but-`win32api`-adjacent imports; verify locally on a Mac before relying on CI) |

### Phase Requirement → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | `xattr` fallback command is quoted identically in JS constant, Python-rendered message, and the release notes template (D-04/D-12) | unit | `node --test frontend/src/lib/macosGatekeeperNotice.test.js` + `python -m unittest tests.test_macos_desktop_runtime.BuildQuarantineFailureMessageTests -v` + new cross-file assertion (D-12, exact file TBD by planner) | ✅ (first two exist and need updates) / ❌ Wave 0 (new D-12 three-way check) |
| DOCS-01 | i18n parity maintained after rewriting `gatekeeper.step1`–`step4` in both locales | unit | `node --test frontend/src/lib/i18n-parity.test.js` | ✅ (already covers the `gatekeeper.*` key set, 24-key list includes all `gatekeeper.step*` keys) |
| DOCS-01/DOCS-02 | Release notes render correctly with quoted command, progressive steps, and prerequisite checklist | manual_procedural | Human end-to-end verification on a clean macOS account (D-13/D-15) — no automated equivalent possible | ❌ Wave 0 (this IS the phase's success criterion, not a pre-existing gap) |
| DOCS-02 | dmg background footer text matches the measured first-run flow, contains no forbidden phrases (`spctl`, `sudo`, `--master-disable`, wide-directory recursion) | manual_procedural | Visual inspection + grep of the source HTML for forbidden phrases (05-01's own precedent — see `05-01-SUMMARY.md`'s "Forbidden-phrase audit") | ❌ Wave 0 (repeat of 05-01's audit technique on the regenerated HTML) |

### Sampling Rate
- **Per task commit:** `node --test frontend/src/lib/*.test.js` for any frontend/i18n change; `python -m unittest tests.test_macos_desktop_runtime -v` for any `launch_app.py` change
- **Per wave merge:** Full suite where feasible (`python -m unittest discover -s tests -v` — noting the macOS-only-import caveat from CLAUDE.md)
- **Phase gate:** Full suite green + the D-13/D-15 human end-to-end checkpoint passed, before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] New cross-file consistency test (D-12) — must read all three surfaces (JS constant, Python-rendered message, release notes template) and assert byte-identical `xattr` command text. Planner's discretion whether this lives in `tests/test_macos_desktop_runtime.py` (extend the existing `BuildQuarantineFailureMessageTests` class) or a new `node:test` file (both can read the Markdown template as plain text).
- [ ] Update `macosGatekeeperNotice.test.js`'s existing quoted-path assertions (currently expects no quotes) to match D-04's new format.
- [ ] Update `tests/test_macos_desktop_runtime.py`'s `test_non_translocated_bundle_message_points_to_its_own_path` and `test_translocated_scenario_matches_frontend_constant` literal-string expectations to include the new quotes.
- [ ] No test framework install needed — both `unittest` and `node:test` are already fully wired per CLAUDE.md's documented commands.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not applicable — no auth surface touched |
| V3 Session Management | no | Not applicable |
| V4 Access Control | no | Not applicable |
| V5 Input Validation | yes (narrowly) | The `shlex`/quoting fix in `build_quarantine_failure_message` is fundamentally an input-validation/output-encoding concern — the "input" is a filesystem path (usually fixed, occasionally the resolved bundle path) rendered into a copy-pasteable shell command string. D-04's fixed double-quote wrap is the standard control for this narrow case; see Common Pitfalls #3 for the boundary of what it does and doesn't cover. |
| V6 Cryptography | no | Not applicable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell command injection / argument splitting via unquoted paths containing spaces or shell metacharacters, when a generated command string is meant to be copy-pasted by a user into Terminal | Tampering (of the command a user unknowingly executes) | Quote the path before interpolating into the displayed/rendered command string (D-04); this is a *user-safety* concern (protecting the user from a broken/misdirected command), not a remote-attacker-controlled input — the path values here originate from the app's own resolved bundle location or a fixed constant, not from untrusted external input, so the risk class is "correctness/safety" rather than classic injection from an adversarial source |
| Social-engineering the user into disabling Gatekeeper globally, granting `sudo`, or recursively stripping quarantine from an overly broad directory (e.g. `~/Downloads` or all of `/Applications`) | Elevation of Privilege | Scope every terminal command shown to the user to a single, named `.app` bundle; never include `spctl --master-disable`, `sudo`, or a recursive operation on a directory wider than the one app bundle. This is already Phase 4/5's established safety boundary (`T-05-01`/`T-05-25` in `05-01-PLAN.md`'s threat table) and must be preserved verbatim in every new surface this phase adds (the release notes template and the regenerated dmg background) |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/05-ci/05-06-SUMMARY.md` — real-hardware first-launch decision sequence, exit-path behavior, `spctl` status, all directly measured on macOS 15.7 (24G222) with timestamped `syspolicyd`/`amfid`/kernel logs
- `.planning/phases/05-ci/05-REVIEW.md` (WR-01, WR-02) — exact quoting/translocation defects in `launch_app.py`'s fallback message
- `.planning/phases/05-ci/05-04-SUMMARY.md`, `.github/workflows/build-release.yml` (line 258, `LSMinimumSystemVersion="15.0"`) — full Mach-O enumeration measurement of the minimum-OS floor, currently shipping
- `.planning/PROJECT.md` (Out of Scope, Key Decisions) — x64 removed from v0.2 on 2026-07-27
- `.planning/phases/05-ci/05-01-SUMMARY.md`, `05-01-PLAN.md` — exact process and safety boundary already used to generate the current (stale-content, correct-process) dmg background assets
- Direct repository reads: `launch_app.py`, `frontend/src/lib/macosGatekeeperNotice.js` (+ its test), `frontend/src/i18n/{zh-CN,en-US}.js`, `README.md`/`README_EN.md`, `.github/workflows/build-release.yml`, `tests/test_macos_desktop_runtime.py`

### Secondary (MEDIUM confidence)
- `raw.githubusercontent.com/softprops/action-gh-release/master/README.md` — fetched twice via WebFetch, cross-checked and internally consistent both times; confirms `body_path` semantics (attempted first, falls back to `body`; prepended before `generate_release_notes`'s auto-changelog) and that `v2.6.2` is the final, no-longer-maintained `v2` release with `v3` recommended (not adopted in this phase's recommendations — see Standard Stack note)

### Tertiary (LOW confidence)
- None — this phase's domain is narrow enough, and Phase 5's real-hardware evidence thorough enough, that no claim in this document rests on unverified web search alone.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new tools; every piece (Markdown, `softprops/action-gh-release@v2`, headless-Chromium screenshot method, `unittest`/`node:test`) is already in active use in this repo, verified by direct file reads
- Architecture: HIGH — the "three consumer surfaces must agree, one source of truth" pattern is an extension of a pattern (05-02's cross-language literal lock) already proven twice in this codebase
- Pitfalls: HIGH — every pitfall traces to a specific, dated, already-written artifact in `.planning/phases/05-ci/` (SUMMARY/REVIEW files), not to speculation

**Research date:** 2026-07-30
**Valid until:** No fixed expiry — this research is tied to Phase 5's specific measured evidence (real hardware, specific macOS build 24G222) rather than a fast-moving external dependency; it should be re-validated only if Phase 5's artifacts are themselves revised, or if a future milestone reintroduces x64 (see Deferred Ideas), at which point DOCS-02 reverts toward its original "双架构选择指引" form.
