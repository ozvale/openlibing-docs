# 【openlibing-cicd-web】流水线列表筛选分页缓存与安全编译选项新增 fstack-check 列 — 技术设计

## 一、流水线列表搜索条件缓存

### 存储设计

| 项       | 值                                                        |
| -------- | --------------------------------------------------------- |
| 存储介质 | `sessionStorage`（会话级，关闭标签页即失效）              |
| Key      | `` `pipeline_filter_cache_${app.projectInfo?.projectId    |     | ''}` `` |
| 隔离维度 | `projectId`，不同项目各自独立缓存                         |
| 序列化   | `JSON.stringify` / `JSON.parse`，解析失败静默降级为无缓存 |

### 缓存结构

```json
{
  "queryParam": { "name": "", "status": [] },
  "pagination": { "pageNum": 1, "pageSize": 10 },
  "byGroup": false,
  "currentPipelineGroup": { "name": "全部分组", "children": [] }
}
```

### 核心函数

| 函数                   | 职责                                             |
| ---------------------- | ------------------------------------------------ |
| `getStorageKey()`      | 按 `projectId` 生成当前项目的缓存 key            |
| `saveFilterCache()`    | 读取当前筛选/分页/分组状态写入 SessionStorage    |
| `restoreFilterCache()` | 先无条件重置为默认值，再读取目标项目缓存覆盖返回 |

### 写入时机

- 统一 `watch` 监听筛选条件（`queryParam.name`、`queryParam.status`）、分页（`pageNum`、`pageSize`）、分组状态（`byGroup`、`currentPipelineGroup`）变化，自动调用 `saveFilterCache()`

### 恢复与重置流程（projectId 变化）

```
watch(app.projectInfo.projectId)
  └─ restoreFilterCache()
       ├─ 1. 无条件重置为默认值（先清残留）
       │     queryParam.name = ''，queryParam.status = []
       │     pageNum = 1，pageSize = 10
       │     byGroup = false，currentPipelineGroup = 全部分组
       ├─ 2. 读 sessionStorage[key]
       │     ├─ 无缓存 → return false（保持默认值）
       │     └─ 有缓存 → JSON.parse 后覆盖各字段
       └─ getPipelineGroupTree() → 重新加载分组树与列表
```

**重置优先设计的原因**：若直接读缓存，目标项目无缓存时上一项目的分组/筛选/分页状态残留，列表被错误过滤；先无条件重置保证任意情况下都回到干净的默认态，再由缓存覆盖。

## 二、安全编译选项新增 fstack-check 列

### 概览表格（SecurityOptions/index.vue）

- 新增 fstack-check 分组，含三列：总文件数 / 满足数 / coverage
- 位置：STACKCLASH 分组之前，倒数第二个分组
- 列配置面板注册 fstack-check 分组，支持用户控制显隐

### 详情弹窗（SecurityOptions/FileDetailDialog.vue）

- 新增 `options.fstackCheck` 列，展示单文件的 fstack-check 检查结果

### 数据来源

后端接口已有返回字段，前端仅补充列定义与展示，无接口改动。

## 影响面分析

- 三个文件均为页面级 scoped 修改，不涉及公共组件、工具函数与接口层
- 缓存读写均在 `pipeline.vue` 内部完成，对组件外无副作用
