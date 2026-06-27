# PR信息获取数据源切换

## 需求背景

PR信息获取方式从 xxl-job 定时任务切换为 dolphinscheduler 任务 + seatunnel 采集。本次变更涉及存储信息表的修改以及数据清理逻辑的调整，同时 openlibing-ops 后端代码需要适配新的数据表结构。

## 功能描述

### 数据采集链路变更

| 环节 | 旧方案 | 新方案 |
|------|--------|--------|
| 调度框架 | xxl-job 定时任务 | dolphinscheduler |
| 数据采集 | xxl-job 内直接调用 API | seatunnel 采集 |
| 数据清洗 | xxl-job 内处理 | dolphinscheduler 任务编排 |

### 涉及数据表

#### 采集层 (raw) — seatunnel 直接写入
- `raw_pull_request_gitcode` — GitCode PR 原始数据
- `raw_pull_request_gitee` — Gitee PR 原始数据
- `raw_pull_request_github` — GitHub PR 原始数据
- `raw_pull_request_files_gitee` — Gitee PR 文件变更原始数据
- `raw_workflow_runs_github` — GitHub workflow 运行原始数据
- `raw_pull_request_commit_github` — GitHub PR commit 原始数据

#### 标准化层 (sdi) — dolphinscheduler 清洗任务
- `sdi_rd_efc_pr_info_raw_gitcode` — GitCode PR 标准化信息
- `sdi_rd_efc_pr_info_raw_gitee` — Gitee PR 标准化信息
- `sdi_rd_efc_pr_files_relation_clean_gitee` — Gitee PR 文件关联清洗
- `sdi_rd_efc_pr_info_raw_github` — GitHub PR 标准化信息
- `sdi_rd_efc_pr_label_relation_clean_github` — GitHub PR 标签关联清洗
- `sdi_rd_efc_workflow_run_raw_github` — GitHub workflow 运行标准化
- `sdi_rd_efc_pr_commit_relation_raw_github` — GitHub PR commit 关联标准化
- `sdi_rd_efc_pipeline_run_pr_relation_codearts`（**新增**）— CodeArts 流水线与 PR 关联关系

#### 明细层 (dwi)
- `dwi_rd_efc_pr_info_sum` — PR 信息汇总
- `dwi_rd_efc_pr_workflow_run`（**新增**）— PR workflow 运行记录

#### 汇总层 (dm)
- `dm_rd_efc_pr_dim_pipeline_run_day` — PR 维度流水线运行日表
- `dm_rd_efc_pr_sum_pipeline_statistics_day` — PR 汇总流水线统计日表
- `dm_rd_efc_repo_dim_pipeline_run_day` — 仓库维度流水线运行日表

### openlibing-ops 后端代码变更

1. 新增 `dwi_rd_efc_pr_workflow_run` 和 `sdi_rd_efc_pipeline_run_pr_relation_codearts` 两张表的 MyBatis-Plus Entity/Mapper/Service
2. Pipeline 查询接口参数从 `prId` 切换为 `repoUrl + number`
3. PipelineHandleImpl PR 绑定关系查询切换到新表 `sdi_rd_efc_pipeline_run_pr_relation_codearts`
4. 旧 workflow 实现重命名为 `workflow_old`，基于新表 `dwi_rd_efc_pr_workflow_run` 实现新的 `workflow`

## 验收标准

- [ ] 新增 Entity/Mapper/Service 编译通过
- [ ] Pipeline 接口参数从 prId 切换为 repoUrl + number
- [ ] PipelineHandleImpl PR 绑定查询切换到新表
- [ ] WorkflowHandleImpl type 改为 workflow_old
- [ ] WorkflowNewHandleImpl 基于新表实现，type 为 workflow
- [ ] 测试用例同步更新

## 影响范围

- 数据采集链路：xxl-job → dolphinscheduler + seatunnel
- 数据清洗逻辑：随表结构调整
- openlibing-ops 后端：PipelineController、PipelineHandle 接口及实现类、新增 Entity/Mapper/Service
