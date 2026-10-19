# Design: publish-token-config

## 方案概览

1. **菜单接入**：`publishSetting/index.vue` 左侧增加第三个 listBox 菜单「发布令牌配置」，右侧条件渲染 `publishTokenTable` 组件。
2. **独立组件**：新建 `publishTokenTable.vue` 承载列表 + 弹窗表单 + 删除/批量删除逻辑，交互对齐「中心仓配置」模块。
3. **接口封装**：`PlatformRelease` 模块 `url.ts`/`api.ts` 增加 4 个发布令牌配置接口。

## 实现逻辑

### 1. 菜单接入（publishSetting/index.vue）

左侧 listBox 复用既有菜单项样式，新增第三项「发布令牌配置」；右侧内容区按当前选中菜单条件渲染 `publishTokenTable`（模块根节点样式高度由用户自测对齐既有模块）。

### 2. 列表与操作（publishTokenTable.vue）

| 表格列     | 字段          | 说明                                |
| ---------- | ------------- | ----------------------------------- |
| 令牌类型   | `tokenType`   | gitee / gitcode                     |
| 账号用户名 | `login`       | -                                   |
| 账号令牌   | `tokenMasked` | 后端脱敏（前 4 位 + `*` + 后 4 位） |
| 创建人     | `creatorName` | -                                   |
| 创建时间   | `createTime`  | -                                   |
| 操作       | -             | 编辑图标、删除图标                  |

- **新建/编辑弹窗**：令牌类型（`el-select`，选项 gitee/gitcode）、账号用户名、账号令牌（字段名 `token`，联调后端后由 `tokenMasked` 改名对齐）；三项必填校验。编辑回显时令牌类型 `disabled`。
- **删除**：操作列删除图标，`ElMessageBox.confirm` 二次确认后调删除接口。
- **批量删除**：表头「批量删除」按钮（`v-uem-record` 埋点），基于表格多选；未勾选时 `ElMessage.warning('请选择至少一条数据')`。

### 3. 接口封装

```ts
// PlatformRelease/url.ts
export const QUERY_PUBLISH_TOKEN_INFO =
  PLATFORM_RELEASE + "/config/queryPublishTokenInfo";
export const ADD_PUBLISH_TOKEN_INFO =
  PLATFORM_RELEASE + "/config/addPublishTokenInfo";
export const UPDATE_PUBLISH_TOKEN_INFO =
  PLATFORM_RELEASE + "/config/updatePublishTokenInfo";
export const DELETE_PUBLISH_TOKEN_INFO =
  PLATFORM_RELEASE + "/config/deletePublishTokenInfo";

// PlatformRelease/api.ts（RequestFunc 封装，同模块既有模式）
export const queryPublishTokenInfo: RequestFunc = (a, s) =>
  apiClient.post(urls.QUERY_PUBLISH_TOKEN_INFO, a, s);
export const addPublishTokenInfo: RequestFunc = (a, s) =>
  apiClient.post(urls.ADD_PUBLISH_TOKEN_INFO, a, s);
export const updatePublishTokenInfo: RequestFunc = (a, s) =>
  apiClient.post(urls.UPDATE_PUBLISH_TOKEN_INFO, a, s);
export const deletePublishTokenInfo: RequestFunc = (a, s) =>
  apiClient.post(urls.DELETE_PUBLISH_TOKEN_INFO, a, s);
```

> 接口为占位定义，路径以后端联调为准。

## 类与组件

| 文件                                                 | 角色             | 变更                                        |
| ---------------------------------------------------- | ---------------- | ------------------------------------------- |
| `.../Publish/publishSetting/index.vue`               | 发布设置页容器   | 新增左侧菜单项 + 右侧条件渲染（+39 行）     |
| `.../Publish/publishSetting/publishTokenTable.vue`   | 发布令牌配置组件 | 新建（287 行）：列表 + 弹窗 + 删除/批量删除 |
| `apps/web-openlibing/src/api/PlatformRelease/url.ts` | 接口地址常量     | 新增 4 个发布令牌接口常量                   |
| `apps/web-openlibing/src/api/PlatformRelease/api.ts` | 接口封装         | 新增 4 个 `RequestFunc` 封装                |

## 数据模型

| 字段          | 类型   | 来源/去向     | 说明             |
| ------------- | ------ | ------------- | ---------------- |
| `tokenType`   | string | 列表/表单     | gitee / gitcode  |
| `login`       | string | 列表/表单     | 账号用户名       |
| `tokenMasked` | string | 列表          | 后端脱敏展示     |
| `token`       | string | 新建/编辑表单 | 明文令牌，仅提交 |
| `creatorName` | string | 列表          | 创建人           |
| `createTime`  | string | 列表          | 创建时间         |

## 安全

- 账号令牌列表仅展示后端脱敏后的 `tokenMasked`，前端不接收明文。
- 明文 `token` 仅在新建/编辑弹窗提交时传输，不落前端缓存。
- 删除/批量删除均有二次确认。

## 影响范围

- 仅影响发布设置页（新增第三个菜单模块），既有「中心仓配置」等模块零改动。
- `PlatformRelease` api 模块新增 4 个接口封装，无既有接口变更。

## 回滚策略

revert 业务 commit 即可整体回退（新组件 + 菜单接入 + 接口封装均为增量，无共享代码改动）。

Generated-by: GLM-5.3
