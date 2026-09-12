# 【openlibing-web】SBOM 成分分析筛选栏布局优化 — 技术设计

## 布局结构

```
.search-params (display: flex; align-items: flex-start)
├── .search-filters (flex: 1; display: flex; flex-wrap: wrap)
│   ├── .query-item (flex-shrink: 0)  License 180px
│   ├── .query-item (flex-shrink: 0)  License 数量 180px
│   ├── .query-item (flex-shrink: 0)  License 合规性 180px
│   ├── .query-item (flex-shrink: 0)  漏洞级别 IncludeExcludeFilter (trigger-width 180)
│   ├── .query-item (flex-shrink: 0)  依赖类型 160px
│   └── .query-item (width: 240px)    package
└── .search-actions (display: flex; flex-shrink: 0)
    └── .action-item (flex-shrink: 0) 查询 / 重置 / 全量导出
```

## 关键样式决策

| 决策                                                   | 说明                                                                   |
| ------------------------------------------------------ | ---------------------------------------------------------------------- |
| `.search-params` 增加 `align-items: flex-start`        | 允许筛选区多行换行时按钮区保持顶部对齐（第一行右上角）                 |
| `.search-filters` 设 `flex: 1` + `flex-wrap: wrap`     | 筛选条件占满剩余宽度，放不下时换行而不是横向溢出                       |
| `.query-item` 设 `flex-shrink: 0`                      | 缩放/窄屏下筛选项保持声明宽度，触发容器换行，避免 el-select 内部被压缩 |
| `.search-actions` / `.action-item` 设 `flex-shrink: 0` | 操作按钮永不换行、永不压缩，固定在第一行右上角                         |

## 筛选项宽度调整

| 筛选项                           | 调整前            | 调整后            | 调整方式                  |
| -------------------------------- | ----------------- | ----------------- | ------------------------- |
| License                          | 240px             | 180px             | el-select 内联 style      |
| License 数量                     | 240px             | 180px             | el-select 内联 style      |
| License 合规性                   | 240px             | 180px             | el-select 内联 style      |
| 漏洞级别                         | trigger-width 240 | trigger-width 180 | IncludeExcludeFilter prop |
| 依赖类型                         | 240px             | 160px             | el-select 内联 style      |
| 依赖类型（IncludeExcludeFilter） | trigger-width 200 | trigger-width 160 | IncludeExcludeFilter prop |
| package                          | 300px             | 240px             | .query-item 内联 style    |

## 影响面分析

- 纯模板结构调整（新增两层 wrapper div）+ scoped 样式修改，无逻辑改动
- `queryInfo`、`queryList`、防抖、导出等行为均不变
- 仅 `CompositionAnalysis/index.vue` 单文件，不涉及公共组件与其他页面
