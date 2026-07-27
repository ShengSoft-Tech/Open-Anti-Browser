# Phase 3: macOS Chrome 启动与能力 API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 3-macOS Chrome 启动与能力 API
**Areas discussed:** 能力 API 契约, 启动链路验证深度, 进程树终止行为, 内核 quarantine 处理

---

## 能力 API 契约(XPLAT-05)

### Q1 — 端点形态

| Option | Description | Selected |
|--------|-------------|----------|
| 新端点 + 并入 bootstrap | 新增 `GET /api/capabilities` 独立端点,同时把 capabilities 块并入 `bootstrap()`。对齐 ROADMAP SC4。 | ✓ |
| 仅新增 /api/capabilities | 只加独立端点,不改 bootstrap;前端需额外发一次请求。 | |
| 仅扩展 bootstrap/engines | 不新增端点,注入现有 get_engine_statuses()/bootstrap;与 SC4 措辞不一致。 | |

**User's choice:** 新端点 + 并入 bootstrap(推荐)

### Q2 — 能力字段粒度

| Option | Description | Selected |
|--------|-------------|----------|
| 显式 available + 窗口功能状态 | per-engine `available`(区分 installed;Firefox macOS available=false)+ 窗口功能 arrange/sync 的 available + reason 文案。前端直接读布尔门控。 | ✓ |
| 只给平台名 + 可用引擎数组 | capabilities 只报 platform + 可用引擎列表,窗口功能由前端自行推断。 | |
| 你决定字段设计 | 由 Claude 设计,满足 Phase 4 隐藏 Firefox + 置灰窗口功能即可。 | |

**User's choice:** 显式 available + 窗口功能状态(推荐)
**Notes:** `available`(平台是否支持)与现有 `installed`/`capability_ok`(路径是否存在)正交,是 Phase 4 UI-01/UI-02 门控的硬依据。

---

## 启动链路验证深度(LAUNCH-01/02/03)

### Q1 — 验收方式

| Option | Description | Selected |
|--------|-------------|----------|
| 真机手动为主 + 补跨平台单测 | arm64 Mac 真机手动冒烟为 LAUNCH 主验收 + mock Popen/psutil 单测锁回归。沿用 D-11/D-12。 | ✓ |
| 仅真机手动冒烟 | 只手动跑通,不加自动化;回归无持续保障。 | |
| 尽量自动化 | mock 自动化为主,真机只做一次端到端确认。 | |

**User's choice:** 真机手动为主 + 补跨平台单测(推荐)

### Q2 — 验证深度

| Option | Description | Selected |
|--------|-------------|----------|
| 逐项实测 | 真实代理(含账号代理走本地桥)、真实装扩展、经代理解析 geo、批量启 2-3 配置验证隔离,每项肉眼确认。 | ✓ |
| 核心实测 + 其余冒烟级 | 启动+停止+CDP 实测;代理/扩展/geo/批量只冒烟(能拉起不报错),深度留 Phase 6。 | |
| 你决定 | 由 Claude 定各项验证粒度。 | |

**User's choice:** 逐项实测(推荐)
**Notes:** Intel x64 原生启动验证仍推迟到 Phase 6(用户仅有 arm64 Mac)。

---

## 进程树终止行为(LAUNCH-03)

### Q1 — 终止策略

| Option | Description | Selected |
|--------|-------------|----------|
| 先 SIGTERM 宽限再 SIGKILL | macOS 上先给全树 SIGTERM + 宽限窗口(3-5s)让 Chromium 干净退出/落盘,超时再 SIGKILL。避免残留 SingletonLock/profile 损坏。 | ✓ |
| 沿用即时 SIGKILL | 保持现 kill_process_tree 全树直接 process.kill(),与 Windows 一致,最简单。 | |
| 你决定 | 由 Claude 选,满足"无残留"即可。 | |

**User's choice:** 先 SIGTERM 宽限再 SIGKILL(推荐)

### Q2 — 捕获机制

| Option | Description | Selected |
|--------|-------------|----------|
| 沿用 psutil 递归子进程 | 保持 kill_process_tree 的 children(recursive=True) 遍历,跨平台一致;Helper 为子进程可捕获。只在 macOS 叠加 SIGTERM 宽限。 | ✓ |
| macOS 额外用进程组 killpg | Popen 时 start_new_session=True,停止用 os.killpg 按进程组终止,更抗孤儿残留,但与 Windows 路径分叉。 | |
| 你决定 | 由 Claude 选捕获机制。 | |

**User's choice:** 沿用 psutil 递归子进程(推荐)
**Notes:** SIGTERM 宽限可用 psutil terminate()→wait_procs(timeout)→kill();Windows 上 psutil terminate 等同 TerminateProcess,故可做统一路径而非 macOS-only 分支。

---

## 内核 quarantine 处理(LAUNCH-01)

### Q1 — quarantine 策略

| Option | Description | Selected |
|--------|-------------|----------|
| 主动剥离 quarantine | 内核落地后 xattr -dr com.apple.quarantine + 研究确认 CLI exec 拦截行为。 | |
| 先假定绕过,仅验证 | 假定 CLI Popen/execve 绕过 Gatekeeper GUI,不主动剥离,被拦再处理。 | |
| 你决定 | 由 Claude 根据实测行为决定。 | ✓ |

### Q2 — 剥离时机

| Option | Description | Selected |
|--------|-------------|----------|
| 内核落地时剥离一次 | 下载/解压/安装后剥离一次,启动路径不重复。 | |
| 每次启动前防御性剥离 | 启动路径检查并 xattr,更抗手动替换带回 quarantine。 | |
| 你决定 | 由 Claude 选时机。 | ✓ |

**User's choice:** 两问均"你决定"(交 Claude 裁量)
**Notes:** 见下方 Claude's Discretion。

---

## Claude's Discretion

- **内核 quarantine(D-07):** 默认倾向 = 先在 arm64 Mac 上以真实下载内核实证 CLI Popen/execve 是否被 Gatekeeper 拦;若确需处理,默认内核落地时 `xattr -dr com.apple.quarantine` 剥离一次 + 启动路径保留防御性兜底。应用自身 bundle 放行归 Phase 4/6,不在此。
- capabilities 字段的具体命名与嵌套结构(满足 D-02 语义前提下)。
- SIGTERM 宽限秒数的确切取值。
- 是否把 capabilities 也暴露到 `/open-api`(自动化面)。

## Deferred Ideas

None — 讨论未越界。跨 phase 备忘见 CONTEXT.md `<deferred>`(open-api capabilities、Intel x64 原生验证推迟 Phase 6、应用 bundle 放行归 Phase 4/6)。
