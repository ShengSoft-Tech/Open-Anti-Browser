# Phase 1: 后端跨平台基础适配 - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** 8（4 个待修改源码文件 + 1 个新增 CI workflow + 3 个新增测试文件）
**Analogs found:** 8 / 8（本 phase 的分析对象绝大多数“分析对象”与“分析对象自身现状”重合——因为 RESEARCH.md 已逐行核对现有代码，本 phase 的核心动作是在既有文件内部新增 `else` 分支，而非新建文件套用外部分析对象）

## File Classification

| 待修改/新增文件 | Role | Data Flow | 最近似分析对象 | Match Quality |
|------------------|------|-----------|-----------------|---------------|
| `requirements.txt` | config | batch（依赖声明，pip 安装时求值） | 自身现状（无需外部分析对象，PEP 508 标记语法是标准写法） | exact |
| `backend/services/window_manager.py` | service（OS 集成层） | request-response（被 browser_manager 同步调用） | 自身现状 + `backend/services/synchronizer.py` 的门禁风格 | exact（改动即在自身文件内新增 `else` 分支） |
| `backend/services/synchronizer.py`（`BrowserSynchronizer.start`） | service（事件转发） | event-driven | 自身现状（`start()` 方法本体） | exact |
| `backend/config.py` | config | transform（路径解析） | 自身现状（`_writable_root`/`SYSTEM_*_EXECUTABLE`/`ENGINE_METADATA`） | exact |
| `backend/runtime_control.py` | service（进程管理） | event-driven（派生/检活/停止子进程） | 自身现状（`start_backend_only` 中 `Popen` 调用） | exact |
| `.github/workflows/ci-tests.yml` | config（CI） | batch | `.github/workflows/build-release.yml`（现有唯一 workflow，命名/触发风格参考） | role-match |
| `tests/test_window_manager_posix.py`、`tests/test_runtime_control_posix.py`、`tests/test_synchronizer_platform_gate.py` | test | request-response / event-driven | `tests/test_sync_regressions.py`（打桩风格：纯 unittest + `unittest.mock.patch`，无 pytest fixture） | exact |
| `tests/test_config_platform.py` | test | transform | `tests/test_sync_regressions.py`（同上打桩风格）+ 需要额外 `importlib.reload` 或直接 mock `sys.platform`/`sys.frozen` | role-match |

**说明：** 本 phase 不是“新建文件抄现有文件模式”的常规场景，而是“在既有文件内部新增平台分支”。因此下面每个条目的“Analog”实际上是**同一个文件的现状代码**（Windows 分支必须保持字节级不变，非 Windows 分支是新增的镜像结构），只有 CI workflow 和四个新测试文件是真正意义上的新文件，其分析对象是仓库里已有的、结构最相似的文件。

## Pattern Assignments

### `backend/services/window_manager.py`（service, request-response）

**Analog：自身现状全文**（`/Users/fanjin/bfwg/Open-Anti-Browser/backend/services/window_manager.py`，共 238 行）

**Imports pattern**（第 1-10 行，Windows 分支保持不变，需要移入 `if sys.platform == "win32":` 块内）：
```python
from __future__ import annotations

import math
from typing import Any, Callable

import psutil
import win32api
import win32con
import win32gui
import win32process
```
改造后顶层需新增 `import sys`，并将上述 `import psutil/win32*` 与 `ENGINE_WINDOW_CLASSES` 常量、`list_monitors/show_windows/set_uniform_size/arrange_windows` 及全部私有辅助函数（`_pick_monitor`/`_arrange_grid`/`_arrange_overlap`/`_collect_profile_windows`/`_pick_primary_window`/`_process_tree_pids`，第 13-238 行）整体缩进进 `if sys.platform == "win32":` 分支，逐字迁移，不改一个字符。

**核心桩函数模式**（非 Windows 分支，新增）：
```python
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
四个函数签名必须与 Windows 分支完全一致（同名、同参数），因为 `browser_manager.py:36` 是具名导入，调用方零改动。

**错误传播路径（无需改动，天然生效）：** `backend/main.py` 第 274-303 行四个窗口排列端点均已有 `try: ... except Exception as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc` 包裹，RuntimeError 会自动转换为 400 + 中文 detail。

---

### `backend/services/synchronizer.py`（service, event-driven）

**Analog：`BrowserSynchronizer.start`（第 1393-1414 行）**

**现状（门禁插入点）：**
```python
class BrowserSynchronizer:
    def __init__(
        self,
        runtime_resolver: Callable[[str], dict[str, Any] | None],
        profile_resolver: Callable[[str], dict[str, Any] | None],
    ) -> None:
        self._runtime_resolver = runtime_resolver
        self._profile_resolver = profile_resolver
        self._lock = threading.RLock()
        self._session: _SyncSession | None = None

    def start(self, master_profile_id: str, follower_profile_ids: list[str], options: dict[str, Any] | None = None) -> dict[str, Any]:
        master_profile_id = str(master_profile_id or "").strip()
        if not master_profile_id:
            raise ValueError("请选择主浏览器")
        follower_ids = [str(item).strip() for item in follower_profile_ids if str(item).strip()]
        ...
```

**改造模式（在既有校验之前插入平台门禁，`import sys` 加入顶层导入块第 1-12 行附近）：**
```python
def start(self, master_profile_id: str, follower_profile_ids: list[str], options: dict[str, Any] | None = None) -> dict[str, Any]:
    if sys.platform != "win32":
        raise RuntimeError("窗口同步仅在 Windows 上可用")
    master_profile_id = str(master_profile_id or "").strip()
    ...  # 现状不变
```

**错误传播路径（无需改动）：** `backend/main.py:245-250`
```python
@app.post("/api/synchronizer/start")
def start_synchronizer(payload: dict) -> dict:
    try:
        return manager.start_synchronizer(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

---

### `backend/config.py`（config, transform）

**Analog：自身现状 `_writable_root`（第 23-34 行）、`SYSTEM_*_EXECUTABLE`/`DEFAULT_*_EXECUTABLE`（第 81-86 行）、`ENGINE_METADATA`（第 112-131 行）**

**现状（Windows 唯一路径，需保持字节级不变并包成 `if sys.platform == "win32":` 分支）：**
```python
def _writable_root() -> Path:
    if _is_packaged():
        executable_dir = Path(sys.executable).resolve().parent
        if os.environ.get("OPEN_ANTI_BROWSER_PORTABLE") == "1":
            return executable_dir
        if (executable_dir / PORTABLE_MARKER).exists():
            return executable_dir
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    return PROJECT_ROOT
```

```python
USERNAME = _current_username()
SYSTEM_CHROME_EXECUTABLE = Path(
    fr"C:\Users\{USERNAME}\AppData\Local\Chromium\Application\chrome.exe"
)
SYSTEM_FIREFOX_EXECUTABLE = Path(r"C:\Program Files\Mozilla Firefox\firefox.exe")
DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"
DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox.exe"
```

```python
ENGINE_METADATA = {
    "chrome": {
        "name": "Fingerprint Chromium 149",
        "default_executable": str(DEFAULT_CHROME_EXECUTABLE),
        "system_executable": str(SYSTEM_CHROME_EXECUTABLE),
        "installer_url": CHROME_INSTALLER_URL,
        "download_name": "fingerprint-chromium-149-1.2-installer.exe",
        "engine_dir": "chrome",
        "bundle_dir": str(ENGINES_DIR / "chrome"),
    },
    "firefox": { ... },  # D-08：macOS 保留不删
}
```

**改造模式（RESEARCH.md 已给出骨架，直接采用）：**
```python
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
            # D-07：macOS 忽略 portable 标记与环境变量，固定用户级路径
            return Path.home() / "Library" / "Application Support" / APP_NAME
    return PROJECT_ROOT


if sys.platform == "darwin":
    SYSTEM_CHROME_EXECUTABLE = Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
    SYSTEM_FIREFOX_EXECUTABLE = Path("/Applications/Firefox.app/Contents/MacOS/firefox")
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
    DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox"  # D-08：路径存在但文件不存在，天然不可用
else:
    SYSTEM_CHROME_EXECUTABLE = Path(
        fr"C:\Users\{USERNAME}\AppData\Local\Chromium\Application\chrome.exe"
    )
    SYSTEM_FIREFOX_EXECUTABLE = Path(r"C:\Program Files\Mozilla Firefox\firefox.exe")
    DEFAULT_CHROME_EXECUTABLE = ENGINES_DIR / "chrome" / "chrome.exe"
    DEFAULT_FIREFOX_EXECUTABLE = ENGINES_DIR / "firefox" / "firefox.exe"
```
`ENGINE_METADATA` 字典结构本身不变（key、字段名都一致），只是 `default_executable`/`system_executable` 引用的常量在两个平台下值不同，字典构造代码零改动。

**重要约束（Pitfall 4）：** macOS 分支绝不能出现 `Path(sys.executable).resolve().parent` 字样——这是 Windows portable 专属逻辑，D-07 明确 macOS 不复用。

---

### `backend/runtime_control.py`（service, event-driven）

**Analog：自身现状 `start_backend_only`（第 136-160 行）中的 `subprocess.Popen` 调用**

**现状：**
```python
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
...
process = subprocess.Popen(
    command,
    cwd=_launcher_cwd(),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
    close_fds=True,
    env={**os.environ},
)
```

**改造模式（只改 Popen 调用点，两个常量定义保留不动）：**
```python
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
`sys` 已在文件顶层导入（第 7 行），无需新增 import。**范围边界（Pitfall 2）：** `backend/services/chrome.py`/`firefox.py` 里同结构的 `CREATE_NEW_PROCESS_GROUP` 兜底为 0，POSIX 上安全，不在本 phase 改动范围内。

---

### `backend/main.py`（验证性任务，非修改任务）

**现状（第 476-489 行，已是跨平台实现，D-04 核销）：**
```python
@app.post("/api/system/open-url")
def open_system_url(payload: dict) -> dict[str, bool]:
    raw_url = str(payload.get("url") or "").strip()
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="只支持打开 http 或 https 链接")

    try:
        if os.name == "nt":
            os.startfile(raw_url)  # type: ignore[attr-defined]
        else:
            webbrowser.open_new_tab(raw_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"打开链接失败：{exc}") from exc
```
无需改动，仅需在 plan 中作验证步骤（macOS 冒烟测试确认此端点可用）。

---

### 测试文件（test, request-response / transform / event-driven）

**Analog：`tests/test_sync_regressions.py`（第 1-80 行，打桩风格参考）**

```python
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services import synchronizer
import launch_app


class FakeSyncClient:
    def __init__(self, profile_id="follower", targets=None, current_target_id="tab-a"):
        ...


class SynchronizerRegressionTests(unittest.TestCase):
    def test_browser_ui_sync_is_enabled_by_default(self):
        options = synchronizer._coerce_sync_options({})
        self.assertTrue(options["sync_browser_ui"])
```

**新增测试文件应遵循的结构（无 pytest fixture，纯 `unittest.TestCase` + `unittest.mock.patch`）：**

- `tests/test_window_manager_posix.py`：`with patch("sys.platform", "darwin"):` 配合 `importlib.reload(window_manager)` 后断言四个函数 `assertRaises(RuntimeError)`；同时应有一组用例在真实运行平台（若为 win32）验证 Windows 分支未受影响（可用 `@unittest.skipUnless(sys.platform == "win32", ...)` 包裹，与现有测试文件里按平台/依赖跳过用例的风格一致）。
- `tests/test_synchronizer_platform_gate.py`（或并入上一个文件）：`patch("backend.services.synchronizer.sys.platform", "darwin")` 后断言 `BrowserSynchronizer(...).start(...)` 抛 `RuntimeError`。
- `tests/test_runtime_control_posix.py`：`patch("subprocess.Popen")` 断言非 Windows 下调用参数里没有非法 `creationflags`、而是 `start_new_session=True`；Windows 下断言 `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`。
- `tests/test_config_platform.py`：mock `sys.platform`/`getattr(sys, "frozen", False)`/`sys._MEIPASS`，`importlib.reload(config)` 后断言 macOS 冻结态 `APP_ROOT == Path.home() / "Library" / "Application Support" / "Open-Anti-Browser"`，以及 Windows 分支各路径值与现状逐字一致（零回归断言）。

## Shared Patterns

### 平台判断统一用 `sys.platform`
**Source:** RESEARCH.md Pitfall 3 + 本 phase 全部新增分支
**Apply to:** `window_manager.py`、`synchronizer.py`、`config.py`、`runtime_control.py` 四个文件的新增分支
```python
if sys.platform == "win32":
    ...
else:
    ...
```
`main.py` 现有的 `os.name == "nt"` 判断保持不变，不做风格统一（避免范围蔓延）。

### HTTPException 400 + 中文 detail 自动转换（无需改动的既有基础设施）
**Source:** `backend/main.py` 第 245-303 行（synchronizer 相关端点）
**Apply to:** 所有窗口排列/同步 API 端点，RuntimeError 抛出后自动被现有 `try/except Exception as exc: raise HTTPException(400, str(exc))` 捕获
```python
try:
    return manager.xxx(payload)
except Exception as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
```

### 纯 unittest + mock.patch 打桩（测试基础设施）
**Source:** `tests/test_sync_regressions.py`
**Apply to:** 全部 4 个新增测试文件
- 不引入 pytest fixture 或新测试框架
- 外部依赖（`subprocess.Popen`、`sys.platform`）一律用 `unittest.mock.patch`
- 需要重新求值模块级平台分支时用 `importlib.reload(module)`

### Windows 分支零回归不变式
**Source:** CONTEXT.md D-05/D-11/D-12 + RESEARCH.md Anti-Patterns
**Apply to:** `config.py`、`window_manager.py`、`runtime_control.py`、`synchronizer.py` 四个文件的 `if sys.platform == "win32":` 分支
- 分支内代码必须是现有代码的逐字迁移，禁止“顺手”优化写法
- 验证方式：diff 中 Windows 分支代码应与改动前完全一致（仅缩进变化，无逻辑变化）

## No Analog Found

| 文件 | Role | Data Flow | 原因 |
|------|------|-----------|------|
| `.github/workflows/ci-tests.yml` | config (CI) | batch | 仓库目前只有 `build-release.yml`（tag 触发的发版 workflow），触发条件（push/PR）和职责（跑测试而非发版）都不同，只能部分参考其 YAML 结构（runs-on、steps 写法），矩阵测试（windows-latest + macos-latest）本身是全新模式 |

## Metadata

**Analog search scope：** `backend/services/`、`backend/config.py`、`backend/runtime_control.py`、`backend/main.py`、`tests/`、`.github/workflows/`
**Files scanned：** `requirements.txt`、`backend/services/window_manager.py`（全文 238 行）、`backend/config.py`（全文 137 行）、`backend/runtime_control.py`（全文 173 行）、`backend/services/synchronizer.py`（导入块 + `BrowserSynchronizer` 类第 1382-1421 行）、`backend/main.py`（第 240-310 行、第 470-489 行）、`tests/test_sync_regressions.py`（前 80 行）
**Pattern extraction date：** 2026-07-24
