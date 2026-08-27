# dockerfile 修改与过滤器恢复

## 需求背景

- 业务 Issue：[#23](https://gitcode.com/openlibing/openlibing-simulation/issues/23)（dockerfile修改, 过滤器恢复）
- Dockerfile 构建时从清华 Adoptium 镜像下载 JRE 的 grep 正则过严，无法匹配镜像新发布的文件名格式，导致镜像构建失败；需放宽匹配规则。
- 内部共享密钥认证过滤器（安全整改产物）需要以 `InternalSimulationAuthFilter` 名称生效，替换原 `InternalAuthFilter`。

## 功能描述

做什么：
- Dockerfile：将 Adoptium JRE 下载的正则由精确匹配放宽为 `OpenJDK21[^"]*\.tar\.gz`，兼容镜像新文件名格式。
- 过滤器：新增内部共享密钥认证过滤器并重命名为 `InternalSimulationAuthFilter`（`@Order(2)`，校验 `X-Openlibing-Internal-Token` 与 `X-Openlibing-User` 头，fail-closed）。
- 构建修复：修复 maven-enforcer `RequireUpperBoundDeps` 依赖上界冲突（reactor-core 3.7.19 / spring-data-commons 3.5.13）；修复 mongodb 驱动版本不一致导致的 gamma 启动失败（mongodb-driver-reactivestreams 对齐 5.5.2、log4j-core 对齐 2.24.3）。

不做什么：
- 不新增业务功能，不调整过滤器认证逻辑。

## 验收标准

- [ ] 分支 `ligao_verfy_ssh` 上相关提交已就位（264d1ce / 4b1653d / 0b0ee7c / 2b0a0f4 / a6ed0a8）
- [ ] Dockerfile 可正常下载并安装 Adoptium JRE
- [ ] `mvn validate` 通过 enforcer 校验
- [ ] gamma 环境重新构建部署后启动成功（不再出现 mongodb NoSuchMethodError）
- [ ] 业务 PR 合入 master，关联 issue #23

## 影响范围

- 仓：openlibing-simulation
- 文件：`Dockerfile`、`pom.xml`、`src/main/java/com/openlibing/simulation/filter/InternalSimulationAuthFilter.java`（重命名自 InternalAuthFilter）、`QemuTaskServiceImpl.java`（引用调整）
