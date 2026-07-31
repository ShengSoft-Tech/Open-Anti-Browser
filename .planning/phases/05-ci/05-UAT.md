---
status: testing
phase: 05-ci
source: [05-VERIFICATION.md]
started: 2026-07-29
updated: 2026-07-31
---

## Current Test

number: 1
name: 推送真实 v* tag,确认 release job 执行并把两平台产物挂到同一个 GitHub Release
expected: |
  单次 tag push 后,`build` 与 `build-macos` 并行跑完并均 success;`release` job
  从既往的 `skipped` 变为 `success`;同一个 GitHub Release 页面上同时出现 Windows
  安装包与 macOS arm64 dmg 两份产物,文件名里的版本号与所推的 tag 一致。
awaiting: none — resolved 2026-07-31

## Tests

### 1. 推送真实 v* tag,确认 release job 执行并把两平台产物挂到同一个 GitHub Release

expected: 单次 tag push 后 `build` 与 `build-macos` 均 success、`release` 由 skipped 变为 success,同一个 Release 上同时挂载 Windows 安装包与 macOS arm64 dmg,版本号与 tag 一致
result: [pass]

evidence: |
  2026-07-31,06-05-PLAN.md Task 2(开发者在 checkpoint:decision 选择 option-a)
  推送真实 `v0.2.0` tag,run id `30656303074`(push 事件,commit `95850b0`):

  - `build-macos`:success(2026-07-31T18:43:40Z → 18:50:19Z)
  - `build`:success(2026-07-31T18:43:39Z → 18:52:16Z)
  - `release`:success(2026-07-31T18:52:18Z → 18:52:49Z)—— 首次从
    `skipped` 变为真正执行并发布

  Release 页面:https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases/tag/v0.2.0
  同时挂载 `Open-Anti-Browser-0.2.0-arm64.dmg` 与 `Open-Anti-Browser-Setup.exe`,
  文件名版本号与 tag 一致。详见 06-05-SUMMARY.md「Release Body 实测」一节 ——
  这次真实执行同时发现并修复了一个此前从未被真实 tag push 触发过的缺陷(release
  job 缺少 checkout 步骤,body_path 文件在 runner 上不存在,详见该 SUMMARY)。

why_human: |
  (历史记录,问题已解决)本 phase 全部 8 次真实 CI 验证均以 `workflow_dispatch`
  触发。按 D-04 的设计,此时 `release` job 因
  `if: startsWith(github.ref, 'refs/tags/')` 结构性跳过。ROADMAP SC1(「推送
  v* tag 后 CI 并行触发」)与 SC4 / PKG-05 前半句(「与 Windows 安装包一并挂到
  同一 GitHub Release」)所描述的触发路径,只有真实 tag push 才会执行。

  这是 05-05-SUMMARY.md 明确记录在案的**已知残余风险**,不是验证新发现的缺陷 ——
  `release` job 的结构正确性已被静态断言与真实 run 反复确认(全工作流
  `softprops/action-gh-release` 恰好 1 次、`needs: [build, build-macos]`、
  产物齐备性断言、零 `continue-on-error` / `if: always()`),缺的只是「结构正确」
  与「真实 tag push 时确实按预期执行」之间那一步。

  2026-07-31 推 `v0.2.0` 真实 tag(milestone v0.2 正式发布)时核销此项。

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
