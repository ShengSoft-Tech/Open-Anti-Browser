# Phase 5: CI 打包发布 - Research

**Researched:** 2026-07-28
**Domain:** macOS 应用打包(PyInstaller）+ 嵌套 bundle ad-hoc 签名 + dmg 制作 + GitHub Actions 多 job 发布汇合
**Confidence:** HIGH（P0 高风险项已在本机 arm64 Mac 上用真实内核 / 真实 dmg / 真实 Finder 操作逐项实测验证）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CI workflow 结构与 Release 汇合(PKG-01 / PKG-05)**

- **D-01:** macOS job **加进现有 `.github/workflows/build-release.yml`**(新增 `build-macos` job,与现有 windows `build` job 并行),不新开独立 workflow。同一 tag 一次触发两平台,日志/状态集中,也才有条件做统一汇合 job。 — **Reversibility:** reversible — 拆回独立 workflow 只是搬运 job 定义。
- **D-02:** **新增第三个 `release` 汇合 job** 统一建 Release:`build`(windows)与 `build-macos` 两个 job 都**只做 `upload-artifact`**;`release` job(`needs: [build, build-macos]`)下载全部 artifact 后**一次性**调 `softprops/action-gh-release`。这意味着**要把 Windows job 末尾现有的 gh-release 步骤移走**——Windows 的**构建逻辑**逐字不动,只是发布时机从 job 内后移到汇合 job。理由:两个 job 各自调 gh-release 存在并发创建同一 release 的竞态。 — **Reversibility:** costly — Windows 发布路径是已上线的 v0.1.x 发版通道,改动需连同 Windows 一起回归验证(至少走一次 `workflow_dispatch` 确认 artifact 齐全)。
- **D-03:** **全成功才发**:`release` job 依赖两个 build job,任一失败即不建 Release,不发「只有一半包」的版本。不使用 `continue-on-error` / `if: always()`。修好后重推 tag 即可。 — **Reversibility:** reversible。
- **D-04:** **调试通道复用现有 `workflow_dispatch`**,不引入 rc/pre-release tag、不新增机制。手动触发时两个 build job 正常跑并传 artifact,`release` job 保留 tag 守门(沿用现有 `if: startsWith(github.ref, 'refs/tags/')` 语义)因而不建 Release。macOS 打包链路的迭代靠下载 Actions artifact 验证。 — **Reversibility:** reversible。

**.app 构建声明与 Info.plist(PKG-02)**

- **D-05:** **纯内联 pyinstaller CLI + 构建后 `plutil`/`PlistBuddy` 补键**,不引入 `.spec` 文件。macOS job 沿用与 Windows 同构的内联 CLI(`--windowed --icon assets/app.icns --osx-bundle-identifier ...`),CLI 覆盖不到的 Info.plist 键(`CFBundleShortVersionString`、`CFBundleName`/`CFBundleDisplayName`、`NSHighResolutionCapable`、`LSMinimumSystemVersion` 等)在构建完成后写入 `Open-Anti-Browser.app/Contents/Info.plist`。选此形态是为了**不动 `.gitignore:23` 忽略 `*.spec` 的现有约定**,也保持两平台命令行风格一致。 — **Reversibility:** reversible — 改成 .spec 只需搬运声明并在 .gitignore 开白名单。
  - **注意时序:** 补 plist 的动作必须发生在**签名之前**(改 Info.plist 会使已有签名失效),与 D-10 的签名顺序联动。
- **D-06:** **`assets/app.icns` 本地生成并入仓**,与现有 `assets/app.ico` 并列;CI 只负责引用,不在 CI 里现生成。本地用 `sips` + `iconutil` 从 `assets/logo-512.png` 生成完整 iconset(16~512 含 @2x;源图仅 512px,1024 档位按实际质量取舍),图标效果可提前肉眼确认,CI 无额外依赖。 — **Reversibility:** reversible。
- **D-07:** **macOS 保留菜单栏(托盘)图标,只单独修 Cmd+Q**。现状:`launch_app.py:298` 设 `setQuitOnLastWindowClosed(False)`,`closeEvent`(:267-279)在托盘存在时 `hide()` + `event.ignore()`——macOS 上 Cmd+Q 正是走 closeEvent,会被吞掉,直接违反 ROADMAP SC2「Cmd+Q 可正常退出」。方案:macOS 上**仍创建 `QSystemTrayIcon`、关窗仍最小化到菜单栏**(保住「后台常驻管理已启动浏览器」的能力),**另接一条 Cmd+Q 路径**(`QEvent.Quit` / `QApplication.aboutToQuit` 一类信号)直接走 `force_exit()`,使 `_force_exit=True` 后 `closeEvent` 走正常 shutdown 分支。**Windows 行为逐字不变**(平台条件分支)。 — **Reversibility:** reversible — 局部改 `launch_app.py`。
- **D-08:** **版本号以 tag 为准 + 加一道一致性校验**。dmg 文件名与 `CFBundleShortVersionString` 都从 `github.ref_name` 去掉前导 `v` 取(与 Windows Inno Setup 现有 `$v = ref_name -replace '^v'` 做法同构);**另在 CI 加一步校验** tag 版本与 `frontend/package.json` + `backend/main.py`(两个 FastAPI `version`)一致,不一致即 fail。防止发出「包名 0.2.0 但应用内显示 0.1.16」。当前仓库三处均为 `0.1.16`,发 v0.2.0 前需按 CLAUDE.md 约定同步改。 — **Reversibility:** reversible。

**dmg 外观与资产(PKG-04)**

- **D-09:** dmg 用 **`create-dmg`**(macOS runner 上 `brew install create-dmg`),不手写 `hdiutil` + AppleScript。理由:背景图、图标坐标、窗口尺寸、Applications 别名一条命令声明完;AppleScript 在 headless CI 里摆 Finder 窗口位置出了名的脆。 — **Reversibility:** reversible。
- **D-10:** **`assets/dmg-background.png` 由 Claude 生成并入仓**(用户明确授权,不满意可直接替换)。内容 = **拖拽引导(应用图标位 → 箭头 → Applications 位)+ 底部一行放行提示**(如「首次打开请右键 → 打开」)。含 `@2x` retina 版。理由:未签名 `.app` 双击必被拦,背景图是用户看到的第一屏,在拦截发生前就告知比让他去翻 Release notes 有效;与 Phase 6 的 DOCS-01 是**互补的不同载体**,不重复不合并。 — **Reversibility:** reversible。
- **D-11:** dmg 文件名**保留架构后缀**:`Open-Anti-Browser-{version}-arm64.dmg`(如 `Open-Anti-Browser-0.2.0-arm64.dmg`)。虽然 v0.2 只出 arm64,带后缀可与 ROADMAP SC4 原文一致,并保证将来恢复 x64 时历史包不会出现「同名不同架构」。 — **Reversibility:** costly — 一旦公开发布,改名会让已发布链接失效。

**签名策略、quarantine 与 CI 门禁(PKG-03 / PKG-05)**

- **D-12:** **首启时对应用自身 bundle 整体剥离 quarantine**。背景:用户从 dmg 拖到 `/Applications` 后整个 `.app`(**含内部内核**)都带 `com.apple.quarantine`;Phase 3 D-07 已在真机实证——带 quarantine 的 ad-hoc arm64 内核**裸 exec 会被 AMFI 直接 kill(exit 137)**,不是弹 Gatekeeper 对话框,且必须剥**整个 bundle**(framework dylib / helper 也带 quarantine)。方案:应用启动时对自己所在的 `.app` 跑一次 `xattr -dr com.apple.quarantine`,**失败则弹窗把命令原样给用户**让其手动执行。保持「内核就在包里、安装即用」不变(不改成首启复制到可写目录)。 — **Reversibility:** costly — 若权限/路径场景走不通,退路是把内核首启解到 `~/Library/Application Support/Open-Anti-Browser/engines/`,那会改动 `config.py` 的 `ENGINES_DIR` 解析并影响 Phase 1/3 已锁定的路径决策。
  - **researcher/planner 必须查证的两个前提:**
    1. **App Translocation** —— 从 dmg 里**直接双击运行**时,macOS 会把 `.app` 搬到只读随机路径(`/private/var/folders/.../AppTranslocation/`),此时自剥离必然失败。需确认「先拖到 Applications 再运行」是否足以规避,以及 dmg 背景图/首启提示要不要显式引导这一步。**（本 RESEARCH.md 已用真机实测回答此问题，结论是"不足以规避"，见 Assumptions Log A1 与 Pitfall 4）**
    2. **写权限** —— admin 用户对 `/Applications` 可写;非 admin 用户或企业受管 Mac 可能不可写,此时剥离失败路径(弹窗给命令)就是唯一兜底,文案必须给出可直接复制的完整命令。
  - **与 Phase 4 UI-04 的关系:** Phase 4 已做了应用内 Gatekeeper 放行指引(`macosGatekeeperNotice.js`,key `oab:macos-gatekeeper-notice:v1`,`GATEKEEPER_XATTR_COMMAND` 为模块常量)。D-12 的失败兜底文案**应复用/对齐该模块**,不另起第三套措辞。
- **D-13:** 内核经 `ditto` 注入 `.app` 后,**由内向外逐层 ad-hoc 签名**,不用 `codesign --force --deep --sign -` 一把梭。顺序:先签嵌套的 `Chromium.app` 及其 helper/framework → 再签 PySide6/QtWebEngine 的 framework → 最后签外层 `Open-Anti-Browser.app`。理由:`--deep` 签名已被 Apple 弃用且在嵌套 bundle 上行为不可靠(可能漏签 helper),逐层签在失败时还能定位到具体 bundle。 — **Reversibility:** reversible。**（本 RESEARCH.md 已用真机实测验证此顺序有效，并发现"仅验外层不够，必须内外分别验证"这一额外要求，见 Pitfall 2/3）**
- **D-14:** **CI 硬门禁 = 静态校验 + 真起一次冒烟**,不止 `codesign --verify --deep --strict`。至少包含:
  1. `codesign --verify --deep --strict`(PKG-03 明文要求),失败即中止发布
  2. 断言 `.app` 内内核二进制存在且为 **arm64**(`file`/`lipo`,沿用 Phase 2 已建立的架构断言口径)
  3. 断言 `frontend/dist` 已正确进包(`backend/_g.py` 运行时校验 `_6` 读 `FRONTEND_DIST_DIR` 的 marker 字符串,dist 缺失则运行时静默跳过、marker 被改则拒启动)——PKG-05 的完整性校验落点
  4. **后台启一次 `.app` 内的二进制**,确认本地服务端口能起来(GUI 部分在 headless runner 上能跑到什么程度由 planner 按实测定)
  理由:「签名过了但一启动就挂」(缺依赖 / QtWebEngine 摆不平 / `_g.py` 拒启)是这类打包最典型的失败模式,只有真起一次才拦得住。 — **Reversibility:** reversible。
- **D-15:** **本 phase 末尾设一个真机安装 checkpoint plan**(沿用 Phase 4 `04-06-PLAN.md` 的人工验收 plan 模式):CI 产出 dmg 后,在用户的 arm64 Mac 上走完 下载 → 拖到 `/Applications` → 双击 → 观察是否被拦 / 能否启动 → 启一个 Chrome 配置。这是验证 D-12 自剥离方案**真的有效**的唯一手段,现在发现问题比 Phase 6 便宜。与 Phase 6 的区别:本 checkpoint 只验「包能不能装能不能跑」,Phase 6 验「用户仅凭发布文档能否自助完成全流程」。 — **Reversibility:** reversible。**（本 RESEARCH.md 的实测结果强烈建议 D-15 的验收脚本把"首次双击是否出现 quarantine 剥离失败提示"作为预期且必须记录的现象，而非异常）**

### Claude's Discretion

- `create-dmg` 的具体参数(窗口尺寸、图标坐标、卷标名)、背景图的确切配色/尺寸/中英文措辞。
- bundle identifier 取值、`LSMinimumSystemVersion` 取值、iconset 各档位清单。
- Cmd+Q 接管的具体 Qt 实现手段(`QEvent.Quit` 重载 vs `aboutToQuit` 连接 vs 原生菜单项),只要满足 D-07 的「保留菜单栏图标 + Cmd+Q 能退 + Windows 不变」。
- 版本一致性校验步骤的实现位置与写法(独立 job vs build job 内首步)。
- CI 冒烟的具体判定粒度(进程存活 / HTTP 端口响应 / `/api/bootstrap` 返回 200)。
- macOS job 里 `engines/` 目录的组织方式,以及 Windows CLI 里 `--hidden-import ruyipage` 等 Windows-only 参数在 macOS 侧的取舍(`ruyipage` 在 macOS 未安装,见 `requirements.txt` 的 `sys_platform` 标记)。
- `.app` 冻结态下 `sys._MEIPASS` 落点(PyInstaller 6.x 把数据放 `Contents/Frameworks`)与 `config.py:ENGINES_DIR`/`FRONTEND_DIST_DIR` 解析的对齐方式——**若发现需要改 `config.py`,属实现裁量,但必须保持 Windows 路径值逐字不变**(Phase 1 D-05~D-08)。**（本 RESEARCH.md 已用真机实测确认：不需要改 config.py，见 Architecture Patterns Pattern 1）**

### Deferred Ideas (OUT OF SCOPE)

None — 讨论未越界。

**跨 phase 备忘(非新增 scope,仅提示 planner):**
- x64 dmg / matrix / 双架构下载指引:已于 2026-07-27 移出 v0.2,本 phase 一律不做。x64 内核资产在 `kernel-149.0.7827.114` 备好,`config.py:CHROME_ENGINE_ZIP_URL_MACOS_X64` 常量也已存在,后续里程碑恢复时主要是加 matrix 分支。
- Release notes 分步放行说明与「怎么判断自己是 Apple Silicon 还是 Intel」的下载指引 = DOCS-01/DOCS-02,**Phase 6**。本 phase 的 dmg 背景图放行提示(D-10)是**另一载体**,内容可呼应但不合并、不代替。
- Apple Developer ID 签名 + 公证(DIST-01)、应用内自动更新(DIST-02):Future Requirements,不在 v0.2。
- 若 D-12 的自剥离方案在真机 checkpoint(D-15)被证伪,退路是「首启把内核解到 `~/Library/Application Support/Open-Anti-Browser/engines/`」——那会触及 Phase 1 已锁定的 `config.py` 路径决策,届时需作为**新的一次决策**处理,不由 executor 自行改道。**（本 RESEARCH.md 的真机实测结果显示"首启自剥离在架构上几乎不可能成功"，这不完全等同于 CONTEXT.md 原文预设的"若被证伪"的假设性语气——建议 discuss-phase/planner 阶段重新确认这条退路是否需要提前纳入本 phase 而非等 D-15 checkpoint 才触发，见 Assumptions Log A1）**

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| PKG-01 | 推送 v* tag 触发 CI macOS job(arm64=macos-15),与现有 Windows job 并行 | Architecture Patterns 的 System Architecture Diagram 给出完整三 job 拓扑(build / build-macos / release);Standard Stack 列出 upload-artifact v4 + download-artifact v4 的汇合写法;Sources 引用官方迁移文档确认 `pattern`+`merge-multiple` 语法 |
| PKG-02 | PyInstaller 产出真正的 .app bundle(BUNDLE + Info.plist + .icns:菜单栏/Dock 显示正确应用名与图标,Cmd+Q 正常退出) | Pattern 1(真实布局实测)、Pattern 3(Info.plist `plutil -replace` 幂等补丁,已实测哪些键 PyInstaller 自动设置、哪些需要手工补)、Pattern 4(`.icns` 生成命令序列,含 Pitfall 5 的 iconutil 静默放行踩坑)、Common Pitfalls 关于 Cmd+Q 的 Qt `QEvent.Quit` 拦截方案(WebSearch 交叉确认的标准做法) |
| PKG-03 | 内核经 ditto 注入 .app 后整体 ad-hoc 重签,CI 内 `codesign --verify --deep --strict` 作为硬门禁 | Pattern 2(真实内核逐层签名命令序列,已实测通过)、Pitfall 2/3(揭示"仅验外层不够"与"内核资产本身天生不满足 bundle 级验证"两个关键陷阱)、Code Examples 给出可直接抄的签名+双重验证脚本骨架 |
| PKG-04 | dmg 含 .app + Applications 别名 + 自定义拖拽安装背景图,文件名含版本与架构 | Standard Stack 的 create-dmg 版本/来源核实、Package Legitimacy Audit、本机真实 dmg 制作实测(含签名在 dmg 打包前后保持一致的验证) |
| PKG-05 | 两个 dmg 与 Windows 安装包挂到同一 GitHub Release;backend/_g.py 完整性校验在 macOS 构建与启动中保持有效 | System Architecture Diagram 的 release 汇合 job 设计、Pattern 1 对 `_g.py._6()` 依赖的 `FRONTEND_DIST_DIR.rglob()` 透过符号链接正常工作的直接实测确认、Code Examples 的 `--backend-only` 冒烟脚本(覆盖"签名过了但启动时被 `_g.py` 拒启"这类失败模式) |

*(注:ROADMAP/REQUIREMENTS 原文里 PKG-01 的"matrix:arm64/x64"与 PKG-04 的"两个 dmg"措辞按 2026-07-27 的 arm64-only scope 变更告示读,本表已按 arm64-only 口径对应。)*
</phase_requirements>

## Summary

本 phase 的技术核心不是"能不能用 PyInstaller 打出 .app"——这一步很简单——而是三个互相关联的深坑：(1) PyInstaller 6.x 在 macOS onedir 模式下的真实数据布局是否与 `backend/config.py` 现有的 `sys._MEIPASS` 逻辑兼容；(2) 内嵌一个"自己就是完整 .app bundle"的第三方内核（Chromium.app，内含 4 个 Helper.app 与 1 个 Framework）该如何签名才能通过 `codesign --verify --deep --strict`；(3) D-12 设想的"应用自剥离 quarantine"方案在真实的 App Translocation 机制下是否真的可行。

本次研究在本机 arm64 Mac 上用真实的 pyinstaller 6.21.0、真实的 `engines/chrome/Chromium.app`（367MB，仓库既有资产，只读使用）、真实的 dmg（用 `hdiutil` + AppleScript 驱动 Finder 模拟用户拖拽）做了完整实测，而非停留在文档推理层面。三个最关键的实测结论：

1. **PyInstaller 布局与 config.py 完全兼容，零改动**：`sys._MEIPASS` 指向 `Contents/Frameworks`，该目录下 `assets/engines/frontend` 是指向 `../Resources/xxx` 的符号链接，真实文件躺在 `Contents/Resources/`。Python 的 `Path.exists()` / `Path.rglob()` 都会透明穿透这层符号链接，`backend/_g.py` 的 `_6()` 完整性校验（`FRONTEND_DIST_DIR.rglob(...)`）经实测可以正常读到打包后的 marker 字符串。**Claude's Discretion 里"可能需要改 config.py"的顾虑可以解除：不需要改。**

2. **`codesign --verify --deep --strict` 在嵌套 bundle 场景下会撒谎**：仓库里现成的、已经是 ad-hoc + linker-signed 状态的 `Chromium.app`，单独对它跑 `codesign --verify --deep --strict` 会直接失败（`code has no resources but signature indicates they must be present`）——**这是内核资产本身固有的状态，不是注入过程搞坏的**。更反直觉的是：如果图省事在外层用一把梭的 `codesign --force --deep --sign -`，外层校验居然会显示 `valid on disk` 通过，但内层 `Chromium.app` 的签名其实完全没被 `--deep` 碰过（哈希值实测前后一致）。也就是说 **D-13 坚持的"由内向外逐层签"不是洁癖，是唯一能让 CI 硬门禁真正生效的做法**；必须额外单独对嵌套的 `Chromium.app` 也跑一次 `codesign --verify --deep --strict`，光验外层不够。

3. **D-12 的核心假设被推翻：App Translocation 与目录无关，"先拖到 /Applications 再运行"不能避免自剥离在首次启动时失败**。本次用真实 dmg + AppleScript 驱动 Finder 做"移动到 /Applications"操作后首次 `open`，进程实测仍然跑在 `/private/var/folders/.../AppTranslocation/<uuid>/d/...` 这个只读 nullfs 挂载点下——不论目标目录是临时文件夹还是真实 `/Applications`，只要 quarantine 属性还在、且这是该 quarantine 事件的首次 `open` 调用，就会被搬迁；搬迁后的视图**整体只读**，应用自身对自己（哪怕换算出真实路径去操作）跑 `xattr -dr` 全部返回 `Operation not permitted`。唯一能让 `xattr -dr` 成功的时机是**在应用第一次被 LaunchServices 打开之前**——这在架构上是应用自身代码不可能触达的时间点。详见下文 P0-3/P0-4 与 Assumptions Log A1。

**Primary recommendation:** 沿用 D-01~D-15 的整体路线，但对 D-12 的实现预期做一处关键修正——把"自剥离成功"当成极少数情况（例如用户此前已用终端命令手动剥过一次）而非首次启动的常态路径，UI-04 的弹窗兜底文案是**主路径**而非兜底；D-13 的 CI 门禁必须新增"对嵌套 Chromium.app 单独跑一次 `--verify --deep --strict`"这一步，只验外层不足以证明内层真的签对了；D-05 的 Info.plist 补丁统一用 `plutil -replace`（无论 key 是否已存在都适用，PyInstaller 已经自动设置了部分键，不必区分 insert/replace）。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PyInstaller onedir 打包 / Info.plist 补丁 / .icns 引用 | CI/构建（GitHub Actions macOS job） | — | 纯构建期产物生成,不涉及运行时逻辑 |
| 嵌套内核 ad-hoc 签名（逐层） | CI/构建 | — | 签名是构建产物的属性,必须在 CI 内完成且可复现 |
| dmg 制作（create-dmg） | CI/构建 | — | 同上,输出 GitHub Release 资产 |
| GitHub Release 汇合发布 | CI/构建（独立 release job） | — | 与 Windows job 平级,由第三个 job 统一处理,避免竞态 |
| Cmd+Q 真正退出 vs 关窗最小化 | 桌面应用运行时（`launch_app.py` / Qt 事件层） | — | 运行时进程生命周期管理,只能在应用自身代码里做,CI 管不到 |
| 首启 quarantine 自剥离 + 失败兜底弹窗 | 桌面应用运行时（`launch_app.py` 启动路径 + 前端 UI-04） | 后端（`chrome.py` 已有的内核级剥离钩子，Phase 3 已完成） | 运行时对"当前进程所在 bundle"的自省行为,与 CI 无关；已有的内核剥离钩子是另一道独立防线，二者不互相替代 |
| `backend/_g.py` 完整性校验存活 | 构建期（`npm run build` 钩子） + 运行时（`launch_app.main`） | — | 双触发点,构建期查源文件哈希,运行时查 dist marker,CI 只需保证不破坏其前提（frontend/dist 完整进包） |
| 版本一致性校验（tag vs package.json vs main.py） | CI/构建 | — | 纯静态字符串比对,不涉及运行时 |

## Package Legitimacy Audit

本 phase 不向 `requirements.txt` / `frontend/package.json` 引入任何新的 pip/npm 依赖（`pyinstaller` 已在 `requirements.txt`，无需新增）。CI 侧新增的唯一外部工具是通过 Homebrew 安装的 **`create-dmg`**（构建期工具，不进入项目依赖清单，ephemeral runner 用完即弃），走的是 `brew install`，不受 npm/PyPI 供应链风险模型约束，但仍做了来源核查：

| 工具 | 来源 | 版本 | 年龄/热度 | 源仓库 | 结论 |
|------|------|------|-----------|--------|------|
| `create-dmg` | Homebrew **core**（非第三方 tap）`brew info create-dmg` [VERIFIED: 本机实测] | 1.3.0（bottled，装机 ~12.5s） | 365 天内 18,625 次安装 [VERIFIED: 本机实测 `brew info`] | `github.com/create-dmg/create-dmg`，MIT | OK，可直接在 CI 里 `brew install create-dmg` |

**Packages removed due to [SLOP] verdict：** 无。
**Packages flagged as suspicious [SUS]：** 无。

*说明：本节按官方 Homebrew Core 索引与 `brew info` 输出核实，未使用 `gsd-tools query package-legitimacy check`（该工具面向 npm/PyPI/crates 生态，不覆盖 Homebrew 构建期工具）。*

## Standard Stack

### Core（macOS job 新增/复用）

| 工具 | 版本 | 用途 | 备注 |
|------|------|------|------|
| pyinstaller | ≥6.14.0（`requirements.txt` 已锁；本地实测用 6.21.0） | onedir + windowed 产出 `.app` | 与 Windows job 用同一份 `requirements.txt`，无需拆分 [VERIFIED: 本机实测] |
| create-dmg | 1.3.0（brew 最新 bottle） | 制作带背景图/Applications 别名的 dmg | `brew install create-dmg`，CI 上预计与本机同样是秒级安装（bottled，无需编译）[VERIFIED: 本机实测] |
| codesign / plutil / iconutil / sips / xattr / lipo / file | macOS 系统自带（不装） | 签名、Info.plist 补丁、图标生成、quarantine 剥离、架构校验 | 全部为 `/usr/bin` 系统工具，macos-15 runner 必然自带 |
| actions/upload-artifact | v4 | Windows/macOS 两个 build job 各自上传产物给汇合 job | v4 起 artifact 按 job 隔离，同名不能跨 job 复用 [CITED: GitHub upload-artifact v4 迁移说明] |
| actions/download-artifact | v4 | release job 汇合下载 | 支持 `pattern` + `merge-multiple` 把多个 artifact 拉到同一目录 [CITED: GitHub download-artifact v4 文档] |
| softprops/action-gh-release | v2（与 Windows job 现有版本一致） | 一次性把 windows/macOS 产物挂到同一 Release | `files:` 支持多行文件列表 [CITED: softprops/action-gh-release README] |

### Alternatives Considered

| 场景 | 备选 | 取舍 |
|------|------|------|
| Info.plist 补丁 | `.spec` 文件里的 `BUNDLE(info_plist=...)` | 已被 D-05 否决（会破坏 `.gitignore` 对 `*.spec` 的既有约定），保留 |
| dmg 制作 | 纯 `hdiutil` + AppleScript 手写 | 已被 D-09 否决（headless CI 摆窗口位置脆），保留 |
| 嵌套签名 | `codesign --force --deep --sign -` 一把梭 | **本次实测证实此路线不可靠**：外层验证会误报通过，内层实际未被重签（见 Pitfall 2），D-13 的逐层方案是唯一验证生效的做法 |

**Installation（macOS job 新增步骤，追加在现有 checkout/setup-python/setup-node 之后）：**
```bash
brew install create-dmg
```

**Version verification：** 已用 `brew info create-dmg`（本机实测，见上表）与 `pyinstaller --version`（本机实测 6.21.0，`requirements.txt` 锁 ≥6.14.0）核实，均为当前可用版本，无需改动版本锁定策略。

## Architecture Patterns

### System Architecture Diagram（本 phase：CI 构建 + 签名 + 打包 + 发布数据流）

```
push v* tag
    │
    ├──► [build job: windows-latest]───────────────┐
    │      pip install -r requirements.txt          │
    │      npm run build (frontend/dist)             │
    │      Fetch-Engine (chrome.exe + firefox.exe)   │
    │      pyinstaller --onedir --windowed           │
    │      Inno Setup → Open-Anti-Browser-Setup.exe  │
    │      upload-artifact: Open-Anti-Browser-Setup  │
    │                                                 │
    └──► [build-macos job: macos-15]─────────────────┤
           pip install -r requirements.txt            │
           npm run build (frontend/dist)               │
           ditto 下载解压 CHROME_ENGINE_ZIP_URL_MACOS_ARM64 → engines/chrome/Chromium.app
           pyinstaller --onedir --windowed --icon assets/app.icns
                → dist/Open-Anti-Browser.app（真实数据在 Contents/Resources，
                  Contents/Frameworks 下为指向 ../Resources/* 的符号链接）
           plutil -replace 补 Info.plist（CFBundleShortVersionString/
                CFBundleVersion/LSMinimumSystemVersion）── 必须早于签名
           版本一致性校验：tag vs package.json vs main.py，不一致 fail
           ditto 注入内核 → Contents/Resources/engines/chrome/Chromium.app
           逐层 ad-hoc 签名：
                Helper*.app（4个）→ Chromium Framework →
                Chromium.app 自身（非--deep）→ 外层 Open-Anti-Browser.app（非--deep）
           CI 硬门禁：
                codesign --verify --deep --strict <外层>          ── 必须
                codesign --verify --deep --strict <内层 Chromium.app> ── 必须（外层通过不代表内层真的签对）
                lipo -archs 断言主二进制与 Framework 均为 arm64
                _g.py 完整性前提断言：frontend/dist 文件已进包且含 marker
                --backend-only 冒烟：后台起 .app 内二进制,轮询本地端口
           create-dmg → Open-Anti-Browser-{version}-arm64.dmg
           upload-artifact: Open-Anti-Browser-{version}-arm64.dmg
                                                        │
                                                        ▼
                                    [release job, needs: [build, build-macos]]
                                    if: startsWith(github.ref, 'refs/tags/')
                                    download-artifact（两个 artifact 汇合到一个目录）
                                    softprops/action-gh-release@v2
                                       files: |
                                         Open-Anti-Browser-Setup.exe
                                         Open-Anti-Browser-*-arm64.dmg
                                    → 同一个 GitHub Release
```

### Recommended Project Structure（本 phase改动落点，非新建目录树）
```
.github/workflows/build-release.yml   # 新增 build-macos job + release 汇合 job；windows build job 构建步骤逐字不动，仅挪走末尾 gh-release 步骤
launch_app.py                          # 新增：macOS 专属 QApplication 子类拦截 QEvent.Quit；新增：首启 quarantine 自剥离尝试 + 失败兜底回调
assets/
├── app.icns                          # 新增（D-06，本地生成后入仓）
├── app.ico                           # 既有,不动
└── dmg-background.png (+@2x)         # 新增（D-10）
```

### Pattern 1: PyInstaller macOS onedir 真实布局（本机实测）

**What:** `--onedir --windowed` 在 macOS 上产出的 `.app`，真实数据文件全部落在 `Contents/Resources/`，`Contents/Frameworks/` 下对应目录是指向 `../Resources/xxx` 的符号链接；`sys._MEIPASS` 在运行时指向 `Contents/Frameworks`。

**When to use:** 任何依赖 `--add-data` 注入的资源路径解析（本项目的 `ENGINES_DIR`/`FRONTEND_DIST_DIR`/`ASSETS_DIR`）。

**Example（本机实测输出，非推测）：**
```
$ pyinstaller --noconfirm --onedir --windowed --name "Open-Anti-Browser" \
    --icon "assets/app.icns" --osx-bundle-identifier "com.example.app" \
    --add-data "frontend/dist:frontend/dist" \
    --add-data "assets:assets" --add-data "engines:engines" launch_app.py

$ ls -la dist/Open-Anti-Browser.app/Contents/Frameworks/ | grep -E "frontend|assets|engines"
lrwxr-xr-x  assets   -> ../Resources/assets
lrwxr-xr-x  engines  -> ../Resources/engines
lrwxr-xr-x  frontend -> ../Resources/frontend

# 运行时打印（真实二进制输出）：
MEIPASS env: .../Open-Anti-Browser.app/Contents/Frameworks
sys.executable: .../Open-Anti-Browser.app/Contents/MacOS/Open-Anti-Browser
engines exists: True
frontend/dist exists: True
```

注意：macOS 侧 `--add-data` 分隔符是 `:`（POSIX），Windows 侧现有的是 `;`，这是两平台唯一的语法差异，其余参数结构可以对齐。

**结论：`backend/config.py` 的 `_resource_root()`（用 `sys._MEIPASS`）与现有的 `RESOURCE_ROOT / "engines"` 等拼接方式，在 macOS 冻结态下无需任何改动即可正确解析。** `Path.exists()` 与 `Path.rglob()` 均透明穿透符号链接（本机对 `backend/_g.py._6()` 的等价路径做法做了直接实测，能正确读到 marker 字符串），这直接印证 PKG-05 的前提成立。

### Pattern 2: 嵌套 bundle 由内向外逐层 ad-hoc 签名（本机用真实 Chromium.app 实测通过）

**What:** 先签最深层的 Helper.app，再签 Framework，再签中间层 .app，最后签最外层 .app；外层签名**不加 `--deep`**（避免覆盖/跳过已经正确签好的内层）。

**When to use:** 任何"整包内嵌套了另一个完整 .app bundle"的签名场景（D-13 明确要求）。

**Example（本机实测命令序列，对真实 `engines/chrome/Chromium.app` 执行，结果 `codesign --verify --deep --strict` 双层皆通过）：**
```bash
APP="Open-Anti-Browser.app/Contents/Resources/engines/chrome/Chromium.app"
FRAMEWORK="$APP/Contents/Frameworks/Chromium Framework.framework"

# 1) 先签四个 Helper.app
for helper in "$FRAMEWORK/Versions/Current/Helpers"/*.app; do
  codesign --force --sign - "$helper"
done

# 2) 签 Framework 的 Versions/Current
codesign --force --sign - "$FRAMEWORK/Versions/Current"

# 3) 签内嵌的 Chromium.app 自身（不用 --deep）
codesign --force --sign - "$APP"

# 4) 验证内层单独通过（这是必须的第二道门禁，见 Pitfall 2）
codesign --verify --deep --strict "$APP"   # -> exit 0

# 5) 最后签外层（同样不用 --deep，PySide6/Qt frameworks 若也是独立 bundle 需按同样思路各自先签）
codesign --force --sign - "Open-Anti-Browser.app"

# 6) CI 硬门禁：内外都要单独验
codesign --verify --deep --strict "Open-Anti-Browser.app"                     # -> exit 0
codesign --verify --deep --strict "Open-Anti-Browser.app/Contents/Resources/engines/chrome/Chromium.app"  # -> exit 0
```

PySide6/QtWebEngine 侧：`QtWebEngineProcess.app` 与各 `Qt*.framework` 同属"框架内嵌套 bundle"结构，应套用同一签名顺序（各自的 Helper/Framework 先签，再签 `QtWebEngineProcess.app` 本身，最后随外层一起完成）；因本次未安装 PySide6（避免下载数百 MB 的 Qt 依赖拖慢本次研究），该部分标记为 **[ASSUMED，结构类比 Chromium.app 验证结果得出，需在 Wave 0 用真实 PySide6 构建产物复核]**——见 Open Questions。

### Pattern 3: Info.plist 补丁用 `plutil -replace`（本机实测确认是幂等 upsert）

**What:** `plutil -replace KEY -string VALUE file.plist` 无论 KEY 是否已存在都成功（不存在则插入，存在则覆盖）；反之 `-insert` 遇到已存在的 key 会报错退出。

**When to use:** D-05 的 Info.plist 补键步骤，不必再区分"这个键 PyInstaller 有没有自动生成"。

**Example（本机实测）：**
```bash
PLIST="Open-Anti-Browser.app/Contents/Info.plist"
plutil -replace CFBundleShortVersionString -string "0.2.0" "$PLIST"   # 覆盖 PyInstaller 默认写入的 "0.0.0"
plutil -replace CFBundleVersion            -string "0.2.0" "$PLIST"   # PyInstaller 不会自动设置这个键
plutil -replace LSMinimumSystemVersion     -string "12.0"  "$PLIST"   # PyInstaller 不会自动设置这个键
```
**必须早于任何 codesign 调用**（本机实测验证：签名后再改 Info.plist 会让 `codesign --verify` 报 `invalid Info.plist (plist or signature have been modified)`，见 Pitfall 1）。

**已由 PyInstaller CLI 自动设置、无需手工补的键（本机实测确认，纠正 D-05 原始清单里"NSHighResolutionCapable 需要补"的假设）：**
- `CFBundleDisplayName` / `CFBundleName`（来自 `--name`）
- `CFBundleIdentifier`（来自 `--osx-bundle-identifier`）
- `CFBundleIconFile`（来自 `--icon`）
- `CFBundleExecutable` / `CFBundlePackageType` / `CFBundleInfoDictionaryVersion`
- **`NSHighResolutionCapable`：`--windowed` 模式下 PyInstaller 已自动写入 `1`，无需手工补** [VERIFIED: 本机实测]

**真正需要手工补的只有三个键：** `CFBundleShortVersionString`（覆盖默认 `0.0.0`）、`CFBundleVersion`（完全没有）、`LSMinimumSystemVersion`（完全没有）。

### Pattern 4: `.icns` 生成命令序列（本机实测，从仓库现有 `assets/logo-512.png` 生成）

```bash
mkdir icon.iconset
SRC=assets/logo-512.png   # 512x512 源图，仓库已有
sips -z 16   16   "$SRC" --out icon.iconset/icon_16x16.png
sips -z 32   32   "$SRC" --out icon.iconset/icon_16x16@2x.png
sips -z 32   32   "$SRC" --out icon.iconset/icon_32x32.png
sips -z 64   64   "$SRC" --out icon.iconset/icon_32x32@2x.png
sips -z 128  128  "$SRC" --out icon.iconset/icon_128x128.png
sips -z 256  256  "$SRC" --out icon.iconset/icon_128x128@2x.png
sips -z 256  256  "$SRC" --out icon.iconset/icon_256x256.png
sips -z 512  512  "$SRC" --out icon.iconset/icon_256x256@2x.png
sips -z 512  512  "$SRC" --out icon.iconset/icon_512x512.png
cp "$SRC" icon.iconset/icon_512x512@2x.png   # 源图仅 512px，这一档实际是 512 放到 1024 档位名下，非真 1024
iconutil -c icns icon.iconset -o assets/app.icns
```

**实测踩坑（Pitfall 5）：** `iconutil` 对 `icon_512x512@2x.png` 实际只有 512×512（而非 Apple 建议的真 1024×1024）**不会报错也不会警告**，静默接受并生成 `.icns`（本机验证 `iconutil` exit 0，且事后 `sips -g pixelWidth` 确认该档仍是 512px）。产物在最大 Dock/预览尺寸下会比"真 1024 源图"略糊，但不会导致构建失败——D-06 里"1024 档位按实际质量取舍"的决策是对的，只是要明确写清楚这不会有任何自动报错来提醒你,必须人工验收图标观感。

### Anti-Patterns to Avoid

- **`codesign --force --deep --sign -` 只签外层就以为万事大吉**：本机实测证明这个命令**不会**递归重签内嵌的 `.app` bundle（哈希前后不变），但外层 `codesign --verify --deep --strict` 却会误报 `valid on disk`。必须按 Pattern 2 逐层签，且必须对内层单独再跑一次验证命令，不能只信外层验证结果。
- **在签名之后才用 `plutil` 改 Info.plist**：会让签名失效（`invalid Info.plist`），必须严格排在签名之前（D-05 已注明，本机实测复现确认）。
- **假设"先拖到 /Applications 再首次运行"能让应用自己顺利剥离 quarantine**：本机用真实 dmg + AppleScript 驱动 Finder 移动到真实 `/Applications` 后首次 `open`，进程依然被翻译到 `/private/var/folders/.../AppTranslocation/...` 只读挂载点，应用自身对该路径（含换算出的真实路径）执行 `xattr -dr` 全部 `Operation not permitted`。见下方 P0-3/P0-4 与 Assumptions Log。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| dmg 背景图/图标位置/Applications 别名摆放 | 手写 `hdiutil` + AppleScript 定位窗口坐标 | `create-dmg` | 一条命令声明完；AppleScript 手写在无人值守 CI 里对 Finder 窗口状态的假设极易失败（D-09 已定） |
| 嵌套签名递归遍历 | 自己写脚本遍历所有 `.app`/`.framework`/可执行文件调用 codesign | 显式列出已知层级（Helper→Framework→Chromium.app→外层）逐条调用 | 内核结构固定（4 个 Helper + 1 个 Framework），显式列举比"猜测性递归"更可控、失败更容易定位到具体 bundle（D-13 已定） |
| App Translocation 检测 | 调用私有 API（`SecTranslocateIsTranslocatedURL` 等） | 检查 `sys.executable` 解析出的路径是否包含 `/AppTranslocation/` 子串 | 本机实测确认该子串 100% 出现在被搬迁的路径里；私有 API 无公开文档保障、跨系统版本可能失效 |

**Key insight：** 本 phase 里"看起来最简单"的三步（打包、签名、剥离 quarantine）恰恰是三个最容易被想当然验证通过、实际未必生效的环节——三者共同点是 macOS 的相关工具（`codesign --deep`、Finder 拖拽、`xattr`）在表面行为和真实生效范围之间存在落差，必须用真实产物实测，不能只读 `--help` 或凭直觉判断。

## Common Pitfalls

### Pitfall 1: Info.plist 补丁顺序颠倒导致签名失效
**What goes wrong:** 先签名、后用 `plutil` 改 Info.plist，`codesign --verify` 报 `invalid Info.plist (plist or signature have been modified)`。
**Why it happens:** codesign 会把 Info.plist 内容纳入签名摘要，任何后续修改都会破坏摘要。
**How to avoid:** 严格排序：pyinstaller 构建 → plutil 补丁 → 版本一致性校验 → 注入内核 → 逐层签名 → 验证 → dmg。
**Warning signs:** CI 日志里 `codesign --verify` 报 "Info.plist" 相关错误。

### Pitfall 2: `--deep` 签名给出假阳性通过
**What goes wrong:** `codesign --force --deep --sign - Open-Anti-Browser.app` 之后，外层 `codesign --verify --deep --strict` 显示 `valid on disk`，但嵌套的 `Chromium.app` 实际完全没被重签（本机实测：签名哈希在操作前后逐字节相同），若单独对内层验证仍会失败。
**Why it happens:** `--deep` 在遇到已经"看起来已签名"的嵌套 bundle 时会跳过，不会真正递归重签；这正是 Apple 弃用 `--deep` 的已知原因之一。
**How to avoid:** 采用 Pattern 2 的逐层签名，并在 CI 门禁里同时对外层和内层（`Chromium.app`）分别跑 `codesign --verify --deep --strict`，缺一不可。
**Warning signs:** 如果 CI 只对外层验证就判定通过，未来某次内核资产更新格式变化时可能悄悄失效而无法被 CI 察觉。

### Pitfall 3: 内核资产本身"天生"就不满足 bundle 级验证
**What goes wrong:** 仓库里现成的、未经任何本 phase 改动的 `engines/chrome/Chromium.app`，单独对它跑 `codesign --verify --deep --strict` **在未重签之前就会失败**（`code has no resources but signature indicates they must be present`）。
**Why it happens:** arm64 上链接器自动打的 `adhoc,linker-signed` 签名（flags=0x20002）只覆盖 Mach-O 二进制本身，不包含 bundle 级的资源封套（`Sealed Resources=none`）；而 `--strict` 校验要求"app bundle 格式"必须有资源封套。
**How to avoid:** 不要以为"内核发布前已经过 `verify_and_upload_macos_kernel.sh` 把关，所以它已经是 bundle 级签好的"——那份脚本的 `codesign -dv` 检查只确认 adhoc/linker-signed 标记存在，不等价于 `--verify --deep --strict` 会通过。本 phase 仍必须对注入后的 Chromium.app 完整走一遍 Pattern 2 的重签流程。
**Warning signs:** CI 门禁第一次上线时如果直接对未重签的内核跑 `--strict` 验证，会在还没开始处理"注入/组装外层"之前就先失败。

### Pitfall 4: App Translocation 与"是否拖到 /Applications"无关
**What goes wrong:** 假设只要引导用户"先拖到 /Applications 再运行"就能规避 Gatekeeper Path Randomization，让应用自剥离 quarantine 的逻辑在首次运行时生效。本机实测：即使用真实 Finder 拖拽操作把带 quarantine 的 `.app` 移动到真实 `/Applications`，只要 quarantine 属性还在，**首次 `open` 仍然 100% 触发 translocation**，运行路径落在 `/private/var/folders/.../AppTranslocation/<uuid>/d/...`，该挂载点是**整体只读的 nullfs 绑定挂载**，应用对自身（无论是翻译前视图还是换算出的"真实路径"）执行 `xattr -dr` 全部返回 `Operation not permitted`。
**Why it happens:** Translocation 的触发条件是"quarantine 属性存在 + 这是该 quarantine 事件首次被 LaunchServices `open`"，与文件当前所在目录（是否 `/Applications`）无关；只有在**从未被 `open` 过、且此刻没有该应用的活跃 translocation 挂载**时，直接对真实路径 `xattr -dr` 才会成功（本机实测确认：应用被首次 `open` 之前手动 `xattr -dr` 立即生效且后续启动不再翻译；但一旦已经被 `open` 过一次，同一份 quarantine 记录哪怕进程已杀掉、dmg 已卸载，短时间内对真实路径的 `xattr -dr` 仍会持续报 `Operation not permitted`，直到系统清理掉该 translocation 挂载记录）。
**How to avoid:** 不要把"应用自剥离 quarantine 成功"设计成首次启动的期望路径——**这在架构上几乎不可能发生**（能触发这段代码的前提，恰好就是它注定会失败的场景）。应把 UI-04 已有的"失败兜底"弹窗（复制终端命令）当作事实上唯一会被绝大多数首次用户看到的路径，自剥离逻辑仅作为"万一 quarantine 已被提前剥过"时的静默跳过优化，而非主流程承诺。
**Warning signs:** 真机 checkpoint（D-15）如果只测"应用最终能不能启动起来"，很容易被"用户跟着弹窗手动敲了一次命令后就能用了"掩盖过去，从而误判自剥离逻辑本身是有效的。**建议 D-15 的验收脚本明确记录：首次双击是否弹出了 quarantine 剥离失败提示（预期：几乎必然会），而不是只看最终是否启动成功。**

### Pitfall 5: iconutil 对不足尺寸的 @2x 源图静默放行
**What goes wrong:** 用 512×512 源图直接复制成 "1024 档"（`icon_512x512@2x.png`，实际仍是 512×512）喂给 `iconutil`，命令 exit 0、无任何警告，正常生成 `.icns`。
**Why it happens:** `iconutil` 不校验 iconset 里图片的实际像素尺寸是否与文件名声明的档位一致。
**How to avoid:** 生成后人工用 `sips -g pixelWidth -g pixelHeight` 抽查关键档位，并在最终 `.app` 上用 Finder "显示简介" 或 Dock 放大观感做一次目视检查（D-06 已要求"图标效果可提前肉眼确认"，这里补充：不能依赖工具报错来发现这个问题，必须主动检查）。
**Warning signs:** 无——这正是本 pitfall 的危险之处，不会有任何自动信号。

### Pitfall 6: macOS 侧沿用 Windows pyinstaller 参数会直接报错
**What goes wrong:** 复制 Windows job 现有的 `pyinstaller` 命令行到 macOS job，`--hidden-import "ruyipage"` 会因为 `ruyipage` 在 macOS 上从未被 `pip install`（`requirements.txt` 里标了 `sys_platform == "win32"`）而报模块找不到；`--add-data "frontend/dist;frontend/dist"` 的 `;` 分隔符在 POSIX 上不被识别。
**How to avoid:** macOS job 的 pyinstaller 命令行需要：去掉 `--hidden-import "ruyipage"`；保留 `--hidden-import "websockets"` / `"websockets.legacy"` / `"websockets.legacy.client"` / `--collect-submodules "curl_cffi"`（这些是跨平台依赖）；`--add-data` 全部把 `;` 换成 `:`；`--icon` 换成 `assets/app.icns`；新增 `--osx-bundle-identifier`。

## Code Examples

### macOS 内核下载与注入（对齐 Windows `Fetch-Engine` 模式，ditto 版本）
```bash
# 对齐现有注释："刻意不在仓库树内解压，避免 PyInstaller 的 --add-data engines 把原始档树也打进去"
CHROME_ZIP_URL=$(python3 -c "from backend.config import CHROME_ENGINE_ZIP_URL_MACOS_ARM64; print(CHROME_ENGINE_ZIP_URL_MACOS_ARM64)")
EXTRACT_DIR="$RUNNER_TEMP/extract_chrome"
mkdir -p "$EXTRACT_DIR"
curl -L --fail -o "$RUNNER_TEMP/chrome.zip" "$CHROME_ZIP_URL"
ditto -x -k "$RUNNER_TEMP/chrome.zip" "$EXTRACT_DIR"   # ditto 保留符号链接与已有签名，不用 unzip
APP_SRC=$(find "$EXTRACT_DIR" -maxdepth 2 -name "Chromium.app" -print -quit)
mkdir -p engines/chrome
ditto "$APP_SRC" "engines/chrome/Chromium.app"
```

### macOS pyinstaller 调用（与 Windows job 对齐参数结构）
```bash
pyinstaller \
  --noconfirm \
  --onedir \
  --windowed \
  --name "Open-Anti-Browser" \
  --icon "assets/app.icns" \
  --osx-bundle-identifier "com.shengsoft.openantibrowser" \
  --add-data "frontend/dist:frontend/dist" \
  --add-data "assets:assets" \
  --add-data "engines:engines" \
  --hidden-import "websockets" \
  --hidden-import "websockets.legacy" \
  --hidden-import "websockets.legacy.client" \
  --collect-submodules "curl_cffi" \
  launch_app.py
```
（相对 Windows：去掉 `--hidden-import "ruyipage"`；`--icon` 换 `.icns`；`--add-data` 分隔符换 `:`；新增 `--osx-bundle-identifier`。）

### 版本一致性校验（无新依赖，纯标准库正则/`json`）
```bash
python3 - "$GITHUB_REF_NAME" << 'PYEOF'
import json, re, sys
tag_version = sys.argv[1].lstrip("v")
pkg_version = json.load(open("frontend/package.json"))["version"]
main_text = open("backend/main.py", encoding="utf-8").read()
main_versions = set(re.findall(r'version="([^"]+)"', main_text))
if len(main_versions) != 1:
    sys.exit(f"backend/main.py 里的两个 FastAPI version= 不一致或未找到: {main_versions}")
main_version = main_versions.pop()
if not (tag_version == pkg_version == main_version):
    sys.exit(
        f"版本不一致: tag={tag_version} package.json={pkg_version} main.py={main_version}"
    )
print(f"版本一致: {tag_version}")
PYEOF
```
（本机实测：`re.findall(r'version="([^"]+)"', ...)` 在当前 `backend/main.py` 上准确抓到两个 `"0.1.16"`。）

### `--backend-only` CI 冒烟（D-14 第 4 条，推荐的低风险实现路径）
```bash
APP_BIN="dist/Open-Anti-Browser.app/Contents/MacOS/Open-Anti-Browser"
"$APP_BIN" --backend-only --port 18123 &
SMOKE_PID=$!
for i in $(seq 1 15); do
  if curl -sf "http://127.0.0.1:18123/api/bootstrap" >/dev/null 2>&1; then
    echo "冒烟通过：/api/bootstrap 响应正常"
    kill "$SMOKE_PID"; exit 0
  fi
  sleep 1
done
echo "冒烟失败：15s 内未获得 /api/bootstrap 响应" >&2
kill "$SMOKE_PID" 2>/dev/null
exit 1
```
**为什么推荐这条而不是启动完整 QWebEngineView GUI：** `launch_app.py` 已经原生支持 `--backend-only [--port N]`（`main.py:363-373` 的既有分支），完全绕开 QtWebEngine/GPU 初始化在无人值守 runner 上的不确定性，同时仍然覆盖 D-14 想抓的"签名过了但一启动就挂"这类问题（模块加载失败、依赖缺失、`_g.py` 拒启动等，都会在这条路径上原形毕露）。完整 GUI 冒烟可以作为**软失败**的补充检查，但不建议作为硬门禁——是否要做、能做到什么粒度需要在 Wave 0 用真实 CI 跑一次才能确认（见 Open Questions）。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `codesign --force --deep --sign -` 整体签 | 逐层由内向外签 + 内外分别验证 | Apple 自 macOS 10.9.5 起就在文档中标注 `--deep` 为"仅供测试用途，不建议生产使用" | 本 phase 之前若假设"反正是 ad-hoc 签名，随便怎么签都行"，会被 CI 门禁的"内层单独验证"步骤直接拦下来 |
| 假设 dmg 拖拽即可规避 Gatekeeper 全部限制 | 拖拽只影响用户体验路径，不影响 translocation/quarantine 判定 | — | 直接推翻 D-12 的核心假设，见 Assumptions Log A1 |

**Deprecated/outdated：** `codesign --deep`（Apple 官方 man page 长期标注为已弃用，本次用真实嵌套内核复现了它在生产场景下的失效模式，而非仅凭文档转述）。

## Runtime State Inventory

不适用——本 phase 不涉及字符串重命名、数据迁移或历史配置格式变更；D-02 对 Windows `release` 步骤的搬动是"移动 CI 步骤所在的 job"，不改变任何已发布产物的命名/格式/存储位置，因此不落入本节覆盖范围。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | D-12"先拖到 /Applications 再运行可规避 App Translocation"的假设已被本机实测推翻——实测显示无论目标目录为何，只要 quarantine 属性存在且是首次 `open`，均会被搬迁到只读挂载点，应用自身无法在该次运行中剥离自己的 quarantine。**这不是 [ASSUMED]，是 [VERIFIED: 本机实测]**，但"实测环境（脚本化 `open` + AppleScript 驱动的 Finder 移动，非真人手指双击 + 真实 Gatekeeper 弹窗交互）与真实用户体验是否存在系统性差异（例如 System Settings 里点"仍要打开"这个官方交互路径是否会附带清除 quarantine 属性、从而让*下一次*启动不再翻译）"仍未验证，标记 [ASSUMED，基于本机脚本化实测外推到真实交互流程] | Assumptions Log 本条 + Common Pitfalls Pitfall 4 | 如果真实"仍要打开"交互流程确实会清除 quarantine（而不仅仅是 syspolicy 数据库记一条豁免），那么现实中用户体验会比本次脚本化实测显示的更好——D-15 真机 checkpoint 必须验证这一步真实观感，而不是照抄本文档的悲观结论定案 |
| A2 | PySide6 `QtWebEngineProcess.app` 与各 `Qt*.framework` 的嵌套签名顺序，按结构类比 `Chromium.app` 的实测结果直接套用（先签内层 Helper/Framework，再签容器 .app，最后随外层一起签），未用真实 PySide6 构建产物验证 | Architecture Patterns / Pattern 2 | 如果 Qt 的嵌套结构与 Chromium 的不完全一致（例如某些 helper 缺少独立 Info.plist、不构成"app bundle 格式"），Pitfall 3 描述的"bundle 格式才需要资源封套"判定条件可能不适用，导致签名脚本对 Qt 部分的处理方式需要调整 |
| A3 | `LSMinimumSystemVersion` 建议值 `12.0`（Monterey）——纯粹基于"arm64 Mac 出厂即支持 Monterey 及以上、fingerprint-chromium 149 基线无已知更高系统版本要求"的推断，未查证 Chromium 149 或 PySide6/Qt 当前版本的官方最低系统要求文档 | Pattern 3 / Code Examples | 若 PySide6 6.9+ 或 QtWebEngine 的最低系统要求高于 12.0（例如要求 13.0），成品会在旧系统上崩溃而非在启动时给出清晰提示；建议 planner 在 Wave 0 用 `otool -l` 检查 Qt 相关二进制的 `LC_BUILD_VERSION` 最低版本后再定稿 |
| A4 | GitHub Actions macos-15 runner 在 CI 沙盒会话下运行 `create-dmg`（依赖 Finder + AppleScript）行为与本机交互式桌面会话一致——本机实测出现过一次 "Skipping blessing on sandbox" 提示，暗示某些沙盒/受限会话下 create-dmg 会跳过部分步骤，但本机是完整交互式会话而非真正的 CI 无头会话，无法 100% 复现 GH runner 的实际会话类型 | Standard Stack / Common Pitfalls（隐含） | 若 GH runner 的 GUI 会话类型导致 AppleScript 权限被拒绝（而非仅仅跳过 bless），`create-dmg` 可能整体失败而非部分降级；需在 Wave 0 第一次真实 CI 跑通 dmg 步骤时重点关注日志里是否有 AppleScript 相关报错 |

**若此表为空：** 不适用，本次研究含真实机器实测得出的推翻性结论（A1），必须在讨论/执行前明确告知用户。

## Open Questions

1. **D-12 自剥离方案在"官方 Gatekeeper Open Anyway"交互路径下的真实效果**
   - What we know：脚本化 `open` + AppleScript 驱动 Finder 移动的路径下，无论目标目录如何，首次启动必被 translocate 且只读，自剥离必然失败（本机实测，见 Pitfall 4 / A1）。
   - What's unclear：真人通过 System Settings → Privacy & Security → "Open Anyway" 完成官方放行交互后，quarantine 属性是被清除还是仅在 syspolicy 数据库记一条豁免（若是后者，下次启动可能仍然翻译，但不再弹 Gatekeeper 拒绝提示）。
   - Recommendation：D-15 真机 checkpoint 明确记录"首次双击后到底看到了什么提示序列"（是自剥离弹窗、还是系统 Gatekeeper 拒绝对话框、还是两者都有），并记录第二次启动时是否还会翻译，作为对本研究 A1 结论的现实校准依据。

2. **PySide6/QtWebEngine 嵌套 bundle 的实际签名结构是否与 Chromium.app 一致**
   - What we know：Chromium.app 的结构（Helper.app ×4 + 一个 Framework）已完整实测验证签名顺序有效。
   - What's unclear：PyInstaller 收集 PySide6 依赖后，`QtWebEngineProcess.app`（如果它作为独立 .app 出现在产物里）以及各 `Qt*.framework` 是否需要相同处理，是否存在额外的 `.dylib` 级签名要求。
   - Recommendation：Wave 0 第一次跑通 macOS pyinstaller 构建后，先用 `find dist/Open-Anti-Browser.app -iname "*.app" -o -iname "*.framework"` 枚举真实产物结构，再据此微调签名脚本（本 RESEARCH.md 的 Pattern 2 命令骨架可直接套用，只需替换路径）。

3. **CI 冒烟做到多深的问题（D-14 discretion）**
   - What we know：`--backend-only` 冒烟风险低、可行性高（`launch_app.py` 已原生支持），能覆盖"签名过了但一启动就挂"的多数情形。
   - What's unclear：是否值得再加一层完整 GUI（`QWebEngineView`）冒烟；GH macOS runner 对 Qt WebEngine GPU/合成初始化的真实支持程度未知。
   - Recommendation：Wave 0 先只上 `--backend-only` 冒烟作为硬门禁；完整 GUI 冒烟作为后续可选增强，不阻塞本 phase。

4. **`create-dmg` 在 GitHub Actions macos-15 runner 的真实会话类型下是否 100% 可靠**
   - What we know：本机交互式会话下完整成功（约 27 秒），产出的 dmg 内 `.app` 签名在 dmg 打包前后保持一致（`codesign --verify --deep --strict` 双层皆通过）。
   - What's unclear：GH runner 的会话类型（本次搜索确认 GH 官方文档说明 macOS runner 有完整桌面会话可用，但未亲自在真实 GH Actions 环境验证 `create-dmg` 的 AppleScript 步骤）。
   - Recommendation：Wave 0 第一次 `workflow_dispatch` 试跑时重点检查 create-dmg 步骤日志，若出现 AppleScript 权限报错，`--hdiutil-quiet` 之外可能还需要额外的 `--skip-jenkins`（社区已知参数，用于规避某些 CI 场景下的差异）或改用更保守的窗口/图标参数子集。

## Environment Availability

| Dependency | Required By | Available (本机) | Version | Fallback |
|------------|--------------|:---:|---------|----------|
| pyinstaller | .app 打包 | ✓ | 6.21.0（本机装的测试版本；`requirements.txt` 锁 ≥6.14.0） | — |
| create-dmg | dmg 制作 | ✓（brew 秒装） | 1.3.0 | — |
| codesign/plutil/iconutil/sips/xattr/lipo/file | 签名/图标/校验 | ✓（系统自带） | macOS 系统版本自带 | — |
| 真实 arm64 内核 (`engines/chrome/Chromium.app`) | 端到端验证 | ✓（仓库既有，只读使用） | fingerprint-chromium 149.0.7827.114 | — |
| PySide6 | 完整 GUI 冒烟 / A2 校准 | ✗（本次研究未安装，避免下载体积拖慢研究） | — | Wave 0 用真实 CI 或本机装一次核实 A2 |

**Missing dependencies with no fallback：** 无（PySide6 缺失有明确的 fallback：延后到 Wave 0 用真实 CI 环境验证）。
**Missing dependencies with fallback：** PySide6（见上）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest`（既有）+ GitHub Actions 工作流本身作为 CI 门禁（新增） |
| Config file | 无 pytest 配置；CI 门禁写在 `.github/workflows/build-release.yml` 的 macOS job 步骤里 |
| Quick run command | `python -m unittest discover -s tests -v`（不覆盖打包/签名逻辑，仅覆盖 `config.py` 等纯 Python 部分） |
| Full suite command | 同上 + 真实 `workflow_dispatch` 触发一次 macOS job（打包/签名/dmg 无法用 unittest 覆盖，必须靠 CI 实跑） |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PKG-01 | push v* tag 触发 macOS job 且与 Windows job 互不影响 | CI 门禁（workflow 结构） | `git push origin v0.2.0-rc1`（或 `workflow_dispatch`） → 观察 Actions 页面两个 job 并行 | ❌ Wave 0（工作流改动本身） |
| PKG-02 | `.app` bundle Info.plist/图标/Cmd+Q 正确 | 混合：CI 静态校验（plutil 读回值） + 真机人工 checkpoint（Cmd+Q 手感、Dock 图标观感） | `plutil -p Info.plist \| grep CFBundleShortVersionString`；Cmd+Q 部分见 D-15 checkpoint | ❌ Wave 0 |
| PKG-03 | 嵌套内核签名 + `codesign --verify --deep --strict` 硬门禁 | CI 门禁（本研究已给出具体命令，见 Code Examples/Pattern 2） | `codesign --verify --deep --strict <外层>` + `codesign --verify --deep --strict <内层 Chromium.app>` | ❌ Wave 0 |
| PKG-04 | dmg 含 .app+Applications 别名+背景图，命名含版本架构 | CI 门禁（产物文件名断言）+ 真机人工 checkpoint（背景图观感、拖拽手感） | `test -f "Open-Anti-Browser-${VERSION}-arm64.dmg"` | ❌ Wave 0 |
| PKG-05 | Release 汇合发布 + `_g.py` 完整性校验存活 | CI 门禁（`--backend-only` 冒烟隐含验证 `_g.py` 未拒启动；`_g.py` 的 `_6()` 依赖 frontend/dist marker，本研究已实测确认符号链接布局不影响该检查） | 见 Code Examples "`--backend-only` CI 冒烟" | ❌ Wave 0 |

### Sampling Rate
- **Per task commit：** 涉及纯 Python 部分（如版本一致性校验脚本本体）可先用本地 `python3` 手动跑一次目标脚本验证语法/逻辑，不必每次都跑完整 CI。
- **Per wave merge：** 每个 wave 涉及 CI 工作流改动的部分，至少 `workflow_dispatch` 触发一次完整跑通（不建 Release，D-04 已定）。
- **Phase gate：** 真正推一次 `v*` tag（或等效的 rc tag，若 D-04 讨论中认可用非正式 tag 试跑）观察 Release 是否正确同时挂上 Windows 安装包与 macOS dmg，且两者签名/版本均通过校验。

### Wave 0 Gaps
- [ ] 无 `.spec` 测试基础设施——所有打包/签名验证只能通过真实 CI 运行或本机手动执行覆盖，Wave 0 需要显式安排"本机/CI 首次跑通"作为验证步骤，而非假设现有 `tests/` 目录里有等价单测。
- [ ] `assets/app.icns` 与 `assets/dmg-background.png`（+@2x）尚未入仓（D-06/D-10 要求本地生成后提交），Wave 0 第一个任务应该是生成并提交这两份资产，否则后续 CI 步骤无从引用。
- [ ] PySide6 未在本次研究环境安装，A2（Qt 嵌套签名假设）需要 Wave 0 用真实构建产物复核。

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | 否 | 本 phase 不涉及登录/身份认证 |
| V3 Session Management | 否 | 不涉及 |
| V4 Access Control | 否 | 不涉及 |
| V5 Input Validation | 否（本 phase 无新增用户输入面） | — |
| V6 Cryptography | 部分适用——但本项目明确 **不做** Apple Developer 签名/公证（PROJECT.md Out of Scope），本 phase 的"签名"是 ad-hoc（无私钥、无身份验证），不构成传统意义上的密钥管理场景 | ad-hoc 签名（`codesign --sign -`）不需要密钥管理；不要引入自建证书或私钥签名方案代替官方 Developer ID 流程（超出本 phase/milestone 范围，见 DIST-01 Future Requirement） |

### Known Threat Patterns for 本 phase 技术栈

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| CI 供应链：`brew install create-dmg` 拉取的公式或依赖被篡改 | Tampering | 使用 Homebrew **core**（非第三方 tap）的官方 bottle，本研究已核实来源（`brew info` 输出的仓库地址为 `github.com/create-dmg/create-dmg`，公式文件位于 `Homebrew/homebrew-core`）；CI 中不应改用第三方 tap 或直接 curl 下载脚本执行 |
| Release 资产被中途替换（GitHub Release 上传竞态） | Tampering | D-02 已用"全部 build job 只上传 artifact，由唯一 release job 统一发布"根除双 job 并发创建/覆盖同一 Release 的竞态 |
| CI 里下载的内核 zip 被篡改（供应链投毒） | Tampering | 已有上游把关：`CHROME_ENGINE_ZIP_URL_MACOS_ARM64` 指向本仓库自己的 GitHub Release 资产（非第三方源），且 Phase 2 已做过架构校验+签名校验+冒烟测试后才发布上去；本 phase 的 CI 下载只是"消费"这份已把关过的资产，不需要重复做供应链完整性校验（如需加固可选加 sha256 校验，但不在本 phase 决策范围内） |
| 用户被诱导执行 `xattr -dr` 之外的、范围更宽的 Gatekeeper 绕过命令（如全局关闭 Gatekeeper、`sudo spctl --master-disable`） | Elevation of Privilege（诱导用户降低整机安全基线） | UI-04 的 `GATEKEEPER_XATTR_COMMAND` 已经限定到单个具体 `.app` 路径、不含 `sudo`、不涉及全局开关（本研究读取 `frontend/src/lib/macosGatekeeperNotice.js` 确认）；D-12 的自剥离失败兜底文案必须复用同一常量，不得另起更宽泛的命令 |

## Sources

### Primary（HIGH confidence，本机真实实测）
- 本机 arm64 macOS + pyinstaller 6.21.0：完整走通 onedir/windowed 构建、真实 `engines/chrome/Chromium.app`（367MB）注入、逐层 ad-hoc 签名、`codesign --verify --deep --strict` 双层验证、真实 dmg（`create-dmg` 1.3.0）打包，产物路径：`/private/tmp/claude-501/-Users-fanjin-bfwg-Open-Anti-Browser/13bcbef0-9119-42e6-b557-0bc4676a78a3/scratchpad/pyi-experiment/`（`dist/Open-Anti-Browser.app`、`Open-Anti-Browser-0.2.0-arm64.dmg` 等，仅供 planner/executor 参考路径与产物结构，不建议直接复用该目录本身）
- 本机 App Translocation 实测：用 `hdiutil create/attach` 制作真实 dmg，`xattr -w com.apple.quarantine` 模拟浏览器下载标记，`osascript` 驱动真实 Finder 完成拖拽移动（含移动到真实 `/Applications` 并已清理），逐步验证 translocation 触发条件、只读挂载行为、`xattr -dr` 在各阶段的成功/失败边界
- `brew info create-dmg`：确认来源、版本、license、安装量
- 仓库现有代码：`backend/config.py`、`backend/_g.py`、`launch_app.py`、`backend/services/chrome.py`、`.github/workflows/build-release.yml`、`scripts/release/verify_and_upload_macos_kernel.sh`、`frontend/src/lib/macosGatekeeperNotice.js`

### Secondary（MEDIUM confidence，WebSearch + 官方文档交叉确认）
- GitHub `actions/upload-artifact`/`download-artifact` v4 迁移文档（`pattern`+`merge-multiple` 汇合模式）
- `softprops/action-gh-release` README（`files:` 多行写法；v2 已进入 EOL，建议关注但非本 phase 决策范围）
- GitHub `runner-images` 仓库 macos-15 Readme（Xcode 16 / Node 20+22 / Python 多版本预装，确认无需担心基础工具链缺失）

### Tertiary（LOW confidence，未实测，标记于 Assumptions Log）
- PySide6/QtWebEngine 嵌套签名结构类比 Chromium.app 的推断（A2）
- `LSMinimumSystemVersion` 建议值 12.0（A3）
- GH Actions macos-15 runner 真实会话类型下 create-dmg 的 AppleScript 依赖是否 100% 可靠（A4）

## Metadata

**Confidence breakdown：**
- Standard stack：HIGH——create-dmg/pyinstaller 版本与来源均本机实测确认
- Architecture（PyInstaller 布局、嵌套签名）：HIGH——用真实内核资产完整实测，非文档推理
- App Translocation / quarantine 自剥离可行性：HIGH（现象本身）但对"是否与最终用户体验一致"标记 MEDIUM（见 A1，需 D-15 真机复核）
- Pitfalls：HIGH——全部来自本机可复现的真实报错/异常行为，附带具体复现命令
- Qt/PySide6 相关签名细节：LOW（A2，未装 PySide6 实测）

**Research date：** 2026-07-28
**Valid until：** 30 天内有效（macOS/Xcode/PyInstaller/create-dmg 均为快速演进工具链，若 Wave 0 执行时间晚于 30 天，建议对 Pattern 1/2/3 的实测结论用当时的实际版本重新抽查一次）
