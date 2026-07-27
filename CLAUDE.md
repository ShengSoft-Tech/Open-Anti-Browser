# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概况

Open-Anti-Browser 是一个本地桌面端指纹浏览器管理器:Python (FastAPI + PySide6) 后端 + Vue 3 前端,管理两套指纹内核(fingerprint-chromium 148 和 firefox-fingerprintBrowser 151)的配置、代理、扩展、批量启动和窗口同步。**运行目标平台是 Windows**(引擎是 .exe、窗口管理依赖 pywin32、打包用 PyInstaller),即使在 macOS/Linux 上开发,涉及进程/窗口的代码也要按 Windows 语义来写。

## 常用命令

```bash
# 后端开发(从仓库根目录运行,前端走 Vite 代理时只需要这个)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 前端开发(Vite 端口 5173,/api 代理到 127.0.0.1:8000)
cd frontend && npm install && npm run dev

# 前端构建(prebuild/postbuild 会运行 python -m backend._g 完整性校验,见下文)
cd frontend && npm run build

# 桌面应用(PySide6 QWebEngine 外壳,需要 Windows + 全部依赖)
python launch_app.py

# 纯后端 API 模式(无界面,默认端口 18000)
python launch_app.py --backend-only [--port 18000]

# 一键本地运行(先构建前端再起 uvicorn,由 FastAPI 托管静态页面)
python run_local.py

# Python 测试(unittest,从仓库根目录运行;依赖见下方"测试环境"说明)
python -m unittest discover -s tests -v
# 单个测试文件 / 单个用例
python -m unittest tests.test_sync_regressions -v
python -m unittest tests.test_sync_regressions.SynchronizerRegressionTests.test_browser_ui_sync_is_enabled_by_default

# 前端测试(node:test,无需额外依赖,从仓库根目录运行)
node --test frontend/src/lib/*.test.js
```

### 测试环境

- Python 测试需要先 `pip install -r requirements.txt`。其中 `pywin32` 只能在 Windows 安装,而 `backend/browser_manager.py` 顶层导入 `services/window_manager.py`(无条件 `import win32api`),所以凡是导入 `backend.browser_manager`、`backend.main` 或 `launch_app` 的测试在非 Windows 上无法运行。只依赖 `backend.services.network`、`backend.models`、`backend.storage` 等模块的测试不受此限制。
- 测试是纯 `unittest`(无 pytest 配置),必须从仓库根目录运行,使外部进程/网络依赖时一律用 `unittest.mock.patch` 打桩(参考 `tests/test_sync_regressions.py` 的 FakeSyncClient 模式)。
- `frontend/src/lib/proxyBypass.test.js` 用 node:test 直接从 `ProfileDialog.vue` 的 `<script setup>` 源码里抽取函数来测,修改该组件里的 bypass 相关辅助函数时注意保持函数声明形式(`function xxx(`),否则测试抽取会失败。

## 资源完整性校验(重要)

`backend/_g.py` 是一个故意混淆命名的完整性校验模块,目的是防止开源声明被移除:

- 它对 `frontend/src/lib/openSourceNotice.js` 和 `frontend/src/App.vue` 做 SHA-256 哈希锁定(哈希表在 `_g.py` 的 `_1` 字典里),并校验构建产物 `frontend/dist` 中包含开源声明的标记字符串。
- 触发时机:`npm run build` 的 prebuild/postbuild 钩子,以及桌面程序启动时(`launch_app.main` 调用 `_7("runtime")`)。校验失败会拒绝构建/启动。
- 因此:**修改这两个文件中的任何一个都会导致构建和启动失败**,除非同步更新 `_g.py` 中对应的哈希值。开源声明本身(首次使用提示)是项目的反商业滥用机制,不要移除它。

## 架构

### 进程模型

桌面形态下 `launch_app.py` 在同一进程内起两样东西:uvicorn 线程(FastAPI,端口 8000 起向上找)+ Qt 主线程的 QWebEngineView 窗口加载 `http://127.0.0.1:<port>?shell=desktop`。单实例通过 QLocalServer 实现。另有"纯后端模式":`runtime_control.py` 以 DETACHED_PROCESS 方式派生独立的 `--backend-only` 子进程(状态记录在 `runtime/backend-only.json`),让自动化 API 在关闭桌面界面后仍可用。

`backend/ui_bridge.py` 是 FastAPI → Qt 的回调注册表(退出应用、原生目录选择对话框),HTTP 端点通过它触发 Qt 主线程动作。

### 后端(backend/)

- `main.py` 定义两个 FastAPI 应用:`app`(本地 UI 用的 `/api/*`,无鉴权)和挂载在 `/open-api` 的 `open_api`(对外自动化 API,需 `X-API-Key` 或 Bearer token,key 存在设置里)。两者都是 `BrowserManager` 单例的薄路由层。`app` 同时把 `frontend/dist` 作为 SPA 静态资源托管(任意路径 fallback 到 index.html)。
- `browser_manager.py` 的 `BrowserManager` 是核心枢纽:配置 CRUD、运行时会话跟踪(`runtime_sessions` 字典 + psutil 检活 + `_session_lock`)、启动/停止浏览器、代理/扩展管理、同步器门面。启动流程见 `start_profile`:解析用户数据目录 → 调用对应引擎的 launch 函数 → 记录 `RuntimeSession`(含调试端口、代理桥、解析出的 IP/时区/语言)。
- `storage.py` 的 `JsonStorage`:线程安全(RLock)+ 临时文件原子写,数据落在 `data/settings.json` 和 `data/profiles.json`。并发修改配置必须走 `update_profiles(updater)` 回调模式,不要 load-修改-save。
- `models.py`:pydantic 模型,`extra="ignore"`。`BrowserProfile` 同时持有 chrome 和 firefox 两套设置,由 `engine` 字段决定生效哪套。旧字段迁移用 model_validator(参考 `proxy_bypass_domains` → `proxy_bypass_rules`)。
- `services/chrome.py` / `services/firefox.py`:把 profile 翻译成各引擎的启动命令。Chrome 走 fingerprint-chromium 的命令行参数(fingerprint seed 等);Firefox 写 `user.js` 偏好 + 指纹文件(fpfile)+ 安装扩展,并分配 marionette 端口。
- `services/network.py`:代理规范化、bypass 规则展开(Chrome bypass list / Firefox no_proxy 格式各异)、`LocalHttpProxyBridge`(本地代理桥,用来给不支持带凭据代理的浏览器转发认证代理)、按 IP 解析地理信息(`resolve_geo_profile` → 语言/时区,带 fallback)、代理连通性测试。
- `services/synchronizer.py`(最大的模块):窗口同步器。向主控窗口注入 JS(`MASTER_INJECT_SCRIPT`)把用户事件写入页面内队列,后端轮询取出后分发给每个跟随窗口的 `_FollowerWorker` 线程重放。Chrome 走 CDP WebSocket(`CdpPageClient`),Firefox 走 RuyiPage/Marionette(`RuyiFirefoxPageClient`),两个客户端类保持相同的方法接口。
- `services/window_manager.py`:win32 窗口排列(显示/统一大小/网格),仅 Windows。
- `config.py`:路径解析的唯一来源,区分开发态和 PyInstaller 冻结态(`sys._MEIPASS` 资源根 vs LOCALAPPDATA 可写根,支持 portable 模式标记文件),以及引擎元数据和下载地址。所有路径常量从这里导入,不要在别处拼路径。

### 前端(frontend/src/)

Vue 3 + Element Plus(unplugin 自动导入,无需手动 import 组件)+ Pinia + vue-i18n。单页应用,`App.vue` 负责侧边栏视图切换,主要状态集中在 `stores/profile.js`。`lib/api.js` 是 fetch 薄封装,请求相对路径 `/api/*`(开发时由 Vite 代理)。新增用户可见文案必须同时更新 `i18n/zh-CN.js` 和 `i18n/en-US.js`(zh-CN 为默认语言)。

### 数据与运行时目录(均已 gitignore)

`data/`(settings/profiles JSON)、`browser-data/`(各配置独立的浏览器用户目录)、`extensions/`(上传的扩展)、`downloads/`(引擎安装包)、`engines/`(内核可执行文件,仓库不含)、`runtime/`(backend-only 状态)。

## 其他约定

- API 错误信息和用户可见文案用中文;commit message 用英文短句(参考 git log:`Fix Firefox geo timezone resolution`)。
- README 刻意不提供打包/构建安装包的步骤,打包脚本(`build_installer.ps1` 等)已 gitignore,不要把打包配置加回仓库。
- 版本号同时存在于 `frontend/package.json` 和 `backend/main.py` 的两个 FastAPI `version` 字段,升版本时三处一起改。
