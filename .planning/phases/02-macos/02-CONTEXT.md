# Phase 2: macOS 内核构建与发布 - Context

**Gathered:** 2026-07-24
**Status:** Ready for planning

<domain>
## Phase Boundary

把 fingerprint-chromium 149.0.7827.114 的 macOS **arm64** 与 **Intel x64** 两个内核作为 kernel release 资产发布出来,让 macOS 用户/后续 CI 能下载到。覆盖需求 KERNEL-01、KERNEL-02、KERNEL-03。

**关键边界澄清(本次讨论锁定):** Chromium 内核的**构建、交叉编译、lipo/file 架构验证、启动冒烟**这些工作**全部归属兄弟仓库 `../fingerprint-chromium`**(那里才有 27G 的构建树和独立的 GSD 流程)。**本仓库 Phase 2 的实际职责收窄为两件事:**
1. 拿到兄弟仓库产出的两个 ditto zip,**上传前在本仓库再做一道把关验证**(file/lipo 架构 + Rosetta 启动冒烟),然后上传到 kernel release;
2. 在 `backend/config.py` 回填 macOS arm64/x64 的内核下载 URL(Phase 1 D-05 已为此留了占位)。

**不在本 phase:** macOS Chrome 实际启动链路(Phase 3)、capabilities API(Phase 3/XPLAT-05)、前端门控(Phase 4)、CI dmg 打包(Phase 5)。x64 的 downloads-macos-x64.ini 补齐与交叉编译本身**不在本仓库**(在兄弟仓库)。

</domain>

<decisions>
## Implementation Decisions

### 补丁基线与 arm64 重建
- **D-01:** Mac 内核资产采用 **021 补丁基线**(含熵门控 canvas/WebGL 噪声改进,过红盒检测,已经兄弟仓库 Phase 07 CDP 回归验证),直接用兄弟仓库现有的 `build/src/out/Default` arm64 build,**不回退到 020** 去对齐现有 Windows -1.2 资产。短期内 Mac(021)与 Windows(020)指纹行为不一致,等兄弟仓库 Phase 08 发布 Windows 021 后自然对齐。 — **Reversibility:** costly — 021 是兄弟仓库整个 v1.2 里程碑的产出,回退到 020 需要 quilt 大重建并放弃熵门控能力。
- **D-02:** 发布前必须**移除 021 补丁里的 LOG(INFO) 校准诊断行再增量重建**。兄弟仓库 07-01-SUMMARY.md 已把这行诊断记为「Phase 8 打包前必须移除或 DLOG 保护」的禁令(is_official_build 树里 DLOG 是 no-op,当前是裸 LOG(INFO),会向 stderr 打每帧 canvas 校准信息)。只改一个 .cc,热树增量重建+重链,非全量,成本可控。这条重建动作发生在**兄弟仓库**,本仓库拿到的是重建后的干净产物。

### x64 交叉编译的归属与验证
- **D-03:** downloads-macos-x64.ini 补齐、flags 改 `target_cpu="x64"`、交叉编译、lipo/file 架构验证**全部在兄弟仓库 `../fingerprint-chromium` 完成**——那里有构建树和独立 GSD。本仓库不驱动跨仓库构建。 — **Reversibility:** reversible — 纯职责划分,不产生本仓库代码。
- **D-04:** x64 内核的启动冒烟测试在**当前 arm64 Mac 走 Rosetta 2** 完成即可;Intel 真机原生启动验证留到 Phase 6 端到端验证,不在本 phase 卡 Intel 硬件。
- **D-05:** 本仓库 Phase 2 职责边界 = **上传两个内核 zip 到 kernel release + 回填 config.py 的 macOS arm64/x64 URL(平台分支)**。构建/lipo/冒烟归兄弟仓库 GSD,本仓库只在上传前把关并验收资产可下载(见 D-09)。 — **Reversibility:** reversible。

### 打包格式与资产命名
- **D-06:** Mac 内核资产**只出 ditto zip**(每架构一个,ditto 打包保符号链接 + ad-hoc 签名),**不出 installer/pkg 变体**。Windows 的 installer.exe 是给独立安装用,Mac 侧 dmg(Phase 5)自带安装流程,内核只需 zip 供 CI 下载注入 .app。
- **D-07:** 文件名**对齐 Windows 命名模式**:`ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` 与 `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip`(现 Windows 资产为 `..._windows_x64.zip`)。格式 = 版本 + revision + 平台 + 架构,config.py 拼 URL 与 Windows 分支同构。
- **D-08:** revision 号用 **`-1.3`** 标识 021 基线,明确区分于 kernel release 里 Windows 现有的 `-1.2`(020 补丁)。等兄弟仓库 Phase 08 发布 Windows 021 时也用 `-1.3` 对齐,避免「同 revision 号不同补丁内容」的追溯混乱。 — **Reversibility:** costly — revision 号一旦写入 config.py URL、资产文件名并公开发布,改名需同步 config.py + 重传资产 + 通知兄弟仓库对齐。

### 验证深度与发布流程
- **D-09:** 上传前**本仓库对拿到的两个 zip 再做一道把关验证**:解压 → file/lipo 确认各自架构匹配 → 启动冒烟(x64 走 Rosetta)。即使兄弟仓库已验过,本仓库仍在上传环节二次把关,防跨仓库传输/解压环节的架构错配(对齐 KERNEL-03「上传前验证」口径)。
- **D-10:** 上传 kernel release + 把关验证**做成仓库内脚本**(解压 → file/lipo 验证 → Rosetta 冒烟 → `gh release upload` 到 `kernel-149.0.7827.114`),可重复、可审计,后续出新 revision 直接复用;不采用「只写文档步骤 + 手动跑」。
- **D-11:** 上传+验证脚本**入仓**。它是 kernel release 发布工具,与 CLAUDE.md 中约定 gitignore 的**应用安装包打包脚本**(build_installer.ps1 / dmg 打包)属于不同类别,进仓便于审计与复用。planner/executor 需在实现时明确这一区分,避免与现有「打包脚本不入仓」约定冲突。 — **Reversibility:** reversible。

### Claude's Discretion
- 上传/验证脚本的具体语言与落点(如 `scripts/` 下的 bash;shell 用法参考仓库既有约定)、file/lipo 与 Rosetta 冒烟的具体命令组织。
- config.py 里 macOS URL 的平台分支写法(沿用 Phase 1 D-05 已确立的平台感知结构;macOS arm64/x64 两条 URL 的常量命名)。
- Rosetta 冒烟「启动成功」的判定粒度(能拉起进程 / 能响应 CDP 端口等),只要满足 KERNEL-03 的启动冒烟语义即可。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与范围(本仓库)
- `.planning/ROADMAP.md` — Phase 2 目标与 3 条成功标准(注意:成功标准原文把「构建/lipo/冒烟」也写进 Phase 2,本次讨论 D-03/D-05 已澄清这些归兄弟仓库,本仓库只负责上传+回填+上传前把关)
- `.planning/REQUIREMENTS.md` — KERNEL-01 / KERNEL-02 / KERNEL-03 验收条件
- `.planning/PROJECT.md` — v0.2 约束(内核只在本地 Mac 构建、以 release 资产分发;CI 从 config.py 读 CHROME_ENGINE_ZIP_URL 单一事实来源)与 Key Decisions
- `.planning/phases/01-backend-cross-platform/01-CONTEXT.md` — D-05:config.py 平台感知路径解析,macOS 内核下载 URL 已留占位待本 phase 回填

### 工程约定(本仓库)
- `CLAUDE.md` — commit message 约定;打包脚本 gitignore 约定(D-11 需与之区分);backend/_g.py 完整性校验注意(本 phase 不碰 openSourceNotice.js / App.vue,无哈希更新需求)
- `backend/config.py:105-140` — `_CHROME_KERNEL_BASE` / `CHROME_ENGINE_ZIP_URL` / `ENGINE_METADATA`,D-05/D-07/D-08 的回填落点;kernel release base 为 `kernel-149.0.7827.114`

### 兄弟仓库(../fingerprint-chromium,构建产物来源)
- `../fingerprint-chromium/.planning/phases/07-021-mac-oab/07-01-SUMMARY.md` — 021 熵门控补丁、LOG(INFO) 校准行禁令(D-02 依据)、arm64 已构建并 CDP 验证
- `../fingerprint-chromium/.planning/phases/07-021-mac-oab/07-02-SUMMARY.md` — kMaxDistinctColors=32 锁定、回归验证 regression-cdp.js、tampering 行为说明
- `../fingerprint-chromium/downloads-macos-arm64.ini` — arm64 工具链下载清单(已备齐;x64 版待兄弟仓库补 downloads-macos-x64.ini)
- `../fingerprint-chromium/flags.macos.gn` — macOS 构建 flags(现 `target_cpu="arm64"`;x64 交叉编译需改)
- `../fingerprint-chromium/build/src/out/Default/Chromium.app` — 现有 arm64 build 产物(149.0.7827.114,ad-hoc linker-signed,Framework 二进制 mtime 2026-07-22)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/config.py` 的 kernel URL 已是单一事实来源:`_CHROME_KERNEL_BASE` 拼 `CHROME_ENGINE_ZIP_URL`,`.github/workflows/build-release.yml:62` 通过 `python -c "from backend.config import CHROME_ENGINE_ZIP_URL"` 读取。macOS URL 回填沿用同结构,Phase 5 CI macOS job 也从 config.py 读。
- 现有 kernel release `kernel-149.0.7827.114` 已存在(含 Windows -1.1/-1.2 的 installer.exe + zip 四个资产)。Mac 资产上传到**同一个 tag**,无需新建 release。
- `gh release upload` 是现成上传机制(仓库已用 gh CLI 管理 release)。

### Established Patterns
- 平台路径/常量统一收敛在 `backend/config.py`(Phase 1 已确立平台感知结构);macOS URL 回填必须走 config.py,不在别处拼路径。
- ditto 打包保符号链接 + ad-hoc 签名是兄弟仓库既定的 Mac 内核打包方式(KERNEL-01 写死),本仓库上传的就是这种 zip。

### Integration Points
- config.py 的 macOS URL → Phase 3 macOS Chrome 启动链路(需要内核可下载/已安装)、Phase 5 CI macOS job(下载内核注入 .app)都消费这个 URL。
- 本 phase 依赖兄弟仓库先产出两个内核 zip(arm64 build 已就绪;x64 需兄弟仓库补 downloads-macos-x64.ini 并交叉编译)——STATE.md 已记此为跨仓库 blocker,进度不在本仓库掌控。

</code_context>

<specifics>
## Specific Ideas

- 资产命名精确样例:`ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip`、`ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip`。
- 现有 arm64 build 事实:`Chromium.app/Contents/MacOS/Chromium` 为 Mach-O arm64、版本 149.0.7827.114、adhoc + linker-signed;Framework 二进制 mtime 为 2026-07-22(即含 021 的那次重建)。D-02 的「移除校准行再重建」会在此基础上再增量重建一次。
- x64 冒烟走 Rosetta 是因为用户手头只有 arm64 Mac;Intel 原生验证明确推迟到 Phase 6。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope。

**跨 phase 备忘(非新增 scope,仅提示 planner):**
- 兄弟仓库 Phase 08(Windows 021 重打包)一旦发布,应回来把 Windows 资产 revision 也对齐到 -1.3(D-08),使 Windows/Mac 同基线同 revision——这属于发布协调,不是本仓库 Phase 2 的交付项。
- ROADMAP Phase 2 成功标准 3 里的「构建/lipo/冒烟」措辞与本次 D-03/D-05 边界收窄存在口径差异;verifier 校验本 phase 时应以「本仓库负责上传前把关 + 回填,构建归兄弟仓库」为准,而非要求本仓库内完成 Chromium 构建。

</deferred>

---

*Phase: 2-macOS 内核构建与发布*
*Context gathered: 2026-07-24*
