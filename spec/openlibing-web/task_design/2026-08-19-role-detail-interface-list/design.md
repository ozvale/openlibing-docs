# 技术方案设计

## 方案概述

本需求为 openlibing-web 前端角色管理模块的功能增强：在角色详情查看模式弹窗内新增「接口列表」面板。技术实现为纯前端改动 + 1 个新增后端接口调用（后端按约定路径提供分页查询能力），不涉及数据库 schema 变更。

## 详细设计

### 1. 接口列表面板

#### 实现方式

- 在 `role.vue` 详情弹窗（`dialogType === 'detail'`）内新增模板块：
  - 标题行（沿用现有 `subTitle line` 样式风格）：「接口列表」+ 接口地址搜索输入框（`el-input` + clearable + `@change` 触发）
  - `el-table`（`table-common` 样式 + `max-height="400px"`）：模块名称（menuName, width 200）、接口地址（menuUrl, show-overflow-tooltip）
  - `el-pagination`（`pagination-common` 样式）：10/20/50/100 每页，background，layout 为 `sizes, total, prev, pager, next`
- 空数据插槽复用 `Empty` 组件

#### 数据与状态

- `menuUrlList`（列表数据）、`menuUrl`（搜索关键字）
- `urlPagination = { pageNum, pageSize, total }`
- 打开详情时初始化查询，搜索/切换每页条数时重置 pageNum=1

### 2. API 层

- url.ts 新增常量：`GET_MENU_URL_DATA = FRAME_WORK + '/manage/menu/query-menu-url-by-role'`
- api.ts 新增函数：`getMenuUrlData`（post，RequestFunc 签名，与现有请求风格一致）
- 请求参数：角色 id + pageNum/pageSize + menuUrl 模糊查询条件

#### 涉及文件

- `apps/web-openlibing/src/views/authorityManagement/role.vue`（+110 行）
- `apps/web-openlibing/src/api/api.ts`（+2 行）
- `apps/web-openlibing/src/api/url.ts`（+2 行）

## 影响范围分析

### 前端影响

- 仅角色详情弹窗新增展示区块，新增/编辑模式不受影响（`v-if="dialogType === 'detail'"` 控制）
- 不涉及路由、状态管理、公共组件变更

### 后端影响

- 需后端提供 `POST /manage/menu/query-menu-url-by-role` 分页查询接口（按角色返回关联菜单接口 URL 列表）
- 无数据库 schema 变更（基于现有菜单-角色关联关系查询）

### 兼容性影响

- 纯新增功能，向前兼容
- 详情弹窗原有信息展示不受影响

## 技术约束

1. 遵循仓库现有 Vue Options API + `apiClient.post` 请求风格
2. 分页参数结构（pageNum/pageSize/total）与现有分页页面保持一致
3. 弹窗内表格限高（max-height 400px）避免长列表撑爆弹窗

## 风险评估

### 低风险

- 面板仅查看模式渲染，不影响表单提交与权限配置逻辑
- 搜索/分页均为独立状态，失败时有空列表兜底

### 风险应对

- 联调阶段核对后端接口路径与返回字段（menuName/menuUrl/total），如有差异仅调整 url.ts 常量与字段映射
