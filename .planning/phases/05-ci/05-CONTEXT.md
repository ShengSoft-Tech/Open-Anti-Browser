# Phase 5: CI 打包发布 - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning

<domain>
## Phase Boundary

推送 `v*` tag 后,CI 在 macOS runner 上自动产出 **arm64** 的 `.app` bundle → 逐层 ad-hoc 签名 → dmg,并与既有 Windows 安装包一并挂到**同一个 GitHub Release**。覆盖需求 PKG-01、PKG-02、PKG-03、PKG-04、PKG-05。

**⚠ 范围收窄(2026-07-27 里程碑级决定):x64/Intel 已从 v0.2 移除、暂时先不支持。** 本 phase 只做 **arm64**:不用 matrix、不出第二个 dmg、不做双架构下载文档、不做 x64 原生验证。ROADMAP Phase 5 SC1 里的 `matrix:arm64=macos-15、x64=macos-15-intel` 与 SC4 里的「两个 dmg」措辞按 arm64-only 口径读;verifier 以此为准。x64 内核资产已在 `kernel-149.0.7827.114` 备好,后续里程碑恢复成本低。

**已锁定继承项(不再讨论):**
- 内核打包进包内、非首启下载(PROJECT.md Key Decision);内核 URL 唯一事实源 = `backend/config.py:CHROME_ENGINE_ZIP_URL_MACOS_ARM64`(Phase 2 D-07/D-08 已回填)
- macOS 不带 Firefox 内核(Phase 1 D-08),macOS 包内 `engines/` 只有 chrome
- 不做 Apple Developer 签名/公证,ad-hoc 签名 + 用户放行(PROJECT.md Out of Scope)
- Windows 现有构建行为零回归(项目铁律)

**不在本 phase:** Release notes 分步放行说明、README 下载指引(DOCS-01/02,Phase 6);全新 Mac 上的完整端到端验证(Phase 6);macOS 窗口排列/同步(里程碑外);x64 dmg(里程碑外)。

**本 phase 会超出「纯 CI」的两处代码改动(已确认在范围内):**
1. `launch_app.py` 的 Cmd+Q 退出路径(ROADMAP SC2 明写「Cmd+Q 可正常退出」,见 D-07)
2. 首启对自身 `.app` 剥离 quarantine(PKG-03 的真实可用性前提,见 D-12)

</domain>

<decisions>
## Implementation Decisions

### CI workflow 结构与 Release 汇合(PKG-01 / PKG-05)

- **D-01:** macOS job **加进现有 `.github/workflows/build-release.yml`**(新增 `build-macos` job,与现有 windows `build` job 并行),不新开独立 workflow。同一 tag 一次触发两平台,日志/状态集中,也才有条件做统一汇合 job。 — **Reversibility:** reversible — 拆回独立 workflow 只是搬运 job 定义。

- **D-02:** **新增第三个 `release` 汇合 job** 统一建 Release:`build`(windows)与 `build-macos` 两个 job 都**只做 `upload-artifact`**;`release` job(`needs: [build, build-macos]`)下载全部 artifact 后**一次性**调 `softprops/action-gh-release`。这意味着**要把 Windows job 末尾现有的 gh-release 步骤移走**——Windows 的**构建逻辑**逐字不动,只是发布时机从 job 内后移到汇合 job。理由:两个 job 各自调 gh-release 存在并发创建同一 release 的竞态。 — **Reversibility:** costly — Windows 发布路径是已上线的 v0.1.x 发版通道,改动需连同 Windows 一起回归验证(至少走一次 `workflow_dispatch` 确认 artifact 齐全)。

- **D-03:** **全成功才发**:`release` job 依赖两个 build job,任一失败即不建 Release,不发「只有一半包」的版本。不使用 `continue-on-error` / `if: always()`。修好后重推 tag 即可。 — **Reversibility:** reversible。

- **D-04:** **调试通道复用现有 `workflow_dispatch`**,不引入 rc/pre-release tag、不新增机制。手动触发时两个 build job 正常跑并传 artifact,`release` job 保留 tag 守门(沿用现有 `if: startsWith(github.ref, 'refs/tags/')` 语义)因而不建 Release。macOS 打包链路的迭代靠下载 Actions artifact 验证。 — **Reversibility:** reversible。

### .app 构建声明与 Info.plist(PKG-02)

- **D-05:** **纯内联 pyinstaller CLI + 构建后 `plutil`/`PlistBuddy` 补键**,不引入 `.spec` 文件。macOS job 沿用与 Windows 同构的内联 CLI(`--windowed --icon assets/app.icns --osx-bundle-identifier ...`),CLI 覆盖不到的 Info.plist 键(`CFBundleShortVersionString`、`CFBundleName`/`CFBundleDisplayName`、`NSHighResolutionCapable`、`LSMinimumSystemVersion` 等)在构建完成后写入 `Open-Anti-Browser.app/Contents/Info.plist`。选此形态是为了**不动 `.gitignore:23` 忽略 `*.spec` 的现有约定**,也保持两平台命令行风格一致。 — **Reversibility:** reversible — 改成 .spec 只需搬运声明并在 .gitignore 开白名单。
  - **注意时序:** 补 plist 的动作必须发生在**签名之前**(改 Info.plist 会使已有签名失效),与 D-10 的签名顺序联动。

- **D-06:** **`assets/app.icns` 本地生成并入仓**,与现有 `assets/app.ico` 并列;CI 只负责引用,不在 CI 里现生成。本地用 `sips` + `iconutil` 从 `assets/logo-512.png` 生成完整 iconset(16~512 含 @2x;源图仅 512px,1024 档位按实际质量取舍),图标效果可提前肉眼确认,CI 无额外依赖。 — **Reversibility:** reversible。

- **D-07:** **macOS 保留菜单栏(托盘)图标,只单独修 Cmd+Q**。现状:`launch_app.py:298` 设 `setQuitOnLastWindowClosed(False)`,`closeEvent`(:267-279)在托盘存在时 `hide()` + `event.ignore()`——macOS 上 Cmd+Q 正是走 closeEvent,会被吞掉,直接违反 ROADMAP SC2「Cmd+Q 可正常退出」。方案:macOS 上**仍创建 `QSystemTrayIcon`、关窗仍最小化到菜单栏**(保住「后台常驻管理已启动浏览器」的能力),**另接一条 Cmd+Q 路径**(`QEvent.Quit` / `QApplication.aboutToQuit` 一类信号)直接走 `force_exit()`,使 `_force_exit=True` 后 `closeEvent` 走正常 shutdown 分支。**Windows 行为逐字不变**(平台条件分支)。 — **Reversibility:** reversible — 局部改 `launch_app.py`。

- **D-08:** **版本号以 tag 为准 + 加一道一致性校验**。dmg 文件名与 `CFBundleShortVersionString` 都从 `github.ref_name` 去掉前导 `v` 取(与 Windows Inno Setup 现有 `$v = ref_name -replace '^v'` 做法同构);**另在 CI 加一步校验** tag 版本与 `frontend/package.json` + `backend/main.py`(两个 FastAPI `version`)一致,不一致即 fail。防止发出「包名 0.2.0 但应用内显示 0.1.16」。当前仓库三处均为 `0.1.16`,发 v0.2.0 前需按 CLAUDE.md 约定同步改。 — **Reversibility:** reversible。

### dmg 外观与资产(PKG-04)

- **D-09:** dmg 用 **`create-dmg`**(macOS runner 上 `brew install create-dmg`),不手写 `hdiutil` + AppleScript。理由:背景图、图标坐标、窗口尺寸、Applications 别名一条命令声明完;AppleScript 在 headless CI 里摆 Finder 窗口位置出了名的脆。 — **Reversibility:** reversible。

- **D-10:** **`assets/dmg-background.png` 由 Claude 生成并入仓**(用户明确授权,不满意可直接替换)。内容 = **拖拽引导(应用图标位 → 箭头 → Applications 位)+ 底部一行放行提示**(如「首次打开请右键 → 打开」)。含 `@2x` retina 版。理由:未签名 `.app` 双击必被拦,背景图是用户看到的第一屏,在拦截发生前就告知比让他去翻 Release notes 有效;与 Phase 6 的 DOCS-01 是**互补的不同载体**,不重复不合并。 — **Reversibility:** reversible。

- **D-11:** dmg 文件名**保留架构后缀**:`Open-Anti-Browser-{version}-arm64.dmg`(如 `Open-Anti-Browser-0.2.0-arm64.dmg`)。虽然 v0.2 只出 arm64,带后缀可与 ROADMAP SC4 原文一致,并保证将来恢复 x64 时历史包不会出现「同名不同架构」。 — **Reversibility:** costly — 一旦公开发布,改名会让已发布链接失效。

### 签名策略、quarantine 与 CI 门禁(PKG-03 / PKG-05)

- **D-12:** **首启时对应用自身 bundle 整体剥离 quarantine**。背景:用户从 dmg 拖到 `/Applications` 后整个 `.app`(**含内部内核**)都带 `com.apple.quarantine`;Phase 3 D-07 已在真机实证——带 quarantine 的 ad-hoc arm64 内核**裸 exec 会被 AMFI 直接 kill(exit 137)**,不是弹 Gatekeeper 对话框,且必须剥**整个 bundle**(framework dylib / helper 也带 quarantine)。方案:应用启动时对自己所在的 `.app` 跑一次 `xattr -dr com.apple.quarantine`,**失败则弹窗把命令原样给用户**让其手动执行。保持「内核就在包里、安装即用」不变(不改成首启复制到可写目录)。 — **Reversibility:** costly — 若权限/路径场景走不通,退路是把内核首启解到 `~/Library/Application Support/Open-Anti-Browser/engines/`,那会改动 `config.py` 的 `ENGINES_DIR` 解析并影响 Phase 1/3 已锁定的路径决策。

- **D-12a(2026-07-28 修订,用户拍板):** **兜底扶正为主路径。** `05-RESEARCH.md` 在本机真实 dmg + Finder 拖拽下实测推翻了 D-12 的前提(见 RESEARCH Pitfall 4 / Assumptions Log A1):App Translocation 的触发条件是「quarantine 属性存在 + 该 quarantine 事件首次被 LaunchServices `open`」,**与 `.app` 是否位于 `/Applications` 无关**;首次启动必落在只读 nullfs 挂载点,应用对自身(含换算出的真实路径)`xattr -dr` 全部返回 `Operation not permitted`。即**能触发自剥离代码的场景恰好就是它注定失败的场景**。修订后的口径:
  - **实现不变**:内核仍在 `.app` 内,`config.py` 的 `ENGINES_DIR` 解析不动,Phase 1 D-05~D-08 的路径决策不动。
  - **语义降级**:自剥离逻辑从「主流程承诺」降级为「quarantine 已被提前剥过时的静默跳过优化」。它成功是幸运,不是设计预期。
  - **文案与验收口径上调**:失败提示弹窗是**预期的首次主路径**,不是异常分支——文案、埋点与 D-15 的验收标准都按这个前提写。
  - **D-15 必须验明的未决点**(RESEARCH Open Question 1):真人走 系统设置 → 隐私与安全性 →「仍要打开」这条**官方交互路径**后,quarantine 属性是被清除(则第二次启动一切正常、自剥离生效),还是仅在 syspolicy 数据库记一条豁免(则 translocation 持续、用户必须敲命令)。D-15 **不得只验「最终能不能启动」**,必须逐条记录首次双击看到的完整提示序列,以及第二次启动是否仍被 translocate。
  - **退路仍然存在但不在本 phase 启动**:若 D-15 证明体验不可接受,再把「内核首启复制到 `~/Library/Application Support/Open-Anti-Browser/engines/`」作为**新的一次决策**处理,不由 executor 自行改道。 — **Reversibility:** reversible — 本修订只改语义与文案口径,不改代码架构。

  - **researcher/planner 必须查证的两个前提:**
    1. ~~**App Translocation**~~ —— **已由 RESEARCH 实测查证并推翻,见 D-12a。**
    2. **写权限** —— admin 用户对 `/Applications` 可写;非 admin 用户或企业受管 Mac 可能不可写,此时剥离失败路径(弹窗给命令)就是唯一兜底,文案必须给出可直接复制的完整命令。
  - **与 Phase 4 UI-04 的关系:** Phase 4 已做了应用内 Gatekeeper 放行指引(`macosGatekeeperNotice.js`,key `oab:macos-gatekeeper-notice:v1`,`GATEKEEPER_XATTR_COMMAND` 为模块常量)。D-12 的失败兜底文案**应复用/对齐该模块**,不另起第三套措辞。

- **D-13:** 内核经 `ditto` 注入 `.app` 后,**由内向外逐层 ad-hoc 签名**,不用 `codesign --force --deep --sign -` 一把梭。顺序:先签嵌套的 `Chromium.app` 及其 helper/framework → 再签 PySide6/QtWebEngine 的 framework → 最后签外层 `Open-Anti-Browser.app`。理由:`--deep` 签名已被 Apple 弃用且在嵌套 bundle 上行为不可靠(可能漏签 helper),逐层签在失败时还能定位到具体 bundle。 — **Reversibility:** reversible。

- **D-14:** **CI 硬门禁 = 静态校验 + 真起一次冒烟**,不止 `codesign --verify --deep --strict`。至少包含:
  1. `codesign --verify --deep --strict`(PKG-03 明文要求),失败即中止发布
  2. 断言 `.app` 内内核二进制存在且为 **arm64**(`file`/`lipo`,沿用 Phase 2 已建立的架构断言口径)
  3. 断言 `frontend/dist` 已正确进包(`backend/_g.py` 运行时校验 `_6` 读 `FRONTEND_DIST_DIR` 的 marker 字符串,dist 缺失则运行时静默跳过、marker 被改则拒启动)——PKG-05 的完整性校验落点
  4. **后台启一次 `.app` 内的二进制**,确认本地服务端口能起来(GUI 部分在 headless runner 上能跑到什么程度由 planner 按实测定)
  理由:「签名过了但一启动就挂」(缺依赖 / QtWebEngine 摆不平 / `_g.py` 拒启)是这类打包最典型的失败模式,只有真起一次才拦得住。 — **Reversibility:** reversible。

- **D-15:** **本 phase 末尾设一个真机安装 checkpoint plan**(沿用 Phase 4 `04-06-PLAN.md` 的人工验收 plan 模式):CI 产出 dmg 后,在用户的 arm64 Mac 上走完 下载 → 拖到 `/Applications` → 双击 → 观察是否被拦 / 能否启动 → 启一个 Chrome 配置。这是验证 D-12 自剥离方案**真的有效**的唯一手段,现在发现问题比 Phase 6 便宜。与 Phase 6 的区别:本 checkpoint 只验「包能不能装能不能跑」,Phase 6 验「用户仅凭发布文档能否自助完成全流程」。 — **Reversibility:** reversible。

### Claude's Discretion

- `create-dmg` 的具体参数(窗口尺寸、图标坐标、卷标名)、背景图的确切配色/尺寸/中英文措辞。
- bundle identifier 取值、`LSMinimumSystemVersion` 取值、iconset 各档位清单。
- Cmd+Q 接管的具体 Qt 实现手段(`QEvent.Quit` 重载 vs `aboutToQuit` 连接 vs 原生菜单项),只要满足 D-07 的「保留菜单栏图标 + Cmd+Q 能退 + Windows 不变」。
- 版本一致性校验步骤的实现位置与写法(独立 job vs build job 内首步)。
- CI 冒烟的具体判定粒度(进程存活 / HTTP 端口响应 / `/api/bootstrap` 返回 200)。
- macOS job 里 `engines/` 目录的组织方式,以及 Windows CLI 里 `--hidden-import ruyipage` 等 Windows-only 参数在 macOS 侧的取舍(`ruyipage` 在 macOS 未安装,见 `requirements.txt` 的 `sys_platform` 标记)。
- `.app` 冻结态下 `sys._MEIPASS` 落点(PyInstaller 6.x 把数据放 `Contents/Frameworks`)与 `config.py:ENGINES_DIR`/`FRONTEND_DIST_DIR` 解析的对齐方式——**若发现需要改 `config.py`,属实现裁量,但必须保持 Windows 路径值逐字不变**(Phase 1 D-05~D-08)。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与范围(本仓库)
- `.planning/ROADMAP.md` — Phase 5 目标与 5 条成功标准,**含 2026-07-27 的 arm64-only scope 变更告示块**(SC1 的 x64 matrix、SC4 的「两个 dmg」按 arm64-only 读)
- `.planning/REQUIREMENTS.md` — PKG-01 ~ PKG-05 验收条件
- `.planning/PROJECT.md` — v0.2 约束(Windows 零回归、内核打包进包不首启下载、不签名公证、仅 arm64)与 Key Decisions 表

### 上游决策(本仓库)
- `.planning/phases/02-macos/02-CONTEXT.md` — D-06/D-07/D-08:Mac 内核只出 ditto zip、资产命名 `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip`、config.py 为 URL 单一事实源;D-11:kernel 发布脚本入仓与「打包脚本不入仓」的类别区分(本 phase 若要落 dmg 脚本需沿用同一判据)
- `.planning/phases/03-macos-chrome-api/03-CONTEXT.md` — D-07 内核 quarantine landmine(本 phase D-12 的直接上游);`chrome.py` 已有启动前剥离钩子
- `.planning/phases/04-frontend-platform-gating/04-CONTEXT.md` — UI-04 应用内 Gatekeeper 指引载体(D-12 失败兜底文案须与之对齐,勿另起第三套措辞)
- `.planning/STATE.md` — Accumulated Decisions,特别是 `[Phase 3] 03-03 D-07 真机实证`(AMFI kill / 必须剥整个 bundle)与 `[Milestone v0.2] x64 移出` 两条

### 工程约定(本仓库)
- `CLAUDE.md` — commit message 用英文短句;**版本号三处同步**(`frontend/package.json` + `backend/main.py` 两个 FastAPI `version`,D-08 依据);**README 刻意不提供打包步骤、打包脚本已 gitignore**(D-05 不引入 .spec 的依据之一);`backend/_g.py` 完整性校验说明
- `.gitignore:22-26` — `*.spec` / `installer/` / `build_installer.ps1` / `build_portable.ps1` 被忽略(D-05 的约束来源)

### 关键落点(勘察确认,full path + 行号)
- `.github/workflows/build-release.yml` — 现有单 job Windows 流水线。`:39-71` Prepare browser engines(`Fetch-Engine` 模式,`:62` 从 `backend.config` 读 `CHROME_ENGINE_ZIP_URL`,macOS 沿用同模式读 `CHROME_ENGINE_ZIP_URL_MACOS_ARM64`);`:73-89` pyinstaller 内联 CLI(D-05 的同构参照,含 `--hidden-import ruyipage` 等 Windows-only 项);`:91-103` Inno Setup(`$v = ref_name -replace '^v'` 是 D-08 的版本取数参照);`:105-119` upload-artifact + gh-release(**D-02 要把 `:112-119` 移到新的 release 汇合 job**)
- `.github/workflows/ci-tests.yml` — 已有 windows-latest + macos-latest 双 runner 全量 unittest(Phase 1 D-12),与本 phase 的发版流水线相互独立
- `.github/installer.iss` — Windows 安装包定义(macOS 无对应物,不动)
- `backend/config.py:110-127` — `_CHROME_KERNEL_BASE` / `CHROME_ENGINE_ZIP_URL` / **`CHROME_ENGINE_ZIP_URL_MACOS_ARM64`**(macOS job 下载内核的唯一事实源);`:13-49` `_is_packaged()` / `_resource_root()`(`sys._MEIPASS`)/ `_writable_root()`(macOS 固定 `~/Library/Application Support/`)/ `ENGINES_DIR` / `FRONTEND_DIST_DIR` / `ASSETS_DIR`;`:86-99` macOS Chrome 二进制路径 `engines/chrome/Chromium.app/Contents/MacOS/Chromium`
- `backend/_g.py:41-77` — `_5` 校验源文件哈希(冻结态源文件不存在则跳过)、`_6` 校验 `FRONTEND_DIST_DIR` 内 marker 字符串、`_7` 入口。`launch_app.py:17` 导入为 `_0x2f`,启动时调 `_7("runtime")`——PKG-05 的核心校验路径
- `launch_app.py:205-206` 托盘创建条件;`:208-223` `_create_tray_icon`;`:262-265` `force_exit`;`:267-282` `closeEvent`(**D-07 改动主体**);`:295-302` `QApplication` 初始化 + `setQuitOnLastWindowClosed(False)`;`:48` `resolve_window_icon_path()`(D-06 的 icns 消费点之一)
- `assets/` — 现有 `app.ico`(Windows)、`logo-512.png`(icns 与 dmg 背景的源图)、`firefox-extensions/`。**本 phase 新增 `app.icns`(D-06)与 `dmg-background.png`(+@2x)(D-10)**
- `scripts/release/verify_and_upload_macos_kernel.sh` — Phase 2 落地的入仓发布脚本,是「什么脚本可以入仓」的先例(D-11 判据),也是 `lipo`/架构断言/`codesign` 分支写法的现成参考(D-14 第 2 条)
- `requirements.txt:14-15` — `pywin32` / `ruyipage` 带 `sys_platform == "win32"` 标记(macOS job 上这两个包不会安装,影响 pyinstaller 的 hidden-import 参数)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Windows job 的 `Fetch-Engine` 模式可直接类比**:下载 zip → 解压到 `RUNNER_TEMP`(**刻意不在仓库树内解压,避免 PyInstaller 的 `--add-data engines` 把原始档树也打进去**)→ 定位可执行文件 → 拷到 `engines/<engine>/`。macOS 版把 `Expand-Archive` 换成 `ditto -x -k`(保符号链接与签名)、把 `chrome.exe` 换成 `Chromium.app`。
- **内核 URL 单一事实源已就绪**:`python -c "from backend.config import CHROME_ENGINE_ZIP_URL_MACOS_ARM64; print(...)"`,与 Windows `:62` 完全同构,无需在 yml 里硬编码内核版本。
- **`scripts/release/verify_and_upload_macos_kernel.sh`** 里已有 `file`/`lipo` 架构断言与**按架构分支的 codesign 处理**(x86_64 平台设计默认不签名、arm64 从严)的成熟写法,D-14 的架构断言与 D-13 的签名脚本可直接借鉴其结构。
- **Phase 4 的 `macosGatekeeperNotice.js`** 已有中英同步的放行指引与 `GATEKEEPER_XATTR_COMMAND` 模块常量,D-12 的剥离失败提示应对齐它而非另写。
- **人工验收 plan 模式**:`04-06-PLAN.md` 是「CI/代码产出 + 真机人工 checkpoint」的现成模板,D-15 沿用。

### Established Patterns
- **平台路径/常量只在 `backend/config.py` 收敛**(Phase 1 起的铁律)。macOS 打包若暴露出 `.app` 内路径解析问题,改动必须落在 config.py,且 **Windows 路径值逐字不变**。
- **CI 从 config.py 读取而非硬编码**(build-release.yml `:62` 已确立),macOS job 沿用。
- **Windows 零回归**:本 phase 唯一触碰 Windows 的地方是 D-02 把 gh-release 步骤后移;构建步骤本身一行不改,且需通过一次 `workflow_dispatch` 验证 artifact 齐全。
- **打包脚本不入仓(CLAUDE.md)vs 发布工具入仓(Phase 2 D-11)** 的判据分歧:若本 phase 想把 dmg 打包动作抽成脚本,planner 需明确落在哪一侧(内联进 yml 最省事,也最贴合现状——Windows 侧就是全内联)。

### Integration Points
- **`_g.py` 完整性校验 → PKG-05**:运行时 `_5` 校验的两个源文件在冻结包里不存在(`_5` 对不存在的文件直接 `continue`),真正生效的是 `_6` 对 `FRONTEND_DIST_DIR` 内 marker 字符串的检查。因此**只要 `frontend/dist` 完整进包且未被压缩/改写,校验即通过**;D-14 第 3 条就是把这个前提变成 CI 断言。注意 macOS runner 上跑 `npm run build` 时 prebuild/postbuild 钩子也会跑 `python -m backend._g`(build 模式,校验源文件哈希)——源码未改则通过。
- **`sys._MEIPASS` 落点 → `ENGINES_DIR` / `FRONTEND_DIST_DIR`**:PyInstaller 6.x 的 macOS onedir bundle 把数据放在 `Contents/Frameworks`(`Contents/Resources` 下是符号链接)。`config.py:19` 已用 `sys._MEIPASS` 兜底,理论上自洽,但**从未在真实 `.app` 里验证过**——这是本 phase 第一个要实证的点。
- **D-12 自剥离 → Phase 3 chrome.py 钩子**:两者是同一 landmine 的两道防线(应用级整包剥离 + 启动前内核兜底),planner 需明确二者关系,避免重复实现或互相假设对方已处理。
- **D-02 → Windows 发版通道**:`release` 汇合 job 是 v0.1.x 已在用的发布路径的改动点,是本 phase 对 Windows 唯一的风险面。

</code_context>

<specifics>
## Specific Ideas

- dmg 文件名精确样例:`Open-Anti-Browser-0.2.0-arm64.dmg`。
- 背景图内容:应用图标位 → 箭头 → Applications 别名位,**底部一行小字放行提示**(如「首次打开请右键 →『打开』」),含 @2x。用户明确表示不满意可直接换图。
- Cmd+Q 期望行为:按下即真正退出(走 `force_exit` → `shutdown` → uvicorn 停 → 进程结束),而不是最小化到菜单栏。关窗(红叉)仍最小化到菜单栏——两者行为**刻意不同**。
- 版本一致性校验:tag `v0.2.0` 时,`frontend/package.json` 与 `backend/main.py` 的两个 `version` 都必须是 `0.2.0`,否则 CI fail。当前三处均为 `0.1.16`。
- CI 冒烟的意图是抓「签名过了但一启动就挂」,不是做功能测试。
- Phase 3 D-07 原始实证记录(供 D-12 参考):新鲜浏览器下载的 ad-hoc arm64 内核带 quarantine 时**裸 exec 被 AMFI kill,exit 137,不是 Gatekeeper 弹窗**;只剥主二进制不够,framework dylib / helper 也带 quarantine,必须剥整个 bundle(修复见 commit `fbac808`)。

</specifics>

<deferred>
## Deferred Ideas

None — 讨论未越界。

**跨 phase 备忘(非新增 scope,仅提示 planner):**
- x64 dmg / matrix / 双架构下载指引:已于 2026-07-27 移出 v0.2,本 phase 一律不做。x64 内核资产在 `kernel-149.0.7827.114` 备好,`config.py:CHROME_ENGINE_ZIP_URL_MACOS_X64` 常量也已存在,后续里程碑恢复时主要是加 matrix 分支。
- Release notes 分步放行说明与「怎么判断自己是 Apple Silicon 还是 Intel」的下载指引 = DOCS-01/DOCS-02,**Phase 6**。本 phase 的 dmg 背景图放行提示(D-10)是**另一载体**,内容可呼应但不合并、不代替。
- Apple Developer ID 签名 + 公证(DIST-01)、应用内自动更新(DIST-02):Future Requirements,不在 v0.2。
- 若 D-12 的自剥离方案在真机 checkpoint(D-15)被证伪,退路是「首启把内核解到 `~/Library/Application Support/Open-Anti-Browser/engines/`」——那会触及 Phase 1 已锁定的 `config.py` 路径决策,届时需作为**新的一次决策**处理,不由 executor 自行改道。

</deferred>

---

*Phase: 5-CI 打包发布*
*Context gathered: 2026-07-28*
