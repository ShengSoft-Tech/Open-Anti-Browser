---
phase: 3
slug: macos-chrome-api
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-27
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (标准库,无 pytest 配置) |
| **Config file** | none — 纯 `python -m unittest discover -s tests -v`,从仓库根目录运行 |
| **Quick run command** | `python -m unittest tests.test_process_termination_macos tests.test_capabilities_api -v` |
| **Full suite command** | `python -m unittest discover -s tests -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m unittest tests.test_process_termination_macos tests.test_capabilities_api -v`
- **After every plan wave:** Run `python -m unittest discover -s tests -v`
- **Before `/gsd-verify-work`:** Full suite must be green + 用户 arm64 真机手动冒烟通过 (D-03 主验收手段)
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | LAUNCH-03 | T-3-01 / — | 优雅终止不残留进程/SingletonLock | unit | `python -m unittest tests.test_process_termination_macos -v` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | XPLAT-05 | — | 只读能力端点,无输入面 | unit | `python -m unittest tests.test_capabilities_api -v` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 2 | LAUNCH-01 | T-3-02 / — | quarantine 剥离路径精确指定内核目录 | manual (真机) | 见 03-RESEARCH.md「真机验证脚本」 | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*(Seed — refined by `/gsd-validate-phase` against final PLAN.md task IDs.)*

---

## Wave 0 Requirements

- [ ] `tests/test_process_termination_macos.py` — stubs for LAUNCH-03 (mock psutil terminate/wait_procs/kill 序列)
- [ ] `tests/test_capabilities_api.py` — stubs for XPLAT-05 (`get_platform_capabilities()` 结构 + `/api/capabilities` 路由 + `bootstrap()` 含 capabilities 字段)
- [ ] 真机验证脚本执行记录 (D-07 quarantine/Gatekeeper — 非自动化,执行阶段留痕)

*框架安装:无需新增,`unittest` 是标准库自带。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| quarantine/Gatekeeper 实际拦截行为 | LAUNCH-01 | OS 级安全机制,无法自动化 | 见 03-RESEARCH.md「真机验证脚本」小节 (arm64 Mac) |
| 代理/geo/扩展/批量启动逐项肉眼确认生效 | LAUNCH-02 | 真机专属,业务逻辑已有单测覆盖 | D-04 人工冒烟清单 (arm64 Mac 真实内核) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
