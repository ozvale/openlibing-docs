# 蓝区支持查询容器内用户连接 — 实现任务清单

## 关联 PR
openlibing/hidevlab-transport-service#84

## 进度: 4/4 complete（PR #84 已合入）

- [x] Task 1: `base/config.py` 新增 `DOCKER_CONTAINER_CHECK_SCRIPTS` Apollo 配置项，JSON 解析 operation → 脚本名映射
- [x] Task 2: `service/docker_manager.py` 新增 `docker_container_check` 方法：根据 operation 查脚本名 → docker cp 到容器 /root/ → docker exec 执行 → 判断输出是否为 "success"
- [x] Task 3: `transport.py` 新增 `/docker/container/check` POST 路由，参数校验（ip/username/pwd/container_name/share_data_path/operation 全必填），SSH 连接 + 调用 docker_container_check + 异常处理
- [x] Task 4: 安全校验：容器名经 `CommandSecurity.safe_container_name`，路径经 `CommandSecurity.safe_path`，脚本名经 `shlex.quote` 转义
