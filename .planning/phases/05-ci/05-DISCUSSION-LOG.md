# Phase 5: CI 打包发布 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-28
**Phase:** 5-CI 打包发布
**Areas discussed:** Release 汇合与 workflow 结构, .app 形态与 Info.plist 来源, dmg 外观与资产来源, 签名门禁/quarantine 与验证深度

---

## 讨论范围选择

| Option | Description | Selected |
|--------|-------------|----------|
| Release 汇合与 workflow 结构 | macOS job 与 Windows job 如何共存并挂到同一 Release | ✓ |
| .app 形态与 Info.plist 来源 | PKG-02 要正确 Info.plist + .icns,但 Windows job 是纯 CLI 且 .gitignore 忽略 *.spec | ✓ |
| dmg 外观与资产来源 | PKG-04 要背景图但资产不存在;create-dmg vs hdiutil | ✓ |
| 签名门禁、quarantine 与验证深度 | 嵌套 bundle 重签、D-07 landmine 延伸、CI 冒烟范围 | ✓ |

**User's choice:** 全部四个区域

---

## Release 汇合与 workflow 结构

### Q1 — macOS job 放哪里?

| Option | Description | Selected |
|--------|-------------|----------|
| 加进 build-release.yml(推荐) | 同一 workflow 新增 build-macos job,与现有 windows job 并行;日志/状态集中,方便加汇合 job。代价:要动这个文件 | ✓ |
| 新开 build-release-macos.yml | 独立 workflow 同样监听 v* tag,build-release.yml 字节不动。代价:无法做统一汇合 job,竞态只能靠 action 容错 | |
| 你定 | 交给 Claude 在 research/planning 阶段决定 | |

**User's choice:** 加进 build-release.yml

### Q2 — 两个平台的产物怎么挂到同一 Release?

| Option | Description | Selected |
|--------|-------------|----------|
| 新增 release 汇合 job(推荐) | 两个 build job 只做 upload-artifact;release job(needs 两者)下载全部后一次性建 Release。无竞态。代价:要删掉 Windows job 末尾的 gh-release 步骤 | ✓ |
| 两个 job 各自上传 | macOS job 末尾也调一次 action-gh-release,Windows job 字节不动。代价:并发创建同一 release 有竞态;单平台失败会发出残缺 Release | |
| macOS 先只传 artifact 不上 Release | 本 phase 只保证 CI 稳定产出 dmg,挂 Release 放到 Phase 6。代价:PKG-05 本 phase 不能核销 | |

**User's choice:** 新增 release 汇合 job

### Q3 — macOS job 失败时 Windows 包还发不发?

| Option | Description | Selected |
|--------|-------------|----------|
| 全成功才发(推荐) | release job needs 两者,任一失败就不建 Release。代价:macOS 不稳时阻塞 Windows 发版 | ✓ |
| macOS 失败不阻塞 Windows | continue-on-error / if: always(),缺 dmg 照发。代价:可能静默发出没有 macOS 包的版本 | |
| 你定 | 交给 planner | |

**User's choice:** 全成功才发

### Q4 — 打包链路的调试迭代通道?

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 workflow_dispatch(推荐) | 现有 workflow 已有 workflow_dispatch,release 步骤带 tag 守门。手动触发只构建传 artifact 不建 Release。无需新机制 | ✓ |
| 额外加 pre-release tag 通道 | 允许 v*-rc* tag 发预发布版验证完整链路。代价:仓库留下一堆测试 tag 和预发布 | |
| 本地先跑通再上 CI | 本机把整条链路跑通并固化成脚本,CI 只调脚本。代价:多写一个入仓脚本,与「打包脚本不入仓」约定有张力 | |

**User's choice:** 复用 workflow_dispatch

---

## .app 形态与 Info.plist 来源

### Q1 — PyInstaller 构建声明怎么写?

| Option | Description | Selected |
|--------|-------------|----------|
| 纯 CLI + 构建后 plutil 补键(推荐) | 沿用 Windows 同构的内联 CLI,建好后用 plutil/PlistBuddy 写 Info.plist 剩余键。不碰 .gitignore 约定,两平台风格一致。代价:改 plist 的步骤散在 yml 里 | ✓ |
| 提交 macOS 专用 .spec | BUNDLE(info_plist={...}) 一处声明完整,可本地复现。代价:要给 *.spec 开白名单,与「打包配置不入仓」相左 | |
| CI 里动态生成 .spec | heredoc 写出 .spec 再调 pyinstaller,不入仓又能用 BUNDLE。代价:yml 里嵌一大块 Python,本地复现要手抄 | |

**User's choice:** 纯 CLI + 构建后 plutil 补键

### Q2 — 应用图标 .icns 从哪来?

| Option | Description | Selected |
|--------|-------------|----------|
| 生成 assets/app.icns 入仓(推荐) | 本地 sips + iconutil 从 logo-512.png 生成 iconset 打成 app.icns 提交,与 app.ico 并列。质量可提前确认,CI 无额外依赖 | ✓ |
| CI 里从 PNG 现生成 | macOS job 里跑 sips/iconutil。仓库不多二进制文件。代价:图标效果要等 CI 跑完才看得到;512 放大到 1024 会糊 | |
| 你定 | 交给 planner 决定生成时机与尺寸清单 | |

**User's choice:** 生成 assets/app.icns 入仓

### Q3 — macOS 上托盘(菜单栏)图标与 Cmd+Q 怎么处理?

> 勘察背景:`launch_app.py:298` 设 `setQuitOnLastWindowClosed(False)`,`closeEvent:267-279` 在托盘存在时 `hide()` + `event.ignore()`。macOS 上 Cmd+Q 正是走 closeEvent,会被吞掉,直接违反 SC2。

| Option | Description | Selected |
|--------|-------------|----------|
| 保留菜单栏图标,只修 Cmd+Q(推荐) | macOS 仍创建 QSystemTrayIcon、关窗仍最小化;另接一条 Cmd+Q 路径直接走 force_exit。Windows 行为完全不变,托盘能力不丢 | ✓ |
| macOS 不建托盘,关窗即退 | 平台分支:darwin 不调 _create_tray_icon,closeEvent 直接 shutdown。最简单最好验。代价:失去后台常驻管理已启动浏览器的能力 | |
| 本 phase 不碰,先发包 | Cmd+Q 归 Phase 6 修。代价:SC2 本 phase 无法完整核销,verifier 会标缺口 | |

**User's choice:** 保留菜单栏图标,只修 Cmd+Q
**Notes:** 用户确认这条虽然动 `launch_app.py` 而非 CI,仍属本 phase 范围(SC2 明写验收点)。

### Q4 — 版本号从哪取?

| Option | Description | Selected |
|--------|-------------|----------|
| 以 tag 为准 + 加一致性校验(推荐) | dmg 名与 Info.plist 版本从 github.ref_name 去 v 取(与 Windows Inno Setup 同构);另加 CI 步骤校验 tag 与 package.json/main.py 一致,不一致 fail | ✓ |
| 只以 tag 为准,不校验 | 完全沿用 Windows 现有做法。代价:代码内版本号忘改时静默不一致 | |
| 以 package.json 为准 | CI 从 package.json 读版本,tag 只管触发。代价:与 Windows 的 tag 取数逻辑分叉 | |

**User's choice:** 以 tag 为准 + 加一致性校验

---

## dmg 外观与资产来源

### Q1 — 背景图从哪来?

| Option | Description | Selected |
|--------|-------------|----------|
| 我生成一张入仓(推荐) | Claude 用代码生成简洁 dmg 背景(箭头/引导文字、含 @2x),提交为 assets/dmg-background.png,不满意可直接换 | ✓ |
| 你提供图 | 用户自己出图放到 assets/,Claude 只接入构建。代价:本 phase 会卡在等图上 | |
| 先不做背景图 | dmg 只放 .app + Applications 别名 + 图标摆位。代价:PKG-04 的「自定义背景图」不能核销,需同步改 REQUIREMENTS/ROADMAP 措辞 | |

**User's choice:** 我生成一张入仓

### Q2 — dmg 怎么做?

| Option | Description | Selected |
|--------|-------------|----------|
| create-dmg(brew 安装,推荐) | 一条命令包定背景图、图标坐标、窗口尺寸、Applications 别名。社区标准工具,AppleScript 摆位它代劳。代价:多一个 brew 依赖 | ✓ |
| 纯 hdiutil + AppleScript | 无外部工具,手写 create/attach → osascript 摆位 → detach → convert。代价:AppleScript 摆位在 headless CI 里脆,调试成本高 | |
| 你定 | 交给 researcher 先验证两者在 macos-15 runner 上的可行性 | |

**User's choice:** create-dmg

### Q3 — arm64-only 下 dmg 还带架构后缀吗?

| Option | Description | Selected |
|--------|-------------|----------|
| 带 -arm64 后缀(推荐) | Open-Anti-Browser-0.2.0-arm64.dmg,与 ROADMAP SC4 原文一致;将来恢复 x64 时不需重命名,历史 Release 不会同名不同架构 | ✓ |
| 不带后缀 | Open-Anti-Browser-0.2.0.dmg,现阶段更干净。代价:将来加 x64 时命名不一致 | |

**User's choice:** 带 -arm64 后缀

### Q4 — 背景图要不要写 Gatekeeper 放行提示?

| Option | Description | Selected |
|--------|-------------|----------|
| 拖拽引导 + 一行放行提示(推荐) | 图标位/箭头/Applications 引导 + 底部一行小字「首次打开请右键 → 打开」。拦截发生前就告知,不依赖用户去看 Release notes。与 Phase 6 DOCS-01 互补不重叠 | ✓ |
| 只做拖拽引导 | 背景图只管安装动作,放行说明全交给 Phase 6 的 Release notes 与应用内提示(Phase 4 UI-04 已做)。图更干净 | |

**User's choice:** 拖拽引导 + 一行放行提示

---

## 签名门禁、quarantine 与验证深度

### Q1 — 内核注入后怎么重签?

| Option | Description | Selected |
|--------|-------------|----------|
| 由内向外逐层签(推荐) | 先签嵌套 Chromium.app 及其 helper/framework,再签 Qt framework,最后签外层 .app。苹果官方推荐顺序(--deep 签名已弃用),失败时能定位到具体 bundle。代价:脚本复杂一些 | ✓ |
| 外层 --force --deep 一把签 | 一条命令搞定,最短。代价:--deep 在嵌套 bundle 上不可靠(可能漏签 helper),且 Apple 已弃用 | |
| 你定 | 交给 researcher 实验后决定签名顺序与参数 | |

**User's choice:** 由内向外逐层签

### Q2 — 用户装到 /Applications 后整包带 quarantine,怎么保证内核能启动?

> 背景:Phase 3 D-07 真机实证——带 quarantine 的 ad-hoc arm64 内核裸 exec 被 AMFI 直接 kill(exit 137),不是 Gatekeeper 弹窗,且必须剥整个 bundle。

| Option | Description | Selected |
|--------|-------------|----------|
| 首启时对自身 bundle 整体剥离(推荐) | 启动时对自己所在的 .app 跑一次 xattr -dr com.apple.quarantine(含内部内核),失败则弹窗给命令让用户手动跑。保持「内核就在包里、安装即用」。代价:需 /Applications 写权限;从 dmg 直接运行会遇 App Translocation 只读路径,需引导先拖到 Applications | ✓ |
| 首启把内核解到可写目录 | 内核仍随 dmg 发,首启从 .app 内复制到 ~/Library/Application Support/.../engines/ 再剥离。绕开只读/权限/translocation 全部问题。代价:首启多等几十秒、多占 ~500MB;要改 config.py 的 ENGINES_DIR 解析 | |
| 只靠 chrome.py 现有启动钩子 | 不加新机制,到 Phase 6 再验证 Phase 3 的钩子在 .app 内部场景是否真能剥掉。代价:若剥不掉,用户拿到的就是启动即闪退的包 | |

**User's choice:** 首启时对自身 bundle 整体剥离

### Q3 — CI 硬门禁做到多深?

| Option | Description | Selected |
|--------|-------------|----------|
| 静态校验 + 真起一次冒烟(推荐) | codesign --verify --deep --strict + 内核架构断言(lipo/file) + frontend/dist 进包断言(_g.py 前提) + 后台启一次 .app 内二进制看端口能起来。能抓住「签名过了但一启动就挂」 | ✓ |
| 只做静态校验 | codesign verify + 文件存在断言,不在 CI 里跑应用。CI 简单快速。代价:启动类问题(缺依赖/QtWebEngine/\_g.py 拒启)要到人工下载才发现 | |
| 你定 | 交给 planner 根据 headless runner 上 GUI 应用能跑到什么程度决定冒烟范围 | |

**User's choice:** 静态校验 + 真起一次冒烟

### Q4 — 本 phase 要不要设真机安装 checkpoint?

| Option | Description | Selected |
|--------|-------------|----------|
| 要 —— 最后一个 plan 做真机安装(推荐) | CI 出 dmg 后在本机 arm64 Mac 走 下载 → 拖到 Applications → 双击 → 观察拦截 → 启一个 Chrome 配置。这是验证 quarantine 自剥离方案有效性的唯一手段,现在发现比 Phase 6 便宜。代价:多一轮人工 | ✓ |
| 不要 —— 全交给 Phase 6 | Phase 5 只对「CI 能产出通过门禁的 dmg」负责。代价:自剥离方案到 Phase 6 才被验证,不行要回头改 Phase 5 产物 | |

**User's choice:** 要 —— 最后一个 plan 做真机安装

---

## Claude's Discretion

- create-dmg 具体参数(窗口尺寸、图标坐标、卷标名)、背景图配色/尺寸/中英文措辞
- bundle identifier 取值、LSMinimumSystemVersion 取值、iconset 各档位清单
- Cmd+Q 接管的具体 Qt 实现手段(QEvent.Quit 重载 / aboutToQuit / 原生菜单项)
- 版本一致性校验步骤的实现位置与写法
- CI 冒烟的判定粒度(进程存活 / 端口响应 / /api/bootstrap 返回 200)
- macOS job 里 engines/ 目录组织,以及 --hidden-import ruyipage 等 Windows-only 参数在 macOS 侧的取舍
- .app 冻结态 sys._MEIPASS 落点与 config.py 的 ENGINES_DIR / FRONTEND_DIST_DIR 解析对齐方式(若需改 config.py,Windows 路径值必须逐字不变)

## Deferred Ideas

无越界内容。跨 phase 备忘:

- x64 dmg / matrix / 双架构下载指引 — 2026-07-27 移出 v0.2,本 phase 一律不做
- Release notes 放行说明与架构判断指引 — DOCS-01/DOCS-02,Phase 6
- Apple Developer ID 签名 + 公证(DIST-01)、应用内自动更新(DIST-02) — Future Requirements
- 若真机 checkpoint 证伪自剥离方案,退路「首启把内核解到 Application Support」需作为新的一次决策处理,不由 executor 自行改道
