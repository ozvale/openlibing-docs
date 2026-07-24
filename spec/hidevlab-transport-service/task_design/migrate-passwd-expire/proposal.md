# migrate-passwd-expire

## 需求背景

`/passwd/expire` 接口当前实现在 `hidevlab-infra-manager-service`，用于 SSH 登录目标机后执行 `chage -d 0 <user>` 强制下次登录修改密码。服务对象同时包括虚拟机和裸金属。

但 infra-manager 部署机（PXE 服务器）无法直连目标机的 OS IP：

- PXE 装机完成后，目标机切到业务网，infra-manager 部署机所在网段不通
- 单独调用 `/passwd/expire` 必然 SSH 超时（`[Errno 110] Connection timed out`，约 130s 后失败）
- 之前在 `/configure_custom_network` 内能复用 PXE IP 建立的 SSH 连接侥幸成功，单独调用必失败

transport-service 部署在目标 OS 本地，可直连本机 IP / 同网段 IP，不存在此问题。因此将该接口迁移到 transport-service。

## 功能描述

### 做什么

1. transport-service 新增 `POST /passwd/expire` 接口，入参契约沿用原接口
2. 新增 service 层实现：SSH 登录后执行 `chage -d 0 <user>`，ubuntu 走 `sudo -S`，其他系统直接执行
3. 接口带 `auth_filter` 鉴权（与 transport 其他业务接口一致）
4. infra-manager 同步移除 `/passwd/expire` 路由、`set_passwd_expire` 函数、相关 import

### 不做什么

- 不改变入参/响应契约
- 不改变 chage 命令的执行方式
- 不调整 infra-manager 其他接口

## 验收标准

- [ ] transport-service `POST /passwd/expire` 可成功对 ubuntu/centos/openeuler 强制下次登录改密
- [ ] 接口未带 token 或 token 无效时返回 401
- [ ] infra-manager 不再暴露 `/passwd/expire` 接口
- [ ] `set_passwd_expire` 函数从 infra-manager 移除，无残留引用
- [ ] 调用方仅切换 host:port 即可完成迁移（路径、入参、响应不变）

## 影响范围

- 跨仓：
  - `hidevlab-transport-service`：新增接口 + service 文件
  - `hidevlab-infra-manager-service`：移除接口 + 函数 + import
- 调用方：所有调用 `/passwd/expire` 的上游服务需将 host:port 从 infra-manager 切换到 transport-service
- 部署：两服务需同步发版，建议先发 transport-service 再发 infra-manager（避免调用方断流）

## 关联 Issue

- openlibing/hidevlab-transport-service#61
