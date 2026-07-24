# Phase 1: 后端跨平台基础适配 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-24
**Phase:** 1-后端跨平台基础适配
**Areas discussed:** 窗口 API 的 macOS 错误形态, config.py 平台化广度, 依赖标记范围, Windows 零回归验证方式

---

## 窗口 API 的 macOS 错误形态

### 门控层次

| Option | Description | Selected |
|--------|-------------|----------|
| window_manager 内部条件化 | 模块顶层按 sys.platform 判断,非 Windows 同名函数抛 RuntimeError;其他文件零改动 | ✓ |
| browser_manager 条件导入 | 导入点按平台选择真实实现或桩;防护面窄 | |
| 路由层门控 | main.py 在非 Windows 直接返回错误;门控与业务分离,易漏 | |

**User's choice:** window_manager 内部条件化
**Notes:** 用户最初误读「仅 Windows 支持」为整个应用的支持范围;澄清后确认该提示仅针对窗口排列/同步功能。此误读被记入 CONTEXT.md specifics:错误文案应明确指向具体功能。

### 错误响应形态

| Option | Description | Selected |
|--------|-------------|----------|
| 沿用 400 + 中文 detail | 与现有端点一致,零改动;前端门控靠 Phase 3 capabilities | ✓ |
| 专用状态码 501 | 机器可读区分平台不支持;需路由层特殊处理 | |
| 400 + 机器可读错误码字段 | 结构化 detail;与现有纯字符串风格不一致 | |

**User's choice:** 沿用 400 + 中文 detail

### 拦截范围

| Option | Description | Selected |
|--------|-------------|----------|
| 窗口排列 + 同步器都拦 | 与 v0.2 决策一致,避免同步器半可用误导用户 | ✓ |
| 仅拦窗口排列 | 严格按 Phase 1 成功标准;同步器门控留给 Phase 3 | |

**User's choice:** 窗口排列 + 同步器都拦

### os.startfile 修复时机

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 1 顺手修 | webbrowser.open 或平台分支;改动小,消除已知地雷 | ✓ |
| 留到 Phase 3 | 属运行时功能,与启动链路一起验证 | |

**User's choice:** Phase 1 顺手修

---

## config.py 平台化广度

### 分支广度

| Option | Description | Selected |
|--------|-------------|----------|
| 平台感知结构化 | 可写根/引擎路径/ENGINE_METADATA/下载 URL 统一按平台解析,macOS URL 留占位 | ✓ |
| 最小分支 | 只改 XPLAT-03 必需两处;Phase 2/5 可能回头再改结构 | |
| 你决定 | 交给规划时权衡 | |

**User's choice:** 平台感知结构化

### portable 模式

| Option | Description | Selected |
|--------|-------------|----------|
| macOS 不支持 portable | 始终写 ~/Library/Application Support;不破坏 Phase 5 签名校验 | ✓ |
| macOS 也支持 portable | 需定义「.app 旁」语义,边界情况多 | |

**User's choice:** macOS 不支持 portable

### firefox 条目处理

| Option | Description | Selected |
|--------|-------------|----------|
| 保留条目不删 | 避免双引擎遍历代码连锁报错;不可用由 capabilities 声明 | ✓ |
| macOS 上移除 firefox 条目 | 平台层面彻底不暴露;改动面和回归风险大 | |

**User's choice:** 保留条目不删

---

## 依赖标记范围

### sys_platform 标记对象

| Option | Description | Selected |
|--------|-------------|----------|
| pywin32 + ruyipage 都标 | ruyipage 仅 Firefox 同步用且导入已有保护,macOS 不装更干净 | ✓ |
| 仅标 pywin32 | 最小改动,ruyipage 能装就照装 | |

**User's choice:** pywin32 + ruyipage 都标

### 构建依赖拆分

| Option | Description | Selected |
|--------|-------------|----------|
| 不拆,保持现状 | pyinstaller 两平台都需要,不引入新依赖文件结构 | ✓ |
| 拆 requirements-build.txt | 运行/构建依赖分离;需同步改 CI 和文档,超出主旨 | |

**User's choice:** 不拆,保持现状

---

## Windows 零回归验证方式

### Windows 环境可用性

| Option | Description | Selected |
|--------|-------------|----------|
| 有 Windows 机器/虚拟机 | 完成后手动跑全量 unittest 验收 | ✓ |
| 没有,靠 CI 验证 | 需加 GitHub Actions Windows job | |
| 没有,也不加 CI | 靠代码约束 + 人工审查 | |

**User's choice:** 有 Windows 机器/虚拟机

### CI 测试 workflow

| Option | Description | Selected |
|--------|-------------|----------|
| 加 CI 测试 job | push/PR 触发:windows-latest 全量 + macos 子集;持续保障 | ✓ |
| 仅手动验证 | Phase 1 不碰 CI,CI 改动留给 Phase 5 | |

**User's choice:** 加 CI 测试 job

### 新增平台分支测试

| Option | Description | Selected |
|--------|-------------|----------|
| 补平台分支单测 | config 路径解析/window_manager 报错/runtime_control 派生/API 拦截 | ✓ |
| 不补,只保既有套件 | 新分支靠手工验证 | |

**User's choice:** 补平台分支单测

---

## Claude's Discretion

- window_manager 条件化的具体实现形式
- SYSTEM_CHROME_EXECUTABLE / SYSTEM_FIREFOX_EXECUTABLE 在 macOS 的具体值
- runtime_control POSIX 派生的具体机制(如 start_new_session=True)
- CI 测试 workflow 的命名、触发条件、macOS 测试子集圈定

## Deferred Ideas

None — 讨论未超出 phase 范围。(CDP-only 跨平台同步已有 SYNC-01 记录在案,非本次新增。)
