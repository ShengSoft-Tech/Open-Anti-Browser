# Phase 3: macOS Chrome 启动与能力 API - Research

**Researched:** 2026-07-27
**Domain:** macOS 进程启动/终止语义（Gatekeeper/quarantine、psutil 跨平台进程树管理）+ 平台能力 API 设计
**Confidence:** MEDIUM — 代码勘察部分 HIGH（直接读仓库源码确认）；quarantine/Gatekeeper 实证部分 MEDIUM（多个独立社区来源交叉印证，但均非 Apple 官方一手文档，且**必须在用户真机上做最终确认**，本研究不能替代真机验证。

## Summary

本 phase 不是从零实现,而是"验证 + 补边角"：`backend/services/chrome.py:launch_chrome_profile` 已是跨平台写法（直接 `Popen` 嵌套 `.app` 内二进制,不经 `open -a`）,`kill_process_tree`（`network.py:839-854`）已用 psutil 递归子进程,`get_engine_statuses()`/`bootstrap()` 已有聚合结构。研究聚焦 CONTEXT.md 明确标出的两个真正未知数（内核 quarantine 处理 D-07、进程树优雅终止 D-05/D-06），外加能力 API 契约、验证深度、测试策略三个较小的确认项。

**最重要的发现（D-07 quarantine）：** 综合本仓库既有的里程碑级研究（`.planning/research/PITFALLS.md`）与本次交叉验证的独立社区来源,现有证据指向两个相互独立、都对本 phase 有利的事实：(1) Gatekeeper 的 GUI 门禁（"无法验证此 App 是否包含恶意软件"弹窗/首次运行拦截）由 **LaunchServices**（Finder 双击、`open`/`open -a`、`NSWorkspace`）触发,命令行 `execve`/`subprocess.Popen` 直接执行二进制**通常不经过这条路径**（`[CITED: eclecticlight.co]`，MEDIUM confidence）；(2) 命令行 `ditto`/`tar`/`unzip` 解压一个带 quarantine 标记的 zip **不会把 quarantine 属性传播到解压出的文件**——只有 Finder 的 Archive Utility（双击解压）才会做这种传播（`[CITED: 社区交叉验证 + eclecticlight.co]`，MEDIUM confidence）。这意味着：如果开发者/用户是**用浏览器下载 kernel zip 后在 Terminal 里跑 `ditto -x -k` 解压**（现有 `scripts/release/verify_and_upload_macos_kernel.sh` 的解压方式）,解压出的 `Chromium.app/Contents/MacOS/Chromium` 大概率**不带 quarantine 属性**；即使带,`subprocess.Popen` 直接 exec 也大概率不触发 Gatekeeper GUI 拦截。但**这与 Apple Silicon 上独立于 quarantine 的"强制代码签名"内核门禁是两回事**（Pitfall 2，本仓库既有研究已确认）——好消息是 Phase 2 的 `verify_and_upload_macos_kernel.sh` 已经对 arm64 内核校验过 `adhoc` + `linker-signed` 标记存活,这道门槛已经满足。**结论：D-07 的默认倾向（研究先行 + 落地时剥离 + 启动路径防御性兜底）是合理的架构,但"CLI exec 是否真的不拦"这个具体判断只能在用户的 arm64 真机上用下面给出的具体测试步骤验证——本研究只能证明"大概率不会拦",不能证明"绝对不会拦"。**

**次要发现（D-05/D-06 进程树终止）：** psutil 官方文档已有明确记载的 `kill_proc_tree` 范式（`children(recursive=True)` → 全部 `terminate()` → `wait_procs(timeout=..., callback=on_terminate)` → 对幸存者 `kill()`），且 `Process.terminate()` 在 Windows 上就是 `TerminateProcess()` 的别名,与现有 `kill()`（`TerminateProcess`）行为等价——CONTEXT D-06 关于"可做统一路径,Windows 行为不变"的判断有据可依。

**Primary recommendation:** 采用统一（非平台分叉）的 `kill_process_tree` 改造，SIGTERM 宽限期用 3 秒（可配置常量，非 magic number）；D-07 的 quarantine 剥离放在**内核落地后一次性 `xattr -dr` + 启动路径 `try/except` 防御性兜底**，并把"在 arm64 真机上实测 CLI Popen 是否被拦"列为本 phase 执行阶段的**强制 checkpoint:human-verify** 任务，而非假设研究结论已经足够。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 指纹 Chrome 启动（Popen 嵌套二进制） | API/Backend（`backend/services/chrome.py`） | — | 后端唯一负责组装 launch_args 与派生子进程,前端只发 `/api/profiles/{id}/start` |
| 进程树优雅终止 | API/Backend（`backend/services/network.py:kill_process_tree`） | — | psutil 递归子进程管理是纯后端职责,与 UI 无关 |
| 代理/本地代理桥/geo 解析 | API/Backend（`services/network.py`） | — | `LocalHttpProxyBridge`、`resolve_geo_profile` 均为后端网络层,浏览器进程只是消费方 |
| 扩展安装 | API/Backend（`services/extensions.py` + `chrome.py:_collect_enabled_chrome_extensions`） | — | 扩展路径解析与 `--load-extension` 参数拼装在后端,前端仅管理扩展元数据 |
| 批量启动/隔离 | API/Backend（`browser_manager.py:start_group`） | — | 独立 `user_data_dir` 隔离逻辑已跨平台,无 UI 侧改动 |
| 平台能力声明（capabilities） | API/Backend（新 `GET /api/capabilities` + `bootstrap()`） | Frontend（Phase 4 消费） | 能力事实来源（`sys.platform`、`window_manager` 门控状态）只应在后端计算一次,前端只读布尔字段,不做二次平台判断 |
| 内核 quarantine 剥离 | API/Backend（内核落地/启动路径,`bundled_engine_executable` 调用点附近） | OS 层（`xattr`/Gatekeeper，超出应用控制） | 应用层只能在自己触碰内核文件的时点（落地后、启动前）做防御性处理,无法控制用户手动操作触发的重新 quarantine |

## Standard Stack

本 phase **不引入任何新的第三方依赖**。`psutil>=5.9.8`（`requirements.txt:3`）已是现有依赖,跨平台（Windows/macOS/Linux）行为一致，本次改动只是调整调用方式（`terminate()`→`wait_procs()`→`kill()`），不涉及新增/升级包。

### Core（沿用现有）
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psutil | >=5.9.8（仓库已锁定，`[VERIFIED: requirements.txt]`） | 进程树遍历（`children(recursive=True)`）、优雅终止（`terminate`/`kill`/`wait_procs`）、存活检测（`pid_exists`） | 官方文档记载的标准 `kill_proc_tree` 范式即基于此库；本仓库 `_refresh_runtime_sessions`（`browser_manager.py:831`）已依赖它做 zombie 检测 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psutil `terminate()`/`kill()`/`wait_procs()` | `os.killpg` + `start_new_session=True`（进程组信号） | CONTEXT D-06 已明确排除：直接 Popen 嵌套二进制场景下 Chromium Helper 本就是子进程,可被 `children(recursive=True)` 递归捕获，引入进程组反而是平台分叉，不必要 |
| 应用层 `xattr -dr` 调用 | 依赖用户"右键打开"一次性放行 | 右键放行只对 Finder 发起的**顶层** `.app` 生效，不会传导到应用用 `Popen` 直接 exec 的**嵌套**内核二进制（本仓库 Pitfalls 研究 Pitfall 3 已确认）——对内核这条路径无效，必须显式 `xattr` |

**Installation:** 无需新增安装命令（无新依赖）。

**Version verification:** `psutil>=5.9.8` 已在 `requirements.txt:3` 锁定,跨平台 wheel 覆盖 macOS（含 arm64）：`[VERIFIED: requirements.txt 现状]`。

## Package Legitimacy Audit

> 本 phase 不安装任何新的外部包（复用现有 `psutil` 依赖，改动仅限调用方式），因此无需执行 Package Legitimacy Gate 校验。

**Packages removed due to [SLOP] verdict:** 无（无新增包）
**Packages flagged as suspicious [SUS]:** 无（无新增包）

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │  前端 /api/profiles/{id}/start (POST)     │
                    └───────────────────┬───────────────────────┘
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │ BrowserManager.start_profile()            │
                    │  1. 解析 user_data_dir                     │
                    │  2. launch_chrome_profile(profile,...)     │
                    └───────────────────┬───────────────────────┘
                                        ▼
     ┌──────────────────────────────────────────────────────────────┐
     │ services/chrome.py: launch_chrome_profile                     │
     │  a. bundled_engine_executable("chrome") 解析路径                │
     │  b. [新增防御性检查] 若路径存在但带 quarantine → 尝试剥离(D-07)   │
     │  c. proxy_config → 如需账号代理，起 LocalHttpProxyBridge 本地桥  │
     │  d. resolve_geo_profile()（经 bridge 出网，取时区/语言）          │
     │  e. 拼装 launch_args（--fingerprint=seed, --proxy-server, ...） │
     │  f. subprocess.Popen(launch_args, ...) 直接 exec 嵌套二进制      │
     │     （不经 open -a，保 PID/进程组关系给 psutil 用）                │
     └───────────────────┬──────────────────────────────────────────┘
                          ▼
     ┌──────────────────────────────────────────────────────────────┐
     │ RuntimeSession 记录（pid, remote_debugging_port, proxy_bridge_url）│
     │ runtime_sessions[profile_id] = {...}                            │
     └───────────────────┬──────────────────────────────────────────┘
                          │
          ┌───────────────┴────────────────┐
          ▼                                 ▼
  /api/profiles/{id}/stop            _refresh_runtime_sessions()
  → stop_profile()                    （psutil.pid_exists 检活）
  → kill_process_tree(pid)                   │
       │                                     ▼
       ▼                              清理 stale runtime_sessions
  [改造后] children(recursive=True)
    → 全部 terminate() (SIGTERM)
    → wait_procs(timeout=3s)
    → 幸存者 kill() (SIGKILL)
       │
       ▼
  proxy_bridge.stop()（如有账号代理本地桥）

     ┌──────────────────────────────────────────────────────────────┐
     │  GET /api/capabilities（新增）                                   │
     │  = { engines: {chrome: {available:true}, firefox:{available:false}},│
     │      window: {arrange:{available:false,reason:"..."},               │
     │               sync:{available:false,reason:"..."}} }                │
     │  同一结构并入 bootstrap() 返回体的 capabilities 字段                    │
     └──────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

本 phase 不新增文件，落点均在既有文件内追加/修改：

```
backend/
├── services/
│   ├── chrome.py         # [改] 启动路径追加 quarantine 防御性检查（可选，视实证结论）
│   └── network.py        # [改] kill_process_tree：terminate→wait_procs→kill
├── browser_manager.py    # [改] get_engine_statuses() 追加 available 字段；新增 get_platform_capabilities()；bootstrap() 并入 capabilities
├── main.py               # [改] 新增 GET /api/capabilities 路由
└── config.py             # [可能改] 若需要一个"内核落地时机"的钩子（如首次解析到内核路径时触发一次性 xattr 剥离），落点待定，Claude's Discretion
tests/
└── test_process_termination_macos.py  # [新] mock psutil.Process/children/wait_procs 的跨平台单测（D-03）
```

### Pattern 1: 跨平台优雅终止（不分叉，D-05/D-06）

**What:** `kill_process_tree` 从"立即全树 SIGKILL"改为"全树 SIGTERM → 宽限窗口 → 对幸存者 SIGKILL"，Windows/macOS 用同一份代码路径。
**When to use:** `stop_profile()`、`_refresh_runtime_sessions()` 清理、应用退出时。
**Example:**
```python
# 参考模式，来源：psutil 官方文档记载的 kill_proc_tree 范式
# [CITED: psutil 官方 recipes，经 WebSearch 交叉验证多个独立引用来源，MEDIUM confidence]
def kill_process_tree(pid: int, grace_period: float = 3.0) -> None:
    try:
        parent = psutil.Process(pid)
    except psutil.Error:
        return
    children = parent.children(recursive=True)
    procs = children + [parent]

    # 阶段一：全树 SIGTERM（Windows 上 terminate() 等同 TerminateProcess，
    # 与当前 kill() 行为等价，故 Windows 侧无回归——[ASSUMED，未能拉取 psutil
    # 在线文档原文确认，属训练知识，但为 psutil 多年稳定 API，建议 planner
    # 在改动后于 Windows 机器上跑一次现有 unittest 套件复核零回归]）
    for process in procs:
        try:
            process.terminate()
        except psutil.Error:
            continue

    # 阶段二：等待宽限期，收集仍存活的进程
    gone, alive = psutil.wait_procs(procs, timeout=grace_period)

    # 阶段三：宽限期后仍存活 → 强制 SIGKILL
    for process in alive:
        try:
            process.kill()
        except psutil.Error:
            continue
    psutil.wait_procs(alive, timeout=5)
```
**风险提示：** 遍历顺序上，CONTEXT D-06 未强制"先子后父"还是"先父后子"——发 SIGTERM 时顺序**不影响**孤儿风险（因为是先枚举完整棵树再统一发送信号，不是边遍历边杀），只有**先杀父不等待、不管子进程**的旧写法才会有孤儿风险。新范式对 `parent` 和 `children` 一视同仁地进入同一个 `procs` 列表统一处理，天然规避了这个问题。

### Pattern 2: 平台能力 API 契约（D-01/D-02，XPLAT-05）

**What:** 后端聚合三类能力事实：per-engine `available`（平台级支持,与 `installed`/`capability_ok` 正交）、窗口功能 `arrange`/`sync` 的 `available`+`reason`。
**When to use:** `GET /api/capabilities` 独立端点 + 并入 `bootstrap()`。
**Example:**
```python
# backend/browser_manager.py 新增方法，紧邻 get_engine_statuses()（:602）
import sys

def get_platform_capabilities(self) -> dict[str, Any]:
    is_windows = sys.platform == "win32"
    window_reason = None if is_windows else "窗口排列仅在 Windows 上可用"
    sync_reason = None if is_windows else "窗口同步仅在 Windows 上可用"
    return {
        "platform": sys.platform,
        "engines": {
            "chrome": {"available": True},   # 两平台皆支持
            "firefox": {"available": is_windows},  # macOS 上结构性不支持（D-08 沿用）
        },
        "window": {
            "arrange": {"available": is_windows, "reason": window_reason},
            "sync": {"available": is_windows, "reason": sync_reason},
        },
    }

# backend/main.py，紧邻 /api/engines（main.py:403）
@app.get("/api/capabilities")
def get_capabilities() -> dict:
    return manager.get_platform_capabilities()

# bootstrap() 追加一行（browser_manager.py:68-74）
def bootstrap(self) -> dict[str, Any]:
    return {
        "settings": self.get_settings().model_dump(mode="json"),
        "profiles": self.list_profiles(),
        "engines": self.get_engine_statuses(),
        "downloads": self.downloads.get_all(),
        "capabilities": self.get_platform_capabilities(),  # 新增
    }
```
字段命名建议：`available`（布尔）+ `reason`（仅不可用时非空字符串，可用时为 `None`/省略），与现有 `installed`/`capability_ok` 语义严格区分（正交,不复用同一字段，见 D-02）。是否暴露到 `/open-api`：非本次讨论新增 scope，planner 按需决定（沿用 CONTEXT 备忘）。

### Anti-Patterns to Avoid
- **用 `installed`/`capability_ok` 兼职表达"平台是否支持"：** 会混淆"内核未下载"与"操作系统结构性不支持"两种完全不同的用户可见状态与补救路径（D-02 已明确排除，见 `.planning/research/ARCHITECTURE.md` Anti-Pattern 2 的既有分析）。
- **用 `spctl --master-disable` 或全局关闭 Gatekeeper 作为放行方案：** 训练用户削弱全局安全性,且不是本 phase 范围（本 phase 只处理内核这一个具体文件的 quarantine,不是应用整体放行,那是 Phase 4/6 的 UI-04/DOCS-01）。
- **对 `kill_process_tree` 做 macOS-only 分支：** CONTEXT D-06 与本研究均确认 psutil 在两平台上行为可统一处理,引入分支只会增加维护面且违背"零回归"的简洁性原则。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| 进程树优雅终止 | 自己写 `os.kill(pid, signal.SIGTERM)` 循环 + `time.sleep` 轮询 | psutil `terminate()` + `wait_procs(timeout=...)` | `wait_procs` 内部已处理跨平台的进程退出检测细节（含 Windows 的句柄等待与 POSIX 的 `waitpid`），手写轮询容易在两平台上行为不一致或产生僵尸进程 |
| Quarantine 属性剥离 | 自己解析 `com.apple.quarantine` 的二进制格式或用 Python 的 `xattr` 第三方包 | 直接 `subprocess.run(["xattr", "-dr", "com.apple.quarantine", path])`（系统自带命令，零新依赖） | `xattr` 是 macOS 系统自带命令行工具，行为稳定；引入 Python `xattr` 包（PyPI 上确有同名第三方库）反而是不必要的新依赖面，且需要额外的 package legitimacy 审计 |
| 平台判断 | 前端用 `navigator.userAgent`/`navigator.platform` 自行嗅探平台再决定显隐 | 后端 `GET /api/capabilities` 单一事实来源 | 前后端各自判断平台会产生"后端认为可用、前端认为不可用"的漂移风险；已有 `config.py` 作为路径的单一事实来源惯例，能力判断应同理收敛到后端（ARCHITECTURE.md 既有分析） |

**Key insight:** 本 phase 所有"不要手搓"的点都指向同一个原则——凡是"跨平台一致性"相关的判断（进程生命周期、平台能力),都应该收敛到一个后端可测试的函数里,而不是分散在多处平台判断代码或前端猜测中。

## Common Pitfalls

### Pitfall 1: 把"Gatekeeper 拦截"和"Apple Silicon 强制签名门禁"当成同一件事

**What goes wrong:** 排查启动失败时,把"进程刚起来就消失"统一归因于"quarantine 没剥"，忽略了 arm64 上还有一个完全独立的、与 quarantine 无关的内核级强制签名门禁。
**Why it happens:** 两者的失败症状相似（进程静默消失、无 GUI 提示），但触发机制和修复方式完全不同：quarantine 由 Gatekeeper/`syspolicyd` 在 **LaunchServices 发起的启动**时检查（`[CITED: eclecticlight.co — "Gatekeeper mechanism is only triggered by launches from the GUI, not the command line"]`）；而 arm64 强制签名是内核 `AMFI` 层面的检查，**不管启动方式是什么**都会生效，唯一修复是让二进制带有效签名（哪怕是 ad-hoc）。
**How to avoid:** 排查启动失败时区分两条独立诊断路径：(1) `codesign -dv <binary>` 确认签名存活（本仓库 `verify_and_upload_macos_kernel.sh` 已在上传前做过这步，Phase 2 已确认 arm64 内核 `adhoc`+`linker-signed` 标记存活）；(2) `xattr -p com.apple.quarantine <binary>` 确认 quarantine 状态；(3) 若失败，用 `log show --predicate 'subsystem == "com.apple.syspolicy"' --last 5m` 或退出码（`137`/`SIGKILL` 常见于签名门禁；Chromium 自身非零退出码则是应用层问题）区分具体是哪一层拦的。
**Warning signs:** 进程 `Popen` 后 `psutil.pid_exists(pid)` 立即返回 False，且 CDP 端口从未起来。

### Pitfall 2: 假设开发者本机的"能跑"能代表用户真机的"能跑"（quarantine 场景尤其明显）

**What goes wrong:** 开发者自己本地构建/复制的 `.app` 或内核目录早已没有 quarantine 属性（从未经过浏览器下载或 Finder 解压环节），所以本机测试"启动正常"，但用户从 GitHub Release 页面用浏览器下载 zip 后走的是完全不同的路径（浏览器下载 → 触发 quarantine → 用户不一定用 `ditto` 解压，也可能双击走 Archive Utility → quarantine 传播到内核二进制）。
**Why it happens:** quarantine 属性的产生依赖"下载/解压的触发方式"，而不是文件内容本身；开发机器上的内核往往来自本地构建或 `git`/`scp` 之类不触发 quarantine 的渠道。
**How to avoid:** 本 phase D-04 已要求"逐项实测"而非"能拉起不报错"——针对 quarantine 这一项，验证步骤必须显式包含"从 GitHub Release 页面用浏览器真实下载一次 zip"这一步，而不是复用本地已构建好的内核目录去测启动。
**Warning signs:** 复现失败的用户报告与开发者自己无法复现的组合，是这个陷阱的典型信号。

### Pitfall 3: 误以为"批量启动隔离"在 macOS 上会有 Windows 没有的坑

**What goes wrong:** 过度设计 macOS 专属的隔离校验逻辑（例如担心 `.app` 层面的单例检测干扰多开）。
**Why it happens:** Chromium 的 `SingletonLock` 机制是**基于 `--user-data-dir` 路径**的，与操作系统无关；只要每个 profile 的 `user_data_dir` 唯一（现有代码已保证，`browser_manager.py:190` 的 `_resolve_user_data_dir`），批量启动隔离在两平台上是同一套逻辑，不需要 macOS 专属处理。
**How to avoid:** 验证时确认的是"每个 profile 目录唯一"这个既有不变量，而不是去找 macOS 特有的隔离 API。
**Warning signs:** 若批量启动出现互相干扰，大概率是 `user_data_dir` 解析逻辑本身的 bug（跨平台共性问题），而非 macOS 专属问题——排查方向应先看 `_resolve_user_data_dir`，不要假设是平台差异。

### Pitfall 4: 优雅终止改造后，`SingletonLock` 残留问题反而因为"宽限期不够"而复现

**What goes wrong:** D-05 的动机就是"避免立即 SIGKILL 导致 `SingletonLock`/profile 损坏"，但如果 `grace_period` 设得太短（例如 <1s），Chromium 可能还没来得及完成 profile 落盘清理就被 SIGKILL，等于没解决问题。
**Why it happens:** Chromium 关闭时需要做的清理工作（写 `Preferences`、清 `SingletonLock`、Session 状态落盘）耗时与机器负载、profile 大小、扩展数量相关，不是恒定的。
**How to avoid:** CONTEXT 建议的 3-5s 区间是合理起点；批量启动/停止 2-3 个配置的验证场景（LAUNCH-02 D-04 已要求）天然也是验证宽限期是否够用的好场景——如果批量停止后重新启动同一批 profile 频繁遇到 `SingletonLock` 冲突，说明宽限期需要调大。
**Warning signs:** 停止后立即重新启动同一 profile 报 "user_data_dir 正在使用中" 或 profile 数据出现截断/损坏的 JSON。

## Code Examples

### 真机验证脚本（D-07 quarantine 实证，供执行阶段 checkpoint:human-verify 使用）

以下步骤应在用户的 arm64 Mac 上手动执行一次，作为 D-07 的最终判定依据（研究不能替代）：

```bash
# 1. 用浏览器（不是 curl/gh）从 GitHub Release 页面真实下载一次 macOS arm64 内核 zip，
#    确保走的是会触发 LSQuarantine 的下载路径
xattr -p com.apple.quarantine ~/Downloads/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip
# 预期：应看到形如 "0083;<hex-timestamp>;Safari;<UUID>" 的输出（确认 zip 本身已被标记）

# 2. 用仓库既有解压方式（ditto，非 Finder 双击）解压
ditto -x -k ~/Downloads/ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip /tmp/kernel-test

# 3. 检查解压产物是否继承了 quarantine（这是本研究的核心待证问题）
xattr -p com.apple.quarantine "/tmp/kernel-test/Chromium.app/Contents/MacOS/Chromium"
# 若报 "No such xattr"：ditto 未传播 quarantine，与 CITED 的社区研究一致（大概率结果）
# 若确实存在：需要在 D-07 的落地流程里保留 xattr -dr 剥离这一步（防御性兜底证明有意义）

# 4. 无论第 3 步结果如何，直接用 subprocess.Popen 风格（不经 open -a）验证能否启动：
"/tmp/kernel-test/Chromium.app/Contents/MacOS/Chromium" \
  --user-data-dir=/tmp/kernel-test-profile \
  --remote-debugging-port=9333 \
  --remote-allow-origins=* \
  --no-first-run --no-default-browser-check &
sleep 3
curl -sf http://127.0.0.1:9333/json/version && echo "CDP 响应正常，未被 Gatekeeper 拦截"
kill %1 2>/dev/null

# 5. 若第 4 步失败，用退出码和系统日志区分是 quarantine/Gatekeeper 还是签名门禁：
echo "退出码: $?"   # 137 (128+SIGKILL) 常提示签名/AMFI 层拦截
log show --predicate 'subsystem == "com.apple.syspolicy" or eventMessage contains "Chromium"' \
  --last 2m --info
```

### `stop_profile`/`_refresh_runtime_sessions` 的跨平台 mock 单测骨架（D-03）

```python
# tests/test_process_termination_macos.py（新文件，沿用 test_sync_regressions.py 的 mock 风格）
import unittest
from unittest.mock import MagicMock, patch

from backend.services import network


class KillProcessTreeGracefulTests(unittest.TestCase):
    @patch("backend.services.network.psutil.wait_procs")
    @patch("backend.services.network.psutil.Process")
    def test_sends_sigterm_before_sigkill(self, mock_process_cls, mock_wait_procs):
        parent = MagicMock()
        child = MagicMock()
        parent.children.return_value = [child]
        mock_process_cls.return_value = parent
        # 模拟宽限期内全部退出（gone=[parent, child], alive=[]）
        mock_wait_procs.return_value = ([parent, child], [])

        network.kill_process_tree(1234)

        parent.terminate.assert_called_once()
        child.terminate.assert_called_once()
        parent.kill.assert_not_called()  # 宽限期内已退出，不应再 SIGKILL
        child.kill.assert_not_called()

    @patch("backend.services.network.psutil.wait_procs")
    @patch("backend.services.network.psutil.Process")
    def test_sigkill_survivors_after_grace_period(self, mock_process_cls, mock_wait_procs):
        parent = MagicMock()
        mock_process_cls.return_value = parent
        parent.children.return_value = []
        # 第一次 wait_procs（宽限期）：全部仍存活；第二次（SIGKILL 后确认）：全部退出
        mock_wait_procs.side_effect = [([], [parent]), ([parent], [])]

        network.kill_process_tree(1234)

        parent.terminate.assert_called_once()
        parent.kill.assert_called_once()  # 宽限期超时后应被强制终止
```
**注：** 此测试模式不导入 `backend.browser_manager`/`backend.main`（只导入 `backend.services.network`），因此**在 Windows 上无需 pywin32 也能跑**，与 CLAUDE.md 的现状约束一致；若测试需要覆盖 `browser_manager.stop_profile` 的整体调用链，CLAUDE.md 记录的约束已确认「Phase 1 后 `browser_manager` 在 macOS 可导入」，本次环境勘察也确认导入失败仅因缺 `psutil` 模块本身（环境未装依赖），而非 `win32api` 类导入问题——`browser_manager` 层面的测试在 CI 的两个 runner 上均可跑，无需额外隔离。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `kill_process_tree` 全树立即 `SIGKILL` | 全树 `SIGTERM` → 宽限 → 幸存者 `SIGKILL` | 本 phase（D-05） | 减少 `SingletonLock`/profile 损坏风险，Windows 行为因 psutil 的 `terminate()`≡`TerminateProcess()` 而保持不变 |
| Gatekeeper 早期（Mojave 及更早）版本对"直接 exec"完全不做检查 | 近年（Catalina 起）macOS 对独立可执行 command-line tool 也加强了公证/签名要求（但这主要针对**独立分发的命令行工具**，不完全等同于"App bundle 内嵌套二进制被父进程 Popen" 场景） | Catalina（10.15）起 | 本仓库既有 Pitfalls 研究与本次搜索均提示 Apple 在逐步收紧，但**尚未发现权威一手文档证实"嵌套 .app 内二进制被父进程 Popen exec"这一具体场景在 Ventura/Sonoma/Sequoia 上被 Gatekeeper 拦截**——这正是必须真机验证而非仅凭研究下结论的原因 |

**Deprecated/outdated:**
- 无——本 phase 未涉及废弃 API。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | 命令行 `execve`/`subprocess.Popen` 直接启动带 quarantine 属性的二进制不会触发 Gatekeeper GUI 拦截 | Summary / Pitfall 1 / D-07 | 若实际会被拦截，D-07 的"启动路径防御性兜底"就从"锦上添花"变成"必需项"，且需要在启动失败时给用户可操作的错误提示（目前 `launch_chrome_profile` 的异常处理未覆盖这一具体场景） |
| A2 | 命令行 `ditto -x -k` 解压不会把源 zip 的 quarantine 属性传播到解压产物 | Summary / 真机验证脚本 步骤 3 | 若实际会传播，则"内核落地时剥离一次"这一步骤（而非只做启动路径防御）就是刚需，不能省略；且需要在 `scripts/release/verify_and_upload_macos_kernel.sh` 或应用自身的内核安装流程里补上这一步 |
| A3 | `psutil.Process.terminate()` 在 Windows 上等同于 `TerminateProcess()`（与现有 `kill()` 行为一致） | Pattern 1 / Standard Stack | 若实际不等价（例如某些 Windows 场景 `terminate()` 需要额外权限或行为有细微差异），Windows 侧回归测试可能捕捉不到,需要在改动后于真实 Windows 机器上手动跑一次现有全量 unittest 复核（CONTEXT D-11 的既定验收方式已覆盖这个兜底） |
| A4 | 用户实际下载/解压内核的具体路径（浏览器下载 zip → Terminal `ditto` 解压，而非 Finder 双击 Archive Utility 解压） | Pitfall 2 / 真机验证脚本 | 若用户实际操作是双击 Finder 解压（走 Archive Utility），quarantine 传播行为与 A2 的假设相反,需要把"内核落地时剥离"从可选项变为强制步骤 |

**风险总评：** A1/A2/A4 都是本次 Gatekeeper/quarantine 研究里唯一无法用工具直接验证、只能靠社区文献交叉印证的部分（无法拉取 Apple 官方 Platform Security Guide 原文，两次尝试均被墙/重定向失败），MEDIUM confidence 上限。**Planner 必须在执行计划里为 D-07 安排一个 `checkpoint:human-verify` 任务，引用上面「真机验证脚本」小节的具体步骤，而不能把本研究的结论当作已验证事实直接写入实现。**

## Open Questions

1. **CLI exec 是否真的不触发 Gatekeeper（A1/A4 的最终判定）**
   - What we know: 多个独立社区来源（Eclectic Light Co、HackTricks 系搜索结果综合）一致认为 Gatekeeper 的 GUI 门禁只在 LaunchServices 发起的启动时触发；本仓库自己的既有 Pitfalls 研究（milestone 级）也持相同结论但同样标注为 MEDIUM confidence、未做过本仓库场景的真实复现。
   - What's unclear: 是否存在 macOS 版本相关的例外（例如某个安全更新收紧了这一行为）；是否存在"首次执行一个新下载的二进制"与"重复执行同一个已执行过的二进制"之间的差异。
   - Recommendation: 按真机验证脚本执行一次即可确证；结果应记录进 03-EXECUTION-LOG 或等价位置，供 Phase 5/6（dmg 分发场景，quarantine 风险更高）复用这次实证结论。

2. **capabilities 是否暴露到 `/open-api`**
   - What we know: CONTEXT 明确标注为"非本次讨论新增 scope，planner 可按需决定"。
   - What's unclear: 自动化用户（`/open-api` 消费方）是否有实际需求读取平台能力。
   - Recommendation: 若无明确需求信号，本 phase 默认不暴露（保持最小改动面），后续有需求再加，不影响 XPLAT-05 验收（ROADMAP SC4 只要求 `GET /api/capabilities` 这一个端点存在）。

3. **SIGTERM 宽限期的确切秒数**
   - What we know: CONTEXT 给出 3-5s 参考区间。
   - What's unclear: 该项目 profile 规模/扩展数量下 Chromium 实际优雅退出所需时间的经验值（无法在研究阶段测得，需要真机批量场景验证）。
   - Recommendation: 先取 3s 作为默认值（在停止/退出这种交互路径上，用户对"稍等几秒"的容忍度高于对"卡住"的容忍度），若 LAUNCH-02 的批量启停验证（D-04）发现 `SingletonLock` 冲突频发，再上调到 5s。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| macOS arm64 真机（用户自有） | LAUNCH-01/02/03 真机手动冒烟（D-03） | 用户侧已确认拥有 | — | 无——ROADMAP/CONTEXT 明确以此为主验收手段，无法用 CI 模拟替代 quarantine/Gatekeeper 这类真机专属行为 |
| macOS arm64 内核资产（`kernel-149.0.7827.114`） | 联调启动链路 | ✓（Phase 2 已发布） | 149.0.7827.114-1.3 | — |
| `psutil` Python 包 | 进程树管理改造 | ✓（`requirements.txt:3` 已锁定 >=5.9.8） | 本次研究环境验证时因未 `pip install` 而报 `ModuleNotFoundError`，属环境未初始化而非代码问题——`pip install -r requirements.txt` 后应可用 | — |
| `xattr`（系统自带命令） | D-07 quarantine 剥离 | ✓（macOS 系统自带，无需安装） | 系统版本自带 | — |
| `codesign`/`lipo`（系统自带命令） | 复核内核签名/架构（诊断用，非本 phase 新增门禁） | ✓（macOS 系统自带） | 系统版本自带 | — |
| Windows 机器/虚拟机（用户侧） | 零回归验证（沿用 D-11） | 用户侧此前已确认拥有（Phase 1 已用过） | — | — |

**Missing dependencies with no fallback:** 无——所有依赖均已就绪或为系统自带工具。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python `unittest`（无 pytest 配置），`[VERIFIED: CLAUDE.md + tests/ 目录现状]` |
| Config file | 无独立配置文件——纯 `python -m unittest discover -s tests -v`，从仓库根目录运行 |
| Quick run command | `python -m unittest tests.test_process_termination_macos -v`（本 phase 新增文件，示例名） |
| Full suite command | `python -m unittest discover -s tests -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| LAUNCH-01 | Popen 直接启动嵌套二进制，记录 PID/端口 | unit（mock Popen） | `python -m unittest tests.test_launch_geo_fallback -v` | ✅ 已存在（可扩展覆盖 macOS 路径场景） |
| LAUNCH-01 | quarantine/Gatekeeper 实际拦截行为 | manual-only（真机） | 见「真机验证脚本」小节 | ❌ Wave 0（无法自动化，OS 级安全机制） |
| LAUNCH-02 | 代理/geo/扩展/批量启动逐项生效 | manual-only（真机肉眼确认，D-04 已定） | 人工冒烟清单（非本 phase 新增自动化） | ❌ Wave 0（业务逻辑本身已有单测覆盖，"肉眼确认生效"这层是真机专属） |
| LAUNCH-03 | 进程树优雅终止（SIGTERM→宽限→SIGKILL） | unit（mock psutil） | `python -m unittest tests.test_process_termination_macos -v` | ❌ Wave 0 — 新文件 |
| XPLAT-05 | `GET /api/capabilities` 返回结构正确 | unit（FastAPI TestClient 或直接调用 `get_platform_capabilities()`） | `python -m unittest tests.test_capabilities_api -v`（示例名，或并入现有 `test_api_docs_content.py`） | ❌ Wave 0 — 新文件或新增用例 |

### Sampling Rate
- **Per task commit:** `python -m unittest tests.test_process_termination_macos tests.test_capabilities_api -v`（只跑本 phase 新增/改动相关文件，快速反馈）
- **Per wave merge:** `python -m unittest discover -s tests -v`（全量，本仓库现状本就是纯 unittest 全量跑，成本可控——现有 7 个测试文件共约 1358 行）
- **Phase gate:** 全量 unittest 绿灯 + 用户 arm64 真机手动冒烟通过（D-03 主验收手段）后才进入 `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_process_termination_macos.py` — 覆盖 LAUNCH-03（mock psutil 的 terminate/wait_procs/kill 序列）
- [ ] `tests/test_capabilities_api.py`（或并入现有文件）— 覆盖 XPLAT-05（`get_platform_capabilities()` 返回结构 + `/api/capabilities` 路由 + `bootstrap()` 含 capabilities 字段）
- [ ] 真机验证脚本执行记录（非自动化测试，但需要在执行阶段留痕，供 D-07 结论追溯）
- 框架安装：无需新增，`unittest` 是标准库自带

## Security Domain

### Applicable ASVS Categories

本项目是本地单用户桌面工具，`/api/*`（本地 UI 用）无鉴权设计是既有架构决策（非本 phase 引入），`/open-api`（自动化面）已有 API Key/Bearer 鉴权。本 phase 新增的 `/api/capabilities` 端点是只读、无敏感数据的能力声明，不改变现有鉴权模型。

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | 否 | 沿用现状——本地 `/api/*` 无鉴权是既有架构决策，本 phase 不新增鉴权面 |
| V3 Session Management | 否 | 同上，无 session 概念 |
| V4 Access Control | 否 | 新增端点只读且无敏感信息（平台名、布尔能力标记），无需访问控制 |
| V5 Input Validation | 否 | `/api/capabilities` 无请求参数，无输入面需要校验 |
| V6 Cryptography | 否 | 本 phase 不涉及任何加密/签名操作（内核签名校验是 Phase 2 已完成的既有工作，非本 phase 新增） |

### Known Threat Patterns for macOS 进程启动/终止

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| 恶意替换内核二进制（用户手动把 `ENGINES_DIR/chrome/Chromium.app` 换成其他二进制） | Tampering | 应用层无法完全防御（本地单用户工具的信任边界本就是"用户对自己机器有完全控制权"），但 D-07 的启动路径防御性兜底（若实现）间接提供了一个"重新触发 quarantine 检查"的机会点——不作为安全边界，仅作为可用性兜底 |
| 进程树终止时残留 `SingletonLock` 被后续启动的其他进程滥用 | Tampering（低风险） | D-05 的优雅终止（SIGTERM→宽限）本身就是缓解手段，无需额外机制——本地单用户场景下这更多是可用性问题而非安全问题 |
| Quarantine 剥离命令（`xattr -dr`）被用于剥离用户其他无关文件 | Elevation of Privilege（误用风险，非本项目引入的漏洞） | 应用层调用 `xattr` 时必须精确指定内核目录路径（`bundled_engine_executable("chrome").parent` 或等价的、范围明确的路径），不得使用宽泛通配符或用户可控输入拼接路径 |

## Sources

### Primary (HIGH confidence)
- 直接读取仓库源码 `backend/services/chrome.py`、`backend/services/network.py`、`backend/browser_manager.py`、`backend/config.py`、`backend/services/window_manager.py`、`backend/main.py`、`scripts/release/verify_and_upload_macos_kernel.sh`、`requirements.txt`、`tests/*.py` — 确认现状实现、既有测试模式、Phase 2 内核签名校验结论
- `.planning/phases/03-macos-chrome-api/03-CONTEXT.md`、`.planning/phases/01-backend-cross-platform/01-CONTEXT.md`、`.planning/phases/02-macos/02-CONTEXT.md`、`.planning/ROADMAP.md`、`.planning/REQUIREMENTS.md`、`.planning/STATE.md` — 本仓库既有 GSD 规划文档，直接读取确认

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md`、`.planning/research/ARCHITECTURE.md`（本仓库里程碑级既有研究，2026-07-23 产出，本次复用并交叉验证其 Pitfall 3/6 关于 quarantine 与 launch 语义的结论）
- [Eclectic Light Co — Explainer: Quarantine](https://eclecticlight.co/2021/12/11/explainer-quarantine/) — "Gatekeeper mechanism is only triggered by launches from the GUI, not the command line" 的直接引用来源
- [Eclectic Light Co — Getting unnotarized apps out of quarantine](https://eclecticlight.co/2020/11/19/getting-unnotarized-apps-out-of-quarantine/)
- WebSearch 交叉验证（多个独立结果一致）：命令行 `unzip`/`tar`/`ditto` 不会将 quarantine 属性传播到解压产物，只有 Finder Archive Utility 会传播
- psutil 官方文档记载的 `kill_proc_tree` 范式（`children(recursive=True)` → `terminate()` → `wait_procs(timeout, callback)` → `kill()`），经 WebSearch 交叉验证多个独立代码示例引用来源一致

### Tertiary (LOW confidence / 需真机验证)
- CLI `execve`/`Popen` 在 Ventura/Sonoma/Sequoia（近期 macOS 版本）上对**嵌套 .app 内二进制**的 Gatekeeper 拦截行为的版本相关细节——两次 WebFetch 尝试拉取更权威来源（HackTricks 页面、Apple 官方文档路径）均因访问限制（402 付费墙、重定向失败）未能确证，本研究的结论建立在社区文献交叉印证而非一手规范文档之上，**必须视为 Assumptions Log A1/A4 所述，需真机验证后才能升级为确认事实**

## Metadata

**Confidence breakdown:**
- Standard stack（无新依赖，沿用 psutil）：HIGH — 直接读取 `requirements.txt` 与现有代码确认
- Architecture（capabilities API 契约、进程终止改造范式）：HIGH — 基于既有代码结构做增量设计，模式本身有官方文档/社区文献支撑
- Pitfalls（quarantine/Gatekeeper 实证细节）：MEDIUM — 多方社区来源交叉印证，但缺一手 Apple 文档确认，且明确要求真机验证补完

**Research date:** 2026-07-27
**Valid until:** quarantine/Gatekeeper 相关结论建议 30 天内完成真机验证后重新确认（macOS 安全策略可能随系统更新调整）；其余架构性结论（capabilities API、进程终止范式）作为设计决策一旦落地即视为稳定，无需按时间失效重新研究

---
*Phase: 3-macOS Chrome 启动与能力 API*
*Research completed: 2026-07-27*
