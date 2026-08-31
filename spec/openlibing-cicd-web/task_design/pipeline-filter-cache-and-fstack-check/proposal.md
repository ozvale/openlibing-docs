# 【openlibing-cicd-web】流水线列表筛选分页缓存与安全编译选项新增 fstack-check 列

## 需求背景

### 1. 流水线列表搜索条件缓存

用户在流水线列表页设置搜索条件（名称、状态、分组）与分页后，切换项目再切回时条件全部丢失，需重新选择。同时在切换项目场景下，若目标项目无缓存，上一项目遗留的分组/筛选状态会导致列表被错误过滤。本次改造将筛选条件、分页参数、分组状态按项目维度缓存到 SessionStorage，切换项目时恢复对应缓存。

### 2. 安全编译选项新增 fstack-check 列

安全编译选项（SecurityOptions）概览与文件详情需要展示 fstack-check 检查项的检查结果，概览表格与列配置面板补充该分组，详情弹窗同步新增对应列。

## 功能描述

### 流水线列表（src/views/pipeline/pipeline.vue）

- 新增 SessionStorage 缓存，key 为 `pipeline_filter_cache_${projectId}`，按项目隔离
- 缓存内容：`queryParam`（名称、状态）、`pagination`（pageNum、pageSize）、`byGroup`、`currentPipelineGroup`
- 统一监听筛选与分页变化，自动写入 SessionStorage
- 切换项目（projectId 变化）时先无条件重置为默认值（清空名称/状态、重置分页、退出分组模式、回到全部分组），再尝试恢复目标项目缓存
- 恢复缓存后重新加载分组树与列表

### 安全编译选项（src/views/SecurityOptions）

- 概览表格新增 fstack-check 分组（总文件数 / 满足数 / coverage），置于 STACKCLASH 分组之前倒数第二个位置
- 列配置面板注册 fstack-check 对应分组
- 文件详情弹窗同步新增 `options.fstackCheck` 列

## 不做什么

- 不修改流水线查询接口入参出参与后端逻辑（纯前端缓存）
- 不修改安全编译选项后端接口（fstack-check 数据为接口已有返回字段，前端仅补展示）
- 不做跨浏览器会话持久化（SessionStorage 生命周期跟随会话）

## 验收标准

- [x] 列表页设置筛选/分组/分页后切换项目再切回，条件自动恢复且列表按恢复的条件查询
- [x] 切换到无缓存的项目时，分组/筛选/分页回到默认值，无上一项目状态残留
- [x] 不同项目的缓存按 projectId 隔离，互不影响
- [x] 概览表格展示 fstack-check 分组（总文件数/满足数/coverage），位置在 STACKCLASH 前
- [x] 列配置面板可控制 fstack-check 分组显隐
- [x] 文件详情弹窗展示 options.fstackCheck 列

## 影响范围

| 文件                                             | 操作 | 说明                                        |
| ------------------------------------------------ | ---- | ------------------------------------------- |
| `src/views/pipeline/pipeline.vue`                | 修改 | SessionStorage 缓存写入/恢复/重置（+66/-1） |
| `src/views/SecurityOptions/index.vue`            | 修改 | 概览表格新增 fstack-check 分组 + 列配置注册 |
| `src/views/SecurityOptions/FileDetailDialog.vue` | 修改 | 详情弹窗新增 options.fstackCheck 列         |

## 关联提交

- `a3ddb4e` feat(pipeline): 缓存流水线列表筛选与分页到 SessionStorage
- `a9edd37` fix(pipeline): 无缓存时重置筛选状态避免残留上个项目分组
- `71da5f3` feat(security-options): 安全编译选项概览与详情新增 fstack-check 列

## 关联 Issue

- https://gitcode.com/openlibing/openlibing-cicd/issues/185（流水线搜索条件缓存部分）
