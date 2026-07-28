---
phase: 5
slug: ci
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-28
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `05-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest`(既有,纯 stdlib)+ GitHub Actions workflow 步骤本身作为 CI 门禁(新增) |
| **Config file** | none — 无 pytest 配置;CI 门禁写在 `.github/workflows/build-release.yml` 的 macOS job 步骤里 |
| **Quick run command** | `python -m unittest discover -s tests -v` |
| **Full suite command** | `python -m unittest discover -s tests -v` + 一次真实 `workflow_dispatch` 触发的 macOS job 全跑 |
| **Estimated runtime** | 本地 unittest ~30s;CI macOS job 预计 ~10-20 min(含内核下载与 PyInstaller) |

**关键约束:** 打包/签名/dmg 逻辑**无法用 unittest 覆盖**,必须靠真实 CI 跑通 + 真机人工 checkpoint。纯 Python 部分(版本一致性校验脚本、quarantine 路径推导、Cmd+Q 分支)可以且应当用 unittest 锁回归。

---

## Sampling Rate

- **After every task commit:** 涉及 Python 代码改动的任务跑 `python -m unittest discover -s tests -v`;仅改 yml/资产的任务跑对应的静态校验命令(如 `plutil -p`、`sips -g pixelWidth`)
- **After every plan wave:** 涉及 CI 工作流改动的 wave 至少 `workflow_dispatch` 触发一次完整跑通(不建 Release,D-04)
- **Before `/gsd-verify-work`:** 本地全量 unittest 必须绿;macOS job 必须有一次 `workflow_dispatch` 成功记录
- **Max feedback latency:** 本地 ~30s;CI ~20 min

---

## Per-Task Verification Map

> 由 planner 在写 PLAN.md 时逐任务回填。下表为 requirement 级骨架,来自 RESEARCH.md § Validation Architecture 的 Phase Requirements → Test Map。

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| PKG-01 | push v* tag / workflow_dispatch 触发 macOS job,与 Windows job 互不影响 | CI 门禁(workflow 结构) | `workflow_dispatch` 触发后观察 Actions 页面两个 build job 并行 + release job needs 二者 | ❌ W0 | ⬜ pending |
| PKG-02 | `.app` bundle 的 Info.plist 键值正确、图标正确、Cmd+Q 可退出 | 混合:CI 静态校验 + unittest + 真机 checkpoint | `plutil -p .../Info.plist` 断言 `CFBundleShortVersionString`/`CFBundleVersion`/`LSMinimumSystemVersion`;Cmd+Q 分支逻辑用 unittest;观感与实际退出行为见 D-15 | ❌ W0 | ⬜ pending |
| PKG-03 | 内核 ditto 注入后逐层 ad-hoc 重签,codesign 验证作硬门禁 | CI 门禁 | `codesign --verify --deep --strict <外层.app>` **且** `codesign --verify --deep --strict <内层 Chromium.app>`(两道缺一不可,见 Pitfall 2) | ❌ W0 | ⬜ pending |
| PKG-04 | dmg 含 .app + Applications 别名 + 背景图,命名含版本与架构 | CI 门禁(产物断言)+ 真机 checkpoint(观感) | `test -f "Open-Anti-Browser-${VERSION}-arm64.dmg"` + 挂载后断言 Applications 别名与 `.background` 存在 | ❌ W0 | ⬜ pending |
| PKG-05 | Release 汇合发布;`_g.py` 完整性校验在构建与启动中存活 | CI 门禁 | `--backend-only` 冒烟(启动成功即证明 `_7("runtime")` 未拒启)+ 断言 `frontend/dist` 已进包 | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `assets/app.icns` — 本地 `sips` + `iconutil` 生成并入仓(D-06);后续所有 CI 步骤引用它
- [ ] `assets/dmg-background.png` + `@2x` — 生成并入仓(D-10);create-dmg 步骤引用它
- [ ] 首次真实 `workflow_dispatch` 跑通 macOS job — 这是本 phase **唯一**能证明打包/签名/dmg 链路成立的手段,不能用现有 `tests/` 里的任何单测代替
- [ ] 用真实 PyInstaller 产物枚举嵌套 bundle 结构(`find dist/Open-Anti-Browser.app -iname "*.app" -o -iname "*.framework"`)以核实 RESEARCH A2 假设(PySide6/QtWebEngine 的嵌套签名结构)
- [ ] 用 `otool -l` 检查 Qt 二进制的 `LC_BUILD_VERSION` 最低系统版本,据此定稿 `LSMinimumSystemVersion`(核实 RESEARCH A3 假设)
- [ ] 新增 unittest 覆盖纯 Python 新增逻辑:版本一致性校验、`.app` bundle 根路径推导 + translocation 检测、Cmd+Q 平台分支(用 mock,不依赖真实 GUI/macOS)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dock/菜单栏显示正确应用名与图标 | PKG-02 | 观感判断,无法自动断言 | 装到 `/Applications` 后启动,肉眼确认 Dock 图标与菜单栏应用名 |
| Cmd+Q 真的退出应用(不是最小化到菜单栏) | PKG-02 | 需要真实 GUI 会话与真实按键 | 启动后按 Cmd+Q,确认进程结束、菜单栏图标消失、本地服务端口释放 |
| dmg 拖拽安装体验与背景图观感 | PKG-04 | 观感与交互判断 | 双击 dmg,确认背景图正确显示、图标摆位合理、拖拽到 Applications 别名可完成安装 |
| **首次双击的完整提示序列** | PKG-03 / D-12 | **RESEARCH A1 的现实校准点** | D-15 checkpoint 必须逐条记录:首次双击看到的是自剥离失败提示、系统 Gatekeeper 拒绝对话框、还是两者;走完官方「仍要打开」后第二次启动是否仍被 translocate。**不能只看"最终能不能启动"** |
| iconset 各档位实际像素尺寸 | PKG-02 | `iconutil` 对尺寸不符静默放行(Pitfall 5) | 生成后用 `sips -g pixelWidth -g pixelHeight` 抽查关键档位 |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (icns / dmg 背景图 / 首次 CI 跑通 / A2 / A3)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s locally
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
