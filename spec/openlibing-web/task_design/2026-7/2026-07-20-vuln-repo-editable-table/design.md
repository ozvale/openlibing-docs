## Context

当前漏洞公告的仓库输入使用 textarea，用户以逗号分隔输入仓库名。后端接口已升级，返回 `repoStatusList`（对象数组，每行有独立 `id`、`pushStatus`、`repoUrl`、`failReason`），提交接口 `repos` 参数改为 `{repoName: branchName}` object。前端需要将 textarea 改造为可编辑表格以匹配后端新数据结构。

现有项目模式参考：
- `runParameterConfiguration.vue`：始终编辑模式的 el-table（v-model 直接绑定行数据）
- `releaseArtifacts.vue`：非表格的 v-for 可编辑列表
- `publishTable.vue`：配置驱动的展示型表格
- 项目中不存在"点击编辑→切换保存/取消"的行内编辑模式，本次为新模式引入

## Goals / Non-Goals

**Goals:**
- 将仓库 textarea 替换为 6 列可编辑表格（仓库名称、分支名、发布结果、发布地址、失败原因、操作）
- 支持行内编辑（编辑/保存/取消切换），仅允许一行处于编辑态
- 支持新增行（直接进入编辑态）和删除行
- 每行独立状态展示，成功行锁定+发布地址链接，失败行可编辑+展示失败原因
- 轮询刷新时编辑行完全不动，非编辑行按 id 整行覆盖
- 公告级状态和表单禁用逻辑保持不变

**Non-Goals:**
- 不改造公告级状态展示（legend statusIcon、isVulnFormDisabled）
- 不改造 fixedProduct 输入框
- 不改造发布决策等其他模块
- 不引入通用可编辑表格组件（仅本次使用）
- 不使用 retryCount 字段

## Decisions

### 1. 组件拆分：抽取 vulnRepoTable 子组件

**选择**: 抽取为 `detail/components/vulnRepoTable.vue` 子组件

**理由**: 与项目现有模式一致（releaseArtifacts、runParameterConfiguration 都是子组件）。表格内部编辑状态管理（editingIndex、editingBackup）逻辑较复杂，内联到 reviewDetail.vue（已 860 行）会进一步膨胀。子组件通过 props/emits 与父组件交互，职责清晰。

**替代方案**: 内联到 reviewDetail.vue → 拒绝，文件过长且逻辑耦合严重

### 2. 编辑状态管理：editingIndex + editingBackup

**选择**: 使用 `editingIndex: number | null` 和 `editingBackup: VulnRepoItem | null` 管理编辑态

**理由**: 仅允许一行编辑，单索引+单备份足够。进入编辑前深拷贝原始值，取消时恢复。新增行无需备份（空行无原始值）。

**替代方案**: 每行自带 `isEditing` flag → 拒绝，互斥约束需要额外逻辑保证

### 3. 数据流：父组件持有 vulnRepoList，子组件通过 props/emits 交互

**选择**: `vulnRepoList` 定义在 reviewDetail.vue，通过 props 传入子组件，子组件 emit `update:repoList` 通知变化

**理由**: vulnRepoList 需要与 getDetailData 回填逻辑、handlePublishVulnNotice 提交逻辑、轮询合并逻辑交互，这些都在父组件中。子组件只负责 UI 渲染和编辑交互。

**替代方案**: 子组件内部持有数据 → 拒绝，轮询合并和提交都需要父组件访问完整数据

### 4. 轮询合并：编辑行完全不动

**选择**: 轮询刷新时，如果某行是当前编辑行（index === editingIndex），不做任何修改

**理由**: 用户明确要求编辑行完全不动。这简化了合并逻辑，避免编辑中字段被后端数据部分覆盖导致混乱。

**替代方案**: 只更新后端字段保留用户输入 → 拒绝，用户要求完全不动

### 5. 提交参数转换：vulnRepoList → repos object

**选择**: 提交时将 vulnRepoList 转换为 `{repoName: branchName}` object

```typescript
const reposMap = {}
vulnRepoList.forEach(row => {
  if (row.repo) {
    reposMap[row.repo] = row.branch || ''
  }
})
```

**理由**: 后端接口要求 repos 为 key-value object，key=仓库名，value=分支名。repo 名称允许重复，object 中同名 key 会自然合并（后端需处理此情况）。

### 6. 行级状态映射：新增 pushStatusConfig

**选择**: 在 config.ts 中新增 pushStatusConfig，映射 pushStatus 到 statusIcon 所需的状态字符串

```typescript
const pushStatusConfig = ref({
  0: 'can_execute',    // 待发布
  1: 'executing',      // 执行中
  3: 'execute_failed', // 发布失败
  4: 'executing',      // 发布中
  5: 'execute_success', // 发布成功
})
```

**理由**: 与项目现有状态配置模式一致（reviewStatusConfig、virusScanStatusConfig 等）

## Risks / Trade-offs

- **[repo 名称重复]** → repos object 中同名 key 会覆盖，后端需明确处理策略。前端不做校验，按用户要求允许重复。
- **[编辑行与轮询冲突]** → 编辑行完全不动，但如果后端状态变化（如从失败变为执行中），用户可能不知道行已重新发布。需在退出编辑态时检查状态是否已变化。
- **[新增行无 id]** → 新增行 id 为 null，轮询合并时无法与后端数据匹配。提交后后端应返回带 id 的数据，下次轮询可匹配。提交前的新增行在轮询中保留不变。
- **[模式引入]** → 项目首次引入"点击编辑→保存/取消"模式，无现有参考。需确保交互体验与项目风格一致。
