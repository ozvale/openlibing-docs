# install-agent — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/hidevlab-transport-service/issues/38
- 业务 PR: https://gitcode.com/openlibing/hidevlab-transport-service/merge_requests/77
- docs PR: <待创建后补充>

## 交付历程

- commit `e311070`: fix(clab-agent): auto-install tar on pxe-fresh hosts and harden retries
- commit `bcc002c`: refactor(clab-agent): move pkg/url to Apollo and split install pipeline
- commit `17db3f1`: refactor(clab-agent): inline package name resolution into download helper
- commit `811358a`: style: 功能拆分（拆分 `_start_agent` 与 `_wait_for_service_active`）
- commit `c720fa8`: Merge remote-tracking branch 'origin/common_alpha_202607' into whh_

## 用户自测反馈

- **问题 1**：PXE 刚装完系统的机器报 `tar: command not found`
  - 修复 commit `e311070`：检测到 tar 不存在时按 OS（ubuntu → apt、openeuler/centos → dnf）自动安装，并给 wget / tar 安装 / 服务状态检查加重试
- **问题 2**：代码评审指出包 URL/包名硬编码
  - 修复 commit `bcc002c`：迁移到 Apollo 配置中心（`CLABAGENT_PACK_SOURCE_URL` / `CLABAGENT_X86_PACK_NAME` / `CLABAGENT_ARM64_PACK_NAME`），并拆分 `install_agent` 为子函数
- **问题 3**：`install_agent` 函数过长
  - 修复 commit `811358a`：拆出 `_start_agent` 与通用轮询工具 `_wait_for_service_active(service_name)`
- **问题 4**：真机自测返回 `failed to download agent`，下载 URL 含 `%s` 占位符
  - 根因：服务未重启，未读到 Apollo 新发布的配置值；重启服务后正常
- **问题 5**：目标机器 `10.x.x.49` 安装请求 120s 后 gunicorn worker 超时
  - 根因：机器已被释放，SSH 不通；非代码问题
- **最终结果**：`{"code":200,"data":"","msg":"install agent in 174.14.2.128 successfully"}`

## 最终验证

- 真机 x86_64 自测：`install agent successfully` ✓
- 真机 aarch64 自测：`host arch is aarch64` 路径走通 ✓
- gunicorn `timeout = 120` 覆盖正常机器的安装全流程；慢/异常机器需排查 SSH 连通性，不是代码问题

## 设计偏差与取舍

- **同步接口 vs 异步任务化**：本期保持同步。clabAgent 安装是低频内部操作，调用方少；异步化引入 task_id 轮询复杂度，收益不匹配。若后续调用频率上升或安装耗时显著增长，再考虑异步化（可参考 `service/docker_manager.py` 的 `async_install_agent` 模式）。
- **`ast.literal_eval` 解析 body**：沿用项目既有模式（`set_agent_interval` 等端点同样使用），未改为标准 JSON。调用方需传 Python 字面量格式，非标准 JSON。
- **未加配置值格式校验**：曾考虑检测 `CLABAGENT_PACK_SOURCE_URL` 是否误带 `%s` 占位符，最终未加——Apollo 配置值由运维管理，加代码层防御属于过度设计。

## 可复用经验

→ 同步到 `ai_memory.md`：

1. **Apollo 配置变更后需重启服务才生效**：本仓的 Apollo 客户端对部分配置项不热更新，新增/修改配置值后必须重启服务，否则运行时读到旧值（可能是 `None`），表现为"配置明明改了但代码不生效"。
2. **gunicorn sync worker 超时是长耗时接口的隐形坑**：`gunicorn_config.py` 的 `timeout` 是硬上限，worker 超时会被 master SIGKILL，日志只记 `Error handling request <path>`，不带 traceback。长耗时操作（远程安装、大文件下载）要么调大 timeout，要么异步化。

## 归档日期

2026-07-24
