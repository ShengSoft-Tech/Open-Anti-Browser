# Phase 4: 前端平台门控 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 4-前端平台门控
**Areas discussed:** Firefox 隐藏范围+既有配置, 窗口同步/排列置灰方式, 限制说明承载位置, 首次放行指引:触发/持久化

---

## Firefox 隐藏范围 + 既有 Firefox 配置(UI-01)

| Option | Description | Selected |
|--------|-------------|----------|
| 入口全隐 + 既有配置禁用保留 | 引擎选择器/筛选 Tab/顶部徽章计数全隐 Firefox;既有 firefox 配置仍显示,带「仅 Windows」标记、禁用启动、保留可见与可删除 | ✓ |
| 入口全隐 + 既有配置也过滤 | 彻底 Chrome-only;迁移来的 firefox 配置变不可见、无法管理/删除 | |
| 仅隐创建时的引擎选项 | 最小改动,筛选 Tab/徽章等表面保留 | |

**User's choice:** 入口全隐 + 既有配置禁用保留
**Notes:** 不静默丢用户数据;符合 UI-01 验收(只要求创建/编辑界面无 Firefox 选项)。既有 firefox 配置须能加载(Phase 1 D-08)。

---

## 窗口同步/排列置灰方式(UI-02)

| Option | Description | Selected |
|--------|-------------|----------|
| 侧栏置灰 + 视图内横幅 | 双层:navItems syncer 项置灰 + hover tooltip(用 capabilities reason);进入视图顶部 banner + 控件全禁用 | ✓ |
| 仅视图内 banner | 侧栏正常可点,仅视图顶部 banner + 控件禁用 | |
| 仅侧栏置灰不可点 | 侧栏项置灰不可点、hover tooltip,不进入视图 | |

**User's choice:** 侧栏置灰 + 视图内横幅
**Notes:** Roadmap 明确要求"置灰+提示,不隐藏"。reason 文案读 capabilities 字段,不在前端另写。

---

## macOS 限制说明承载位置(UI-03)

| Option | Description | Selected |
|--------|-------------|----------|
| 设置页新增卡片 | AppSettings.vue 加「平台限制/macOS 说明」卡片;不改导航;作为限制说明"永久家" | ✓ |
| 新增专属侧栏项 | navItems 加「平台说明」项(macOS 才显);更显眼但要动 App.vue 导航结构 | |
| 从置灰横幅弹 dialog | 无独立页,靠「了解更多」弹说明框 | |

**User's choice:** 设置页新增卡片
**Notes:** 自然归属"设置",不新增导航;UI-02 置灰 banner 与 UI-04 首启弹窗都指向它回查。

---

## 首次放行指引:触发/持久化(UI-04)

| Option | Description | Selected |
|--------|-------------|----------|
| 首启模态弹窗 + 独立 key | macOS 首启弹一次模态(「仍要打开」步骤 + xattr 命令);新独立 localStorage key 记忆;复用首启模式但不改被锁的 openSourceNotice.js | ✓ |
| 首启可关闭横幅 | 首启顶部可关闭横幅,点开看完整步骤 | |
| 不单独弹,并入 UI-03 | 放行指引直接写进限制说明,用户自己去看 | |

**User's choice:** 首启模态弹窗 + 独立 key
**Notes:** Gatekeeper 是 macOS 用户首次打开就撞上的硬门槛,主动弹最有用;用新独立 key(建议 `oab:macos-gatekeeper-notice:v1`)避免碰被 `_g.py` 锁定的 openSourceNotice.js;之后从 UI-03 卡片回查。与 Phase 6 release 文档放行说明是两处不同载体。

---

## Claude's Discretion

- 各处新增文案的确切措辞(zh-CN / en-US)与 UI-04 localStorage key 最终命名。
- 既有 firefox 配置"禁用"的确切范围(启动必禁、删除必留;编辑/复制/导出由 planner 定)。
- 门控在前端的落地形式(store computed getter 消费 capabilities),满足"单一事实源、不硬编码平台"即可。
- macOS 首启同时命中开源声明首启提示与放行弹窗时的先后/叠加顺序。
- 限制说明卡片是否在 Windows 上也显示(默认 macOS-only)。

## Deferred Ideas

None — 讨论未越界。跨 phase 备忘:CI dmg 打包(Phase 5)、release notes 放行说明 DOCS-01/02(Phase 6);UI-04 应用内放行弹窗与 Phase 6 发布文档放行说明是两处不同载体,不合并。
