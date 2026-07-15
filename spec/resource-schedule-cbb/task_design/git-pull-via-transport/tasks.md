# git-pull-via-transport — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 新增 `GitPullRequest` 请求 DTO（容器连接信息 + repo 列表）
- [ ] Task 2: 新增 `GitRepoCallbackSPI` 接口（`executeGitPull(GitPullRequest)`）
- [ ] Task 3: `AutoDeployFacade.buildGitRepos()` 弃用 playbook git_repos 逻辑（或加配置开关）
- [ ] Task 4: `ContainerDeployScheduler.handleAllDeploySuccess()` 后置钩子：检查 `NodeSpec.repos`，为各容器组装 `GitPullRequest`，调用 SPI
- [ ] Task 5: 异常处理：SPI 调用失败仅 warn 日志，不阻断 RUNNING 状态
- [ ] Task 6: 补充单元测试（SPI 调用 + 空 repos 跳过 + 失败容错）
