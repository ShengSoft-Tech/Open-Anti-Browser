---
status: resolved
phase: 04-frontend-platform-gating
source: [04-VERIFICATION.md]
started: 2026-07-28T02:10:00Z
updated: 2026-07-28T02:20:00Z
---

## Current Test

number: —
name: 全部完成
awaiting: none — 3/3 通过，无待办

## Tests

### 1. ProfileList 在 capabilities 迟到加载时的响应式切换

source: 04-03-PLAN.md must_haves — `verification: backstop`
expected: capabilities 从 undefined 变为已加载的那一刻，引擎筛选下拉与行内「仅 Windows」标记正确切换为门控后的结果，不残留首帧状态、不闪烁。
why_human: 静态代码只能证明 `firefoxEngineVisible` 是基于响应式 ref `store.capabilities` 的 computed（理论上会更新），无法证明用户实际观察到的过渡没有闪烁或竞态。04-06 的 UAT 测的是稳态界面，未覆盖「迟到加载」窗口期。
how_to_test: |
  1. 打开 http://localhost:5173/ ，F12 → Network 面板
  2. Throttling 选 "Slow 3G"（或自定义 2000ms 延迟）
  3. Cmd+Shift+R 硬刷新，全程盯住配置列表页
  4. 观察引擎筛选下拉与行内标记
result: PASS — Slow 3G 节流硬刷新下无闪烁，引擎筛选下拉与行内标记直接呈现门控后的最终状态，未观察到 Firefox 选项一闪而过。
tested_on: macOS 15.7 (24G222)，2026-07-28

### 2. AppSettings 卡片内 xattr 命令的逐字渲染

source: 04-04-PLAN.md must_haves — `verification: backstop`
expected: `xattr -dr com.apple.quarantine /Applications/Open-Anti-Browser.app` 在设置页「平台限制说明」卡片中逐字显示，连字符/斜杠/点号未被 HTML 转义或引号美化，可完整选中复制。
why_human: 04-06 的 B3 验证的是 App.vue 首启弹窗（`dangerouslyUseHTMLString` 拼接字符串）这条路径；AppSettings 卡片走的是 Vue 双花括号文本插值，是**不同的渲染路径**，共用同一个模块常量不等于两条路径都验过。
how_to_test: |
  1. 进入 设置 → 平台限制说明 卡片
  2. 找到终端命令那一行，逐字比对
  3. 尝试选中并复制，粘贴到文本编辑器确认内容完整
result: PASS — 设置卡片内命令逐字完整，未见 HTML 转义或引号美化，可完整选中复制。Vue 双花括号插值路径与首启弹窗路径均已各自确认。
tested_on: macOS 15.7 (24G222)，2026-07-28

### 3. 侧栏导航与 SyncManager 按钮在 capabilities 迟到加载时的禁用态切换

source: 04-05-PLAN.md must_haves — `verification: backstop`
expected: capabilities 解析完成后，侧栏「同步器」导航项与视图内同步/排列按钮立即变为禁用态，不出现短暂可点击又被禁用的闪烁。
why_human: `isNavDisabled`/`navDisabledReason` 是**普通函数而非 computed**，在模板里被直接调用。虽然它们读的是响应式的 `store.capabilities`、模板绑定理论上会随之重渲染，且 `app-content` 有 `v-loading="store.loading"` 遮罩，但没有一次针对该竞态窗口的实际观察记录。
how_to_test: |
  1. 保持 Slow 3G 节流
  2. Cmd+Shift+R 硬刷新，盯住侧栏「同步器」项
  3. 刷新后进入同步器视图，观察其中的同步/排列按钮禁用态
result: PASS — 侧栏「同步器」项与视图内同步/排列按钮的禁用态正常，未出现短暂可点击又变灰的闪烁。确认 isNavDisabled/navDisabledReason 作为普通函数在模板中直接调用没有丢失响应性。
tested_on: macOS 15.7 (24G222)，2026-07-28

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None — 3 项 backstop 真值全部通过人工确认，无遗留缺口。
