# PR看板新增E2E配置弹窗与指标字段 — 实现任务

## 进度: 0/5 complete

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/api/dashboard/open-source-project.ts` | 修改 | 扩展 `batchConfigBranch` 支持 `targetMinutes`；更新 `RepoItem` 接口 |
| `src/views/dashboard/open-source-project/scan-branch-config.vue` | 修改 | 弹窗内容改为 2 个页签，新增 E2E 达标时长配置页签 |
| `src/views/dashboard/open-source-project/sub-table.vue` | 修改 | 按钮名称改为"配置" |
| `src/views/dashboard/open-source-project/columns/pr-columns.ts` | 修改 | `prPipelineColumnData` + `prInfoDetailColumn` 新增字段 |

### 任务清单

- [ ] Task 1: **更新 API 接口** — 扩展 `batchConfigBranch` 支持 `targetMinutes`；更新 `RepoItem` 接口加 `targetMinutes` 字段
- [ ] Task 2: **修改 `scan-branch-config.vue`** — 添加 `el-tabs` 分页签；Tab1 原内容不变；Tab2 新增 E2E 配置表格；提交时携带 `targetMinutes`
- [ ] Task 3: **修改 `sub-table.vue`** — 按钮名称"代码量扫描分支配置"改为"配置"
- [ ] Task 4: **修改 `prPipelineColumnData`** — 新增 PR E2E 时长组(f)、流水线启动时长组(f)、合入时长组(f) + E2E达标率
- [ ] Task 5: **修改 `prInfoDetailColumn`** — 新增 prE2eTime、pipelineStartupTime、mergeLeadTime

### 验证方式
- 构建通过（`npm run build` 或 IDE 类型检查）
- 按钮名称改为"配置"
- 弹窗含 2 个页签
- 新增表格字段位置正确、带单位