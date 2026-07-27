---
phase: 02-macos
reviewed: 2026-07-27T05:24:02Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - scripts/release/verify_and_upload_macos_kernel.sh
  - backend/config.py
  - tests/test_config_platform.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 02-macos: Code Review Report

**Reviewed:** 2026-07-27T05:24:02Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

审查了 macOS 内核构建与发布相关的三个文件:上传把关脚本 `verify_and_upload_macos_kernel.sh`、`backend/config.py` 中新增的两个 macOS 内核 URL 常量、以及对应的 `tests/test_config_platform.py`。

整体实现质量较高:脚本全程用 `ditto` 保留 Framework 符号链接与签名、双二进制架构断言、`--clobber` 幂等上传、上传文件名从 `backend.config` 单一来源解析(不二次硬编码)等设计都是经过深思熟虑的。按 review 指令,arch-conditional 的 codesign 阶段(仅 arm64 校验签名、x86_64 跳过)属于既定设计,未作为缺陷提出。

未发现 Critical 级别问题(无注入、无硬编码密钥、无鉴权绕过)。但发现 3 个 Warning 级别的健壮性/一致性问题,以及 5 个 Info 级别的可改进点,详见下文。其中最值得关注的是 WR-03:`backend/config.py` 中 macOS 内核版本号相关注释已经与 Windows 分支的实际状态(`-1.4`)脱节,存在版本漂移风险,需要人工确认 macOS 内核是否需要同步 `-1.4` 的 pixelscan 补丁。

## Warnings

### WR-01: `--arch` 缺值时参数解析以生硬的 bash 内建错误崩溃,而非走 usage()

**File:** `scripts/release/verify_and_upload_macos_kernel.sh:35-38`
**Issue:** 参数解析循环中:
```bash
--arch)
  ARCH="${2:-}"
  shift 2
  ;;
```
若脚本以 `--arch` 结尾调用(即 `$2` 不存在、剩余位置参数只有 1 个),`ARCH="${2:-}"` 本身不会报错(默认空串),但紧接着的 `shift 2` 在只剩 1 个位置参数时会失败(`shift: shift count out of range`,返回非 0)。由于脚本头部是 `set -euo pipefail`,这个非 0 返回会让脚本立即以内建错误信息终止,而不会像其他非法参数那样走到 `usage()` 给出友好中文提示。已用如下方式复现:
```bash
$ bash -c 'set -euo pipefail; args=("--arch"); set -- "${args[@]}";
while [[ $# -gt 0 ]]; do case "$1" in --arch) ARCH="${2:-}"; shift 2;; esac; done'
$ echo $?
1
```
对于一个人工/CI 都会调用的发布把关脚本,这种失败模式会让排查者看到无意义的 bash 报错而非清晰的用法提示,增加调试成本。
**Fix:** 显式校验 `$2` 是否存在,不存在时直接给出 usage 提示:
```bash
--arch)
  if [[ $# -lt 2 || -z "${2:-}" ]]; then
    echo "错误: --arch 需要一个值" >&2
    usage
  fi
  ARCH="$2"
  shift 2
  ;;
```

### WR-02: 冒烟测试只 kill 主进程 pid,Chromium 派生的子进程(GPU/渲染器/网络服务)未被回收

**File:** `scripts/release/verify_and_upload_macos_kernel.sh:170-198`
**Issue:** `smoke_test` 后台启动 launcher(`"${launch_cmd[@]}" ... &`)并记录 `pid=$!`,校验结束后只做 `kill "$pid"` + `wait "$pid"`。Chromium 类浏览器启动后通常会 fork 出多个子进程(GPU process、渲染进程、network service 等);仅杀主进程并不能保证这些子进程也随之退出(取决于父子进程组关系及浏览器自身的清理逻辑)。在 CI/自托管 runner 上对 arm64、x86_64 两个架构连续跑该脚本时,若子进程未完全退出,会残留后台进程占用文件描述符/端口,并且随后 `rm -rf "$profile_dir"`(行 198)可能在这些子进程仍在写该目录时执行。
**Fix:** 使用进程组(`setsid`/`kill -- -$pid`)或 `pkill -P "$pid"` 兜底回收子进程,并在删除 `profile_dir` 前给子进程留出退出时间:
```bash
kill "$pid" 2>/dev/null || true
pkill -P "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
rm -rf "$profile_dir"
```

### WR-03: `backend/config.py` 中 macOS 内核版本注释已与 Windows 现状不符,存在版本漂移风险

**File:** `backend/config.py:120-121`
**Issue:**
```python
# macOS 内核资产（arm64/x64 分开出包，不做 universal binary）。-1.3 revision 标识
# 021 基线（macOS 首次构建），与 Windows 现有 -1.2 区分，同样复用 _CHROME_KERNEL_BASE。
```
`git log` 显示:该注释和 `-1.3` 常量是在 Windows 侧仍为 `-1.2` 时(commit `093abf5`)写下的;随后 `52dd959`("Bump chrome kernel to 149-1.4 pixelscan patch")把 Windows 的 `CHROME_ENGINE_ZIP_URL` / `CHROME_INSTALLER_URL` 升到了 `-1.4`(引入 pixelscan 补丁),但**没有同步修改**紧邻上方 macOS 常量的这段注释,也没有评估 macOS 内核是否需要同一个 pixelscan 补丁。当前文件状态是:Windows 分支注释(107-109 行)正确写着 "-1.4 revision adds the pixelscan patch",而 macOS 分支注释仍然说 "与 Windows 现有 -1.2 区分"——两处注释互相矛盾,后来的维护者据此判断 macOS 基线时会被误导。更实质的风险是:如果 pixelscan 补丁是安全/反检测相关的功能性修复,macOS 用户可能正在使用一个缺少该修复的内核,而没有任何显式记录或 TODO 标注这个已知差距。
**Fix:** 至少更新注释以反映当前真实状态,并显式记录是否有意延后 macOS 补丁同步:
```python
# macOS 内核资产（arm64/x64 分开出包，不做 universal binary）。-1.3 revision 标识
# 021 基线（macOS 首次构建）。注意：Windows 侧已于 -1.4 引入 pixelscan 补丁，
# macOS 尚未同步该补丁（TODO: 评估是否需要为 macOS 内核补齐 pixelscan patch）。
```
并跟踪一个后续任务，确认 macOS 内核是否需要重新出包以携带 pixelscan 补丁。

## Info

### IN-01: 冒烟测试的端口选择存在极小概率的 TOCTOU 竞态

**File:** `scripts/release/verify_and_upload_macos_kernel.sh:148-151`
**Issue:** 用 `python3 -c 'socket.bind(("",0)); print(port); close()'` 拿到一个"当前空闲"端口后立即关闭 socket,再传给 Chromium 的 `--remote-debugging-port`。socket 关闭和 Chromium 实际 bind 之间存在时间窗口,理论上可能被同一台机器上的其他进程抢占该端口,导致冒烟测试出现偶发性、难以复现的失败。这是业界常见做法,风险很低,仅作记录。
**Fix:** 可选地在失败重试逻辑中区分"端口被占用"与"真正的 CDP 未响应"错误,或改用 Chromium 自身的 `--remote-debugging-port=0`(若该 fork 支持)让浏览器自行选择并从日志里解析实际端口。

### IN-02: `wait "$pid"` 无超时,若进程不响应 SIGTERM 脚本可能挂起

**File:** `scripts/release/verify_and_upload_macos_kernel.sh:196-197`
**Issue:** `kill "$pid"` 发送默认 SIGTERM 后紧跟 `wait "$pid"`,没有超时兜底。正常情况下 Chromium 会响应 SIGTERM 退出,但如果进程卡死或忽略信号,`wait` 会无限期阻塞,使整个 CI 任务挂起而不是快速失败。
**Fix:** 加超时后升级为 SIGKILL,例如用 `timeout` 包裹 wait,或轮询 `kill -0 "$pid"` 若干秒后强制 `kill -9`。

### IN-03: zip/`.app` 后缀匹配大小写敏感

**File:** `scripts/release/verify_and_upload_macos_kernel.sh:77-89`
**Issue:** `[[ "$ARTIFACT" == *.zip ]]` 与 `[[ "$ARTIFACT" == *.app ]]` 均为大小写敏感匹配,若传入 `Foo.ZIP` 或 `Foo.APP` 会直接落入最后的 `else` 分支报"必须是 .zip 文件或 .app 目录"的误导性错误。属于小概率场景,不影响正常发布流程。
**Fix:** 视需要可加 `shopt -s nocasematch` 或显式转小写比较;非必须。

### IN-04: 测试直接依赖 `backend.config` 的下划线前缀"私有"常量

**File:** `tests/test_config_platform.py:89, 101`
**Issue:** `test_macos_arm64_kernel_url` / `test_macos_x64_kernel_url` 直接引用 `config._CHROME_KERNEL_BASE`(下划线前缀,按约定属于模块内部实现细节)来做断言前缀比较和拼接期望值。测试与实现细节耦合较紧,未来如果 `_CHROME_KERNEL_BASE` 改名/重构会连带改测试,但这属于常见的可接受权衡,不构成缺陷。
**Fix:** 可选:直接用字面量 URL 常量断言,或将 `_CHROME_KERNEL_BASE` 提升为无下划线的公开常量(如果它确实是脚本/CI 也依赖的 SSOT)。

### IN-05: `find` 只取第一个匹配的 `.app`,归档含多个 bundle 时结果不确定

**File:** `scripts/release/verify_and_upload_macos_kernel.sh:91`
**Issue:** `find "$SCRATCH" -maxdepth 2 -name '*.app' -print -quit` 依赖文件系统遍历顺序选取第一个匹配项。目前的内核产物预期只包含单个 `.app`,风险较低,但如果上游打包流程未来引入辅助/嵌套 `.app`(例如 Crashpad handler 或第三方 helper app),行为将取决于遍历顺序而非确定性规则,可能悄悄选中错误的 bundle 而不报错。
**Fix:** 如果产物结构后续变复杂,建议改为显式校验"仅存在一个 `.app`"(`find ... | wc -l` 断言为 1)后再取值,而不是静默取第一个。

---

_Reviewed: 2026-07-27T05:24:02Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
