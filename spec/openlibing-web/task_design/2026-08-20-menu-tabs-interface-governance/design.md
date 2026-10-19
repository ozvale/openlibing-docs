# 技术方案设计

## 方案概述

本需求为 openlibing-web 前端菜单管理页面的结构性改造 + 接口治理功能新增。技术实现以 Vue 3 + Element Plus 组件化拆分为主，新增 4 个 tab 子组件，并为接口治理操作定义对应的 API 请求函数。不涉及后端代码变更（接口路径按后端命名规范对接）。

## 详细设计

### 1. tabs 结构改造

#### 实现方式

- 主页 `menu.vue` 用 div 基本元素实现 tab 切换（`tabList` 数组渲染 tab 头 + `activeTab` 状态 + `v-if` 控制内容区），替换 el-tabs/el-tab-pane
- 4 个新 tab 内容拆分为独立子组件，通过 `v-if="activeTab === 'xxx'"` 控制挂载实现懒加载（切到时 mounted 拉数据）
- 菜单 tab 保留原有内容

#### 涉及文件

- `apps/web-openlibing/src/views/authorityManagement/menu.vue`
- `apps/web-openlibing/src/views/authorityManagement/components/OfflineInterfaceTab.vue`（新增）
- `apps/web-openlibing/src/views/authorityManagement/components/InterfaceListTab.vue`（新增）
- `apps/web-openlibing/src/views/authorityManagement/components/AccessWhitelistInterfaceTab.vue`（新增）
- `apps/web-openlibing/src/views/authorityManagement/components/FalseReportInterfaceTab.vue`（新增）
- `apps/web-openlibing/src/views/authorityManagement/components/UrlConfig.vue`（新增，URL 配置行组件）

### 2. 已下线接口 tab

- 分页表格 + 请求 URL 模糊查询（`menuUrl` 参数）
- 表格列：请求方式、请求URL、操作
- 操作列：删除按钮（deleteOfflineInterface）+ 按 flag 区分的误报按钮——flag=1 显示撤销误报（revokeFalseReportOfflineInterface），否则显示确认误报（falseReportOfflineInterface）
- 操作前 `$confirm` 二次确认，成功后刷新当前页

### 3. 接口列表 tab

- 分页表格 + 请求 URL 模糊查询 + 接口用途/类型下拉过滤
- 表格列：代码仓、请求方式、请求URL、接口用途/类型、操作
- 修改弹窗：接口用途/类型单选（必填），选项值：人机接口/机机接口/服务内接口/无认证访问白名单/豁免登录接口/无用户信息白名单/未配置接口；确定调 updateInterfaceType，取消关闭
- 手动同步按钮：确认后调 syncInterfaceList，成功后重置页码刷新

### 4. 访问白名单接口 tab

- 分页表格 + 请求 URL 模糊查询
- 表格列：请求方式、请求URL、是否豁免登录白名单、是否无用户信息白名单、是否无认证访问白名单、操作
- 新增弹窗：请求方式/请求URL输入 + 三项白名单是/否单选（是-1/否-0）；修改模式下请求方式/URL 不渲染（不可编辑），仅提交 id + 三项白名单
- 删除按钮：确认后调 deleteAccessWhitelistInterface

### 5. 误报接口 tab

- 分页表格 + 请求 URL 模糊查询
- 表格列：请求方式、请求URL、操作
- 操作列撤销误报按钮，复用 revokeFalseReportOfflineInterface 接口

### 6. 菜单 tab URL 配置优化

- URL 地址改为 `el-select`（filterable + remote + allow-create + default-first-option），remote-method 调 queryMenuUrlOptions 拉取选项
- 下拉项与已选中回显：flag=1 时加 `url-flag-red` class 显示红色
- 修改回显时把当前 menuUrl 放入 options，空查询不清空 options 保证回显

### 7. API 层

新增 9 个 URL 常量（url.ts）与 RequestFunc 函数（api.ts），路径按 `FRAME_WORK + '/manage/service-interface/xxx'` 命名规范定义。

## 影响范围分析

### 前端影响

- 菜单管理页结构重构（单页 → tabs + 子组件）
- 新增 4 个子组件文件、1 个 URL 配置组件
- api.ts / url.ts 新增接口常量与函数

### 后端影响

- 无后端代码变更；前端新增的接口调用需后端按约定路径提供（部分路径为命名规范占位值，联调时如有差异同步调整 url.ts 常量）

### 兼容性影响

- 菜单 tab 原有功能保持不变
- 新增 tab 为全新功能，向前兼容

## 技术约束

1. 子组件遵循仓库现有 Vue Options API + apiClient.post 请求风格
2. 分页参数结构与现有分页页面保持一致（pageNum/pageSize + total）
3. radio 值为数字 1/0，打开弹窗时归一化处理避免字符串不选中
4. Windows 环境分支命名不用斜杠

## 风险评估

### 中风险

- 部分后端接口路径为占位值，联调时可能需调整 url.ts（影响面小，仅改常量）
- switch/按钮操作后列表刷新依赖接口返回 flag 状态正确

### 低风险

- tabs 拆分为纯前端结构调整，子组件自包含不影响其他模块
- URL 下拉远程搜索失败时有空 options 兜底，不阻塞手输（allow-create）

### 风险应对

- 联调阶段逐个核对接口路径与字段名（repoName/requestMethod/menuUrl/interfaceType/flag 等）
- 操作按钮均有二次确认与失败静默取消，避免误触
