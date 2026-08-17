# apollo-eureka-to-nacos — 实现任务

## 进度: 8/8 complete

- [x] Task 1: 根 `pom.xml` 升级 `openlibing-common` 到 1.0.20.0（dependencyManagement）；清理 `apollo-client.version` / `eureka-client.version` 属性及对应 dependencyManagement 声明。
- [x] Task 2: `sbom-web/pom.xml` 移除 `spring-cloud-starter-netflix-eureka-client` 直接依赖及其 exclusions。
- [x] Task 3: `SbomManagerApplication.java` 新增 `static { SnapShotSwitch.setIsSnapShot(false); }` 静态块，import `com.alibaba.nacos.client.config.utils.SnapShotSwitch`（已从 nacos-client-3.0.3.jar 验证包路径）。
- [x] Task 4: `application-dev.properties` 移除 eureka.* 配置项；新增 Nacos config + discovery 配置（namespace=openlibing-beta，server-addr=1.95.74.1:31252，Data ID: sbom, application）。dev 是 HTTP 环境（ssl.enabled=false），不配 secure。
- [x] Task 5: `application-prod.properties` 移除 eureka.* 与 apollo.* 配置项；新增 Nacos config + discovery 配置（namespace=openlibing-prod，server-addr=华为云 CSE Nacos，Data ID: sbom, application，secure=true 注册为 HTTPS）。
- [x] Task 6: `application-gama.properties` 移除 eureka.* 与 apollo.* 配置项；新增 Nacos config + discovery 配置（namespace=openlibing-gamma，server-addr=华为云 CSE Nacos，Data ID: sbom, application，secure=true 注册为 HTTPS）。
- [x] Task 7: `start-openlibing-sbom.sh` 删除 `-Dapollo.cache.file.enable=false` JVM 参数行。
- [x] Task 8: 删除 `ConfigContextInitializer.java`（cache 模块，原从环境变量 TRUST_STORE 加载 SSL trustStore，迁移后不再需要）；`SbomManagerApplication.java` 移除其 import 与 `addInitializers(new ConfigContextInitializer())` 调用。Grep 确认全仓仅此一处引用。

## 适配决策

- `application.properties` 不含 `secure=true`：因 dev 是 HTTP 环境（ssl.enabled=false），secure 下放到 prod/gama 各自声明；`application.properties` 仅删除 apollo 的 `app.id` 配置项。
- 不添加 `spring-cloud-alibaba-dependencies` BOM：openlibing-common 1.0.20.0 已传递管理 nacos 2025.0.0.0 版本。
- 删除 `ConfigContextInitializer`：原用于从环境变量 TRUST_STORE 加载 javax.net.ssl.trustStore，迁移到 Nacos 后由配置中心统一管理，不再需要此类；全仓 Grep 确认仅 SbomManagerApplication 引用，删除安全。
- 配置文件保持 `.properties` 格式：用户确认不迁移到 yaml，沿用 sbom 既有 properties 格式。

## 验证方式

- 编译验证：`mvn clean compile -pl sbom-web -am`（在 openlibing-sbom 根目录执行）→ BUILD SUCCESS（-q 模式 EXIT=0，无 ERROR）
- 配置项检查：Grep 确认 4 个 properties 文件无 `apollo.` / `eureka.` 残留，dev/prod/gama 含 `spring.cloud.nacos.` 完整配置
- 脚本检查：start-openlibing-sbom.sh 无 apollo 参数
- SnapShotSwitch import 验证：编译通过即说明 `com.alibaba.nacos.client.config.utils.SnapShotSwitch` 包路径正确
- ConfigContextInitializer 删除验证：编译通过即说明无残留引用
