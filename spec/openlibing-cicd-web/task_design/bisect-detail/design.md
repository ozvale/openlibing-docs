# Design: PR 问题二分定位功能（BisectDetail）

## 技术方案

### 变更文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/api/pipeline/url.ts` | 修改 | 新增 `BISECT` 和 `BISECT_RESET` URL 常量 |
| `src/api/pipeline/api.ts` | 修改 | 新增 `postBisectAxios`、`getBisectAxios`、`postBisectResetAxios` 三个 API 函数 |
| `src/views/pipeline/PipelineDetail/Detail.vue` | 修改 | 新增 BisectDetail 组件导入、入口链接和对话框实例 |
| `src/views/pipeline/PipelineDetail/components/BisectDetail/BisectDetail.vue` | 新增 | 二分定位进度弹窗主组件 |
| `src/views/pipeline/PipelineDetail/components/BisectDetail/BisectDetailLabel.vue` | 新增 | 对话框标题行组件（含帮助文档链接） |
| `src/views/pipeline/PipelineEdit/pipelineBisectDebug.vue` | 新增 | 二分定位配置组件 |
| `src/views/pipeline/PipelineEdit/pipelineEditDialog.vue` | 修改 | 集成 bisectDebug Tab、序列化与保存逻辑 |
| `src/views/pipeline/PipelineEdit/pipelineEventTriggerSettings.vue` | 修改 | 微调 |

### API 接口

| 函数 | 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|------|
| `getBisectAxios` | GET | `/project/pipeline/bisect` | `pipelineRunId` | 获取分析任务信息和进度列表 |
| `postBisectAxios` | POST | `/project/pipeline/bisect` | `projectId`, `pipelineId`, `pipelineRunId` | 启动分析任务 |
| `postBisectResetAxios` | POST | `/project/pipeline/bisect/reset` | `id`(param), `projectId`(data) | 重置单条 PR 记录 |

### 数据结构

**taskInfo（分析任务信息）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `locateStatus` | string | 分析状态码 |
| `locateStatusDesc` | string | 状态中文描述 |
| `locatedPr` | number | 定位到的问题 PR 编号 |
| `locatedPrUrl` | string | 问题 PR 跳转 URL |
| `failureMsg` | string | 失败消息 |
| `createTime` | string | 分析创建时间 |
| `updateTime` | string | 分析更新时间 |
| `successTime` | string | 最近成功节点时间 |
| `failureTime` | string | 当前失败节点时间 |

**tableData 行（进度列表）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | number | 记录 ID（用于重置） |
| `prId` | number | PR 编号 |
| `prTitle` | string | PR 标题 |
| `prUrl` | string | PR 跳转 URL |
| `pipelineRunId` | string | 分析用流水线运行 ID |
| `runNumber` | number | 流水线运行编号 |
| `mergedAt` | string | PR 合入时间 |
| `status` | string | 进度状态 |
| `statusDesc` | string | 状态描述 |
| `failureMsg` | string | 失败消息 |

### 实现细节

#### 1. API 层（url.ts / api.ts）

新增两个 URL 常量：

```ts
export const BISECT = pipeline + '/project/pipeline/bisect';
export const BISECT_RESET = pipeline + '/project/pipeline/bisect/reset';
```

新增三个 API 函数：`postBisectAxios`（POST 启动分析）、`getBisectAxios`（GET 查询进度）、`postBisectResetAxios`（POST 重置记录）。

#### 2. Detail.vue 入口集成

- 导入并注册 `BisectDetail` 组件
- 新增 `showBisectDialog` ref 控制对话框显隐
- 页头子标题栏新增入口链接：`PR问题定位：查看详情`，仅 `isExecuted` 时展示
- 模板中实例化 `BisectDetail`，传入 `pipelineId` 和 `pipelineRunId`

#### 3. BisectDetail.vue 主组件

**Props**：`pipelineId`（必填）、`pipelineRunId`（必填），通过 `defineModel` 实现对话框显隐双向绑定。

**数据加载**：`loadData()` 调用 `getBisectAxios`，将 `res.data.task` 映射到 `taskInfo`，`res.data.progress` 映射到 `tableData`。

**启动分析**：`handleCreateTask()` 弹出确认框后调用 `postBisectAxios`，传入 `projectId`、`pipelineId`、`pipelineRunId`。

**重置**：`handleReset(row)` 调用 `postBisectResetAxios`，仅当状态为 `QUEUED/QUEUED_TIME_OUT/FAILED/RUN_FAILED` 时可用。

**状态图标**：两级映射 — 任务级 `getLocateStatusIcon` 和进度行级 `getStatusIcon`，分别将状态码映射为绿色对勾/红色叉号/蓝色旋转加载/灰色禁止图标。

**watch**：对话框打开时自动调用 `loadData()`。

#### 4. BisectDetailLabel.vue 标题组件

纯展示组件，渲染标题"PR问题定位进度列表"和帮助文档问号图标（跳转帮助中心 `id=234`）。

#### 5. pipelineBisectDebug.vue 配置组件

**核心数据** `concurrencyControl`：

```ts
{
  isBisectOn: false,      // 开关
  bisectStrategy: '',     // PR 筛选策略
  bisectRepo: '',         // 代码源 URL
}
```

**代码源选项**：从 `pipelineDetailData.sources` 提取，仅 `git_type === 'gitcode'` 可选。

**表单校验**：`isBisectOn` 为 true 时 `bisectRepo` 必填。

**数据同步**：`syncBisectSettings()` 从父数据同步到本地表单；`watch(pipelineDetailData)` 监听父数据变化。

**暴露接口**：`concurrencyControl` 和 `validate()`。

#### 6. pipelineEditDialog.vue 集成

- 导入 `pipelineBisectDebug`，注册为 `'bisectDebug'` Tab
- 左侧菜单项"辅助功能"，非批量编辑模式下展示
- 序列化 `serializeBisectDebugPayload()` 输出 `isBisectOn` + `bisectRepo`
- 保存 `confirmEditBisectDebugSettings()` 提交 `isBisectOn` + `bisectRepo` + `bisectStrategy`
- 纳入 `runTabValidate` 校验链路

### 数据流

**查看分析**：
```
用户点击"查看详情" → showBisectDialog = true
  → BisectDetail 对话框打开 → watch 触发 loadData()
  → GET /bisect?pipelineRunId=xxx → 返回 task + progress
  → 渲染摘要区域 + 进度列表表格
```

**启动分析**：
```
用户点击"分析" → 确认框 → POST /bisect {projectId, pipelineId, pipelineRunId}
  → 提示"已启动分析" → 自动刷新 loadData()
```

**重置记录**：
```
用户点击"重置" → POST /bisect/reset {id, projectId}
  → 刷新 loadData()
```

**配置保存**：
```
用户编辑配置 → 切换到其他 Tab 或保存
  → confirmEditBisectDebugSettings()
  → updatePinelineConfigAxios {isBisectOn, bisectRepo, bisectStrategy}
```

### 无变更项

- 后端 API：无新增，接口已有
- 路由/权限：无变更
- 外部依赖：无新增
