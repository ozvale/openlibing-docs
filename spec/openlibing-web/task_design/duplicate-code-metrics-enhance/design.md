# 技术方案：仓库重复代码度量详情增强

## 1. 架构概览

```
index.vue (Repos 主页面)
├── branches.vue (仓库分支列表，v-model 双向绑定搜索关键字)
│   └── emit: goMetricsDetail → 父组件处理
├── MetricsDetailDialog.vue (度量详情，作为页面区域而非弹窗)
│   └── DuplicationCodeDrawer.vue (重复代码块抽屉，仅 metricType=3)
└── 用户管理页
```

核心变化：MetricsDetailDialog 从 branches.vue 内的 el-dialog 提升为 index.vue 中的独立页面区域，通过 `showMetricsDetail` 控制显示/隐藏。

## 2. DuplicationCodeDrawer 组件设计

### 2.1 技术选型

- **编辑器**：CodeMirror 6（`codemirror`，只读模式）
- **包引入**：`@codemirror/state`、`@codemirror/view`、`codemirror`(minimalSetup)
- **原因**：需要代码高亮 + 行号 + 自定义 Gutter 颜色条纹，CodeMirror 6 的 GutterMarker 和 Decoration API 能满足需求

### 2.2 核心数据结构

```
lineMap: doc行号 → 原始文件行号（null 表示段间省略占位行）
ellipsisLines: 省略占位行的 doc 行号集合
duplicationBlocks: [{ startLine, endLine, ... }]  // 重复代码块列表
blockLanes: 每个块分配的轨道（用于重叠块的颜色条纹分层）
```

### 2.3 颜色条纹标识

- 行号旁 Gutter 区域渲染自定义 `BlockColorMarker`
- 通过 `computeBlockLanes` 算法计算重叠块的分层轨道
- 选中块：红色（`#e74c3c`），未选中块：黄色（`#f1c40f`）
- 重叠块按横向偏移排列，保持整个块范围在同一轨道位置

### 2.4 交互功能

| 功能 | 实现方式 |
|------|----------|
| 上一个/下一个块 | `currentBlockIndex` 索引切换，scrollIntoView |
| 跳转到顶部/底部 | 编辑器 scrollDOM 操作 |
| 全屏模式 | `isFullscreen` 状态 + CSS fixed 定位 |
| 省略中间行 | 距离 > 10 行的块之间插入省略占位行 |

### 2.5 Props / Emits

```typescript
// Props
visible: boolean       // 抽屉可见性
repoId: string|number  // 仓库 ID
branchName: string     // 分支名
pipelineRunId: string|number  // 流水线运行 ID
filePath: string       // 文件路径

// Emits
update:visible         // 双向绑定可见性
```

## 3. MetricsDetailDialog 重构

### 3.1 从弹窗到页面区域

**之前**：branches.vue 中 `<el-dialog>` 包裹 `<MetricsDetailDialog>`
**之后**：index.vue 中通过 `v-if="showMetricsDetail"` 切换显示

```vue
<!-- index.vue -->
<div v-if="!showMetricsDetail" class="repo-container">
  <branches @go-metrics-detail="goMetricsDetail" ... />
</div>
<div v-else class="repo-container">
  <MetricsDetailDialog ref="metricsDetailRef" ... />
</div>
```

### 3.2 新增列（metricType=3）

| 列名 | prop | 排序 | 说明 |
|------|------|------|------|
| 文件名称 | filePath | - | 改为可点击链接（蓝色 + hover 下划线） |
| 重复代码行数 | duplicationLineCount | 支持 | 非空非注释行连续 10 行相同 |
| 有效代码行数 | totalLines | 支持 | - |
| 重复率 | duplicationRate | 支持（默认降序） | 重复行数 ÷ 有效行数 × 100% |
| 重复代码块数量 | duplicationBlockCount | 支持 | 该文件中的重复代码块总数 |

### 3.3 表头 Tooltip 系统

在 `metricsColumnMap` 列定义中新增 `tooltip` 字段：

```typescript
{
  prop: 'duplicationLineCount',
  label: '重复代码行数',
  tooltip: '非空非注释行连续10行相同的代码片段...',
}
```

模板中统一渲染：`el-popover` + `QuestionFilled` 图标，hover 触发。

### 3.4 排序优化

- `handleSortChange` 中增加去重判断：`prop` 和 `order` 均未变化时直接 return，避免重复请求
- 初始化时对 metricType=3 默认按 `duplicationRate` 降序排列，通过 `tableRef.sort()` 同步 UI 状态

### 3.5 总文件重复率（metricType=4）改造

- 移除 `mergeMethod` 合并单元格逻辑
- 移除 `filePathColumn`，改为显示 `duplicatedFile`（原始文件名）
- 序号列标签改为"重复文件序列号"
- 通过 `tableRowClassName` 实现奇偶行交替背景色

### 3.6 文件名称点击

仅在 metricType=3 时文件名称可点击：

```typescript
const isFilePathClickable = computed(() => props.metricType === '3');
const onFilePathClick = (row) => {
  currentFilePath.value = row?.filePath || '';
  dupDrawerVisible.value = true;
};
```

## 4. 组件通信模式

### branches.vue → index.vue

```typescript
// branches.vue
const emits = defineEmits(['freshData', 'toUpdate', 'goMetricsDetail', 'update:modelValue']);

const openMetricsDetail = (col, row) => {
  emits('goMetricsDetail', {
    repoId, repoName, pipelineRunId, metricType, branchName
  });
};

// index.vue
function goMetricsDetail(params) {
  Object.assign(metricsDetailProps, params);
  showMetricsDetail.value = true;
  syncMetricsQuery(params);
  nextTick(() => metricsDetailRef.value?.init());
}
```

### 分支搜索缓存（v-model）

```typescript
// index.vue
const branchSearchCache = ref('');
<branches v-model="branchSearchCache" ... />

// branches.vue
const props = defineProps(['repo', 'modelValue']);
const emits = defineEmits(['update:modelValue']);
const branchSearchKey = computed({
  get: () => props.modelValue || '',
  set: (v) => emits('update:modelValue', v),
});
```

## 5. URL 同步策略

### 进入度量详情时同步

```typescript
function syncMetricsQuery(params) {
  // 将 repoId, branchName, pipelineRunId, metricType 同步到 route.query
  // 仅在参数变化时触发 router.replace({ query })
}
```

### 切换项目时清理

```typescript
// watch projectInfo 变化时
needResetUrlQuery.value = true;

// onActivated（keep-alive 重新激活）
onActivated(() => {
  if (needResetUrlQuery.value) {
    needResetUrlQuery.value = false;
    router.replace({ path: route.path, query: {} });
  }
});
```

### autoGoBranch 仅首次触发

```typescript
watch(() => useApp.projectInfo, (newValue, oldValue) => {
  // ...
  if (!oldValue && route.query.repoId) {
    autoGoBranch(String(route.query.repoId));  // 仅首次进入
  }
});
```

## 6. 新增 API 接口

| 接口函数 | URL | 入参 | 出参 |
|----------|-----|------|------|
| `fileContent` | `/code-repo/metrics/code/file-content` | repoId, branchName, pipelineRunId, filePath | 文件内容字符串 |
| `duplicationBlockDetail` | `/code-repo/metrics/code/duplication-block/detail` | repoId, branchName, pipelineRunId, filePath | 重复代码块列表（含 startLine, endLine） |
| `queryRepoFilterMeta` | `/code-repo/project-repo/query-repo-filter-meta` | projectId | 仓库筛选元数据 |

## 7. 风险与注意事项

- CodeMirror 6 在只读模式下性能良好，但大文件（>10000 行）需关注渲染性能
- 重复代码块省略逻辑（块间距 > 10 行时省略）需要在 lineMap 中标记占位行
- keep-alive 场景下 `onActivated` 与 `onMounted` 的触发时机差异需要正确处理
- 排序切换去重逻辑依赖 `sortByField` 和 `sort` 的比较，需确保初始化时状态一致