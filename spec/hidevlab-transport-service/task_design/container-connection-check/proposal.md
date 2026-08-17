# 蓝区支持查询容器内用户连接 — 确保容器无人使用

## 关联 PR
openlibing/hidevlab-transport-service#84

## 需求背景

在在线开发（IDE）场景中，蓝区（调度/控制面）需要判断容器是否正在被用户使用，以决定是否可以安全回收、重启或迁移容器。当前缺少一种可靠的机制来检测容器内是否存在活跃的用户连接。

黄区（前端/业务面）调用 transport-service 接口，在容器内执行检测脚本，检查以下三类连接是否存在：
1. SSH 连接
2. CodeServer（VSCode Server）连接
3. 本地 IDE 连接

如果存在任一活跃连接，则表示容器正在被用户使用，不可回收。

## 功能描述

### 新增接口 `/docker/container/check`

- **方法**：POST
- **入参**：
  - `ip`：远端机器 IP
  - `username`：SSH 用户名
  - `password`：SSH 密码
  - `container_name`：容器名称
  - `share_data_path`：共享数据路径（含检测脚本）
  - `operation`：检测类型（对应 Apollo 配置中的脚本名映射）
- **返回**：
  - `success` / `data: "success"`：容器内无人使用（脚本返回 "success"）
  - `failed` / `data: "failed"`：容器有人使用或执行失败

### 新增 Apollo 配置

- `DOCKER_CONTAINER_CHECK_SCRIPTS`：JSON 格式的 operation → 脚本名映射，默认 `{}`

### 新增方法 `DockerManager.docker_container_check`

1. 根据 `operation` 从 `DOCKER_CONTAINER_CHECK_SCRIPTS` 获取脚本名
2. `docker cp` 将脚本拷贝到容器 `/root/`
3. `docker exec` 执行脚本，输出为 `"success"` 表示成功（无人使用）

## 验收标准

- [ ] `/docker/container/check` 接口正常响应，参数校验完整
- [ ] 支持 SSH、CodeServer、本地 IDE 三种连接检测（通过 Apollo 配置映射脚本名）
- [ ] 脚本返回 "success" 时接口返回成功，表示容器无人使用
- [ ] 脚本返回非 "success" 时接口返回失败，表示容器有人使用
- [ ] 后端异常（SSH 连接失败、docker cp/exec 失败）返回 500 错误
- [ ] 安全：容器名和路径均经 `CommandSecurity` 校验
- [ ] 已通过 codecheck 和 CI 流水线
