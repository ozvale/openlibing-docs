# install-agent

## 需求背景

业务 Issue [#38](https://gitcode.com/openlibing/hidevlab-transport-service/issues/38) 反馈 DevEnv 规格机上 ModelAgent 本地 IDE 起不来，根因是 ssh 写不进容器、连接失败。为了在 PXE 装机后能在目标主机上快速装好 `clabAgent`（负责容器内 Agent 的注册与生命周期对接），需要 transport 服务提供一个内部接口，远程驱动安装流程。

## 功能描述

- 新增内部接口 `POST /install/agent`，由上层服务（非对外暴露）调用。
- 接口入参：`host_ip` / `user_name` / `user_pwd` / `host_port` / `server_id`。
- 接口通过 SSH 连接目标主机，依次：识别架构 → 下载安装包 → 确保 tar 可用 → 解压 → 写 `id_ip.txt` → 启动 clabagent → 轮询校验服务状态 → 清理临时包。
- 安装包 URL 与包名通过 Apollo 配置中心管理，避免硬编码。
- 适配 PXE 刚装完系统的机器（可能缺 tar）：自动按 OS 类型用 apt / dnf 安装 tar。

不做：
- 不对外暴露接口，不做鉴权。
- 不做异步任务化（本期保持同步，超时由 gunicorn timeout 承载）。

## 验收标准

- [x] `POST /install/agent` 能在 x86_64 / aarch64 主机上成功安装并启动 clabagent。
- [x] PXE 刚装完系统的机器（无 tar）能自动安装 tar 后继续解压。
- [x] 安装包 URL / 包名通过 Apollo 配置，不再硬编码。
- [x] 返回结构：`{"code":200,"data":"","msg":"install agent in <ip> successfully"}`。
- [x] 真机自测通过：`install agent in 174.14.2.128 successfully`。

## 影响范围

- 业务仓：`hidevlab-transport-service`
- 修改文件：
  - `service/clab_agent.py`（新增 `install_agent` 及子函数）
  - `transport.py`（新增 `/install/agent` 路由）
  - `base/config.py`（新增 3 项 Apollo 配置）
- 运行时依赖：Apollo `agent` 命名空间下新增 3 个配置项。
