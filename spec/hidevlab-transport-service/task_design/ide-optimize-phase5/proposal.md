# IDE 五期优化 — 镜像上架/下架逻辑修改 & 只读共享目录挂载

## 关联 Issue
openlibing/hidevlab-transport-service#40

## 关联 PR
openlibing/hidevlab-transport-service#61（已合入）

## 需求背景

当前在线开发特性使用过程中存在以下问题：

1. **镜像下架未删除 Harbor 仓库镜像**：`/docker/image/unpublish` 链路仅在远端机器执行 `docker rmi`，完全未调用 Harbor API 删除仓库镜像。删除环境时，对应的物理机和 Harbor 仓没有把自定义镜像删除，普通镜像删除环境时 Harbor 仓也没有把镜像删除。
2. **镜像上架逻辑需优化**：`docker commit` 后未检查镜像层数，层数过多（≥80）时推送到 Harbor 可能失败；commit 失败时未回调上层，导致上层无感知。
3. **缺少共享目录只读挂载**：在线开发容器需要访问共享资源（如公共工具、数据集），但当前仅挂载用户数据目录，无共享只读目录。

## 功能描述

### 功能 1：修改镜像上架（publish）逻辑
- `docker commit` 后检查返回值，失败时立即回调上层（`DOCKER_IMAGES_SAVE_CALLBACK_URL`）并终止流程
- commit 成功后检查镜像层数（`_get_image_layer_count`），达到 80 层时自动执行 squash（`_squash_image`）压缩镜像，避免推送到上限
- 自定义镜像 publish 流程中，不再在本地 `docker rmi` 删除源镜像和 Harbor 镜像（由下架/清理流程统一处理）

### 功能 2：修改镜像下架（unpublish）逻辑
- `docker_stop` 和 `docker_remove` 接口新增 `harbor_server_password` / `harbor_server_path` 参数透传
- `docker_clear` 接收 `clear_params` 字典（替代原位置参数），新增 `harbor_server` / `auth_token` / `new_image_name` / `is_clear_data` 参数
- `docker_clear` 在 `is_clear_data == "true"` 时调用 `_delete_harbor_image_via_curl` 删除 Harbor 仓库镜像
- 新增 `_delete_harbor_image_via_curl` 方法：通过 curl 调用 Harbor v2 API `DELETE /api/v2.0/projects/{project}/repositories/{repo}` 删除仓库镜像
- `async_docker_image_unpublish` 新增 `lab` 参数，完善回调机制：回调包含 `taskId`、`action`、`result`、`msg`（JSON 格式的设备删除详情）、`lab`
- `CommandSecurity.ALLOWED_COMMANDS` 新增 `curl` 命令白名单

### 功能 3：增加只读方式挂载共享目录
- `docker_start` 中，当 `is_docker_mount == "true"` 时，在原有 `-v user_data:/workspace/user_data` 基础上，新增 `-v share_data/shared_assets:/workspace/shared_assets:ro` 只读挂载
- 共享目录路径 `share_data_path` 已有安全验证（`CommandSecurity.validate_path`）

## 验收标准

- [ ] 镜像上架：commit 失败时回调上层，上层可感知失败原因
- [ ] 镜像上架：层数 ≥ 80 时自动 squash，推送不再因层数上限失败
- [ ] 镜像下架：`docker_stop` / `docker_remove` / `docker_clear` 流程中能删除 Harbor 仓库镜像
- [ ] 镜像下架：unpublish 回调包含完整设备删除详情和 lab 信息
- [ ] 共享目录：容器启动时 `/workspace/shared_assets` 以只读方式挂载，用户可读取但不可写入
- [ ] 向后兼容：不传 Harbor 参数时行为不变；不挂载共享目录时不影响原有逻辑
