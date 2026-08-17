# 蓝区支持查询容器内用户连接 — 技术设计方案

## 关联 PR
openlibing/hidevlab-transport-service#84

## 架构决策

### AD-1：脚本检测方式 — docker cp + docker exec
- **决策**：将检测脚本通过 `docker cp` 拷贝到容器 `/root/`，再通过 `docker exec` 执行
- **原因**：
  - 容器内环境与宿主不同，无法直接在宿主执行容器内命令
  - `docker cp` + `docker exec` 是最通用的方式，无需容器预装 agent
  - 检测脚本由运维维护在共享目录，更新时无需改代码
- **风险**：`docker cp` 可能静默失败（命令本身成功但文件未拷贝），通过后续 `docker exec` 执行失败兜底

### AD-2：operation → 脚本名映射 — Apollo 配置
- **决策**：通过 `DOCKER_CONTAINER_CHECK_SCRIPTS` Apollo 配置项，以 JSON 格式映射 operation 类型到脚本名
- **原因**：
  - 新增检测类型（如 VNC 连接）无需改代码发版，只需改配置
  - 默认 `{}`，未配置的 operation 返回 `Unsupported operation`
- **风险**：配置错误时接口返回 500，需运维配合校验

### AD-3：安全校验 — CommandSecurity 复用
- **决策**：容器名通过 `CommandSecurity.safe_container_name`，路径通过 `CommandSecurity.safe_path`
- **原因**：与项目其他 docker 操作保持一致的安全策略，防止命令注入

## 影响范围

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `base/config.py` | 修改 | 新增 `DOCKER_CONTAINER_CHECK_SCRIPTS` 配置项 |
| `service/docker_manager.py` | 修改 | 新增 `docker_container_check` 方法 |
| `transport.py` | 修改 | 新增 `/docker/container/check` 接口路由 |

## 接口契约

### POST /docker/container/check

**请求体**：
```json
{
  "ip": "10.0.0.1",
  "username": "root",
  "password": "xxx",
  "container_name": "ide-container-xxx",
  "share_data_path": "/mnt/share_data",
  "operation": "ssh_check"
}
```

**成功响应**（容器无人使用）：
```json
{"code": 200, "msg": "", "data": "success"}
```

**失败响应**（容器有人使用或执行失败）：
```json
{"code": 500, "msg": "<脚本输出或错误信息>", "data": "failed"}
```

**Apollo 配置示例**：
```json
{
  "ssh_check": "check_ssh_connections.sh",
  "codeserver_check": "check_codeserver_connections.sh",
  "ide_check": "check_ide_connections.sh"
}
```

## 风险缓解

| 风险 | 缓解措施 |
|------|----------|
| docker cp 静默失败 | 后续 docker exec 执行失败兜底，返回明确错误信息 |
| 脚本不存在 | Apollo 配置校验 + operation 未配置时返回 Unsupported operation |
| SSH 连接超时 | 已有 `manager.connect` 超时机制 |
| 命令注入 | CommandSecurity 校验容器名和路径，shlex.quote 转义脚本名 |
