# git-pull-via-transport

## 需求背景

当前代码在 `AutoDeployFacade.buildGitRepos()` 中将 `NodeSpec.repos` 转换为 `git_repos` 参数，塞入 `multi_container_overrides_json` 的 `docker_container.git_repos`，由 playbook 在容器拉起阶段（phase-c-git-repos.sh.j2）执行 git clone。这种方案有两个问题：

1. **耦合到拉起流程**：git clone 发生在容器首次创建时，后续无法增量更新代码
2. **不灵活**：受限于 playbook 实现，不易支持认证仓库、稀疏检出等场景

新方案将 git 拉取操作从构建阶段解耦到**部署完成后**，通过 transport-service 登录容器执行 git pull/clone，支持容器运行后按需拉取代码。

## 功能描述

**做**：
1. **弃用** `AutoDeployFacade.buildGitRepos()` 中向 playbook 传递 `git_repos` 的逻辑（不再让 playbook 处理 git clone）
2. **新增 `GitRepoCallbackSPI`**：宿主系统实现此 SPI，调用 transport-service 登录容器执行 git pull/clone
3. **后置钩子**：`ContainerDeployScheduler.handleAllDeploySuccess()` 中，部署全部成功后检查 `NodeSpec.repos`，非空则通过 SPI 为各容器执行 git pull
4. **错误处理**：git pull 失败仅记录 warn 日志，不阻塞 task RUNNING 状态

**不做**：
- 不改动现有 `EnvCreateRequest` / `NodeSpec` / `RepoSpec` 模型（复用 `NodeSpec.repos`）
- 不处理 BMS 场景（git pull 仅容器场景有意义）
- 不替代 transport-service 侧的认证/加密机制

## 验收标准

- [ ] `buildGitRepos` 不再向 `docker_container` 写入 `git_repos`（或可通过配置开关控制）
- [ ] `GitRepoCallbackSPI` 接口定义完成，含 `executeGitPull(GitPullRequest)` 方法
- [ ] 容器部署成功后，若 `NodeSpec.repos` 非空，调用 `GitRepoCallbackSPI` 为每个容器执行 git pull
- [ ] git pull 失败时 task 仍为 RUNNING，仅记 warn 日志
- [ ] 单元测试覆盖：SPI 调用链路、空 repos 跳过、失败不影响任务状态
- [ ] PMD/SpotBugs 通过，圈复杂度 ≤ 20，单函数 ≤ 50 行

## 影响范围

- `resource-schedule-cbb`：
  - 新增 `spi/GitRepoCallbackSPI.java`
  - 新增 `spi/request/GitPullRequest.java`
  - 修改 `scheduler/ContainerDeployScheduler.java`（`handleAllDeploySuccess` 后置钩子）
  - 修改 `deploy/AutoDeployFacade.java`（弃用 `buildGitRepos`）
  - 补充单元测试
