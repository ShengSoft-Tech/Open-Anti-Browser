# Phase 5: CI 打包发布 - Pattern Map

**Mapped:** 2026-07-28
**Files analyzed:** 6(新增/修改)
**Analogs找到:** 6 / 6(其中 3 处"无同构 analog,须直接沿用 RESEARCH.md 已实测模板")

## File Classification

| 新/改文件 | Role | Data Flow | 最近似 Analog | Match Quality |
|---|---|---|---|---|
| `.github/workflows/build-release.yml`(新增 `build-macos` job + `release` 汇合 job) | CI workflow / config | batch(构建产物流水线) | 该文件自身既有的 Windows `build` job | exact(同文件内新增同构 job) |
| `launch_app.py`(macOS Cmd+Q 接管) | provider(Qt 应用生命周期) | event-driven | 该文件自身既有的 `DesktopMainWindow.closeEvent` / `force_exit` / 托盘菜单 `exit_action` | exact(同文件内平台分支扩展) |
| `launch_app.py`(首启 quarantine 自剥离 + 失败兜底) | utility(启动期自检) | request-response(同步 subprocess 调用 + UI 反馈) | `backend/config.py` 的 `sys.platform == "darwin"` 分支写法;`frontend/src/lib/macosGatekeeperNotice.js` 的失败兜底文案与命令常量 | role-match(平台分支惯例) + exact(文案复用对象) |
| `assets/app.icns`(新增二进制资产) | config/asset | file-I/O | `assets/app.ico`、`assets/logo-512.png` | role-match(同目录同类资产,无生成逻辑可比,生成命令按 RESEARCH Pattern 4) |
| `assets/dmg-background.png` + `@2x`(新增二进制资产) | config/asset | file-I/O | 无仓库内同类先例(dmg 背景图是全新资产类型) | no-analog → 用 RESEARCH D-10 决策 + Claude's Discretion 直接生成 |
| `tests/test_*.py`(新增,覆盖版本一致性校验 / bundle 路径推导 / translocation 检测 / Cmd+Q 平台分支) | test | transform(纯函数/字符串处理测试) + event-driven(Qt 分支测试) | `tests/test_config_platform.py`(`sys.platform`/`sys.frozen` patch 惯例)、`tests/test_process_termination_macos.py`(mock 外部工具调用) | exact |

## Pattern Assignments

### `.github/workflows/build-release.yml`(新增 `build-macos` + `release` job)

**Analog:** 该文件自身的 Windows `build` job(`:12-119`)

**Job 骨架 / checkout+setup 模式**(`:13-31`):
```yaml
jobs:
  build:
    runs-on: windows-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install Python dependencies
        run: pip install -r requirements.txt
      - name: Build frontend
        run: |
          cd frontend
          npm install
          npm run build
```
`build-macos` job 逐字复用这一段(`runs-on: macos-15`,其余不变——两平台共用同一份 `requirements.txt`,不必拆分)。

**从 config.py 读内核 URL、解压到 RUNNER_TEMP 而非仓库树内 的既有约定**(`:39-64`):
```powershell
function Fetch-Engine($url, $zip, $exeName, $dest) {
  ...
  # Extract to RUNNER_TEMP so the raw archive tree is never picked up by PyInstaller's engines/ add-data.
  $extract = Join-Path $env:RUNNER_TEMP ("extract_" + [IO.Path]::GetFileNameWithoutExtension($zip))
  ...
}
$chromeZipUrl = (python -c "from backend.config import CHROME_ENGINE_ZIP_URL; print(CHROME_ENGINE_ZIP_URL)").Trim()
```
macOS 版把 `Expand-Archive` 换成 `ditto -x -k`、`chrome.exe`/`Get-ChildItem -Filter` 换成 `find -name "Chromium.app"`,读取常量换成 `CHROME_ENGINE_ZIP_URL_MACOS_ARM64`。**RESEARCH.md 的 "Code Examples / macOS 内核下载与注入" 一节已给出可直接抄的 bash 实现**,该实现本身就是照此 Windows 段落同构改写的,不必另起写法。

**内联 pyinstaller CLI 参数结构**(`:73-89`):
```
pyinstaller --noconfirm --onedir --windowed --name "Open-Anti-Browser"
  --icon "assets/app.ico" --add-data "frontend/dist;frontend/dist"
  --add-data "assets;assets" --add-data "engines;engines"
  --hidden-import "websockets" --hidden-import "websockets.legacy"
  --hidden-import "websockets.legacy.client" --hidden-import "ruyipage"
  --collect-submodules "curl_cffi" launch_app.py
```
macOS 版对齐这个结构,但按 **RESEARCH Pitfall 6** 三处必改:`;` → `:`(POSIX 分隔符)、`assets/app.ico` → `assets/app.icns`、去掉 `--hidden-import "ruyipage"`(macOS 不装该包)、新增 `--osx-bundle-identifier`。RESEARCH "Code Examples / macOS pyinstaller 调用" 已给出实测通过的完整命令行,直接采用。

**版本号从 tag 剥离 `v` 前缀的既有写法**(`:98-99`,D-08 的同构参照):
```powershell
$v = "${{ github.ref_name }}" -replace '^v', ''
if (-not ($v -match '^\d+(\.\d+)+')) { $v = '0.0.0' }
```
macOS 侧 dmg 文件名与 `CFBundleShortVersionString` 用等价 bash 写法(`${GITHUB_REF_NAME#v}`)取值,再叠加 D-08 要求的"与 `frontend/package.json` + `backend/main.py` 一致性校验"——**RESEARCH "Code Examples / 版本一致性校验" 一节的 Python 脚本可直接内联进 workflow 步骤**,无需另写。

**upload-artifact + gh-release 步骤(D-02 要求拆分)**(`:105-119`):
```yaml
- name: Upload installer artifact
  uses: actions/upload-artifact@v4
  with:
    name: Open-Anti-Browser-Setup
    path: installer_out/Open-Anti-Browser-Setup.exe
    if-no-files-found: error

- name: Create GitHub Release
  if: startsWith(github.ref, 'refs/tags/')
  uses: softprops/action-gh-release@v2
  with:
    files: installer_out/Open-Anti-Browser-Setup.exe
    generate_release_notes: true
    name: "Open-Anti-Browser ${{ github.ref_name }}"
```
**改动指令(D-02):** 把 `:112-119` 的 `Create GitHub Release` 步骤整段从 `build` job 移除,`build` job 到 `:105-110` 的 `upload-artifact` 为止(逐字不动)。新增的 `build-macos` job 只做等价的 `upload-artifact`(artifact 名建议 `Open-Anti-Browser-macos-dmg`,path 指向 `Open-Anti-Browser-*-arm64.dmg`)。新增第三个 `release` job:
```yaml
release:
  needs: [build, build-macos]
  runs-on: ubuntu-latest
  if: startsWith(github.ref, 'refs/tags/')
  permissions:
    contents: write
  steps:
    - uses: actions/download-artifact@v4
      with:
        pattern: 'Open-Anti-Browser-*'
        merge-multiple: true
        path: release-assets
    - uses: softprops/action-gh-release@v2
      with:
        files: release-assets/*
        generate_release_notes: true
        name: "Open-Anti-Browser ${{ github.ref_name }}"
```
不使用 `continue-on-error` / `if: always()`(D-03 全成功才发)。`download-artifact@v4` 的 `pattern` + `merge-multiple` 语法见 RESEARCH Standard Stack 表格引用的官方迁移文档。

---

### `launch_app.py` — macOS Cmd+Q 接管(D-07)

**Analog:** 该文件自身的 `force_exit` / `closeEvent` / 托盘菜单(`:208-292`)

**现状核心结构(逐字保留,Windows 分支不变)：**
```python
def force_exit(self) -> None:
    self._force_exit = True
    self.showNormal()
    self.close()

def closeEvent(self, event: QCloseEvent) -> None:
    if not self._force_exit and self.tray_icon is not None:
        self.hide()
        if not self._tray_notified:
            self.tray_icon.showMessage(...)
            self._tray_notified = True
        event.ignore()
        return
    self.shutdown()
    event.accept()
    QTimer.singleShot(0, QApplication.instance().quit)
```
**改动落点:** 在 `qt_app = QApplication.instance() or QApplication([])`(`:295`)之后、`setQuitOnLastWindowClosed(False)`(`:298`)附近,新增 `sys.platform == "darwin"` 分支,给 `qt_app` 挂一条独立于 `closeEvent` 的 Cmd+Q 路径,直接调用已有的 `window.force_exit()`(不新写退出逻辑,只是换一个触发源)。**Claude's Discretion** 明确三种实现手段任选(`QEvent.Quit` 重载 / `aboutToQuit` 连接 / 原生菜单项),但都必须收敛到调用既有 `force_exit()`,不要平行发明第二套 shutdown 路径。

**平台分支写法参照** `backend/config.py:23-39` 的 `if sys.platform == "win32": ... if sys.platform == "darwin": ...` 结构(同一函数内并列分支,而非拆两个函数),`launch_app.py` 里新增代码应沿用同一风格,靠近 `qt_app` 初始化处即可,不必抽独立模块。

---

### `launch_app.py` — 首启 quarantine 自剥离 + 失败兜底(D-12/D-12a)

**Analog 1(平台分支惯例):** `backend/config.py:35-38`
```python
if sys.platform == "darwin":
    # macOS：忽略 portable 标记与环境变量（D-07），固定写用户级 Application Support，
    # 不使用任何基于 sys.executable 的路径推导（Pitfall 4：.app bundle 内部结构不适用）。
    return Path.home() / "Library" / "Application Support" / APP_NAME
```
新逻辑同样只在 `sys.platform == "darwin"` 且 `_is_packaged()`(即 `sys.frozen`)为真时触发,复用 `config._is_packaged()` 判定,不要重新发明冻结态探测。

**Analog 2(失败兜底文案与命令常量,必须复用不得另起):** `frontend/src/lib/macosGatekeeperNotice.js:11`
```js
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app'
```
D-12 的 Python 侧失败弹窗给用户的命令文本应与此常量语义一致(同一条 `xattr -dr` 命令、同一个限定到具体 bundle 路径的范围,不含 `sudo`、不含全局 `spctl` 开关)。**⚠ 按 RESEARCH D-12a 的修正:此弹窗是预期的首次主路径,不是异常分支**,文案措辞应明确告知"这是正常现象",而不是当作报错处理。

**核心 subprocess 调用模式参照:** 仓库内暂无 Python 侧调用 `xattr`/`codesign` 的既有代码,`scripts/release/verify_and_upload_macos_kernel.sh`(bash)是唯一同域参照,其错误处理风格(`|| { echo "错误: ..." >&2; exit 1; }`,即"失败立即给出可操作的错误信息"而非静默吞掉)应被 Python 版翻译采用,例如:
```python
result = subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(bundle_path)], capture_output=True, text=True)
if result.returncode != 0:
    # 预期路径（D-12a）：弹窗把 GATEKEEPER_XATTR_COMMAND 同款命令原样交给用户
    ...
```

**⚠ 明确警告(遵循 phase 指导,不得提议改动 `backend/config.py`):** RESEARCH Pattern 1 已实测确认 PyInstaller 的 macOS 布局与现有 `_resource_root()` / `ENGINES_DIR` / `FRONTEND_DIST_DIR` 解析零改动兼容(`sys._MEIPASS` 指向 `Contents/Frameworks`,符号链接被 `Path.exists()`/`Path.rglob()` 透明穿透)。本 phase 涉及 `config.py` 的唯一合法引用是"读取其平台分支写法作为风格参照",**不要修改 `config.py` 本体**。若实现中发现需要改动,必须作为一条显式警告写回 SUMMARY,而不是直接改。

---

### `assets/app.icns` / `assets/dmg-background.png`(+@2x)

**Analog:** `assets/app.ico`(现有 Windows 图标,同目录同角色资产,无生成脚本可比——纯二进制文件,无代码模式可抄)

**icns 无仓库内 analog,直接采用 RESEARCH Pattern 4 的实测命令序列(本机已验证 exit 0 且产物可用)：**
```bash
mkdir icon.iconset
SRC=assets/logo-512.png
sips -z 16 16 "$SRC" --out icon.iconset/icon_16x16.png
... (完整 9 档,见 05-RESEARCH.md Pattern 4)
iconutil -c icns icon.iconset -o assets/app.icns
```
**Pitfall 5 警告:** `iconutil` 对不足尺寸的 @2x 源图静默放行(exit 0 无警告),生成后必须用 `sips -g pixelWidth -g pixelHeight` 人工抽查 + 目视检查最终图标观感,不能只看命令是否报错。

`dmg-background.png` **无任何仓库内同类资产**(全新资产类型),内容与生成方式按 CONTEXT.md D-10 决策(拖拽引导 + 底部放行提示文案,含 @2x)与 Claude's Discretion(配色/尺寸/措辞)自行产出,不套用现有资产的既有模式。

---

### `tests/test_*.py`(新增)

**Analog 1(平台分支 mock 惯例):** `tests/test_config_platform.py:22-36`
```python
def test_macos_frozen_app_root_is_application_support(self) -> None:
    with patch.object(sys, "platform", "darwin"), patch.object(
        sys, "frozen", True, create=True
    ):
        importlib.reload(config)
        expected = Path.home() / "Library" / "Application Support" / "Open-Anti-Browser"
        self.assertEqual(config.APP_ROOT, expected)
```
新增测试(覆盖 quarantine 自剥离的路径判定、Cmd+Q 平台分支是否仅在 darwin 触发)必须用同样的 `patch.object(sys, "platform", ...)` + `patch.object(sys, "frozen", ..., create=True)` 组合,且在 `tearDown` 里 `importlib.reload(config)` 复原(`:14-16`),避免污染其他测试文件的模块级常量。**关键约束(CLAUDE.md 已述):这类测试涉及 `launch_app.py` 顶层导入(`backend.browser_manager`→`services/window_manager.py`→`win32api`)在非 Windows 上会直接 ImportError**——若新逻辑写入 `launch_app.py` 顶层模块,对应测试要么只 mock 到函数级别、避免整模块 import 在 Windows CI runner 上失败,要么把可测逻辑抽成不依赖顶层 win32 导入的纯函数(建议做法:把"是否应该自剥离"、"是否应该拦截 Cmd+Q"的判定逻辑抽成独立纯函数,类似 `macosGatekeeperNotice.js` 把可测逻辑与 Vue 组件分离的思路)。

**Analog 2(mock 外部子进程调用):** `tests/test_process_termination_macos.py:8-22`
```python
@patch("backend.services.network.psutil.wait_procs")
@patch("backend.services.network.psutil.Process")
def test_sends_sigterm_before_sigkill(self, mock_process_cls, mock_wait_procs):
    parent = MagicMock()
    ...
    network.kill_process_tree(1234)
    parent.terminate.assert_called_once()
```
版本一致性校验脚本(纯 `json`/`re`,无外部子进程)可以直接用普通 unittest 断言,不需要 mock;但若把 `xattr -dr` 剥离逻辑包装成 Python 函数供测试,对 `subprocess.run` 的调用应比照此文件的 `@patch(...)` 风格打桩,不要在测试里真的执行 `xattr`。

**测试覆盖 no-analog 提示:** App Translocation 路径检测(`/AppTranslocation/` 子串判定,RESEARCH "Don't Hand-Roll"表)是全新逻辑,仓库无任何同类字符串匹配测试可比,直接写纯函数单测(输入路径字符串 → 布尔值)即可,难度低,不需要额外 analog。

---

## Shared Patterns

### 平台分支写法(适用于 `launch_app.py` 全部新增分支)
**Source:** `backend/config.py:23-39`
```python
if sys.platform == "win32":
    ...
if sys.platform == "darwin":
    # 说明性注释解释为何 darwin 分支与 win32 不同
    ...
```
**Apply to:** `launch_app.py` 的 Cmd+Q 接管、quarantine 自剥离两处新增代码。**硬约束:Windows 分支逐字不变**(CLAUDE.md「运行目标平台是 Windows」+ CONTEXT.md「Windows 现有构建行为零回归」铁律)。

### CI 从 config.py 读取而非硬编码
**Source:** `.github/workflows/build-release.yml:62`(`$chromeZipUrl = (python -c "from backend.config import CHROME_ENGINE_ZIP_URL; print(...)")`)
**Apply to:** `build-macos` job 读取 `CHROME_ENGINE_ZIP_URL_MACOS_ARM64` 的写法,以及 dmg 打包脚本按需读取版本号/常量时,一律走 `python3 -c "from backend.config import X; print(X)"` 而不是在 yml 里重复写死。

### 失败即中止 + 给出可操作错误信息
**Source:** `scripts/release/verify_and_upload_macos_kernel.sh`(全篇 `|| { echo "错误: ..." >&2; exit 1; }` 风格,例如 `:47`、`:79`、`:107`)
**Apply to:** macOS job 里的架构断言(`lipo -archs`)、签名校验(`codesign --verify --deep --strict`)、`--backend-only` 冒烟,全部沿用"失败立即打印可定位的错误信息并以非零退出码中止"的写法,不要吞掉 stderr 或静默 continue。

### 反商业滥用 / 完整性校验相关文件不可修改
**Source:** CLAUDE.md「资源完整性校验」章节 + `backend/_g.py`
**Apply to:** 本 phase 任何步骤都不得触碰 `frontend/src/lib/openSourceNotice.js`、`frontend/src/App.vue` 或 `backend/_g.py` 的哈希表;D-14 第 3 条的"断言 frontend/dist 已正确进包"是**只读校验**,不是修改这些文件。

## No Analog Found

| File | Role | Data Flow | 原因 / 权威模板落点 |
|---|---|---|---|
| `assets/dmg-background.png`(+@2x) | config/asset | file-I/O | 仓库无任何 dmg 背景图先例;内容与生成方式按 CONTEXT.md D-10 + Claude's Discretion 自行产出,不套用其他资产模式 |
| dmg 制作步骤(`create-dmg` 调用) | CI step | batch | 仓库无任何 dmg/hdiutil/create-dmg 先例;直接采用 `05-RESEARCH.md` Standard Stack + Architecture Patterns 的 `create-dmg` 参数与调用方式作为权威模板 |
| 嵌套 bundle 逐层 codesign 脚本(D-13) | CI step / utility | batch | `scripts/release/verify_and_upload_macos_kernel.sh` 只做**校验**(不做重签),没有"重签"逻辑可抄;直接采用 `05-RESEARCH.md` Pattern 2 的实测命令序列(Helper→Framework→Chromium.app→外层,非 `--deep`)作为权威模板 |
| Info.plist `plutil -replace` 补丁步骤(D-05) | CI step | transform | 仓库无 `.spec` 也无既有 plist 补丁脚本;直接采用 `05-RESEARCH.md` Pattern 3 的 `plutil -replace` 命令(仅需补 `CFBundleShortVersionString`/`CFBundleVersion`/`LSMinimumSystemVersion` 三键,`NSHighResolutionCapable` 等已由 PyInstaller CLI 自动写入,不必手工补) |

## Metadata

**Analog 搜索范围:** `.github/workflows/`、`scripts/release/`、`backend/`(config.py、_g.py）、`launch_app.py`、`frontend/src/lib/`、`tests/`、`assets/`
**扫描文件数:** ~15(含 grep 命中的平台分支测试文件与既有 workflow/脚本)
**Pattern 提取日期:** 2026-07-28
