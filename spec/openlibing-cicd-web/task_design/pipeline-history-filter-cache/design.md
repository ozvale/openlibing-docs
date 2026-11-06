# Design: 执行历史 Tab 筛选条件临时缓存 — 技术设计

## 1. 方案设计

### 背景

流水线详情页三个 tab（流水线详情/执行历史/排队列表）在 [index.vue](file:///d:/openlibing/openlibing-cicd-web/src/views/pipeline/PipelineDetail/index.vue) 中以 `v-if` 互斥渲染，切 tab 即销毁重建「执行历史」组件实例，查询条件全部回到默认值。

### 候选方案对比

| 候选方案                    | 结论   | 理由                                                                                                    |
| --------------------------- | ------ | ------------------------------------------------------------------------------------------------------- |
| 父组件 `v-show` 替代 `v-if` | 不采用 | 三个 tab 常驻内存，Detail/Queue 各自持有定时刷新逻辑，改动影响面大                                      |
| `keep-alive` 缓存组件       | 不采用 | 需改父组件结构，缓存整组件（含表格数据）内存开销大，与"只恢复条件"不匹配                                |
| **sessionStorage 条件快照** | 采用   | 仓库既有模式（pipeline.vue 列表筛选缓存已验证），只存轻量条件对象，天然支持刷新恢复，改动收敛在单文件内 |

### 整体流程

```
挂载 → projectInfo watch(immediate) 触发
        ├─ URL 带 status 参数（外链跳转）→ 以 URL 为准 + 重置第 1 页，不恢复缓存（优先级最高）
        └─ 正常进入 → restoreFilterCache() 恢复缓存 → 直接按恢复后的条件查询
任何查询（getPipelineRunHistory）→ saveFilterCache() 先保存条件快照
卸载（切 tab）→ 状态随实例销毁，快照已在 sessionStorage
再次挂载 → 恢复快照，回到离开时的条件与页码
```

### 关键决策

| 决策                                                        | 原因                                                                                                                                     |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 保存时机选在"每次查询时"而非"watch 条件变化"                | 组件内所有条件变更（日期 change、筛选、翻页、排序）都会触发查询，查询时快照 = 列表数据实际使用的条件，缓存与展示强一致，免增深度 watcher |
| 初始加载 `searchTable()` 改为直接 `getPipelineRunHistory()` | `searchTable()` 强制重置页码，会覆盖恢复出的页码；手动查询路径（searchTable）保留重置行为不变                                            |
| 恢复去重（restoredCacheKey）                                | projectInfo 为深度 watch，可能多次触发；同 pipelineId 只恢复一次，避免覆盖用户已修改的条件                                               |
| 排序条件恢复但不绑定 el-table default-sort                  | 挂载期绑定 default-sort 有触发二次请求的风险；查询按恢复的排序生效，点击列头后箭头回显，功能无损                                         |
| 不设 TTL                                                    | "临时"语义由 sessionStorage 生命周期天然保证，标签页关闭即清                                                                             |

## 2. 实现逻辑设计

### saveFilterCache（每次查询时执行）

1. 构造快照对象：owner（当前 userId）+ searchDateValue + searchStatusValue + searchMergeIdValue + pageNum + pageSize + sortField + sortType。
2. `sessionStorage.setItem(key, JSON.stringify(快照))`。
3. try/catch 包裹：隐私模式/配额耗尽时静默降级为不缓存，不报错。

### restoreFilterCache（初始加载、非外链场景执行）

1. `getItem` + `JSON.parse`，整体 try/catch，解析失败回落默认值。
2. owner 归属校验：owner 与当前 userId 双方齐全且不匹配 → 删除缓存并放弃恢复；缺失一方跳过校验（兼容旧缓存，口径同 pipeline.vue）。
3. 逐字段合法性校验，非法字段保持默认值：searchDateValue 必须为二元数组；pageSize 必须在 pageSizes 内；sortType 仅允许 `ASC` / `DESC` / 空串；pageNum > 0。
4. 去重守卫：restoredCacheKey 与当前 pipelineId 相同则直接返回，防止深度 watch 重复触发时覆盖用户已修改的条件。

### 初始加载分支（projectInfo watch immediate）

- `route.query.status` 存在（外链跳转）→ 沿用原有 URL 覆盖逻辑，重置页码为 1，不恢复缓存。
- 否则 → restoreFilterCache() 后直接调用 `getPipelineRunHistory()`（不走 searchTable，避免重置页码）。

### 边界条件

- 恢复的页码超出当前总页数（数据已变化）：与现有任意越界页行为一致，后端返回空列表 + 最新 total，不特殊处理。
- 外链跳入后用户改条件再触发深度 watch：route.query 未变，仍命中 URL 分支，行为与改动前一致。

## 3. 类设计

不适用 + 原因：改动为 Vue 3 `<script setup>` 单组件内的函数级扩展（新增 saveFilterCache / restoreFilterCache / getStorageKey 三个函数），无新增类、组件、hook 或模块抽象，不引入组件间新职责划分。

## 4. 数据模型设计

无业务数据模型变更（无接口字段、无后端 schema 变化）。仅新增一份 sessionStorage 存储格式：

```
key:   pipeline_history_filter_cache_<pipelineId>     # 按流水线隔离
value: {
  owner:              userId,            # 归属校验，防跨账号残留
  searchDateValue:    [start, end],      # YYYY-MM-DD 字符串，与 value-format 一致
  searchStatusValue:  ['FAILED', ...],   # 状态多选
  searchMergeIdValue: '123',             # Merge ID 筛选
  pageNum:            3,
  pageSize:           20,
  sortField:          'runTime',
  sortType:           'DESC'
}
```

## 5. 性能设计

不适用 + 原因：读写均为 sessionStorage 单键小对象（< 200B）的 O(1) 操作，发生在用户主动查询时，频率低、耗时微秒级；列表数据不进缓存，无内存与存储膨胀风险。

## 6. API 接口设计

不适用 + 原因：纯前端组件态缓存，查询仍走既有 `getPipelineRunHistory` 接口，入参出参零变化，无新增/变更接口契约，无需产出 api.md。

## 7. 安全设计

- 跨账号数据隔离：缓存写入 owner（userId），恢复时双方齐全且不匹配即删除并放弃恢复，防止同一浏览器先后登录的不同账号看到对方筛选残留。
- 敏感信息：缓存内容仅为查询条件与页码，不含凭证、token 或业务敏感数据；存储于 sessionStorage（标签页级生命周期），不落盘、不上传。
- 输入信任边界：JSON.parse 结果不可信，逐字段类型与合法性校验后才写入组件状态，无直接注入面。
- 降级安全：所有存储读写 try/catch 静默降级，异常不阻断主流程。

## 涉及文件

| 文件                                                              | 操作 | 说明                                                                                                                                                                                  |
| ----------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| openlibing-cicd-web/src/views/pipeline/PipelineDetail/History.vue | 修改 | 新增缓存常量与 getStorageKey / saveFilterCache / restoreFilterCache；getPipelineRunHistory 首行保存快照；projectInfo watch 初始加载分支重写（URL 优先 / 恢复缓存 / 不再强制重置页码） |

## 风险 & 缓解

| 风险                                       | 缓解                                                             |
| ------------------------------------------ | ---------------------------------------------------------------- |
| 恢复页码越界显示空列表                     | 与现有越界页行为一致，用户翻页即恢复；不特殊处理                 |
| 表头排序箭头不回显（查询已按恢复排序生效） | 已知取舍：绑定 default-sort 有挂载期二次请求风险；点击列头即回显 |
| projectInfo 深度 watch 多次触发反复恢复    | restoredCacheKey 同 pipelineId 去重                              |

## 影响范围

- 单文件 +72/-1，无接口/数据模型/依赖变化，无部署影响
- 不涉及其他仓
