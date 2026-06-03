# Nightly 流水线失败 PR 自动二分定位 — 实现任务

## 进度: 0/8 complete

### 阶段一：接口参数扩展

- [ ] Task 1: `/run` 接口 DTO 增加 `choose_stages`、`choose_jobs` 参数（List\<String\> 类型，可选）
- [ ] Task 2: `/run` 接口 DTO 增加 `build_type` 参数，支持 `"commitId"` 类型
- [ ] Task 3: `/run` 接口 DTO 增加 `commit_id` 参数（String 类型，可选）
- [ ] Task 4: 流水线执行服务适配 `choose_stages`、`choose_jobs` 参数，实现部分任务执行

### 阶段二：二分定位服务

- [ ] Task 5: 新增 `PipelineBisectService` 服务类，实现二分定位核心逻辑
  - 查询最近一次成功运行记录（调用 `/pipeline-run/list`）
  - 获取 PR 列表（调用 GitCode API）
  - 二分迭代逻辑
  - 结果收敛判断

- [ ] Task 6: 新增 GitCode API 客户端，获取两个 commit 之间合入的 PR 列表
  - 接口：`GET /repos/{owner}/{repo}/compare/{base}...{head}`
  - 或使用 PR 列表接口按时间范围筛选

- [ ] Task 7: 新增二分定位触发接口 `POST /pipeline/bisect`
  - 入参：流水线 ID、失败运行记录 ID
  - 出参：二分任务 ID（用于查询进度）
  - 异步执行二分分析

- [ ] Task 8: 新增二分定位进度查询接口 `GET /pipeline/bisect/{taskId}`
  - 返回当前进度、正在验证的 PR、已验证次数、预估剩余次数
  - 完成后返回最先引入问题的 PR 信息

### 阶段三：前端集成（可选，视前端排期）

- [ ] Task 9: 流水线详情页新增"二分定位"按钮（仅失败状态显示）
- [ ] Task 10: 二分分析进度弹窗组件
- [ ] Task 11: 分析结果展示组件（问题 PR、commit 信息、链接跳转）

## 技术要点

### GitCode API 获取 PR 列表

方案一：使用 compare 接口
```
GET /repos/{owner}/{repo}/compare/{base_commit}...{head_commit}
响应包含两个 commit 之间的 commits 列表，从中提取 PR 信息
```

方案二：使用 PR 列表接口
```
GET /repos/{owner}/{repo}/pulls
  ?state=merged
  &base=master
  &since={success_commit_date}
  &until={failure_commit_date}
```

### 二分终止条件

1. PR 列表只剩 1 个：该 PR 即为问题 PR
2. 连续多次验证结果一致：可能存在多个问题 PR，取最早的一个
3. 达到最大迭代次数：返回当前范围内最可能的 PR

### 只运行失败任务的实现

调用 `/detail` 获取流水线详情：
```json
{
  "jobs": [
    { "identifier": "job-1", "status": "SUCCESS" },
    { "identifier": "job-2", "status": "FAILED" },
    { "identifier": "job-3", "status": "FAILED" }
  ]
}
```

提取失败任务的 identifier，调用 `/run` 时传入：
```json
{
  "choose_jobs": ["job-2", "job-3"],
  "build_type": "commitId",
  "commit_id": "target_commit"
}
```
