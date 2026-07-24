# Phase 1: 后端跨平台基础适配 - Context

**Gathered:** 2026-07-24
**Status:** Ready for planning

<domain>
## Phase Boundary

让后端在 macOS 上能装(`pip install -r requirements.txt` 直接成功)、能导入、能启动(含 `--backend-only` 纯后端模式),路径全部解析到 macOS 约定位置;窗口排列/同步类功能在 macOS 返回「仅 Windows 支持」错误。同时 Windows 现有行为零回归(既有 unittest 套件保持通过且行为不变)。覆盖需求 XPLAT-01 ~ XPLAT-04。

**不在本 phase**:macOS Chrome 实际启动链路(Phase 3)、capabilities API(Phase 3/XPLAT-05)、前端门控(Phase 4)、CI 打包(Phase 5)。

</domain>

<decisions>
## Implementation Decisions

### 窗口 API 的 macOS 错误形态
- **D-01:** 平台门控放在 `backend/services/window_manager.py` 内部:模块顶层按 `sys.platform` 判断,Windows 照常导入 win32api 系列;非 Windows 时导出同名函数但一律抛 RuntimeError(如「窗口排列仅在 Windows 上可用」)。`browser_manager.py:36` 的导入语句与其他调用方零改动。
- **D-02:** 错误响应沿用现状:HTTPException 400 + 中文 detail(main.py 现有 try/except 包裹自动生效),不引入专用状态码或机器可读错误码字段。前端平台门控将来依赖 Phase 3 的 capabilities API,不靠错误码判断。
- **D-03:** 拦截范围 = 窗口排列四个端点(`/api/synchronizer/monitors`、`show-windows`、`uniform-size`、`arrange-windows`)**加上**同步器启动(`/api/synchronizer/start` 等入口)。macOS 上同步器整体不可用,不允许出现半可用状态。— **Reversibility:** reversible — 后续里程碑做 CDP-only 跨平台同步(SYNC-01)时放开即可。
- **D-04:** `main.py:485` 的 `os.startfile(raw_url)` 在 Phase 1 顺手修为跨平台实现(标准库 `webbrowser.open` 或平台分支),消除已知的 macOS 运行时崩溃点。

### config.py 平台化广度
- **D-05:** config.py 做**平台感知结构化**,不是最小补丁:可写根、引擎可执行路径、`ENGINE_METADATA`、内核下载 URL 统一按平台解析;macOS 的内核下载 URL 先留占位(Phase 2 产出 kernel release 资产后填入真实 URL)。约束:Windows 平台解析出的所有值必须与现值完全一致(零回归)。— **Reversibility:** costly — ENGINE_METADATA 结构被 storage.py、browser_manager.py、CI workflow(读 CHROME_ENGINE_ZIP_URL)多处消费,结构一旦定型 Phase 2/3/5 都在其上叠加。
- **D-06:** macOS 路径按 XPLAT-03 锁定值:冻结态可写根 `~/Library/Application Support/Open-Anti-Browser/`;Chrome 引擎可执行路径解析到 `Chromium.app/Contents/MacOS/Chromium`(位于 ENGINES_DIR 下)。开发态两平台继续用 PROJECT_ROOT。
- **D-07:** portable 模式为 **Windows 专属特性**:macOS 上忽略 `OPEN_ANTI_BROWSER_PORTABLE` 环境变量与 `portable.mode` 标记,始终写 `~/Library/Application Support/`。理由:数据写入 .app bundle 违反 macOS 惯例且会破坏 Phase 5 的 `codesign --verify --deep --strict` 硬门禁。
- **D-08:** `ENGINE_METADATA` 的 firefox 条目在 macOS **保留不删**(路径按平台解析,引擎不存在即天然不可用),避免遍历双引擎结构的代码(storage.py 等)连锁报错;「firefox 在 macOS 不可用」由 Phase 3 capabilities API 声明、Phase 4 前端隐藏。已有 firefox 配置的 profiles.json 在 macOS 上必须能正常加载。

### 依赖标记范围
- **D-09:** `requirements.txt` 中 `pywin32` 与 `ruyipage` 都加 `; sys_platform == "win32"` 环境标记。ruyipage 仅服务 Firefox 同步(macOS 已排除 Firefox),且 `synchronizer.py:14-18` 的导入已有 try/except 保护,macOS 不装是安全的。
- **D-10:** `pyinstaller` 等构建期依赖**不拆分**,保持在 requirements.txt(两平台都需要,Phase 5 macOS 打包也用),不引入 requirements-build.txt 之类的新依赖文件结构。

### Windows 零回归验证方式
- **D-11:** 用户有 Windows 机器/虚拟机:Phase 1 完成后在 Windows 上手动跑全量 `python -m unittest discover -s tests -v` 作为零回归验收。
- **D-12:** Phase 1 新增一个 push/PR 触发的 CI 测试 workflow(独立于现有发版 workflow):`windows-latest` 跑全量 unittest;macOS runner 跑非 Windows 依赖的测试子集。零回归从一次性验证变成持续保障。
- **D-13:** 为新增平台分支补两平台可跑的单元测试:config 路径解析(mock `sys.platform` / 冻结态)、window_manager 非 Windows 报错、runtime_control 派生参数平台条件化、窗口/同步 API 的 macOS 拦截行为。注:Phase 1 完成后 `browser_manager` 在 macOS 可导入,CLAUDE.md 中「非 Windows 无法跑相关测试」的限制随之大幅解除,新测试应利用这一点。

### Claude's Discretion
- window_manager 条件化的具体实现形式(顶层 if/else、桩函数组织方式)。
- `SYSTEM_CHROME_EXECUTABLE` / `SYSTEM_FIREFOX_EXECUTABLE` 在 macOS 的具体值(如 `/Applications/Chromium.app/...`)。
- `runtime_control.py` 在 POSIX 上替代 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` 的具体机制(如 `start_new_session=True`),只要满足 XPLAT-04 的派生/检活/停止语义。
- CI 测试 workflow 的文件命名、触发条件细节、macOS 测试子集的圈定方式。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与范围
- `.planning/ROADMAP.md` — Phase 1 目标与 5 条成功标准(含「Windows 字节级不变」口径)
- `.planning/REQUIREMENTS.md` — XPLAT-01 ~ XPLAT-04 具体验收条件
- `.planning/PROJECT.md` — v0.2 约束(零回归、sys_platform 标记、平台条件分支)与 Key Decisions

### 工程约定
- `CLAUDE.md` — 测试环境约束(pywin32/导入链限制)、`backend/_g.py` 完整性校验注意事项、commit message 约定

No external specs beyond the above — requirements fully captured in decisions.

</canonical_refs>

<code_context>
## Existing Code Insights

### 关键改动落点(扫描确认)
- `requirements.txt:14` — `pywin32>=308` 无标记;`ruyipage>=1.0.0`(line 15)同样需标记。
- `backend/services/window_manager.py:7-10` — 顶层 `import win32api/win32con/win32gui/win32process`,是 macOS 导入崩溃的根源;D-01 的改动主体。
- `backend/browser_manager.py:36` — 顶层 `from .services.window_manager import ...`,D-01 方案下无需改动。
- `backend/config.py` — `_writable_root()`(line 23-34,LOCALAPPDATA 逻辑)、`SYSTEM_*_EXECUTABLE`、`DEFAULT_*_EXECUTABLE`(.exe 硬编码)、`ENGINE_METADATA` 与下载 URL;D-05/D-06/D-07 的改动主体。
- `backend/runtime_control.py:19` — `DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)` 兜底值非零,POSIX 上传给 Popen 的 `creationflags` 非零会直接 ValueError,是 `--backend-only` 在 macOS 崩溃的根源(XPLAT-04)。
- `backend/services/chrome.py:22` / `firefox.py:129` — `CREATE_NEW_PROCESS_GROUP = getattr(..., 0)` 兜底为 0,POSIX 上传 0 合法,不阻塞 Phase 1(启动链路属 Phase 3)。
- `backend/main.py:485` — `os.startfile`,D-04 修复点。
- `backend/main.py:274-311` — synchronizer 端点统一 try/except → HTTPException(400, str(exc)),D-02 依赖此现状。

### Established Patterns
- 所有路径常量从 `backend/config.py` 导入(唯一来源),平台分支必须收敛在 config.py 内。
- 测试为纯 unittest + `unittest.mock.patch` 打桩(参考 `tests/test_sync_regressions.py` 的 FakeSyncClient 模式),从仓库根目录运行。
- `backend/_g.py` 完整性校验:Phase 1 不触碰 `frontend/src/lib/openSourceNotice.js` / `App.vue`,无哈希更新需求。

### Integration Points
- 现有 CI 仅有 `.github/workflows/build-release.yml`(推 v* tag 触发发版),D-12 的测试 workflow 是新增文件,互不干扰。
- `tests/` 现有 7 个测试文件,其中依赖 `backend.browser_manager` 导入链的在 macOS 上目前跑不了;Phase 1 后可解锁。

</code_context>

<specifics>
## Specific Ideas

- 错误文案示例:「窗口排列仅在 Windows 上可用」/「窗口同步仅在 Windows 上可用」——中文、与现有 API 错误风格一致。
- 用户曾误读「仅 Windows 支持」为全应用范围——文案应明确指向具体功能(窗口排列/窗口同步),避免让 macOS 用户以为整个应用不支持 mac。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.(同步器的 CDP-only 跨平台化已在 REQUIREMENTS.md Future Requirements 中记录为 SYNC-01,非本次讨论新增。)

</deferred>

---

*Phase: 1-后端跨平台基础适配*
*Context gathered: 2026-07-24*
