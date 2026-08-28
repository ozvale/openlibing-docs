# Tasks: Apollo/Eureka 迁移至 Nacos

## 进度: 8/10 complete

### 阶段 1：依赖升级 ✅

- [x] Task 1: 升级 `openlibing-common-sdk` 版本
  - 文件: `pom.xml`
  - 变更: `1.0.19.5` → `1.0.20.4`（含两次 commit：3a164cb 升到 1.0.20.1，3c85d3c 升到 1.0.20.4）
  - 验证: `mvn dependency:tree | grep openlibing-common` 显示 1.0.20.4

### 阶段 2：启动类改造 ✅

- [x] Task 2: 移除 Apollo 客户端入口
  - 文件: `src/main/java/com/openlibing/gateway/GatewayApplication.java`
  - 变更:
    - 移除 `import com.ctrip.framework.apollo.spring.annotation.EnableApolloConfig`
    - 移除 `import com.openlibing.common.config.ConfigContextInitializer`
    - 移除 `@EnableApolloConfig` 注解
    - 移除 `.initializers(new ConfigContextInitializer())` 调用
  - 验证: 启动日志中无 Apollo 客户端初始化记录

- [x] Task 3: 关闭 Nacos 本地快照
  - 文件: `src/main/java/com/openlibing/gateway/GatewayApplication.java`
  - 变更:
    - 新增 `import com.alibaba.nacos.client.config.utils.SnapShotSwitch`
    - 在 `GatewayApplication` 类中添加静态初始化块 `static { SnapShotSwitch.setIsSnapShot(false); }`
  - 验证: 启动后 `${user.home}/nacos/` 目录下不生成快照文件

### 阶段 3：环境配置迁移 ✅

- [x] Task 4: 迁移 beta 环境配置到 Nacos
  - 文件: `src/main/resources/application-beta.yaml`
  - 变更: 替换 `apollo.meta` + `apollo.bootstrap` 为 `spring.cloud.nacos.config` + `spring.cloud.nacos.discovery`
  - 关键参数:
    - server-addr: `ee0b6e65-a9e9-4c41-a989-06ae99f0b744.nacos.cn-southwest-2.cse.myhuaweicloud.com:8848`
    - namespace: `openlibing-beta`
    - group: `OPENLIBING`
    - file-extension: `properties`
  - 验证: beta 环境启动后能拉取到 Nacos 中的 `application` 和 `gateway` 配置

- [x] Task 5: 迁移 gamma 环境配置到 Nacos
  - 文件: `src/main/resources/application-gama.yaml`
  - 变更: 同 Task 4，namespace=`openlibing-gamma`，server-addr 与 beta 共用 CSE 实例
  - 验证: gamma 环境启动后能拉取到 Nacos 配置

- [x] Task 6: 迁移 prod 环境配置到 Nacos
  - 文件: `src/main/resources/application-prod.yaml`
  - 变更: 同 Task 4，namespace=`openlibing-prod`，server-addr 使用 prod 独立 CSE 实例 `12a78981-a734-4182-b524-ff63681b905e.nacos.cn-southwest-2.cse.myhuaweicloud.com:8848`
  - 提交: 由 LinYP300 在 PR !182 中独立提交（commit 45b6a64「修改生产配置」）
  - 验证: prod 环境启动后能拉取到 Nacos 配置

### 阶段 4：启动脚本与镜像调整 ✅

- [x] Task 7: 移除启动脚本中的 Apollo JVM 参数
  - 文件: `start.sh`
  - 变更: 移除 `-Dapollo.cache.file.enable=false` 一行
  - 原因: Apollo 客户端已移除，该参数已无意义
  - 验证: `start.sh` 中 grep 不到 `apollo` 关键字

- [x] Task 8: 调整 Dockerfile 清华镜像源 JRE 正则
  - 文件: `Dockerfile`
  - 变更: JRE 文件名匹配正则
    - 旧: `OpenJDK21U-jre_x64_linux_hotspot_\d+\.\d+\.\d+_\d+\.tar\.gz`
    - 新: `OpenJDK21[^"]*\.tar\.gz`
  - 原因: Adoptium 21 版本文件命名格式调整，旧正则无法匹配新版本
  - 验证: Docker 构建能成功下载并解压 JRE 21 包

### 阶段 5：发布与验证 ⏳

- [ ] Task 9: 校验 Nacos 配置项完整性
  - 操作: 对照 Apollo 原 `application` 和 `gateway` 两个 namespace 的所有 key 列表
  - 在 Nacos 控制台 beta/gamma/prod 三个 namespace 下确认 `application` 和 `gateway` 两个 dataId 的 properties 内容已完整迁移
  - 启动后通过 `/actuator/env` 端点对比配置加载情况
  - 完成标准: 所有原 Apollo key 在 Nacos 中都能找到对应配置

- [ ] Task 10: 生产部署验证
  - 操作: 在 prod 发布窗口执行镜像部署
  - 验证项:
    - 服务实例正常注册到 Nacos（namespace=`openlibing-prod`）
    - `/actuator/env` 显示配置来自 Nacos
    - 登录回调、Redis、JWT、第三方鉴权等关键链路功能正常
    - 监控告警无异常
  - 完成标准: prod 环境稳定运行 24 小时无异常

## 关联 PR

- PR !181: `chentao_release_20260827_iter2` → `release_20260827_iter2`
  - 包含 commit: 3a164cb（迁移主体）、3c85d3c（common-sdk 升级）、494ab5b（Dockerfile 调整）
  - 标签: `ai-assisted`、`needs-issue`
- PR !182: `gateway_20260827_iter2` → `release_20260827_iter2`
  - 包含 commit: 45b6a64（prod 配置迁移，作者 LinYP300）

## 备注

- Task 6（prod 配置迁移）由 LinYP300 独立提交，不在 chentao 的 PR !181 中，但属于本次迁移的整体范围。
- Task 9 和 Task 10 为运维侧操作与发布后验证，不在代码仓 commit 中体现。
