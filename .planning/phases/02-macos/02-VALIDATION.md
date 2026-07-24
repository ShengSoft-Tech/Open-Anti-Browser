---
phase: 2
slug: macos
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-24
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 02-RESEARCH.md "Validation Architecture" + per-task verification map derived from 02-01…02-04 PLAN.md.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (existing repo convention, no pytest config) |
| **Config file** | none — `python -m unittest discover -s tests -v` |
| **Quick run command** | `python -m unittest tests.test_config_platform -v` |
| **Full suite command** | `python -m unittest discover -s tests -v` |
| **Estimated runtime** | ~1-2s (config-only quick run); a few seconds (full suite, excluding pywin32-dependent modules that cannot import on macOS) |

**Scoping note (from RESEARCH):** Only the `backend/config.py` URL-backfill (02-02) is meaningfully unit-testable in `unittest` (mirroring `test_config_platform.py`'s `importlib.reload(config)` pattern). The verify+upload shell script's `ditto`/`lipo`/`codesign`/`gh`/Rosetta-launch logic operates on real binaries and a live GitHub release — it is validated by a `--dry-run`/self-test invocation against the currently-available arm64 build (02-01), and the real uploads (02-03/02-04) are human-gated `checkpoint:human-verify` tasks, not unittests.

---

## Sampling Rate

- **After every task commit:**
  - config.py / test tasks → `python -m unittest tests.test_config_platform -v`
  - script tasks → `bash -n scripts/release/verify_and_upload_macos_kernel.sh` + `--dry-run` self-test
- **After every plan wave:** `python -m unittest discover -s tests -v` (confirm zero regression across existing tests)
- **Before `/gsd-verify-work`:** Full suite green PLUS the human-gated upload confirmation (`gh release view kernel-149.0.7827.114 --json assets`) shows the expected macOS assets
- **Max feedback latency:** < 30s — the arm64-native CDP self-test uses a short retry budget (~15 × 1s); the long ~60s budget is reserved for the x86_64/Rosetta path, which runs only against a real x64 artifact (02-04), not in the fast loop.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | KERNEL-03 | T-02-01 / T-02-04 | 双二进制架构断言 + codesign + CDP 冒烟通过才继续;CLI 参数(`--arch`/路径)校验 | script self-test | `bash -n scripts/release/verify_and_upload_macos_kernel.sh && bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch arm64 ../fingerprint-chromium/build/src/out/Default/Chromium.app` | ❌ W0 (脚本由本任务创建) | ⬜ pending |
| 02-01-02 | 01 | 1 | KERNEL-02, KERNEL-03 | T-02-01 / T-02-02 | 架构不匹配守卫非零退出;无令牌字面量;Rosetta 长预算不回落 arm64 | script self-test (negative) | `bash -n scripts/release/verify_and_upload_macos_kernel.sh && ! bash scripts/release/verify_and_upload_macos_kernel.sh --dry-run --arch x86_64 ../fingerprint-chromium/build/src/out/Default/Chromium.app` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 1 | KERNEL-01, KERNEL-02 | T-02-07 | URL 常量含正确 revision/arch、复用 `_CHROME_KERNEL_BASE`、无二次硬编码 | unit (inline import) | `python3 -c "from backend import config; a=config.CHROME_ENGINE_ZIP_URL_MACOS_ARM64; x=config.CHROME_ENGINE_ZIP_URL_MACOS_X64; assert '-1.3' in a and '_macos_arm64' in a and '-1.3' in x and '_macos_x64' in x"` | ✅ (config.py exists) | ⬜ pending |
| 02-02-02 | 02 | 1 | KERNEL-01, KERNEL-02 | T-02-07 / T-02-08 | 常量断言 + Windows 现有常量零回归 | unit | `python -m unittest tests.test_config_platform -v` | ✅ (extend existing) | ⬜ pending |
| 02-03-01 | 03 | 2 | KERNEL-01 | T-02-01 | post-D-02 handoff(LOG(INFO) 已移除)人工确认后才上传 | manual / checkpoint (blocking) | N/A — `checkpoint:human-verify` (无法从 zip 静态检出，Pitfall 6) | N/A | ⬜ pending |
| 02-03-02 | 03 | 2 | KERNEL-01, KERNEL-03 | T-02-01 | 上传前双二进制架构 + codesign + CDP 冒烟通过才 `--clobber` 上传 | manual (live gh API) | `gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name' \| grep -F 'ungoogled-chromium_149.0.7827.114-1.3_macos_arm64.zip'` | N/A (live release) | ⬜ pending |
| 02-03-03 | 03 | 2 | KERNEL-03 | T-02-01 | 人工确认 arm64 资产命名(含 `arm64`)/可下载 | manual / checkpoint (blocking) | N/A — `checkpoint:human-verify` | N/A | ⬜ pending |
| 02-04-01 | 04 | 2 | KERNEL-02 | T-02-05 | 兄弟仓库 x64 交叉编译产物(downloads-macos-x64.ini + x64 build)交付人工确认 | manual / checkpoint (blocking) | N/A — `checkpoint:human-verify` (跨仓库 blocker，Open Question 2) | N/A | ⬜ pending |
| 02-04-02 | 04 | 2 | KERNEL-02, KERNEL-03 | T-02-05 / T-02-06 | 双二进制 x86_64 + codesign + `arch -x86_64` Rosetta CDP 冒烟(长预算)通过才上传 | manual (live gh API + Rosetta e2e) | `gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name' \| grep -F 'ungoogled-chromium_149.0.7827.114-1.3_macos_x64.zip'` | N/A (live release) | ⬜ pending |
| 02-04-03 | 04 | 2 | KERNEL-03 | T-02-05 | 人工确认 x64 资产命名(含 `x64`)/架构正确 | manual / checkpoint (blocking) | N/A — `checkpoint:human-verify` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Sampling continuity: no 3 consecutive tasks without automated verify — Wave 1 (02-01/02-02) is fully automated; Wave 2 checkpoints (02-03/02-04) each interleave with an automated `gh release view` grep between the two human-gate checkpoints.*

---

## Wave 0 Requirements

- [ ] `scripts/release/verify_and_upload_macos_kernel.sh` — does not exist yet; created by 02-01 Task 1 (tracer) with a `--dry-run`/self-test mode so its file/lipo/codesign/CDP-smoke logic can be exercised against the currently-available arm64 build before the real uploads (02-03/02-04) run.
- [ ] `tests/test_config_platform.py` — extend with `test_macos_arm64_kernel_url` / `test_macos_x64_kernel_url` (02-02 Task 2) covering KERNEL-01/KERNEL-02's config.py constants. File already exists; add two methods.
- [x] No new test framework install needed — `unittest` already covers everything this phase can automate.

*These Wave 0 items are created inline by the first wave-1 tasks (script + tests), then consumed by wave-2's real-artifact uploads. `wave_0_complete` flips to `true` after 02-01 Task 1 and 02-02 Task 2 land.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 真实 `gh release upload --clobber` 幂等 + 资产落地 | KERNEL-01 / KERNEL-02 | 命中 live GitHub API,`unittest` 不可达 | `gh release view kernel-149.0.7827.114 --json assets --jq '.assets[].name'` 命中对应 arch zip;02-03/02-04 各含 blocking `checkpoint:human-verify` 人工确认 |
| post-D-02 LOG(INFO) 校准诊断行已移除/DLOG 保护 | KERNEL-01 | 只在运行期 `--enable-logging=stderr` + gate-skip 码路触发,无法从 zip 内容静态检出(Pitfall 6) | 兄弟仓库 git log / `07-01-SUMMARY.md` hand-off note,或重跑 `regression-cdp.js --mode calibrate` 确认无噪声 LOG;02-03 Task 1 blocking checkpoint |
| 兄弟仓库 x64 交叉编译产物交付 | KERNEL-02 | 跨仓库 blocker;`downloads-macos-x64.ini` + x64 build 当前不存在,不在本仓库掌控 | 02-04 Task 1 blocking checkpoint 确认兄弟仓库交付并给出 zip 绝对路径 |
| Rosetta x64 CDP 启动冒烟 | KERNEL-03 | 需真实 x64 产物 + Rosetta 运行,e2e 非 `unittest`;长重试预算 ~60s | 02-04 脚本 `--arch x86_64` 真实运行(非 dry-run),02-04 Task 3 checkpoint 抽查 Framework 二进制 `lipo -archs` == x86_64 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify, a Wave 0 dependency, or a `checkpoint:human-verify` gate (live-API / cross-repo-blocked behaviors are human-gated by design per RESEARCH Validation Architecture)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (Wave 1 fully automated; Wave 2 checkpoints interleave with `gh release view` greps)
- [x] Wave 0 covers all MISSING references (script self-test entry + config test methods)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (arm64-native self-test short budget; ~60s Rosetta budget confined to the real-x64 path, off the fast loop)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (draft → validated transition owned by validate-phase §6)
