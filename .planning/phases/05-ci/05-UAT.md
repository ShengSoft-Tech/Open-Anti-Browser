---
status: testing
phase: 05-ci
source: [05-VERIFICATION.md]
started: 2026-07-29
updated: 2026-07-29
---

## Current Test

number: 1
name: 推送真实 v* tag,确认 release job 执行并把两平台产物挂到同一个 GitHub Release
expected: |
  单次 tag push 后,`build` 与 `build-macos` 并行跑完并均 success;`release` job
  从既往的 `skipped` 变为 `success`;同一个 GitHub Release 页面上同时出现 Windows
  安装包与 macOS arm64 dmg 两份产物,文件名里的版本号与所推的 tag 一致。
awaiting: user response

## Tests

### 1. 推送真实 v* tag,确认 release job 执行并把两平台产物挂到同一个 GitHub Release

expected: 单次 tag push 后 `build` 与 `build-macos` 均 success、`release` 由 skipped 变为 success,同一个 Release 上同时挂载 Windows 安装包与 macOS arm64 dmg,版本号与 tag 一致
result: [pending]

why_human: |
  本 phase 全部 8 次真实 CI 验证均以 `workflow_dispatch` 触发。按 D-04 的设计,
  此时 `release` job 因 `if: startsWith(github.ref, 'refs/tags/')` 结构性跳过。
  ROADMAP SC1(「推送 v* tag 后 CI 并行触发」)与 SC4 / PKG-05 前半句(「与 Windows
  安装包一并挂到同一 GitHub Release」)所描述的触发路径,只有真实 tag push 才会执行。

  这是 05-05-SUMMARY.md 明确记录在案的**已知残余风险**,不是验证新发现的缺陷 ——
  `release` job 的结构正确性已被静态断言与真实 run 反复确认(全工作流
  `softprops/action-gh-release` 恰好 1 次、`needs: [build, build-macos]`、
  产物齐备性断言、零 `continue-on-error` / `if: always()`),缺的只是「结构正确」
  与「真实 tag push 时确实按预期执行」之间那一步。

  ⚠ 注意:推 `v*` tag 会触发**真实发版**,产物对用户可见。这一项应当在你确实准备
  发布 v0.2 时顺带核销,不建议为了验证而单独推一个 tag。

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
