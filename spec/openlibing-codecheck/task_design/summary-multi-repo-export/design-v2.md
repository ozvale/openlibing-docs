# summary-multi-repo-export — 详细设计方案（v2）

> 本文档为 `design.md` 的深化版。关联 Issue：https://gitcode.com/openlibing/openlibing-codecheck/issues/174
> 范围：门禁检查 / 版本级检查 CodeCheck 子页面仓库下拉筛选框多选（2026-08-25 确认，导出需求不在本期范围）。

---

## 1. 方案设计

### 1.1 需求与目标

| 编号 | 需求                                             | 目标                                              |
| ---- | ------------------------------------------------ | ------------------------------------------------- |
| R1   | 门禁检查 / 版本级检查 CodeCheck 子页仓库下拉多选 | 单次查询跨多仓库汇总，过滤参数 `repoNames` 集合化 |
| R2   | 多选仓库时分支下拉展示所选仓库分支的去重并集     | 分支筛选在多仓上下文下仍可用（仍单选）            |

### 1.2 总体架构

```
┌─ openlibing-web ─────────────────────────────────────────────┐
│ GatingCheck.vue / StaticCheck.vue   （筛选：仓库多选→分支并集） │
│ IncrementCheckList.vue / StaticCheckList.vue                   │
│   └─ 列表查询：repoNames 数组参数（原 repoName 不再传）          │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTP (ci-portal 网关)
┌─ openlibing-codecheck ─────▼──────────────────────────────────┐
│ 现有列表接口（微改）：QuerySummaryModel + repoNames             │
│   IncSummaryOperation.getCriteria / CommonOperation.getSummaryCriteria │
│   → Mongo: repoNameEn ∈ repoNames（in 查询）                   │
└────────────────────────────────────────────────────────────────┘
```

不新增任何接口：复用现有两个列表接口，仅扩展查询参数。

### 1.3 技术路线决策

| 决策点             | 选择                                                                                     | 备选与取舍                                                                            |
| ------------------ | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 多选参数表示       | 新增 `repoNames: List<String>`，保留 `repoName`                                          | 备选：复用 `repoName` 传逗号串——类型不安全、与既有单值调用方（APIG 网关等）冲突，弃用 |
| Criteria 构建      | `repoNames` 优先 `in` 查询，空则回退 `repoName is`                                       | 保证既有单选调用方零影响，向后兼容                                                    |
| 分支下拉选项       | 所选仓库分支的 Set 去重并集（保持原有大小写不敏感排序）                                  | 备选：仅取第一个仓库分支——多仓场景语义错误，弃用                                      |
| 多选交互           | `multiple` + `collapse-tags` + `collapse-tags-tooltip`；保留 `filterable`，多选场景禁用 `allow-create` | collapse 避免标签撑爆筛选栏；tooltip 查看完整选择；自定义值无分支且不可查，禁用以消除歧义 |
| 仓库切换时分支处理 | 清空已选分支                                                                             | 旧分支可能不属于新仓库集合，保留会产生空结果歧义                                      |

### 1.4 兼容性边界

- 后端：`repoNames` 缺省或空数组时行为与现状完全一致（回退 `repoName` 单值）；不改任何接口签名与响应结构
- 前端：仅 CodeCheckPages 五文件改动；AntiPoison 子页、子行展开（`getIncChildCheckList` 按行数据查询，不经表单）等既有功能不动
- 数据：无数据模型变更（无 Mongo 集合结构变化，仅查询条件扩展）

---

## 2. 实现逻辑设计

### 2.1 多选查询流程

```
用户多选仓库 [repoA, repoB]
  → el-select(multiple) v-model="formInline.repoNames"（string[]）
  → handleRepoChanged：
       branchOptions = 去重排序(targetDomain[repoA] ∪ targetDomain[repoB])
       formInline.branch = ''          // 清空已选分支
  → 触发列表刷新（triggerFormInlineChange → isFormInlineChanged JSON 比较）
  → POST 列表接口 data: { ..., repoNames: ['repoA','repoB'], ... }  // 原 repoName 字段不再传
  → 后端 QuerySummaryModel.repoNames 绑定
  → getCriteria / getSummaryCriteria：
       repoNames 非空  → criteria.and("repoNameEn").in(repoNames)
       repoNames 空    → repoName 非空 ? and("repoNameEn").is(repoName) : 无仓库过滤
  → Mongo 查询返回（分页、排序、enrichment 均复用现状，不感知多选）
```

### 2.2 前端交互逻辑

```
【选择仓库】el-select(multiple, collapse-tags, filterable, 禁用 allow-create)
  // 多选场景禁用 allow-create：自定义输入的仓库名不在 targetDomain 键集合内，
  // 分支并集无法为其派生分支且后端 in 查询必然为空，属于「可选不可查」，故从根上禁止
  change → handleRepoChanged()
    branchOptions = [...new Set(selectedRepos.flatMap(r => targetDomain[r] || []))]
                    .filter(Boolean)
                    .sort(大小写不敏感)        // 与现有单选排序行为一致
    formInline.branch = ''
    $refs 列表组件.triggerFormInlineChange()

【表单状态同步】
  shared.ts formInlineFactory: repoName:'' → repoNames: []（响应式共享单例）
  resetFormInline(): repoNames = []
  列表组件 data.formInline（本地副本，用于 isFormInlineChanged 差异比较）：repoName:'' → repoNames: []
  同步时须防御性拷贝：formInline.repoNames = [...shared.repoNames]  // 新建数组引用，禁止直接赋值共享同一引用
  isFormInlineChanged: JSON.stringify 全量比较，依赖上述「本地副本持有独立数组引用」，否则恒判相等、无法触发刷新

【查询参数构造】
  IncrementCheckList.getIncCheckList / StaticCheckList.getCheckList:
    repoName: this.formInline.repoName || ''  →  repoNames: this.formInline.repoNames || []
```

### 2.3 数据流（状态归属）

```
useAppStore.projectInfo ──► getSelect() ──► targetDomain: Map<repo, branch[]>
                                              │
formInline.repoNames (shared.ts 单例) ◄──── 用户选择
        │                                    │
        ├─► GatingCheck/StaticCheck 渲染下拉  ├─► handleRepoChanged 计算分支并集
        │                                    │
        └─► 列表组件 JSON 副本 ──► 查询参数 repoNames ──► 后端 in 查询
```

---

## 3. 类设计

### 3.1 后端（openlibing-codecheck，3 个修改类，零新增）

| 类                    | 包                           | 修改点                                                                                                                  |
| --------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `QuerySummaryModel`   | business.entity              | + `private List<String> repoNames;`（Lombok @Data 自动生成访问器）                                                      |
| `IncSummaryOperation` | business.operation.codecheck | `getCriteria()` 增加分支：repoNames 非空 → `repoNameEn in(repoNames)`，否则回退 `repoName is`（门禁列表 Criteria 构建） |
| `CommonOperation`     | business.operation.common    | `getSummaryCriteria()` 同样分支（版本级列表 Criteria 构建）                                                             |

Criteria 扩展片段（两处同构）：

```java
List<String> repoNames = querySummaryModel.getRepoNames();
if (CollectionUtils.isNotEmpty(repoNames)) {
  criteria.and("repoNameEn").in(repoNames);
} else if (StringUtils.isNotBlank(querySummaryModel.getRepoName())) {
  criteria.and("repoNameEn").is(querySummaryModel.getRepoName());
}
```

复用类（零改动）：`CheckboardController`、`CheckboardDelegateImpl`（列表编排与 enrichment 不感知多选）。

### 3.2 前端（openlibing-web，5 个修改文件，零新增）

| 文件                       | 角色          | 改动                                                                                                                          |
| -------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `CodeCheckPages/shared.ts` | 表单与 API 层 | `formInlineFactory`: `repoName: ''` → `repoNames: [] as string[]`；`resetFormInline` 同步重置                                 |
| `GatingCheck.vue`          | 门禁筛选容器  | 仓库 el-select + `multiple collapse-tags collapse-tags-tooltip`，v-model→`formInline.repoNames`；`handleRepoChanged` 分支并集 |
| `StaticCheck.vue`          | 版本筛选容器  | 同上                                                                                                                          |
| `IncrementCheckList.vue`   | 门禁列表      | 本地 `data.formInline.repoName` → `repoNames: []`；`getIncCheckList` 参数 `repoName` → `repoNames`                            |
| `StaticCheckList.vue`      | 版本列表      | 同上                                                                                                                          |

组件职责边界：筛选容器（GatingCheck/StaticCheck）只管表单与下拉选项；列表组件持有查询状态并构造查询参数（filterResult 在列表组件内），与现状一致。

---

## 4. 数据模型设计

### 4.1 QuerySummaryModel 扩展（唯一后端模型变更）

```java
// 新增字段（Lombok @Data）
private List<String> repoNames;   // 多选仓库过滤；非空时优先于 repoName
```

### 4.2 查询集合与过滤条件

| 集合                      | 页面       | Criteria 变化                                          | 现有过滤保留                                              |
| ------------------------- | ---------- | ------------------------------------------------------ | --------------------------------------------------------- |
| `task_inc_result_summary` | 门禁检查   | `repoNameEn ∈ repoNames`（原 `repoNameEn = repoName`） | projectId、sourceBranch→gitBranch、时间区间、mrId、result |
| `task_result_summary`     | 版本级检查 | 同上                                                   | projectId、manifestBranch、时间区间、result、isCompile    |

### 4.3 前端表单模型变更

```ts
// shared.ts formInlineFactory（两页面共享）
{
  projectName: '',
  projectId: '',
  branch: '',
  repoName: '' → repoNames: [] as string[],   // string → string[]（唯一类型变更）
  triggerUser: '',
  startTime: '',
  endTime: '',
  time: [] as string[],
  mrId: '',
}
// IncrementCheckList / StaticCheckList 的 data.formInline 本地副本同步该字段类型，
// 同步时对 repoNames 做防御性拷贝（新建数组引用），保证 isFormInlineChanged 全量比较可感知多选变化
```

### 4.4 数据兼容性

- `repoNames` 为空数组 / 不传：后端回退 `repoName` 单值过滤，与历史调用方（APIG 网关、内部单选调用）行为一致
- 两个过滤字段同时传值时 `repoNames` 优先（新前端只传 `repoNames`，不存在歧义场景）

---

## 5. 性能设计

| 项           | 措施                                                                                                                  | 依据                                    |
| ------------ | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| in 查询      | `repoNameEn` in 条件走既有索引（列表现状已按 repoNameEn 等值查询）；repoNames 数量由项目仓库数自然约束（通常 ≤ 数十） | Mongo in 查询等价于多次索引等值查询合并 |
| 分支并集计算 | `flatMap + Set 去重`，O(Σrepo branches)，在 change 事件内即时完成                                                     | 无感知延迟                              |
| 前端渲染     | `collapse-tags` 折叠标签，避免多选标签撑爆筛选栏引发布局重排                                                          | Element Plus 标准能力                   |
| 查询数据量   | 多选扩大结果集后分页查询行为不变（pageNum/pageSize 服务端分页）                                                       | 列表接口现状即分页                      |

---

## 6. API 接口设计

### 6.1 门禁检查列表（现有接口，参数扩展）

`POST /ci-portal/v1/codecheck/inc/v1/task/result/summary`

```jsonc
// request body（data 节选）
{
  "data": {
    "pageNum": 1,
    "pageSize": 10,
    "projectId": 123,
    "projectName": "xxx",
    "repoNames": ["repoA", "repoB"], // 新增：多选仓库
    "sourceBranch": "",
    "mrId": "",
    "result": "",
    "startTime": "",
    "endTime": "",
  },
}
```

响应结构不变（MultiResponse + 分页列表）。

### 6.2 版本级检查列表（现有接口，参数扩展）

`POST /ci-portal/v1/codecheck/full/task/result/summary`

`repoNames` 同上；分支字段为 `manifestBranch`。响应结构不变。

### 6.3 参数兼容规则

| 请求情形                               | 后端行为                                  |
| -------------------------------------- | ----------------------------------------- |
| `repoNames` 非空数组                   | `repoNameEn ∈ repoNames`                  |
| `repoNames` 空/缺省 且 `repoName` 非空 | `repoNameEn = repoName`（现状，向后兼容） |
| 两者均空                               | 无仓库过滤（现状）                        |
| 两者同时非空                           | `repoNames` 优先                          |

---

## 7. 验证方式

- 后端：`mvn compile` 编译验证；如仓内有单测基建补 Criteria 构建用例，无则以人工自测说明
- 前端：lint + type-check；测试环境自测：多选过滤、清空/重置、单选回归（不传 repoNames 的旧路径）、分支并集与分支筛选联动
