# Design: 安全编译选项数据工程能力建设

## 1. 方案设计

### 1.1 总体架构

以「检测 → 概览 → 下钻 → 备案 → 跟踪」为主线，将原单一概览页面拆分为多页面 + 自研组件的可扩展结构：

```
路由层 (router/index.ts)
├── /securityOptions                       主页面 (index.vue)
├── /securityOptions/package-detail        产物包详情 (PackageDetailPage → PackageDetailView)
└── /securityOptions/filing-records        备案记录 (FilingRecordsPage → FilingRecordsView)

API 层 (api/SecurityOptions/{api,url}.ts)
├── overview  / dropdown / file-detail      检测数据
└── filing/save / cancel / list / record-list / filer-list   备案闭环

视图层 (views/SecurityOptions/)
├── index.vue                              主页面（构建产物 tab）
├── FileDetailDialog.vue                   文件详情弹窗
├── FilingBatchDialog.vue                  批量备案对话框
├── FilingListView.vue                     备案列表视图
├── FilingRecordsPage.vue + View           备案记录独立页
├── PackageDetailPage.vue + View           产物包详情独立页
└── constants.ts                           14 项安全编译选项元数据

组件层 (components/)
├── CategorySearch/                        自研分类筛选工具栏
│   ├── CategorySearch.vue
│   ├── CategorySearchEditor.vue
│   ├── types.ts
│   └── index.ts
├── ColumnFilter.vue                        表格列筛选器
├── TableHeaderFilter.vue                   表头筛选器（增强 placement/popperClass）
└── BatchOperation.vue                      批量操作组件（适配 filing）
```

### 1.2 关键决策

| 决策                  | 选择                                             | 原因                                                                                              |
| --------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| 路由形态              | 主页面 + 两个 hideInMenu 子路由                  | 主页面承载概览；详情页与备案记录页独立路由，便于深链与 noKeepAlive 隔离状态                       |
| 筛选组件              | 自研 CategorySearch                              | el-table 表头筛选 + 多种类型（checkbox / radio / text / dateRange）混合，原生组件拼装复杂且不复用 |
| 安全指标枚举          | 14 项常量化到 constants.ts                       | 与后端 overviewData / file-detail options 的 key 严格一致，避免散落字符串                         |
| 未扫描项              | `UNSCANNED` 占位值                               | 区分「未扫描」与「N/A」语义，避免颜色映射混淆                                                     |
| 备案定位              | `recordId` 贯穿 filer-list / save / list         | 数据变更后通过 recordId 同步定位，保证幂等性                                                      |
| 备案原因              | 可选（FilingBatchDialog）                        | 业务方反馈非必填，去掉强制校验                                                                    |
| 详情弹窗 popover 挂载 | 挂载到 dialog body                               | 防止 popover 被 dialog overflow 截断                                                              |
| 时间排序              | CategorySearch dateRange + 表格 sortByField/sort | 双轨：筛选用 dateRange，排序用 table column                                                       |

### 1.3 跨仓影响

本次改动仅限 `openlibing-cicd-web` 前端仓，对应后端接口已在 `openlibing-cicd` 后端仓提供（属同 FE 需求的协同改动，不在本 spec 范围）。

## 2. 实现逻辑设计

### 2.1 主页面流程

1. 进入 `/securityOptions` → 触发 `buildArtifactSecOptionDropdown` 拉取代码仓 / 文件下拉
2. `CategorySearch` 收集筛选条件（repoName / packageName / dateRange / 多选指标）
3. 触发 `buildArtifactSecOptionOverview` 拉取概览数据，参数含 `projectId` / `repoName` / `packageName` / `startTime` / `endTime` / `sortByField` / `sort`
4. 表格列：3 列固定（代码仓 / 流水线 / 文件） + 14 列安全指标 + 概要列
5. 点击文件名 → 打开 `FileDetailDialog`，调用 `metricsCodeFileDetail` 拉取明细
6. 点击产物包行 → 跳转 `/securityOptions/package-detail?recordId=...`
7. 点击导航「备案记录」→ 跳转 `/securityOptions/filing-records`

### 2.2 备案闭环流程

```
FilingListView (列表)
   │  表头筛选 (CategorySearch) ──┐
   │  批量选择文件 (BatchOperation)│
   ▼                              ▼
FilingBatchDialog            filer-list 接口拉取候选
   │  填写备案原因（可选）
   ▼
filing/save (携带 recordId + 文件列表 + 原因)
   │
   ▼
filing/list 刷新当前视图 ──> filer-list 同步刷新
   │
   ▼（单条取消）
确认对话框 → filing/cancel (携带 recordId) → 刷新
```

### 2.3 产物包详情流程

1. 从主页面跳转 `/securityOptions/package-detail?recordId=xxx`
2. `PackageDetailPage` 读取 `recordId` 后委托给 `PackageDetailView`
3. `PackageDetailView` 调用 `file-detail` 接口拉取该产物包下所有文件明细
4. 文件扫描结果按「已扫描项」过滤，与概览页指标对齐
5. 提供「批量备案」入口，复用 `FilingBatchDialog`

### 2.4 文件详情弹窗

1. 由主页面「文件名」列点击触发
2. `FileDetailDialog` 调用 `metricsCodeFileDetail` 拉取文件级数据
3. popover 挂载到 dialog body，避免被裁剪
4. 表头 `TableHeaderFilter` 提供文件名模糊搜索
5. `rawOptions` 重命名为 `options`，对齐后端 schema

### 2.5 备案记录页流程

1. 进入 `/securityOptions/filing-records`
2. `FilingRecordsPage` 壳组件，挂载 `FilingRecordsView`
3. `FilingRecordsView` 调用 `filing/record-list` 拉取历史备案
4. 通过 `recordId` 定位 filer-list，数据变更后自动同步

## 3. 类设计

### 3.1 常量与类型

```ts
// constants.ts
export interface SecOptionMeta {
  key: string; // bindNow / nx / pic / pie / aslr / relro / rpath / sp / strip / fortify / fvisibility / ftrapv / fstackCheck / stackClash
  name: string; // BIND_NOW / NX / ...
  shortName: string; // 同 name
  description: string; // tooltip 中文说明
}

export const SEC_OPTIONS: SecOptionMeta[]; // 14 项
export const SEC_OPTION_KEYS: string[]; // 派生 keys
export const UNSCANNED_VALUE = "UNSCANNED"; // 未扫描占位值
export const OPTION_VALUE_TYPE: Record<string, "success" | "danger" | "info">;
export function getSecOptionMeta(key: string): SecOptionMeta | undefined;
export function rateClass(val: string | number | null | undefined): string;
//   >=80% => 'rate-high'
//   >=50% => 'rate-medium'
//   < 50% => 'rate-low'
//   N/A / 空 => ''
```

### 3.2 CategorySearch 类型

```ts
// components/CategorySearch/types.ts
export type CategorySearchType = "checkbox" | "radio" | "text" | "dateRange";

export interface CategorySearchOption {
  disabled?: boolean;
  label: string;
  value: string;
}

export interface CategorySearchCategory {
  field: string;
  group?: string;
  label: string;
  maxLength?: number;
  options?: CategorySearchOption[];
  placeholder?: string;
  searchable?: boolean;
  type: CategorySearchType;
}

export type CategorySearchFieldValue = string | string[];
export type CategorySearchModel = Record<
  string,
  CategorySearchFieldValue | undefined
>;
export type CategorySearchOperation = "add" | "clear" | "remove" | "update";

export interface CategorySearchChangeEvent {
  field?: string;
  model: CategorySearchModel;
  operation: CategorySearchOperation;
}
```

### 3.3 API 客户端

```ts
// api/SecurityOptions/api.ts
type RequestFunc = (
  a?: AxiosRequestConfig,
  s?: ApiClientSetting,
) => AxiosPromise<any> | Promise<any>;

export const buildArtifactSecOptionOverview: RequestFunc; // 概览
export const metricsCodeFileDetail: RequestFunc; // 文件详情
export const buildArtifactSecOptionDropdown: RequestFunc; // 下拉
export const secOptionFilingSave: RequestFunc; // 备案保存
export const secOptionFilingCancel: RequestFunc; // 备案取消
export const secOptionFilingList: RequestFunc; // 备案列表
export const secOptionFilingRecordList: RequestFunc; // 备案记录列表
export const secOptionFilingFilerList: RequestFunc; // 备案过滤列表
```

### 3.4 组件层级

```
CategorySearch (容器)
└── CategorySearchEditor (编辑器子组件，按 type 渲染不同控件)
       ├── el-select  (checkbox / radio)
       ├── el-input   (text)
       └── el-date-picker (dateRange)

TableHeaderFilter (表头筛选器)
└── el-popover (placement + popperClass 可控)

ColumnFilter (列筛选器)
└── el-checkbox-group
```

## 4. 数据模型设计

### 4.1 概览行数据

```json
{
  "repoName": "openlibing-cicd",
  "runNumber": 123,
  "pipelineLink": "/pipeline/run/123",
  "packageName": "openlibing-cicd-web.jar",
  "detectionCompletedAt": "2026-09-23 12:00:00",
  "recordId": "rec-abc-001",
  "overviewData": {
    "bindNow":    { "totalFiles": 10, "yesCount": 8, "rate": "80%" },
    "nx":         { "totalFiles": 10, "yesCount": 7, "rate": "70%" },
    "pic":        { ... },
    "pie":        { ... },
    "aslr":       { ... },
    "relro":      { ... },
    "rpath":      { ... },
    "sp":         { ... },
    "strip":      { ... },
    "fortify":    { ... },
    "fvisibility":{ ... },
    "ftrapv":     { ... },
    "fstackCheck":{ ... },
    "stackClash": { ... }
  }
}
```

### 4.2 文件详情数据

```json
{
  "recordId": "rec-abc-001",
  "packageName": "openlibing-cicd-web.jar",
  "files": [
    {
      "fileName": "AppComponent.class",
      "options": {
        "bindNow":    "YES",
        "nx":         "NO",
        "pic":        "N/A",
        "aslr":       "UNSCANNED",
        ...
      }
    }
  ]
}
```

### 4.3 备案数据

```json
// filing/save 请求
{
  "recordId": "rec-abc-001",
  "fileNames": ["AppComponent.class", "Utils.class"],
  "reason": "依赖未提供该编译选项，备案跟踪"
}

// filing/list 行
{
  "recordId": "rec-abc-001",
  "repoName": "openlibing-cicd",
  "packageName": "openlibing-cicd-web.jar",
  "fileName": "AppComponent.class",
  "reason": "...",
  "filingUser": "zhangsan",
  "filingAt": "2026-09-23 12:00:00",
  "status": "FILED"
}

// filing/record-list 行（按产物包维度聚合）
{
  "recordId": "rec-abc-001",
  "repoName": "openlibing-cicd",
  "packageName": "openlibing-cicd-web.jar",
  "filedCount": 5,
  "lastFilingAt": "2026-09-23 12:00:00",
  "lastFilingUser": "zhangsan"
}
```

### 4.4 下拉数据

```json
// buildArtifactSecOptionDropdown 响应
{
  "repoNames": ["openlibing-cicd", "openlibing-codecheck", ...],
  "packageNames": ["openlibing-cicd-web.jar", "openlibing-docs.jar", ...]
}
```

### 4.5 筛选 / 排序参数

| 参数          | 类型              | 来源                      | 说明                              |
| ------------- | ----------------- | ------------------------- | --------------------------------- |
| `projectId`   | string            | `app.projectInfo`         | 项目上下文                        |
| `repoName`    | string            | CategorySearch 代码仓下拉 | 精确匹配                          |
| `packageName` | string            | CategorySearch 文件下拉   | 联动数据                          |
| `startTime`   | string (ISO)      | CategorySearch dateRange  | 检测完成时间起                    |
| `endTime`     | string (ISO)      | CategorySearch dateRange  | 检测完成时间止                    |
| `sortByField` | string            | 表格排序                  | 去掉 `overviewData.` 前缀的字段名 |
| `sort`        | `'asc' \| 'desc'` | 表格排序                  | 排序方向                          |

## 5. 性能设计

### 5.1 表格渲染

- 主表格列数：3（固定） + 14（安全指标） + 1（概要） = 18 列；行规模通常 ≤ 500，采用 `el-table` 默认渲染 + `fixed="left"` 固定前三列
- 弹窗内文件明细表格：开启 `TableHeaderFilter` 模糊搜索前置过滤，避免一次性渲染上万行

### 5.2 接口请求

- 下拉接口：进入页面时一次性拉取 `repoNames` + `packageNames`，文件下拉本地联动不重复请求
- 概览接口：依赖 `projectId` + 筛选条件，筛选变化才触发请求
- 备案 filer-list：仅在 `recordId` 变化或 filing/save / cancel 后刷新，避免无谓轮询

### 5.3 组件复用

- `CategorySearch` 内部按 `category.type` 懒渲染子组件，未激活类别不挂载 DOM
- `FileDetailDialog` 使用 `v-model:visible` 控制挂载，关闭即销毁，避免大对象驻留

### 5.4 路由隔离

- 子路由 `filing-records` / `package-detail` 配置 `noKeepAlive: true`，避免缓存跨页状态污染
- 主页面保留 keep-alive，使筛选条件在跳转子页返回后保持

## 6. API 接口设计

| 接口函数                       | 路径                                                                    | 方法 | 用途                         | 入参                                                                                             | 出参                                              |
| ------------------------------ | ----------------------------------------------------------------------- | ---- | ---------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------- |
| buildArtifactSecOptionOverview | `/gateway/openlibing-cicd/build-artifact/sec-option/overview`           | POST | 概览列表数据                 | `{ projectId, repoName, packageName, startTime, endTime, sortByField, sort, pageNum, pageSize }` | `{ list: OverviewRow[], total }`                  |
| buildArtifactSecOptionDropdown | `/gateway/openlibing-cicd/build-artifact/sec-option/dropdown`           | POST | 下拉选项数据                 | `{ projectId }`                                                                                  | `{ repoNames: string[], packageNames: string[] }` |
| metricsCodeFileDetail          | `/gateway/openlibing-cicd/build-artifact/sec-option/file-detail`        | POST | 文件详情数据                 | `{ recordId, fileName? }`                                                                        | `{ recordId, packageName, files: FileRow[] }`     |
| secOptionFilingSave            | `/gateway/openlibing-cicd/build-artifact/sec-option/filing/save`        | POST | 备案保存                     | `{ recordId, fileNames: string[], reason? }`                                                     | `{ success: boolean }`                            |
| secOptionFilingCancel          | `/gateway/openlibing-cicd/build-artifact/sec-option/filing/cancel`      | POST | 备案取消                     | `{ recordId, fileNames: string[] }`                                                              | `{ success: boolean }`                            |
| secOptionFilingList            | `/gateway/openlibing-cicd/build-artifact/sec-option/filing/list`        | POST | 备案列表                     | `{ projectId, repoName?, packageName?, pageNum, pageSize }`                                      | `{ list: FilingRow[], total }`                    |
| secOptionFilingRecordList      | `/gateway/openlibing-cicd/build-artifact/sec-option/filing/record-list` | POST | 备案记录列表（按产物包聚合） | `{ projectId, repoName?, pageNum, pageSize }`                                                    | `{ list: FilingRecordRow[], total }`              |
| secOptionFilingFilerList       | `/gateway/openlibing-cicd/build-artifact/sec-option/filing/filer-list`  | POST | 备案过滤列表                 | `{ recordId }`                                                                                   | `{ list: FilerRow[] }`                            |

## 7. 安全设计

### 7.1 权限控制

- 备案操作（save / cancel）按用户 filing 权限启用 / 禁用，前端按钮 disabled + 后端校验双轨
- `FilingBatchDialog` 提交前再次校验当前用户 filing 权限，过期则提示并阻止

### 7.2 输入校验

- `reason` 字段 maxLength 限制（来自 `CategorySearchCategory.maxLength`），避免后端超长
- `recordId` / `fileName` 仅接受后端返回白名单值，前端不做用户自由输入
- `dateRange` 通过 `el-date-picker` 限制可选范围，禁止未来时间

### 7.3 数据展示

- 检测值严格映射 `YES` / `NO` / `N/A` / `UNSCANNED` 四态，避免误判
- 开启率颜色分级以数值边界为依据（≥80 / ≥50 / <50），不依赖字符串匹配

### 7.4 接口调用

- 所有接口通过统一 `ApiClient` 携带 `Authorization`，禁止在 url.ts / api.ts 内硬编码 token
- 跨页跳转携带的 `recordId` 经 `route.query` 读取后立刻送入接口，不做持久化存储

### 7.5 防误操作

- 单条取消备案弹出确认对话框，避免误点
- 批量备案支持选择文件列表预览，提交前可见可选
