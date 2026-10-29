# Tasks: 公开漏洞详情内嵌列表同页

## 实现清单

### 1. 路由与 store 清理

- [x] `noMenu.ts`：删除 `publicVulnerabilityAnalysis` 路由（含动态 import 与路由记录）
- [x] `stores/publicVulnerability.ts`：整体删除（v-show 保留 DOM 后暂存机制不再需要）
- [x] 全仓 grep 确认 `publicVulnerabilityAnalysis` / `usePublicVulnerabilityStore` / `stores/publicVulnerability` 无残留引用

### 2. 列表页容器（index.vue）

- [x] 新增 `detailRow` ref 内存态；`goDetail(row)` 提取 `issueNum/cveNum/software`
- [x] 页签容器与列表内容区改 `v-show="!detailRow"`（保留 DOM，过滤条件/页码不丢）
- [x] 详情态渲染面包屑（返回箭头 + 「漏洞列表 / 漏洞分析详情」），父级可点击返回、悬浮变色 `#5e7ce0`
- [x] 详情组件 `v-if` + `:key="detailRow.cveNum"`（切换漏洞强制重挂载）
- [x] 详情态容器 `is-detail` 类 padding 归零，边距由详情组件自身提供；面包屑补 `padding: 16px 20px 0`

### 3. 列表页（vulnerabilityList.vue）

- [x] `goPage` 改为 `emit('goDetail', row)`，删除 `router.push`
- [x] 删除 Pinia store 暂存（`setListQuery`）与 `onMounted` 恢复逻辑
- [x] cve 编号链接增加 `canHandle('public_cve:details')` 校验，无权限降级纯文本
- [x] 清理不再使用的 `useRouter` / store 导入

### 4. 详情组件（vulnAnalysis/）

- [x] `index.vue`：props 接收 `detailInfo`，`provide('publicVulnDetailQuery', props.detailInfo)`；`getStepStatus` 改用 `props.detailInfo`；删「返回」按钮与 `goBack`；内容区高度 `calc(100% - 50px)`，恢复自身 `padding: 16px 20px`
- [x] `basicInformation.vue` / `vulnerabilityImpact.vue` / `vulnerabilityRepair.vue` / `impactForm.vue`：`useRoute()` 替换为 `{ query: inject('publicVulnDetailQuery', {}) }` 兼容对象（`route.query.*` 用法零改动）

## 验证记录

- [x] ESLint：改动文件 0 error（仅 5 条既有 no-nested-ternary warning，非本次引入）
- [x] vue-tsc 类型检查：与改造前基线报错清单逐条比对，报错均为 vite.config.mts / internal 工具包 / node_modules 双实例等环境既有问题，无本次改动文件相关错误
- [x] 样式回归：操作历史展开后左右间隔透出灰底；详情态外圈边距与原独立详情页一致；面包屑悬浮变色
- [ ] 权限回归：有 `public_cve:details` 权限账号列表 cve 编号渲染为链接、可进入详情；无权限账号渲染纯文本；旧 URL `/apps/publicVulnerabilityAnalysis` 已不可直达
- [x] pre-commit 钩子（prettier / ESLint / secrets 检测）全部通过

## 交付记录

- 业务仓 commit：`052f8f5ac`（feat(publicVulnerability): 公开漏洞详情内嵌列表同页并支持面包屑返回），分支 `feat-public-vulnerability-migration`
- 2026-10-21 完成编码与本地验证，待用户自测
