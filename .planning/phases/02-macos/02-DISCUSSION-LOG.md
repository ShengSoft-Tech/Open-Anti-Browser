# Phase 2: macOS 内核构建与发布 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-24
**Phase:** 2-macOS 内核构建与发布
**Areas discussed:** 补丁版本对齐与 arm64 重建, x64 交叉编译的归属与验证, 打包格式与资产命名, 验证深度与发布流程

---

## 补丁版本对齐与 arm64 重建

### Mac 内核资产采用哪个补丁基线?

| Option | Description | Selected |
|--------|-------------|----------|
| 021 基线(含熵门控,不重建) | 直接用现有 arm64 build,有熵门控改进、过红盒检测、已回归验证;与 Windows -1.2 短期不一致,等兄弟仓库 Phase 08 对齐 | ✓ |
| 020 基线(对齐现有 Windows -1.2) | quilt 回退到 020 大重建,与现有 Windows 包立即一致,但放弃熵门控且 Windows 也快切 021 | |

**User's choice:** 021 基线(含熵门控,不重建)
**Notes:** 用户先要求把选项讲清楚(误看了),重新确认后仍选 021。理由:重建成本省,Windows 侧马上跟上 021。

### 现有 arm64 build 里的校准诊断日志行怎么处理?

| Option | Description | Selected |
|--------|-------------|----------|
| 移除后重建再打包 | 删掉 021 补丁的 LOG(INFO) 校准诊断行(兄弟仓库 SUMMARY 已记为 Phase 8 打包前禁令),热树增量重建+重链后再出资产 | ✓ |
| 原样打包(不重建) | 直接用现有 build,发布内核会向 stderr 打每帧 canvas 校准信息,泄露实现细节 + 性能噪声,且违反兄弟仓库禁令 | |

**User's choice:** 移除后重建再打包
**Notes:** 重建动作发生在兄弟仓库;本仓库拿到的是重建后的干净产物。

---

## x64 交叉编译的归属与验证

### 补齐 downloads-macos-x64.ini + 交叉编译 x64 内核算哪个仓库的工作?

| Option | Description | Selected |
|--------|-------------|----------|
| 全部在兄弟仓库完成 | downloads-macos-x64.ini 补齐、flags 改 x64、交叉编译、lipo/file 验证、冒烟都在 ../fingerprint-chromium 做 | ✓ |
| 本仓库驱动、跨仓库构建 | 本仓库 plan 直接调用兄弟仓库构建脚本;职责模糊、跨仓库副作用 | |

**User's choice:** 全部在兄弟仓库完成

### x64 内核上传前的启动冒烟测试在什么环境跑?

| Option | Description | Selected |
|--------|-------------|----------|
| 当前 arm64 Mac 走 Rosetta | 交叉编译出 x64 后用 Rosetta 2 直接启动验证,成本低;Intel 原生留到 Phase 6 | ✓ |
| 必须 Intel 真机原生验证 | 上传前就在真 Intel Mac 原生启动;更严格但需 Intel 机器且与 Phase 6 重叠 | |

**User's choice:** 当前 arm64 Mac 走 Rosetta

### 既然构建+验证都在兄弟仓库,本仓库 Phase 2 的职责边界怎么定?

| Option | Description | Selected |
|--------|-------------|----------|
| 上传资产 + 回填 config.py | 本仓库 = 上传两个 zip 到 kernel release + config.py 加 macOS URL;构建/验证归兄弟仓库,本仓库只上传前把关+验收可下载 | ✓ |
| 连构建一起纳入本仓库 Phase 2 | plan 直接驱动兄弟仓库构建验证;职责模糊,与上一题矛盾 | |
| 先保留,等规划时再拆 | 不锁边界,交给 planner | |

**User's choice:** 上传资产 + 回填 config.py

---

## 打包格式与资产命名

### Mac 内核资产文件名怎么定?

| Option | Description | Selected |
|--------|-------------|----------|
| 对齐 Windows 命名模式 | ungoogled-chromium_149.0.7827.114-1.x_macos_arm64.zip / _macos_x64.zip,与 _windows_x64.zip 同风格 | ✓ |
| 精简名(只带架构) | chromium-mac-arm64.zip 等,更短但不带版本/revision,不利区分 | |
| 你来拟名 | 用户给具体规则 | |

**User's choice:** 对齐 Windows 命名模式

### Mac 内核只出一个压缩包资产还是也出 installer 变体?

| Option | Description | Selected |
|--------|-------------|----------|
| 只出 ditto zip | 每架构一个 ditto zip(保符号链接+ad-hoc 签名),CI 下载注入 .app;Mac dmg 自带安装,不需 installer | ✓ |
| zip + pkg 双资产 | 额外出 .pkg;dmg 已是分发形式,pkg 多余且未签名体验差 | |

**User's choice:** 只出 ditto zip

### Mac 021 资产的 revision 号用什么?

| Option | Description | Selected |
|--------|-------------|----------|
| 新 revision -1.3 标识 021 | Mac 用 -1.3 区分于 Windows -1.2(020);等兄弟仓库 Phase 08 发 Windows 021 也用 -1.3 对齐 | ✓ |
| 沿用 -1.2 与现 Windows 对齐 | Mac 也用 -1.2;同号在 Windows(020)/Mac(021)下内容不一致,难追溯 | |
| 交给兄弟仓库定 | revision 由兄弟仓库 Phase 08 统一分配 | |

**User's choice:** 新 revision -1.3 标识 021

---

## 验证深度与发布流程

### 上传前本仓库要不要对拿到的 zip 再做一道把关验证?

| Option | Description | Selected |
|--------|-------------|----------|
| 上传前本仓库再验一遍 | 解压后跑 file/lipo 架构确认 + 启动冒烟(x64 走 Rosetta),作发布把关,对齐 KERNEL-03「上传前验证」 | ✓ |
| 信任兄弟仓库结果,直接上传 | 不重复验证;有跨仓库传输/解压传错架构风险 | |

**User's choice:** 上传前本仓库再验一遍

### 上传 kernel release + 把关验证 这套流程怎么执行?

| Option | Description | Selected |
|--------|-------------|----------|
| 脚本化(仓库内脚本) | 解压→file/lipo→Rosetta 冒烟→gh release upload,可重复可审计,后续复用 | ✓ |
| 手动执行(文档化步骤) | 只写步骤手动跑;不可重复、易漏验证步骤 | |

**User's choice:** 脚本化(仓库内脚本)

### 上传+验证脚本放哪里?(CLAUDE.md 约定打包脚本 gitignore)

| Option | Description | Selected |
|--------|-------------|----------|
| 入仓(内核发布工具,非应用打包) | 与 build_installer.ps1/dmg 打包脚本属不同类别,进仓便于审计复用;需在 CONTEXT 明确区分 | ✓ |
| gitignore(比照现有打包脚本惯例) | 与 build_installer.ps1 一样不入仓;发布流程不可审计,与「脚本化」初衷打折扣 | |

**User's choice:** 入仓(它是内核发布工具,非应用打包)

---

## Claude's Discretion

- 上传/验证脚本的具体语言与落点(如 scripts/ 下的 bash)、file/lipo 与 Rosetta 冒烟的命令组织。
- config.py 里 macOS arm64/x64 两条 URL 的平台分支写法与常量命名(沿用 Phase 1 D-05 平台感知结构)。
- Rosetta 冒烟「启动成功」的判定粒度,只要满足 KERNEL-03 启动冒烟语义。

## Deferred Ideas

None — 讨论未越出 phase 范围。两条跨 phase 备忘(非新增 scope):兄弟仓库 Phase 08 发 Windows 021 后回来对齐 Windows revision 到 -1.3;ROADMAP Phase 2 成功标准 3 的「构建/lipo/冒烟」措辞与本次边界收窄口径不同,verifier 应以「本仓库负责上传前把关+回填」为准。
