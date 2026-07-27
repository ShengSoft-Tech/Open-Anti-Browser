---
phase: 02-macos
verified: 2026-07-27T00:00:00Z
status: passed
score: 3/3 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: macOS 内核发布 Verification Report

**Phase Goal:** fingerprint-chromium 149.0.7827.114 的 macOS arm64 与 Intel x64 两个内核已在本地(../fingerprint-chromium)构建完成,并作为 kernel release 资产可供下载。
**Verified:** 2026-07-27T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

**Scope boundary applied(与 discuss D-03/D-05 一致):** 本仓库(Open-Anti-Browser)只承担 (a) 上传前把关脚本、(b) gh release 发布、(c) backend/config.py URL 回填三件事;Chromium 构建/交叉编译/lipo/冒烟的执行发生在兄弟仓库 `../fingerprint-chromium`,该仓库不在本仓库范围内,内核可执行文件本就不入本仓库。验证以此为准,不因兄弟仓库构建产物不在本仓库而判定失败。

## Goal Achievement

### Observable Truths(对齐 ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | macOS arm64 内核可从 kernel release(kernel-149.0.7827.114)下载,产物经 ditto 打包保留符号链接并附带 ad-hoc 签名 | VERIFIED | 实时 `gh release view kernel-149.0.7827.114 --json assets` 命中 `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip`(155,462,650 字节)。本次verify 独立对本地留存的同一 zip(`~/bfwg/kernel-artifacts/...arm64.zip`,与 release 端字节数完全一致)重跑 `verify_and_upload_macos_kernel.sh --dry-run --arch arm64`:ditto 往返解压 → 双二进制 `lipo -archs` 均报 `arm64` → `codesign -dv` 检出 `adhoc`+`linker-signed` → CDP 冒烟 `/json/version` 命中 `149.0.7827.114`,退出码 0,耗时 4.8s,结束后 `pgrep` 确认无残留进程 |
| 2 | 兄弟仓库已补齐 downloads-macos-x64.ini,Intel x64 内核在 arm64 Mac 上交叉编译产出,同样可从同一 kernel release 下载 | VERIFIED | 实时 `gh release view` 命中 `ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip`(165,782,894 字节),与本仓库范围内可验证的目标(“同样可从同一 release 下载”)一致。兄弟仓库 `downloads-macos-x64.ini` 补齐 + 交叉编译本身按 D-03/D-05 边界归兄弟仓库,不在本仓库判定范围;02-04-SUMMARY.md 记录的兄弟仓库提交号(91d6603b/f0985747/30d2553a)作为过程佐证,未作为唯一证据来源 |
| 3 | 两个内核资产在上传前都通过 file/lipo 架构验证(确认各自架构匹配)与本机启动冒烟测试,文件名包含明确架构标识(如 arm64/x64) | VERIFIED | 独立对本地留存的 x64 zip 重跑 `verify_and_upload_macos_kernel.sh --dry-run --arch x86_64`:双二进制 `lipo -archs` 均报 `x86_64`(架构匹配)→ codesign 阶段按架构条件正确跳过(x86_64 平台设计不签名,见下方说明)→ `arch -x86_64` 经 Rosetta 2 拉起后 CDP `/json/version` 命中 `149.0.7827.114`,退出码 0,耗时 34.6s(在 x86_64 长预算 ~60s 上限内)。两资产文件名 `..._macos_arm64.zip` / `..._macos_x64.zip` 均含明确架构标识 |

**Score:** 3/3 truths verified(0 present-but-behavior-unverified —— 本次未采纳 SUMMARY 叙述,而是独立重跑了脚本对真实 zip 字节的 dry-run 全流程,两条架构分支均产生真实退出码与真实 CDP 响应)

**关于 x64 未签名的说明(非缺陷):** x86_64 Mach-O 二进制在链接器默认设置下不做 ad-hoc 签名(`-no_adhoc_codesign`),这是平台层面的既定行为,ROADMAP Success Criterion 1 的“ad-hoc 签名”要求仅适用于 arm64。脚本对 codesign 阶段做了按架构条件跳过(commit `02b6688`),x64 一侧的完整性改由双二进制架构断言 + 真实 Rosetta 启动冒烟兜底 —— 本次已独立复现该冒烟通过。

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/release/verify_and_upload_macos_kernel.sh` | 上传前把关+发布脚本,ditto-only、双二进制架构校验、按架构条件的 codesign、本机/Rosetta CDP 冒烟、`gh release upload --clobber` | VERIFIED | 文件存在,`bash -n` 通过;`grep -c ditto` = 9(≥2 达标);去注释后 `unzip|cp -R` 命中 0(禁用工具未出现,唯一一处 `cp` 是对已是 `.zip` 文件的复制,非 `.app` bundle 搬运,不违反禁令);`GH_TOKEN|--token|ghp_` 命中 0;含 `gh release upload` + `--clobber` + `ShengSoft-Tech/Open-Anti-Browser`;`git check-ignore` 无输出(未被 gitignore) |
| `backend/config.py`(`CHROME_ENGINE_ZIP_URL_MACOS_ARM64` / `_X64`) | 复用 `_CHROME_KERNEL_BASE` 的模块级常量,basename 与已发布资产名逐字一致 | VERIFIED | `python3 -c "from backend import config"` 打印两条常量,basename 分别为 `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` / `..._macos_x64.zip`,与实时 `gh release view` 输出的资产名逐字节一致(SSOT 闭环) |
| `tests/test_config_platform.py`(`test_macos_arm64_kernel_url` / `test_macos_x64_kernel_url`) | 锁定两常量的 shape | VERIFIED | `python3 -m unittest tests.test_config_platform -v` 全部 10/10 通过,含两条新测试与既有 Windows 常量回归守卫 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `verify_and_upload_macos_kernel.sh`(上传步骤) | `backend/config.py` | `python3 -c "from backend.config import CHROME_ENGINE_ZIP_URL_MACOS_*"` 解析 basename 作为上传资产名 | WIRED | 脚本第 217-230 行按 `--arch` 选对应常量、取 basename 作 `ZIP_NAME`,不硬编码文件名字面量;实际发布资产名与该 basename 逐字一致(已核对) |
| `backend/config.py` 常量 | GitHub Release 资产 | SSOT basename ⇄ 实时 release 资产名 | WIRED | 两端逐字节比对一致(见上表) |
| KERNEL-01/02/03 requirements frontmatter | REQUIREMENTS.md | 各 PLAN `requirements:` 字段 | WIRED | 02-01 声明 [KERNEL-01,02,03];02-02 声明 [KERNEL-01,02];02-03 声明 [KERNEL-01,03];02-04 声明 [KERNEL-02,03];REQUIREMENTS.md 追踪表三项均标记 Complete,且与 4 份 SUMMARY 的 `requirements-completed` 字段互相印证 |

### Behavioral Spot-Checks(独立重跑,非采信 SUMMARY 叙述)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| arm64 全流程(ditto 往返→双二进制 lipo→codesign→本机 CDP 冒烟)对**真实 zip 字节**跑通 | `bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch arm64 ~/bfwg/kernel-artifacts/...arm64.zip` | 退出 0;两行 `lipo -archs` 均 `arm64`;`codesign` 检出 adhoc+linker-signed;CDP 响应含 `149.0.7827.114`;4.8s;`pgrep` 后无残留进程 | PASS |
| x64 全流程(ditto 往返→双二进制 lipo→codesign 按架构跳过→Rosetta CDP 冒烟)对**真实 zip 字节**跑通 | `bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch x86_64 ~/bfwg/kernel-artifacts/...x64.zip` | 退出 0;两行 `lipo -archs` 均 `x86_64`;codesign 阶段正确跳过并打印说明;`arch -x86_64` 经 Rosetta 拉起,CDP 响应含 `149.0.7827.114`;34.6s(< 60s 长预算上限) | PASS |
| 双架构资产在 release 上实际存在 | `gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name' --repo ShengSoft-Tech/Open-Anti-Browser` | 输出含 `ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip` 与 `..._macos_x64.zip`,大小分别为 155,462,650 / 165,782,894 字节,与本地留存 artifact 字节数完全一致 | PASS |
| config.py 常量 basename 与实际发布资产名一致 | `python3 -c "from backend import config; ..."` | 两条 basename 逐字节匹配 release 端资产名 | PASS |
| `test_config_platform` 全量回归 | `python3 -m unittest tests.test_config_platform -v` | 10/10 通过,含两条新增测试与既有 Windows 回归守卫 | PASS |

### Probe Execution

未发现本 phase 声明或约定式 `scripts/*/tests/probe-*.sh`;上表「Behavioral Spot-Checks」已覆盖等价的端到端脚本执行验证,故跳过本节的独立探针执行。

### Requirements Coverage

| Requirement | 来源 Plan | Description | Status | Evidence |
|-------------|----------|-------------|--------|----------|
| KERNEL-01 | 02-01, 02-02, 02-03 | macOS arm64 指纹内核可从 kernel release 下载(ditto 打包保符号链接,ad-hoc 签名) | SATISFIED | arm64 资产实时可见于 release;`verify_and_upload_macos_kernel.sh --dry-run --arch arm64` 独立复现 ditto/lipo/codesign/CDP 全通过;config.py 常量 basename 与资产名一致 |
| KERNEL-02 | 02-01, 02-02, 02-04 | macOS Intel x64 指纹内核可从 kernel release 下载(arm64 Mac 交叉编译) | SATISFIED | x64 资产实时可见于 release;`verify_and_upload_macos_kernel.sh --dry-run --arch x86_64` 独立复现 ditto/lipo/Rosetta CDP 全通过;config.py 常量 basename 与资产名一致 |
| KERNEL-03 | 02-01, 02-03, 02-04 | 内核资产上传前通过架构验证(file/lipo)与本机启动冒烟测试,文件名含明确架构标识 | SATISFIED | 双架构均在本次 verify 中独立重跑 lipo 架构断言 + CDP 冒烟(arm64 原生、x64 经 Rosetta),两资产文件名分别含 `arm64`/`x64` 标识 |

未发现 REQUIREMENTS.md 中映射到 Phase 2 但未被任何 PLAN 的 `requirements:` 字段认领的孤儿需求(ORPHANED)——三项均被至少一个 PLAN 声明并在其 SUMMARY 的 `requirements-completed` 中闭合。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | 未发现 `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`、令牌字面量、`unzip`/`cp -R`(除合规的 zip 文件 `cp`)等反模式 | — | 无 |

ℹ️ Info(非 blocker,非本 phase 交付物问题):`.planning/STATE.md` 的 `stopped_at`/`Session Continuity` 仍写着「02-04 Task 3 checkpoint — awaiting final human confirm」,但 `02-04-SUMMARY.md` 明确记录 Task 3 已获人工「approved」批准,`REQUIREMENTS.md` 也已将 KERNEL-01/02/03 三项标记为 Complete。这是 STATE.md 元数据未随最后一次批复同步更新的记账滞后,不影响本 phase 实际交付的资产/代码/测试状态,已通过本次对 release 资产与脚本行为的独立复核确认交付物本身完整正确;建议下一次会话开场顺手把 STATE.md 的 `stopped_at`/`status` 刷新为已完成。

### Human Verification Required

无。本次已用脚本对两条架构的真实内核字节独立重跑端到端 dry-run 流水线(ditto→lipo→codesign/条件跳过→CDP 冒烟),并用实时 `gh release view` 交叉核对资产存在性与文件大小,未依赖 SUMMARY.md 的叙述作为证据来源。

### Gaps Summary

无 gaps。三条 ROADMAP Success Criteria 与 KERNEL-01/02/03 三项需求均在代码/脚本/实时 GitHub Release 状态层面得到独立验证;唯一发现的问题(STATE.md 记账滞后)已在 Anti-Patterns 一节记录为非阻塞的 ℹ️ Info 项。

---

_Verified: 2026-07-27T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
