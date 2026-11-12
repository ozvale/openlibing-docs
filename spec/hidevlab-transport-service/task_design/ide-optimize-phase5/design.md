# IDE 五期优化 — 技术设计方案

## 关联 Issue
openlibing/hidevlab-transport-service#40

## 架构决策

### AD-1：Harbor 镜像删除方式 — curl 而非 Python SDK
- **决策**：通过 SSH 到远端机器执行 `curl -X DELETE` 调用 Harbor v2 API
- **原因**：transport-service 运行在控制节点，Harbor API 仅在内网可达，需通过已建立 SSH 连接的远端机器代理调用。引入 Python Harbor SDK 增加依赖且无网络直连优势。
- **风险**：curl 命令含认证信息，需确保不泄露到日志。通过 `log_command=False` 和 `shlex.quote` 转义缓解。

### AD-2：docker_clear 参数改为字典
- **决策**：`docker_clear(self, container_name, user_id, task_id, ...)` 改为 `docker_clear(self, clear_params)` 字典传参
- **原因**：新增 `harbor_server` / `auth_token` / `new_image_name` / `is_clear_data` 4 个参数，继续用位置参数会导致签名过长且调用方需全部对齐。字典传参更灵活，新增参数不影响已有调用方。
- **影响**：`transport.py` 中 `docker_stop` / `docker_remove` 调用 `docker_clear` 的地方需同步改为字典。

### AD-3：镜像层数检查与 squash
- **决策**：commit 成功后通过 `docker history -q | wc -l` 获取层数，≥80 时调用 `_squash_image` 压缩
- **原因**：Docker 镜像层数上限为 127，实际在 80+ 层时推送 Harbor 已可能出现超时或失败。squash 可将多层合并为一层，减少推送体积和时间。
- **风险**：squash 本身耗时，可能增加 publish 总时长。但相比推送失败重试，整体更优。

### AD-4：共享目录只读挂载
- **决策**：在 `docker_start` 的 `-v` 参数中追加 `:ro` 标志
- **原因**：共享资源（工具、数据集）应只读，防止用户误修改影响其他用户。Docker 原生支持 `:ro`，无需额外配置。

## 影响范围

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `service/docker_manager.py` | 修改 | docker_clear 签名重构、Harbor 删除、commit 检查与 squash、共享目录挂载 |
| `transport.py` | 修改 | docker_stop/docker_remove 透传 Harbor 参数、unpublish 新增 lab 参数 |
| `utils/command_security.py` | 修改 | ALLOWED_COMMANDS 新增 `curl` |

## 风险缓解

| 风险 | 缓解措施 |
|------|----------|
| Harbor 凭证泄露 | curl 命令用 `log_command=False`，参数用 `shlex.quote` 转义 |
| curl 命令注入 | `CommandSecurity` 白名单已新增 `curl`，路径/镜像名均有安全校验 |
| squash 失败 | squash 失败不阻断流程，仅记 warning 日志，继续推送原镜像 |
| docker_clear 签名变更 | 所有调用方已同步改为字典传参，无遗漏 |
