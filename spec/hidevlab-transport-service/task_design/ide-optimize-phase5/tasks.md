# IDE 五期优化 — 实现任务清单

## 关联 Issue
openlibing/hidevlab-transport-service#40

## 进度: 7/7 complete（PR #61 已合入）

- [x] Task 1: `service/docker_manager.py` `docker_commit` 后检查返回值，失败时回调上层并终止
- [x] Task 2: `service/docker_manager.py` commit 成功后检查镜像层数，≥80 层自动 squash
- [x] Task 3: `service/docker_manager.py` 自定义镜像 publish 流程中移除本地 `docker rmi` 和 Harbor 删除（由下架流程统一处理）
- [x] Task 4: `service/docker_manager.py` `docker_clear` 改为字典传参，新增 `harbor_server` / `auth_token` / `new_image_name` / `is_clear_data` 参数，在 `is_clear_data == "true"` 时调用 `_delete_harbor_image_via_curl`
- [x] Task 5: `service/docker_manager.py` 新增 `_delete_harbor_image_via_curl` 方法，通过 curl 调用 Harbor v2 API 删除仓库镜像
- [x] Task 6: `transport.py` `docker_stop` / `docker_remove` 透传 `harbor_server_password` / `harbor_server_path`；`docker_image_unpublish` 新增 `lab` 参数，完善回调机制
- [x] Task 7: `service/docker_manager.py` `docker_start` 新增共享目录只读挂载 `-v share_data/shared_assets:/workspace/shared_assets:ro`；`utils/command_security.py` 新增 `curl` 白名单
