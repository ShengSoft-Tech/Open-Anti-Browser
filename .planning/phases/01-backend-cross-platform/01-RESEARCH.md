# Phase 1: 后端跨平台基础适配 - Research

**Researched:** 2026-07-24
**Domain:** Python 后端跨平台适配(pip 依赖标记、条件导入、subprocess creationflags、冻结态路径解析)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 平台门控放在 `backend/services/window_manager.py` 内部:模块顶层按 `sys.platform` 判断,Windows 照常导入 win32api 系列;非 Windows 时导出同名函数但一律抛 RuntimeError(如「窗口排列仅在 Windows 上可用」)。`browser_manager.py:36` 的导入语句与其他调用方零改动。
- **D-02:** 错误响应沿用现状:HTTPException 400 + 中文 detail(main.py 现有 try/except 包裹自动生效),不引入专用状态码或机器可读错误码字段。前端平台门控将来依赖 Phase 3 的 capabilities API,不靠错误码判断。
- **D-03:** 拦截范围 = 窗口排列四个端点(`/api/synchronizer/monitors`、`show-windows`、`uniform-size`、`arrange-windows`)**加上**同步器启动(`/api/synchronizer/start` 等入口)。macOS 上同步器整体不可用,不允许出现半可用状态。— **Reversibility:** reversible — 后续里程碑做 CDP-only 跨平台同步(SYNC-01)时放开即可。
- **D-04:** `main.py:485` 的 `os.startfile(raw_url)` 在 Phase 1 顺手修为跨平台实现(标准库 `webbrowser.open` 或平台分支),消除已知的 macOS 运行时崩溃点。**研究发现:此改动在当前代码库中已经存在(见 Common Pitfalls Pitfall 1),规划时应改为验证性任务而非代码修改任务。**
- **D-05:** config.py 做**平台感知结构化**,不是最小补丁:可写根、引擎可执行路径、`ENGINE_METADATA`、内核下载 URL 统一按平台解析;macOS 的内核下载 URL 先留占位(Phase 2 产出 kernel release 资产后填入真实 URL)。约束:Windows 平台解析出的所有值必须与现值完全一致(零回归)。— **Reversibility:** costly — ENGINE_METADATA 结构被 storage.py、browser_manager.py、CI workflow(读 CHROME_ENGINE_ZIP_URL)多处消费,结构一旦定型 Phase 2/3/5 都在其上叠加。
- **D-06:** macOS 路径按 XPLAT-03 锁定值:冻结态可写根 `~/Library/Application Support/Open-Anti-Browser/`;Chrome 引擎可执行路径解析到 `Chromium.app/Contents/MacOS/Chromium`(位于 ENGINES_DIR 下)。开发态两平台继续用 PROJECT_ROOT。
- **D-07:** portable 模式为 **Windows 专属特性**:macOS 上忽略 `OPEN_ANTI_BROWSER_PORTABLE` 环境变量与 `portable.mode` 标记,始终写 `~/Library/Application Support/`。理由:数据写入 .app bundle 违反 macOS 惯例且会破坏 Phase 5 的 `codesign --verify --deep --strict` 硬门禁。
- **D-08:** `ENGINE_METADATA` 的 firefox 条目在 macOS **保留不删**(路径按平台解析,引擎不存在即天然不可用),避免遍历双引擎结构的代码(storage.py 等)连锁报错;「firefox 在 macOS 不可用」由 Phase 3 capabilities API 声明、Phase 4 前端隐藏。已有 firefox 配置的 profiles.json 在 macOS 上必须能正常加载。
- **D-09:** `requirements.txt` 中 `pywin32` 与 `ruyipage` 都加 `; sys_platform == "win32"` 环境标记。ruyipage 仅服务 Firefox 同步(macOS 已排除 Firefox),且 `synchronizer.py:14-18` 的导入已有 try/except 保护,macOS 不装是安全的。
- **D-10:** `pyinstaller` 等构建期依赖**不拆分**,保持在 requirements.txt(两平台都需要,Phase 5 macOS 打包也用),不引入 requirements-build.txt 之类的新依赖文件结构。
- **D-11:** 用户有 Windows 机器/虚拟机:Phase 1 完成后在 Windows 上手动跑全量 `python -m unittest discover -s tests -v` 作为零回归验收。
- **D-12:** Phase 1 新增一个 push/PR 触发的 CI 测试 workflow(独立于现有发版 workflow):`windows-latest` 跑全量 unittest;macOS runner 跑非 Windows 依赖的测试子集。零回归从一次性验证变成持续保障。
- **D-13:** 为新增平台分支补两平台可跑的单元测试:config 路径解析(mock `sys.platform` / 冻结态)、window_manager 非 Windows 报错、runtime_control 派生参数平台条件化、窗口/同步 API 的 macOS 拦截行为。注:Phase 1 完成后 `browser_manager` 在 macOS 可导入,CLAUDE.md 中「非 Windows 无法跑相关测试」的限制随之大幅解除,新测试应利用这一点。

### Claude's Discretion

- window_manager 条件化的具体实现形式(顶层 if/else、桩函数组织方式)。
- `SYSTEM_CHROME_EXECUTABLE` / `SYSTEM_FIREFOX_EXECUTABLE` 在 macOS 的具体值(如 `/Applications/Chromium.app/...`)。
- `runtime_control.py` 在 POSIX 上替代 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` 的具体机制(如 `start_new_session=True`),只要满足 XPLAT-04 的派生/检活/停止语义。
- CI 测试 workflow 的文件命名、触发条件细节、macOS 测试子集的圈定方式。

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.(同步器的 CDP-only 跨平台化已在 REQUIREMENTS.md Future Requirements 中记录为 SYNC-01,非本次讨论新增。)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XPLAT-01 | macOS 用户可以直接 `pip install -r requirements.txt` 成功(pywin32 等仅 Windows 依赖加 sys_platform 环境标记) | 见 Standard Stack(PEP 508 标记方案,本机 pip dry-run 实测验证)、Package Legitimacy Audit(pywin32/ruyipage 现状核对) |
| XPLAT-02 | 后端在 macOS 可正常导入与启动(window_manager 条件导入;窗口排列 API 在 macOS 返回"仅 Windows 支持"错误,Windows 行为字节级不变) | 见 Architecture Patterns Pattern 1(window_manager 条件导入骨架)、Pattern 3(synchronizer 门禁,D-03 拦截范围核对)、Common Pitfalls Pitfall 3(sys.platform vs os.name) |
| XPLAT-03 | config.py 平台分支生效:冻结态可写根为 `~/Library/Application Support/Open-Anti-Browser/`,Chrome 引擎路径为 `Chromium.app/Contents/MacOS/Chromium` | 见 Code Examples(config.py 平台化骨架)、Common Pitfalls Pitfall 4(macOS .app bundle 结构对冻结态路径推导的影响) |
| XPLAT-04 | 纯后端模式(`--backend-only`)在 macOS 可派生、检活与停止(creationflags 平台条件化) | 见 Architecture Patterns Pattern 2(POSIX 后台派生实现,本机实测 creationflags 行为)、Common Pitfalls Pitfall 2(CREATE_NEW_PROCESS_GROUP 与 DETACHED_PROCESS 兜底值风险不对称) |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

以下为项目级强制约定,规划与实现必须遵守,不得与之冲突:

- **目标平台语义:** 运行目标平台是 Windows,即使在 macOS/Linux 上开发,涉及进程/窗口的代码也要按 Windows 语义来写——本 phase 的目标恰恰是在保留 Windows 语义的前提下补齐 macOS 分支,不能反向"把 Windows 代码改成更通用但行为不同"的写法。
- **测试运行方式:** Python 测试是纯 `unittest`(无 pytest 配置),必须从仓库根目录运行;凡是导入 `backend.browser_manager`、`backend.main` 或 `launch_app` 的测试在 pywin32 未安装的非 Windows 环境上目前无法运行——Phase 1 完成后这一限制应大幅解除(window_manager 改为条件导入后,这条导入链在 macOS 上不再触发 win32api 导入错误)。
- **打桩约定:** 外部进程/网络依赖一律用 `unittest.mock.patch` 打桩,参考 `tests/test_sync_regressions.py` 的 FakeSyncClient 模式;新增测试(D-13)应遵循同样的打桩风格,不引入 pytest fixture 或新测试框架。
- **资源完整性校验(`backend/_g.py`):** 对 `frontend/src/lib/openSourceNotice.js` 与 `frontend/src/App.vue` 做 SHA-256 哈希锁定,构建/桌面启动时触发。本 phase 不涉及这两个文件,不需要同步更新 `_g.py` 中的哈希值——但需注意 `launch_app.main()` 无条件调用 `_0x2f("runtime")`(即 `_7("runtime")`),该调用本身平台无关(仅做 Path/hash 操作),不会在 macOS 上因平台原因失败,规划时不需要为此单独设计防护任务。
- **路径常量单一来源:** 所有路径常量从 `backend/config.py` 导入,平台分支必须收敛在 config.py 内——与 D-05 一致,规划任务不应该在其他文件里新增独立的平台路径判断。
- **commit message 约定:** 英文短句(参考 git log 风格,如 `Fix Firefox geo timezone resolution`);API 错误信息与用户可见文案用中文——D-01/D-02 的 RuntimeError 文案(「窗口排列仅在 Windows 上可用」)已符合此约定。
- **版本号同步:** 若本 phase 任何改动触及版本号(通常不会,本 phase 是纯适配性改动,不建议顺带升版本),需同时改 `frontend/package.json` 与 `backend/main.py` 的两个 FastAPI `version` 字段——规划时若无版本号改动需求,应明确排除,不要顺带升版本。

## Summary

本 phase 的核心工作全部落在标准库与已知语言特性范围内,不涉及新框架或新第三方库选型,因此研究重点是**在本仓库当前代码上逐行验证根因假设**,而不是探索技术选型。本次研究直接读取了 `requirements.txt`、`backend/services/window_manager.py`、`backend/config.py`、`backend/runtime_control.py`、`backend/main.py`、`backend/services/chrome.py`/`firefox.py`/`synchronizer.py`/`network.py`、`launch_app.py`、`backend/_g.py` 与全部 7 个测试文件,并在本机(macOS/darwin,Python 3.14)用真实 Python 解释器验证了两个关键假设:

1. `subprocess.Popen(creationflags=...)` 在 POSIX 上,**非零** creationflags 会直接抛 `ValueError: creationflags is only supported on Windows platforms`;**零值**则合法通过。这精确解释了 `runtime_control.py` 里 `DETACHED_PROCESS` 兜底值 `0x00000008`(非零)是 macOS 下 `--backend-only` 崩溃的根因,而 `chrome.py`/`firefox.py` 里 `CREATE_NEW_PROCESS_GROUP` 兜底值 `0` 在 POSIX 上是安全的、不阻塞本 phase。
2. pip 的 PEP 508 环境标记(`; sys_platform == "win32"`)在本机用 `pip install --dry-run` 实测有效——macOS 环境下 pip 会正确跳过打了标记的 `pywin32`,不产生解析错误。

此外发现一个**与 CONTEXT.md 的 code_context 不一致的事实**:main.py 里 `os.startfile` 相关代码(D-04 提到的"main.py:485 修复点")在当前代码库中**已经是跨平台实现**(`git blame` 显示该分支写法早在 2026-04-18 的提交 `8afdce3` 中就已存在,而非本次要修的问题)。规划阶段应当据实核销 D-04 对应的任务,不要重复"修复"一个已经修好的地方,只需在验证清单里确认它、无需新增改动任务。

**Primary recommendation:** 严格按 D-01~D-13 的既定决策实施,把改动收敛在 4 个文件(`requirements.txt`、`backend/services/window_manager.py`、`backend/config.py`、`backend/runtime_control.py`)+ `backend/services/synchronizer.py`(新增一处平台门禁,D-03 要求同步器整体不可用,现有代码里没有天然的门禁点,需要新增)。Windows 分支必须原封不动(`sys.platform == "win32"` 判断为真时执行的代码路径不应有任何字符级改动),新增分支只在 `else` 侧插入。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| pip 依赖解析(sys_platform 标记) | 依赖声明(requirements.txt) | — | pip/PEP 508 在安装时求值,不涉及运行时代码 |
| 窗口排列/窗口同步平台门禁 | API / Backend(FastAPI 路由 + BrowserManager + services 层) | — | HTTPException 转换发生在 main.py,RuntimeError 抛出发生在 services 层,门禁逻辑应尽量下沉到 services 层单点判断 |
| 路径解析(可写根/引擎路径/资源根) | API / Backend(config.py 单一来源) | — | CLAUDE.md 明确"所有路径常量从 config.py 导入",平台分支必须收敛在这一层 |
| 纯后端模式派生/检活/停止 | API / Backend(runtime_control.py) | OS 进程管理 | Popen creationflags 与 psutil 检活都是后端进程管理职责,不涉及前端或存储层 |
| CI 零回归验证 | CI/CD(GitHub Actions) | 测试(tests/) | 新增 workflow 属于工程基础设施层,与业务代码分离 |

## Package Legitimacy Audit

本 phase **不引入任何新依赖**,只对 `requirements.txt` 中两个已在使用多个版本周期的既有包(`pywin32`、`ruyipage`)追加 PEP 508 环境标记(`; sys_platform == "win32"`),不改变其版本号或来源。因此正式的"新包引入"审计门禁不适用,但为完整性记录如下:

| Package | Registry | Age(按仓库现状) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pywin32 | PyPI | 长期维护包(>10 年),已在本仓库固定使用 | 高(周下载数千万级) | github.com/mhammond/pywin32 | OK | 保留,仅追加 `sys_platform == "win32"` 标记 |
| ruyipage | PyPI | 本仓库既有依赖,来自协作方 LoseNine 维护的 Firefox 指纹内核配套包 | 未知(小众专用包) [ASSUMED] | github.com/LoseNine/ruyipage(见 firefox.py 引用) | OK(已被现有 try/except 保护,风险已被现状缓解) | 保留,仅追加 `sys_platform == "win32"` 标记 |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none — 两者均为仓库已长期使用的既有依赖,非本 phase 新引入,不触发 slopsquatting 风险模型。

## Standard Stack

本 phase 不引入新的第三方库;全部实现基于 Python 标准库能力。

### Core

| 能力 | 标准做法 | 用途 | 为什么是标准做法 |
|------|---------|------|-----------------|
| 依赖条件安装 | PEP 508 environment markers(`; sys_platform == "win32"`) | 让 pip 按目标平台跳过不兼容依赖 | pip/setuptools 官方支持的标准语法,[VERIFIED: 本机 `pip install --dry-run` 实测](见 Code Examples) |
| 平台分支判断 | `sys.platform`(取值 `"win32"` / `"darwin"` / `"linux"`) | 模块级/函数级平台门禁 | 标准库文档明确的跨平台判断入口;比 `os.name`(仅 `"nt"`/`"posix"`,分不清 macOS/Linux)更精确,推荐用于新代码 |
| POSIX 进程分离 | `subprocess.Popen(..., start_new_session=True)` | 替代 Windows 的 `DETACHED_PROCESS \| CREATE_NEW_PROCESS_GROUP` | Python 标准库文档记载的 POSIX 等价机制;`start_new_session=True` 内部调用 `setsid()`,使子进程脱离父进程会话,达到"派生后台进程、不随父进程退出"的等价效果 [CITED: docs.python.org/3/library/subprocess.html] |
| 冻结态检测 | `getattr(sys, "frozen", False)` + `sys._MEIPASS` | 区分开发态/PyInstaller 冻结态 | 现有 `config.py` 已用此模式,PyInstaller 官方文档记载的标准检测方式,直接复用即可,无需新写法 [VERIFIED: 现有代码 + PyInstaller 官方约定] |
| macOS 应用数据目录 | `~/Library/Application Support/<AppName>/` | 冻结态可写根 | Apple 官方文件系统编程指南记载的标准约定位置,已在 D-06 锁定为决策,非本次探索项 |
| 浏览器打开 URL | `webbrowser.open_new_tab()` | 跨平台打开系统默认浏览器 | 标准库封装了各平台差异(macOS 用 `open`,Linux 用 `xdg-open`);main.py 已经这样实现,`os.startfile` 仅在 `os.name == "nt"` 分支使用 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sys.platform == "win32"` | `platform.system() == "Windows"` | 效果等价,但项目里 `os.name == "nt"` 与 `sys.platform` 已混用(main.py 用 `os.name`,建议新代码统一用 `sys.platform`,与 D-01 描述一致,避免第三种写法混入) |
| `start_new_session=True` | `os.setsid()` + `preexec_fn` | `preexec_fn` 在 CPython 文档中已标注"在多线程程序中不安全"且计划弃用倾向,`start_new_session=True` 是官方推荐的现代替代,不应使用 `preexec_fn` |

**Installation:**
```bash
# requirements.txt 改动示例(不改变版本号,只加标记)
pywin32>=308; sys_platform == "win32"
ruyipage>=1.0.0; sys_platform == "win32"
```

**Version verification:** 本 phase 不升级任何包版本,`pywin32>=308`、`ruyipage>=1.0.0` 均维持现状。已用 `pip install --dry-run` 在本机(darwin)验证标记语法生效(见 Code Examples)。

## Architecture Patterns

### System Architecture Diagram

```
pip install (macOS)                                    pip install (Windows)
       │                                                        │
       ▼                                                        ▼
requirements.txt (PEP 508 markers) ──skip pywin32/ruyipage──► 全部安装
       │
       ▼
backend 模块导入链
  main.py → browser_manager.py → services/window_manager.py
                                        │
                          sys.platform 判断（模块顶层）
                          ┌─────────────┴─────────────┐
                          ▼                            ▼
                   win32: import win32api 等      非 win32: 桩函数
                   （现状不变，字节级一致）         （同名导出，调用即 raise RuntimeError）
                                                        │
                                                        ▼
                                          browser_manager.py 调用处
                                          （无需改动，异常沿现有
                                           try/except → HTTPException(400) 路径冒泡）

--backend-only 启动流程
  runtime_control.start_backend_only()
       │
       ▼
  sys.platform 判断（函数内）
  ┌──────────────┴──────────────┐
  ▼                             ▼
win32: creationflags=          POSIX: start_new_session=True
DETACHED_PROCESS |             （不传 creationflags，或传 0）
CREATE_NEW_PROCESS_GROUP
       │                             │
       └──────────────┬──────────────┘
                       ▼
              subprocess.Popen(...)
                       │
                       ▼
        psutil.Process(pid).is_running()（跨平台一致，无需分支）
                       │
                       ▼
        kill_process_tree()（已用 psutil，跨平台一致，无需改动）

config.py 路径解析
  sys.platform 判断（模块顶层，_writable_root / SYSTEM_*_EXECUTABLE / ENGINE_METADATA）
  ┌──────────────┴──────────────┐
  ▼                             ▼
win32: LOCALAPPDATA / chrome.exe   darwin: ~/Library/Application Support/
                                    / Chromium.app/Contents/MacOS/Chromium
```

### Recommended Project Structure

本 phase 不新增目录,改动全部落在既有文件内:

```
backend/
├── config.py                 # 平台分支：_writable_root / SYSTEM_*_EXECUTABLE / ENGINE_METADATA
├── runtime_control.py        # 平台分支：creationflags / start_new_session
├── services/
│   ├── window_manager.py     # 平台分支：win32 导入 vs 桩函数
│   └── synchronizer.py       # 新增：BrowserSynchronizer.start() 顶部平台门禁（D-03）
└── main.py                   # 无需改动（os.startfile 分支已是跨平台实现，见下方 Common Pitfalls）

.github/workflows/
└── ci-tests.yml              # 新增：push/PR 触发，windows-latest 全量 + macos-latest 子集（D-12，命名由 Claude 裁量）

tests/
├── test_config_platform.py       # 新增（D-13）：mock sys.platform / frozen 态，验证路径解析
├── test_window_manager_posix.py  # 新增（D-13）：非 Windows 下四个函数均 raise RuntimeError
└── test_runtime_control_posix.py # 新增（D-13）：验证 POSIX 分支不传非法 creationflags
```

### Pattern 1: 条件导入 + 桩函数(D-01 的实现形态)

**What:** 模块顶层按 `sys.platform` 分两路——Windows 路径正常 `import win32api` 等并保留全部现有函数体;非 Windows 路径下,导出**同名**函数,但函数体只做一件事:`raise RuntimeError("...")`。

**When to use:** 当调用方(`browser_manager.py`)已经用 `from .services.window_manager import arrange_windows, list_monitors, set_uniform_size, show_windows` 做具名导入,且不希望改动调用方代码时。

**Example:**
```python
# backend/services/window_manager.py
from __future__ import annotations

import sys
from typing import Any, Callable

if sys.platform == "win32":
    import math
    import psutil
    import win32api
    import win32con
    import win32gui
    import win32process

    ENGINE_WINDOW_CLASSES = {...}

    def list_monitors() -> list[dict[str, Any]]:
        ...  # 现状不变，字节级一致

    def show_windows(runtime_lookup, profile_ids):
        ...  # 现状不变

    def set_uniform_size(runtime_lookup, profile_ids):
        ...  # 现状不变

    def arrange_windows(runtime_lookup, profile_ids, monitor_id=None, arrange_mode="grid"):
        ...  # 现状不变

else:
    _UNSUPPORTED_MSG = "窗口排列仅在 Windows 上可用"

    def list_monitors() -> list[dict[str, Any]]:
        raise RuntimeError(_UNSUPPORTED_MSG)

    def show_windows(runtime_lookup: Callable[[str], dict[str, Any] | None], profile_ids: list[str]) -> dict[str, Any]:
        raise RuntimeError(_UNSUPPORTED_MSG)

    def set_uniform_size(runtime_lookup: Callable[[str], dict[str, Any] | None], profile_ids: list[str]) -> dict[str, Any]:
        raise RuntimeError(_UNSUPPORTED_MSG)

    def arrange_windows(runtime_lookup, profile_ids, monitor_id=None, arrange_mode="grid") -> dict[str, Any]:
        raise RuntimeError(_UNSUPPORTED_MSG)
```
[VERIFIED: 现有文件结构 backend/services/window_manager.py 全文已读取，改动点已逐行核对]

### Pattern 2: POSIX 后台派生(XPLAT-04 的实现形态)

**What:** `runtime_control.py` 的 `start_backend_only()` 里 `subprocess.Popen(..., creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)` 改为平台条件化。

**Example:**
```python
# backend/runtime_control.py
import sys

_POPEN_KWARGS: dict[str, Any] = {}
if sys.platform == "win32":
    _POPEN_KWARGS["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
else:
    _POPEN_KWARGS["start_new_session"] = True

process = subprocess.Popen(
    command,
    cwd=_launcher_cwd(),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    close_fds=True,
    env={**os.environ},
    **_POPEN_KWARGS,
)
```
[VERIFIED: 本机 darwin/Python 3.14 实测 `creationflags=0x00000008` 抛 `ValueError: creationflags is only supported on Windows platforms`；`creationflags=0` 通过；CPython `subprocess.py` 源码 `if creationflags != 0: raise ValueError(...)` 确认判断条件是"非零即报错"而非"任何显式传参即报错"]

**注意:** `DETACHED_PROCESS`/`CREATE_NEW_PROCESS_GROUP` 两个 module 级常量本身的 `getattr(subprocess, "...", fallback)` 写法不需要改——问题只出在"把它们无条件传给 Popen"这一步。保留这两个常量定义(Windows 分支仍然用得到),只改 Popen 调用点。

### Pattern 3: 同步器整体禁用(D-03 的实现形态)

**What:** `BrowserSynchronizer.start()`(`backend/services/synchronizer.py:1393`)当前没有任何平台判断,是 `/api/synchronizer/start` 等入口的唯一执行体。D-03 要求"同步器启动"整体在 macOS 拦截,需要在此新增门禁,而不是像窗口排列那样在 `window_manager.py` 里做——因为同步逻辑本身(CDP WebSocket/Marionette 事件转发)并不依赖 win32 API,是独立的一套阻断点。

**Example:**
```python
# backend/services/synchronizer.py
import sys

class BrowserSynchronizer:
    def start(self, master_profile_id: str, follower_profile_ids: list[str], options: dict[str, Any] | None = None) -> dict[str, Any]:
        if sys.platform != "win32":
            raise RuntimeError("窗口同步仅在 Windows 上可用")
        master_profile_id = str(master_profile_id or "").strip()
        ...  # 现状不变
```
[VERIFIED: 现有 backend/services/synchronizer.py:1393-1414 全文已读取，确认此处是唯一自然门禁点]

**范围核对(D-03):** 需要拦截的端点 = `/api/synchronizer/monitors`、`/api/synchronizer/show-windows`、`/api/synchronizer/uniform-size`、`/api/synchronizer/arrange-windows`(这四个走 `window_manager.py` 桩函数自然拦截)**加上** `/api/synchronizer/start`(走上面的 `BrowserSynchronizer.start()` 门禁)。`main.py` 里所有这些端点已经有 `try/except Exception as exc: raise HTTPException(400, str(exc))` 包裹(main.py:260-320 已核对),RuntimeError 会自动转换为 400,无需改动 main.py。

### Anti-Patterns to Avoid

- **在 `browser_manager.py` 里加 `if sys.platform == "win32"` 判断:** D-01 明确要求调用方零改动,平台分支必须收敛在 `window_manager.py`/`synchronizer.py` 内部,否则平台判断逻辑会分散到多处,难以维护也难以测试。
- **用 `preexec_fn` 实现 POSIX 后台分离:** Python 官方文档警告 `preexec_fn` 在多线程场景下有死锁风险且行为在未来版本可能变化,应使用 `start_new_session=True`。
- **把 `creationflags` 兜底值设为 Windows 专属常量的原始整数值(如硬编码 `0x00000008`)传给 POSIX 分支:** 即使传 0 也要通过平台分支显式区分,不要依赖"POSIX 恰好能接受非 Windows 分支的默认值"这种隐式行为——本次验证已确认 `DETACHED_PROCESS` 现有兜底值 `0x00000008` 是非零的、会直接崩溃,不能假设兜底值天然安全。
- **改动 Windows 分支代码的同时"顺手"重构:** D-05/D-11/D-12 反复强调 Windows 现状字节级不变,任何 `if sys.platform == "win32":` 分支下的代码必须是现有代码的逐字迁移,不要在迁移时"顺便"优化写法。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 判断进程是否存活/是否为孤儿/僵尸进程 | 自己解析 `/proc` 或调用 `kill -0` | `psutil.Process(pid).is_running()` + `.status() != psutil.STATUS_ZOMBIE`(已在用) | psutil 已抽象跨平台差异,现有 `runtime_control.py:_is_pid_alive` 已经是跨平台正确实现,不需要改动 |
| 结束进程树 | 自己遍历子进程再逐个 kill | `psutil` 的 `children(recursive=True)` + `kill()`(已在用,`services/network.py:kill_process_tree`) | 已验证跨平台正确,Phase 1 不需要碰这个函数 |
| 打开系统默认浏览器 | 自己判断平台调用 `open`/`xdg-open`/`start` | `webbrowser.open_new_tab()`(已在用) | 标准库已封装,main.py 现状已经是这个模式,不需要新增代码 |
| POSIX 后台派生子进程 | 手写 `os.fork()` + `os.setsid()` 双重 fork 之类的 daemonize 逻辑 | `subprocess.Popen(start_new_session=True)` | 标准库参数已提供等价能力,没有必要手写更复杂的 daemonize 流程,当前需求只是"派生后不随父进程退出"而非严格意义的 Unix daemon |

**Key insight:** 本 phase 所有"能力缺口"在标准库或既有依赖(psutil)里都已有现成解法,真正的工作量在于**把判断点从隐式的兜底值(`getattr(..., fallback)`)改为显式的平台分支**,而不是引入新工具。

## Common Pitfalls

### Pitfall 1: 误以为 `os.startfile` 仍需修复(D-04 状态核销)

**What goes wrong:** 按 CONTEXT.md 的 code_context 描述去"修复" `main.py:485` 的 `os.startfile`,但实际上这段代码已经是跨平台实现。

**Why it happens:** CONTEXT.md 的 code_context 编写时间与代码实际状态之间存在偏差——`git blame` 显示这段 `if os.name == "nt": os.startfile(...) else: webbrowser.open_new_tab(...)` 的写法在提交 `8afdce3`(2026-04-18)就已存在,早于本次 phase 讨论。

**How to avoid:** 规划阶段直接核实 `backend/main.py` 中 `open_system_url` 函数现状(第 474-491 行),确认其已经是:
```python
try:
    if os.name == "nt":
        os.startfile(raw_url)  # type: ignore[attr-defined]
    else:
        webbrowser.open_new_tab(raw_url)
except Exception as exc:
    raise HTTPException(status_code=400, detail=f"打开链接失败：{exc}") from exc
```
将 D-04 对应的任务改为"验证性任务"(跑一条 macOS 冒烟测试确认此端点可用),而不是"修改代码"任务,避免在计划里产生一个无事可做、验证会显示"文件未变化"的空任务。

**Warning信号:** 如果 diff 中 `main.py` 出现改动却发现改动前后逻辑完全一致,说明该任务本就不需要执行。

### Pitfall 2: `CREATE_NEW_PROCESS_GROUP` 与 `DETACHED_PROCESS` 两个兜底值的风险不对称

**What goes wrong:** 容易把 `chrome.py`/`firefox.py` 里的 `CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)` 和 `runtime_control.py` 里的 `DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)` 一视同仁地认为"反正都是 getattr 兜底,应该都要改"。

**Why it happens:** 两处写法看起来结构一致,但兜底数值不同——前者兜底为 `0`(POSIX 上传 `creationflags=0` 合法,已实测确认),后者兜底为非零值 `8`(POSIX 上会直接 `ValueError`)。

**How to avoid:** 只改 `runtime_control.py` 的 Popen 调用点(XPLAT-04 范围内);`chrome.py`/`firefox.py` 的 Popen 调用点保持不变(这些属于 Phase 3 macOS Chrome 启动链路的范围,当前 phase 不应该动,动了反而超出边界)。

**Warning signs:** 如果计划里出现"顺便把 chrome.py/firefox.py 的 creationflags 也改一下"的任务,应该被拒绝——这是范围蔓延,且 CONTEXT.md 已经在 code_context 里明确排除了这两处("不阻塞 Phase 1")。

### Pitfall 3: `sys.platform` vs `os.name` 混用

**What goes wrong:** 代码库里已经同时存在 `os.name == "nt"`(main.py)和即将新增的 `sys.platform == "win32"`(config.py/window_manager.py/runtime_control.py/synchronizer.py)两种平台判断写法,如果新代码不统一,后续维护者会困惑到底该用哪个。

**Why it happens:** 两者在 Windows/POSIX 二元判断上等价,但 `os.name` 无法区分 macOS 和 Linux(都是 `"posix"`),而本仓库明确只支持 Windows + macOS 两个平台,`sys.platform` 更精确(`"darwin"` vs `"linux"` 可区分,为未来可能的 Linux 排除逻辑留出空间)。

**How to avoid:** 新增代码统一用 `sys.platform == "win32"` 判断(与 CONTEXT.md D-01 描述的措辞一致);已有的 `main.py:os.name == "nt"` 保持不变(属于"Windows 现状字节级不变"的范围,不要因为"统一风格"去改动这个已经工作正常的判断)。

**Warning signs:** 如果计划任务里出现"统一 main.py 的平台判断写法",这属于非必要的范围蔓延,应排除。

### Pitfall 4: 冻结态判断需要同时处理 macOS `.app` bundle 结构

**What goes wrong:** macOS 打包后,`sys.executable` 指向 `.app/Contents/MacOS/<binary>`,如果直接套用 Windows 现有的"`sys.executable` 所在目录"逻辑(`Path(sys.executable).resolve().parent`)去寻找 `LOCALAPPDATA` 等价物或引擎目录,会得到 `.app/Contents/MacOS/` 而不是期望的 `.app` 顶层或用户级路径。

**Why it happens:** `_writable_root()`(config.py:23-34)目前的 Windows 分支用 `executable_dir = Path(sys.executable).resolve().parent` 来判断 portable marker 文件是否存在;这个逻辑在 D-07 里已经被裁定为"Windows 专属特性",macOS 分支不应该复用这段路径推导,而应直接返回 `Path.home() / "Library" / "Application Support" / APP_NAME`,不依赖 `sys.executable` 的位置。

**How to avoid:** 按 D-06/D-07 实现:macOS 冻结态分支直接返回固定的 `~/Library/Application Support/Open-Anti-Browser/`,不引入任何基于 `sys.executable` 路径推导的 portable 逻辑;Phase 5 打包验证时需要确认 `.app` bundle 内不会意外写入数据(codesign 深度校验的前提)。

**Warning signs:** 如果新增的 macOS 分支代码里出现 `Path(sys.executable).resolve().parent` 字样,说明可能在无意中复用了 Windows 专属的 portable 判断逻辑。

## Code Examples

### 验证 sys_platform 环境标记生效(本机实测)
```bash
# Source: 本机实测（darwin, Python 3.14, pip 26.0.1），非训练知识引用
$ pip install --dry-run 'pywin32>=308; sys_platform == "win32"' 'psutil>=5.9.8'
Ignoring pywin32: markers 'sys_platform == "win32"' don't match your environment
Collecting psutil>=5.9.8
  Using cached psutil-7.2.2-cp36-abi3-macosx_11_0_arm64.whl.metadata (22 kB)
Would install psutil-7.2.2
```
[VERIFIED: 本机 pip dry-run 实测]

### 验证 creationflags 平台限制(本机实测)
```python
# Source: 本机实测（darwin, Python 3.14），并对照 CPython subprocess.py 源码
import subprocess
subprocess.Popen(['/bin/echo', 'hi'], creationflags=0x00000008)
# -> ValueError: creationflags is only supported on Windows platforms

subprocess.Popen(['/bin/echo', 'hi'], creationflags=0)
# -> 正常启动，无异常
```
[VERIFIED: 本机实测 + CPython subprocess.py 源码 `if creationflags != 0: raise ValueError(...)`]

### config.py 平台化骨架(D-05/D-06/D-07 的实现形态)
```python
# backend/config.py
import sys

def _writable_root() -> Path:
    if _is_packaged():
        if sys.platform == "win32":
            executable_dir = Path(sys.executable).resolve().parent
            if os.environ.get("OPEN_ANTI_BROWSER_PORTABLE") == "1":
                return executable_dir
            if (executable_dir / PORTABLE_MARKER).exists():
                return executable_dir
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / APP_NAME
            return Path.home() / "AppData" / "Local" / APP_NAME
        if sys.platform == "darwin":
            # macOS：忽略 portable 标记与环境变量（D-07），固定写用户级 Application Support
            return Path.home() / "Library" / "Application Support" / APP_NAME
    return PROJECT_ROOT


if sys.platform == "darwin":
    SYSTEM_CHROME_EXECUTABLE = Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
    SYSTEM_FIREFOX_EXECUTABLE = Path("/Applications/Firefox.app/Contents/MacOS/firefox")  # 保留字段但 macOS 不启用（D-08）
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox"  # macOS 无 firefox 内核，路径存在但文件不存在（D-08 自然不可用）
else:
    SYSTEM_CHROME_EXECUTABLE = Path(fr"C:\Users\{USERNAME}\AppData\Local\Chromium\Application\chrome.exe")
    SYSTEM_FIREFOX_EXECUTABLE = Path(r"C:\Program Files\Mozilla Firefox\firefox.exe")
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"
    DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox.exe"
```
[ASSUMED: 具体的 `SYSTEM_CHROME_EXECUTABLE`/`SYSTEM_FIREFOX_EXECUTABLE` macOS 路径值属于 CONTEXT.md "Claude's Discretion" 范围，规划时应最终确认——Chromium.app 是否真的安装在 `/Applications/` 还是通过 Homebrew Cask 等其他位置，需要在实现时结合 Phase 2 的内核打包形态最终定；本 phase 只需保证路径解析结构正确，具体系统级路径不影响 XPLAT-01~04 的验收标准（验收标准锁定的是 ENGINES_DIR 下的路径，不是 SYSTEM_* 字段）]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `preexec_fn=os.setsid` 实现 POSIX 后台派生 | `subprocess.Popen(start_new_session=True)` | Python 3.2+ 起提供 `start_new_session` 参数 | 更安全（避免 `preexec_fn` 在多线程程序中的已知问题），本仓库应直接使用新参数,不需要考虑旧写法 |
| `os.name` 判断平台 | `sys.platform` 判断平台 | 无版本变更,是两套并存的标准库 API,长期共存 | 本仓库新增平台分支代码应统一选用 `sys.platform`（可区分 darwin/linux）,与已有 `os.name` 判断（main.py）共存但不强行统一 |

**Deprecated/outdated:** 无——本 phase 涉及的标准库 API 均为当前稳定推荐用法,没有过时/废弃的 API 需要规避。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SYSTEM_CHROME_EXECUTABLE`/`SYSTEM_FIREFOX_EXECUTABLE` 在 macOS 的具体值(如 `/Applications/Chromium.app/Contents/MacOS/Chromium`) | Code Examples | 低——这两个字段是"系统级已安装浏览器"的检测路径,不是 XPLAT-01~04 验收标准锁定的路径(验收标准锁定的是 `ENGINES_DIR` 下的 bundle 路径);即使写错,只影响"系统安装检测"这一辅助能力,不影响 Phase 1 五条成功标准 |
| A2 | ruyipage 包的具体下载量/受欢迎程度描述 | Package Legitimacy Audit | 低——该包本就是既有依赖(非本 phase 新增),且已有 try/except 保护,即使评估偏差也不影响功能正确性 |

**说明:** 本次研究里绝大多数关键判断(subprocess creationflags 行为、pip sys_platform 标记生效、现有代码结构)都通过**在本机直接执行验证**,因此标记为 `[VERIFIED]` 而非训练知识推测,风险敞口很小。上面两条 `[ASSUMED]` 都是低风险的外围细节,不影响本 phase 五条 Success Criteria 的可验证性。

## Open Questions

1. **CI workflow 的 macOS runner 具体跑哪些测试子集(D-12 留给 Claude 裁量)**
   - What we know: 现有 7 个测试文件中,3 个(`test_firefox_extensions_and_selenium.py`、`test_concurrent_profile_storage.py`、`test_api_docs_content.py`)当前因导入链触达 `backend.browser_manager`/`backend.main` 而间接触达 `win32api`,在 Phase 1 完成后这条导入链会被打通(window_manager 改为条件导入后,这三个文件在 macOS 上应该都能正常导入并运行,只是其中依赖真实 Windows 行为的具体用例可能需要额外 skip)。`test_sync_regressions.py` 依赖 `backend.services.synchronizer`,该模块顶层导入不含 win32,本身在 macOS 上早已能正常导入(受阻的是 `websocket`/`ruyipage` 等包是否装,不是 win32)。
   - What's unclear: Phase 1 完成后,7 个测试文件是否**全部**可以直接在 macOS CI 上跑(即"全量"还是"子集"),需要在实现阶段实际跑一遍来确认是否有真正依赖 Windows 专属行为(如窗口句柄断言)的测试用例需要额外 skip。
   - Recommendation: 规划时把"跑一遍 macOS 上 `python -m unittest discover -s tests -v` 看哪些用例失败"作为一个显式验证步骤,再据此决定 CI workflow 里 macOS job 的测试范围(全量 or 子集 + skip 列表),不要在计划阶段就假设"全部能跑"或"只能跑一部分"。

2. **Chromium.app 在开发机上的实际安装位置(SYSTEM_CHROME_EXECUTABLE 的现实校准)**
   - What we know: fingerprint-chromium 项目本身是 ungoogled-chromium 的一个 fork,macOS 上通常以 `.app` bundle 形式分发,可执行文件位于 `<AppName>.app/Contents/MacOS/<AppName>`。
   - What's unclear: 用户系统上实际安装的 Chromium.app 应用名/路径("Chromium" vs "Chromium.app" 内部可执行文件名是否也叫 "Chromium")在 Phase 2 内核发布之前无法从本仓库确认。
   - Recommendation: 这属于 Claude's Discretion 范围且验收标准未锁定该值,规划时可以先用一个合理占位值(`/Applications/Chromium.app/Contents/MacOS/Chromium`),标记为"Phase 2/3 校准"的后续 TODO,不阻塞 Phase 1 验收。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 后端运行时 | ✓(本机) | 3.14.4(CI 用 3.11,与 requirements 声明的最低版本兼容) | — |
| pip | 依赖安装 | ✓ | 26.0.1 | — |
| pywin32 | Windows 窗口管理 | ✗(本机 macOS,预期内) | — | 打 `sys_platform == "win32"` 标记后跳过安装,属于本 phase 目标行为而非缺口 |
| psutil | 跨平台进程检活 | 需安装(本机沙盒未预装,可用 `pip install` 补齐) | 7.2.2(dry-run 探测到的可用版本) | 无需 fallback,标准跨平台依赖 |
| GitHub Actions macOS runner | D-12 新 CI workflow | 未在本次研究中实际起跑(超出研究范围,属实现阶段验证项) | — | 无 fallback,是 D-12 明确要新增的能力 |

**Missing dependencies with no fallback:** 无——本 phase 涉及的所有依赖缺口都有明确的既定处理方式(标记跳过或本机已验证可行)。

**Missing dependencies with fallback:** 无实质性缺口,`psutil` 等运行时依赖在实现阶段执行 `pip install -r requirements.txt` 即可补齐。

## Validation Architecture

`.planning/config.json` 在本仓库中不存在,`workflow.nyquist_validation` 视为默认启用,因此包含本节。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python 标准库 `unittest`(无 pytest 配置,`find /Users/fanjin/bfwg/Open-Anti-Browser -maxdepth 2 -iname pytest.ini/setup.cfg/pyproject.toml` 均无命中) |
| Config file | 无——`tests/` 下无 conftest,纯 `unittest.TestCase` 子类 |
| Quick run command | `python -m unittest tests.<module> -v`(单文件) |
| Full suite command | `python -m unittest discover -s tests -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XPLAT-01 | macOS 下 `pip install -r requirements.txt` 成功跳过 pywin32/ruyipage | 手动验证(pip 行为非 unittest 可覆盖) | `pip install -r requirements.txt`(macOS 环境) | ❌ Wave 0 — 无自动化测试文件,靠 CI macOS job 的安装步骤本身作为验证 |
| XPLAT-02 | window_manager 在非 Windows 下四个函数均 raise RuntimeError；Windows 分支行为不变 | unit | `python -m unittest tests.test_window_manager_posix -v` | ❌ Wave 0 — 需新建 |
| XPLAT-02 | 窗口/同步 API 端点在 macOS 返回 400 + 中文 detail | unit(mock BrowserManager 或直接测 services 层) | `python -m unittest tests.test_window_manager_posix -v`(可与上一条合并在同一文件的不同用例) | ❌ Wave 0 — 需新建 |
| XPLAT-03 | config.py 冻结态在 macOS 解析到 `~/Library/Application Support/Open-Anti-Browser/` 与 `Chromium.app/Contents/MacOS/Chromium` | unit(mock `sys.platform`/`sys.frozen`) | `python -m unittest tests.test_config_platform -v` | ❌ Wave 0 — 需新建 |
| XPLAT-03 | Windows 分支路径解析值字节级不变(既有值回归) | unit | `python -m unittest tests.test_config_platform -v`(同文件内 Windows 分支用例) | ❌ Wave 0 — 需新建（现状没有专门测 config.py 路径解析的文件） |
| XPLAT-04 | `--backend-only` 在 macOS 可派生/检活/停止,`creationflags` 不向 POSIX 传非法参数 | unit(mock subprocess.Popen 或直接跑真实子进程) | `python -m unittest tests.test_runtime_control_posix -v` | ❌ Wave 0 — 需新建 |
| (零回归) | 现有 7 个测试文件在 Windows 上原样通过 | integration(手动,D-11) | `python -m unittest discover -s tests -v`(Windows 机器/VM 上手动跑) | ✅ 已存在 — 无需新建,只需人工在 Windows 上执行 |

### Sampling Rate

- **Per task commit:** 对应改动文件的单测(如改 `window_manager.py` 后跑 `test_window_manager_posix`)
- **Per wave merge:** `python -m unittest discover -s tests -v`(本机 macOS 全量,验证新分支不破坏现有可导入的测试)
- **Phase gate:** macOS 全量 unittest 通过 + Windows 手动全量 unittest 通过(D-11)+ 新 CI workflow 在两个 runner 上都跑绿,三者都满足才进入 `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_window_manager_posix.py` — 覆盖 XPLAT-02(非 Windows 分支 raise RuntimeError;可用 `unittest.mock.patch("sys.platform", "darwin")` 配合 `importlib.reload` 或直接在非 Windows 环境下跑原生断言)
- [ ] `tests/test_config_platform.py` — 覆盖 XPLAT-03(mock `sys.platform`/`sys.frozen`/`sys._MEIPASS`,断言 macOS 冻结态路径 = `~/Library/Application Support/Open-Anti-Browser/`,断言 Windows 分支路径值与现状逐字一致)
- [ ] `tests/test_runtime_control_posix.py` — 覆盖 XPLAT-04(断言 POSIX 分支不会把非零 `creationflags` 传给 `subprocess.Popen`;可用 `unittest.mock.patch("subprocess.Popen")` 断言调用参数,不需要真的起子进程)
- [ ] 同步器门禁测试(D-03)— 可并入 `test_window_manager_posix.py` 或单独一个 `test_synchronizer_platform_gate.py`,断言 `BrowserSynchronizer.start()` 在非 Windows 下 raise RuntimeError
- [ ] 框架安装: 无——`unittest` 是标准库,无需新增安装步骤

## Security Domain

`.planning/config.json` 不存在,`security_enforcement` 视为默认启用,包含本节。本 phase 是纯平台适配工作,不涉及新的信任边界,ASVS 相关性普遍较低,但仍逐项核对:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | 否 | 本 phase 不涉及 `/open-api` 鉴权逻辑改动 |
| V3 Session Management | 否 | 不涉及 |
| V4 Access Control | 部分适用 | 窗口排列/同步端点在 macOS 上的"仅 Windows 支持"错误属于**功能可用性门禁**而非访问控制漏洞;需确保门禁逻辑本身不能被绕过(如直接调用 `BrowserSynchronizer.start()` 而非走 API 层——但由于门禁下沉到 services 层内部,天然无法绕过) |
| V5 Input Validation | 否(现状不变) | 本 phase 不改动任何请求体校验逻辑 |
| V6 Cryptography | 否 | 不涉及 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 平台门禁被绕过(如前端隐藏了功能但后端仍可被直接调用执行 Windows 专属逻辑,导致 macOS 上抛出未预期的底层异常而非清晰错误) | Denial of Service(轻微,表现为 500 而非预期的 400) | 门禁下沉到 `window_manager.py`/`synchronizer.py` 内部(而非仅在前端隐藏或仅在 `main.py` 路由层判断),保证任何调用路径都会触达同一个 RuntimeError,现有 `main.py` 的 `try/except → HTTPException(400)` 包裹已经能兜住 |
| POSIX 后台派生进程权限/文件描述符泄漏 | Elevation of Privilege(低风险) | `start_new_session=True` 只影响会话归属,不影响权限;现有 `close_fds=True`、`stdin/stdout/stderr=DEVNULL` 已经是良好实践,保持不变 |

## Sources

### Primary (HIGH confidence)

- 本机 Python 3.14 REPL 实测:`subprocess.Popen(creationflags=...)` 在 darwin 上的行为(见 Code Examples)
- 本机 `pip install --dry-run` 实测:PEP 508 `sys_platform` 标记在 darwin 上的解析行为(见 Code Examples)
- 本机 `git blame backend/main.py`:确认 `os.startfile` 跨平台分支已在 2026-04-18 提交 `8afdce3` 中存在
- 本机 CPython 标准库源码(`inspect.getsource(subprocess.Popen.__init__)`):确认 `creationflags != 0` 才报错的精确判断条件
- 全文读取:`requirements.txt`、`backend/services/window_manager.py`、`backend/config.py`、`backend/runtime_control.py`、`backend/services/chrome.py`(前140行)、`backend/services/network.py`(kill_process_tree 及前60行)、`backend/services/synchronizer.py`(顶部导入 + `BrowserSynchronizer.start()`)、`backend/main.py`(相关端点段落)、`launch_app.py`、`backend/_g.py`、7 个测试文件的 import 语句、`.github/workflows/build-release.yml`

### Secondary (MEDIUM confidence)

- Python 官方文档关于 `subprocess.Popen(start_new_session=...)` 与 `preexec_fn` 风险提示的既有认知(training knowledge,与本机源码核对结果一致,标记 CITED)
- Apple 文件系统编程指南关于 `~/Library/Application Support/` 约定的既有认知(该值已由用户在 D-06 锁定为决策,非本次探索结论)

### Tertiary (LOW confidence)

- ruyipage 包的下载量/生态位描述(training knowledge,未做实时核实,已在 Assumptions Log 标注为低风险)

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 全部为标准库能力,且关键假设(creationflags 行为、pip 标记生效)均已本机实测验证
- Architecture: HIGH — 直接读取全部相关源文件,改动落点逐行核对,新增门禁点(BrowserSynchronizer.start)也已定位到具体行号
- Pitfalls: HIGH — 4 条 pitfall 均来自对当前代码库的直接观察(尤其 D-04 状态核销这一条,是本次研究发现的与 CONTEXT.md 假设不一致的实质性事实)

**Research date:** 2026-07-24
**Valid until:** 30 天(本 phase 完全基于标准库语义和当前代码库快照,技术栈稳定,唯一时效性风险是"代码库在规划与执行之间被其他改动影响",建议规划落地前重新核对改动落点行号是否漂移)
