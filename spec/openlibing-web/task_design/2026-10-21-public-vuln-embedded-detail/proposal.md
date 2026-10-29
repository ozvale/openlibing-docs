# Proposal: 公开漏洞详情内嵌列表同页（面包屑返回）

## 需求背景

公开漏洞模块迁移（见 [2026-09-15-public-vulnerability-migration](../2026-09-15-public-vulnerability-migration/)）后，详情页是独立 noMenu 路由 `/apps/publicVulnerabilityAnalysis`（query 传 `issueNum/cveNum/software`）。存在两个问题：

1. **多页签噪音**：从列表进入详情会在 tabbar 新开一个「公开漏洞分析详情」页签，与「公开漏洞」页签并存，与合法合规模块（`/apps/sca/componentAnalysis`）"列表页内切详情、单页签"的体验不一致
2. **URL 带参数**：详情态 URL 携带 query，用户期望与合法合规一致——URL 全程不变，详情为页内内存态

## 功能描述

- 公开漏洞列表页 `/apps/publicVulnerability` 内嵌漏洞分析详情：点击列表 cve 编号 → 页内切换到详情态，URL 不变
- 详情态顶部展示页内面包屑「漏洞列表 / 漏洞分析详情」：父级可点击（悬浮变色 `#5e7ce0`）返回列表，附带返回箭头图标
- 返回列表时过滤条件、页码、滚动位置天然保留（列表 DOM 经 `v-show` 保留，替代原先 Pinia store 暂存/恢复机制）
- 权限语义变化：`public_cve:details` 从路由守卫（`meta.auth`）降级为列表行 cve 编号链接的入口级 `canHandle` 校验（无权限不渲染链接，纯文本展示）

## 验收标准

- [x] 点击列表 cve 编号进入详情态，URL 保持 `/apps/publicVulnerability` 不变，tabbar 始终单个「公开漏洞」页签
- [x] 面包屑「漏洞列表 / 漏洞分析详情」展示正确；点击「漏洞列表」或返回箭头回到列表态
- [x] 详情态设置过滤条件 → 进详情 → 面包屑返回，过滤条件/页码保留
- [x] 详情三步页签（基本信息/漏洞影响分析/漏洞修复）、步骤状态接口流转、「下一步」按钮行为与改造前一致
- [x] 基本信息页签操作历史展开后，左侧表单与右侧历史表之间的间隔透出页面灰底（非白色）
- [x] 详情态外层边距与原独立详情页一致（容器 padding 归零，由详情组件自身 `padding: 16px 20px` 提供）
- [x] 无 `public_cve:details` 权限的账号，列表 cve 编号不再渲染为可点击链接
- [x] `noMenu.ts` 中 `publicVulnerabilityAnalysis` 路由删除；`stores/publicVulnerability.ts` 暂存 store 删除，全仓无残留引用
- [x] lint 通过（无新增告警），类型检查无本次改动引入的错误

## 关联

- 业务仓：openlibing-web，分支 `feat-public-vulnerability-migration`，commit `052f8f5ac`
- 前置 spec：[2026-09-15-public-vulnerability-migration](../2026-09-15-public-vulnerability-migration/)（本次变更其中任务 9/10 的方案演进：store 暂存被 v-show 内存态取代）
