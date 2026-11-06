# 技术方案：安全 Issue 集中整改

## 1. #170 导出回执异常文案收敛

[SbomExportServiceImpl.processExport](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-sbom/sbom-web/src/main/java/org/opensourceway/sbom/service/sbom/impl/SbomExportServiceImpl.java) catch 链按仓内异常收敛约定分层：

- `SbomRuntimeException` → 保留 `e.getMessage()`（业务语义文案，约定允许对外暴露）
- `IOException` → 固定文案「导出文件生成失败，请重试」
- 其余 `RuntimeException` → 固定文案「导出文件处理失败，请重试」（不再透传原始异常，如 JDBC URL 等内网信息）

配套测试：`SbomExportServiceImplTest` 新增 2 个用例（未知异常不透传含内网信息的 message；业务异常文案保留）。
服务端日志仍打印完整堆栈（troubleshooting 不受影响），仅收敛外部回执。

## 2. #158 出站解码缓冲统一

`LicenseClientImpl.createWebClientForPlainText` 删除硬编码 `1024 * 1024 * 1024`，改为 `(int) DataSize.parse(maxInMemorySize).toBytes()` 复用 `spring.codec.max-in-memory-size`。全局值固定 **256MB**（`application.properties` 显式配置），系经评估的业务决策：SBOM 数据体量大，10MB 级上限不适用。本项消除的是代码中最后一处**游离于配置治理之外的 1GB 级上限**；残余 DoS 面（大响应驻留堆内存、出站下载无并发限流）不因本项闭环，大文件下载流式化、出站并发限流、Spring 解码器 shim 移除确认已登记为待办（见 tasks.md）。GZIP 解压的双上限（min(256MB, 压缩体×100)）此前已收敛。

## 3. #90 依赖治理（漏洞依赖整改）

- 删除死依赖 `sshd-core`（root pom 属性 + dependencyManagement + sbom-web 直依赖，连带消除 5 个 SSHD CVE）。
- `openlibing-common` BOM `1.0.21.2 → 1.0.21.3` 统一治理；显式升级 `httpcore5/httpcore5-h2 5.4.3`（CVE-2026-54399/54428）、`joda-time 2.14.3`。
- Log4j 版本治理移交 Spring Boot BOM（删除本地硬编码属性与 dependencyManagement 条目）。
- 扫描清单逐项定性：`apr/jruby/jsch/jline/latencyutils/lz4/plexus-utils/analyzer` 均不在本仓 Maven 依赖树（扫描环境 OS 包/工具运行时），非业务运行时依赖。
- kotlin 链路说明：`kotlin-stdlib-common 1.8.0` 由 okio-jvm 3.4.0 传递引入（dependency:tree 确认）；kotlin-bom 2.x 对该 artifact 仅声明 `type=pom` 无法匹配 jar 依赖，管理失效为 Kotlin 生态已知残留。空壳定性有实测证据：本地仓库 jar（`kotlin-stdlib-common-1.8.0.jar`）共 374 个 entry、**0 个 `.class` 文件**（仅 `.kotlin_metadata`/`.kotlin_builtins`/MANIFEST），无可执行字节码，无 CVE 攻击面。注意：#90 扫描所报 kotlin CVE（CVE-2020-29582 等）针对 2.0.20 完整 stdlib，与本 artifact 是两条不同链路。（版本治理仍待向 common 仓反馈。）

### 删 spring-boot-starter-parent 的两个连锁坑（已修）

| 坑                 | 现象                                                                                                                                                      | 修复                                                                              |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `-parameters` 丢失 | Spring Data 对 `@Param` 混用（部分参数加注解部分不加）从宽容变严格校验，`RawSbomRepository.queryOneTaskByTaskStatusWithLock` 启动即失败（gamma 部署事故） | root pom compiler plugin 显式 `<parameters>true</parameters>` + 补齐缺失 `@Param` |
| surefire 版本失控  | Boot parent 原锁定 surefire 3.x；删后漂到 Maven 默认 3.2.5 且无 pluginManagement 管理，离线构建因 provider 缺失失败                                       | root pom pluginManagement 锁定 surefire 3.2.5                                     |

依赖树对比结论（verbose JSON 全量对比）：338 节点无增减。

## 4. #89 / #100 运行时域名外置 Nacos

### 分类（78 项命中，A 16 + B 1 + C 61 = 78）

- **A 类（16 项，整改）**：vcs/uvp/sonatype/license.properties 全部域名 → 本地值清空、key 保留占位，值迁各环境 Nacos `sbom` dataId；token 类维持 `${ENV_VAR:}` 占位不变。
- **清单外增量（1 项）**：`sbom.service.website.domain`（非本次 78 项命中，关联 #105）一并外置，故外置 key 合计 17 个。
- **B 类（1 项，整改）**：`LicenseClientImpl` 的 `static final GITCODE_LICENSE_BASE_URL` 改 `@Value` 注入（static final 无法被外部配置覆盖）。
- **C 类（61 项，噪音）**：licenseMap.yml 许可证静态映射、.mvn/settings.xml、gradle/dockerfile 镜像源、pre-commit hook 源、规则文档链接——构建链路/静态数据，非运行时出网。

### 关键机制

4 个独立 properties 经 `application.properties` 的 `spring.config.import=classpath:/...` 导入；环境 profile 的 Nacos import 优先级更高，同名 key 直接覆盖，Java 侧零改动。`UvpClientImpl.needRequest()` 空值守卫保证 url 清空后安全跳过；`majun.vul.api.url` 的消费者 `MajunVulClientImpl` 为死代码（现行链路走 Feign `VulViewClient` + Nacos 服务发现）。

### 验证

临时 `NacosConfigCheckRunner`（ApplicationRunner）启动时打印全部外置 key 的解析结果；**gamma 部署实测 17/17 `[OK]`**（16 A 类 + 1 增量项），验证后该类已删除；beta 与 gamma 共用 openlibing-beta namespace 的同一份 Nacos 值，gamma 结果对 beta 同样成立。**prod 侧 Nacos 值已录入但未随镜像部署实测**，登记为待办。注意 Nacos 值不能带反引号等杂质（URL 非法，运行时调用才暴露）。

### 非 Nacos 环境空值兜底

本地值清空后，域名取值完全依赖 Nacos 覆盖。当前所有部署 profile（local/beta/gama/prod）均配置 Nacos import，CI 仅构建不运行应用，故无实际受影响环境；但缺省空值在「Nacos 不可达 + 配置缺失」场景下会导致非守卫 client（LicenseClientImpl/SonatypeClientImpl 等）以空 base url 发起出站调用，运行期才暴露。缓解已登记待办：对 A 类关键 key 增加启动期非空 fail-fast 断言、其余出站 client 空值守卫对齐 `UvpClientImpl.needRequest()` 模式。

## 5. SpotBugs/findsecbugs 门禁加固

- root pom 激活 `findsecbugs-plugin`（`findsecbugs.version` 属性此前已声明但未挂载）与 `sb-contrib`。
- **CRLF_INJECTION_LOGS 56 处**：该检测器对一切非字面量 logger 参数告警、不做污点分析，无法通过 Sanitizer 包装消除（已实验验证）；运行时防护已由 log4j2 `%enc{%msg}{CRLF}`（文件）/`%replace`（console）落地。处置：`SbomController`/`ApigController`/`InternalController`/`SignatureUtil` 4 个类加 `@SuppressFBWarnings("CRLF_INJECTION_LOGS")`（justification 注明运行时清洗兜底）；新增 `spotbugs-annotations` provided 依赖；include 白名单保持该 pattern 在线，其他类照常扫描。
- **SignatureUtil COMMAND_INJECTION**：误报（`ProcessBuilder` 数组式 exec 无 shell、临时目录路径白名单校验、输入仅来自配置），以新建 `spotbugs-exclude.xml`（挂载为 `excludeFilterFile`）方法级豁免。

## 6. bandit 整改

- `branch-diff.py`：`subprocess.run(..., shell=True)` 改列表参数（去 shell 注入面）。
- `run-mvn.py`：B603 以独立行 `# nosec` 注释豁免（nosec 尾注会被 bandit 1.9 误解析为规则 ID，必须独立成行）。
