# Design: remove-ort-dependency

本文件为 spec 落盘版，完整设计随本归档落盘。

> **行为声明基准**：本需求主交付为 commit `934be424`；业务 PR #158 后续追加 `c9f9d4f4`（移除 `SPDX_3_0_1_JSON_SBOM` 类型支持、下线 fetchOpenEulerRepoMeta 定时任务）与 `a22ec3d5`（清理测试残留与 FileUtil 死代码）。本文档行为声明已同步至最终交付 head `a22ec3d5`，与主交付时点不一致处均以"最终行为"注明。

## 1. 方案设计

| 层            | 动作                                                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| analyzer 模块 | 整体删除（27 文件：25 个 Java + pom.xml + build.gradle.kts），根 pom `<modules>` 移除，sbom-web pom 依赖移除                       |
| interface     | 删 `SbomContentAnalyzer`、`SbomService#persistSbomFromTraceData` 声明                                                              |
| model         | `SbomContentType` 删 2 枚举值；删 ProcessData/ProcessIdentifier/PublishSbomConstants/BATCH_SBOM_CONTENT_TYPE_KEY/两个 INORDER 常量 |
| utils         | `PublishSbomRequestValidator` 删内容解包校验段（~130 行），保留 `validateParam`                                                    |
| sbom-web      | 删 `/uploadSbomTraceData` + `persistSbomFromTraceData` 实现 + TraceDataAnalyzer 注入 + 3 测试                                      |
| batch         | 删 2 Analyze Step + Decider，job XML 直连；SelectWaitRawSbomStep 查询白名单；FillUpLicenseStep 换库                                |
| pom           | 根 pom 删 3 个 ORT artifact（java-spdx-library 沿用既有 2.0.3 声明）；batch pom 2 个 ORT → java-spdx-library                       |

保留不动：`clients` 模块 `VcsServiceImpl`（SpdxReader/CollectStatisticsStep 使用）、`publishSbom` 主链路、`SbomSpecification` 枚举（存量 SPDX 3.0.1 文档查询仍在引用）。最终行为：`findBySpecAndFormat` 已随追加提交 `c9f9d4f4` 收敛为仅 SPDX 2.2 + JSON 分支（SPDX 3.0.1 文档上传/导出直接抛 `unsupported spec and format` 拒绝）。

## 2. 实现逻辑设计

### 改造后主链路

```
POST /publishSbomFile (spdx_2.2_json_sbom)
  → validateParam（两类 type 在 isValidType 处自然拒绝，消息含合法类型列表）
  → raw_sbom 落库 WAIT → readSbomJob
  → selectWaitRawSbomTask（SQL 白名单过滤 value_type）
  → parseSbomMetadataTask → openHarmonySpecialTaskDecision → persistSbomMetadataTask
  → split: extractLicense→fillUpLicense（java-spdx-library）/ resolveMavenDep+extractUvp
  → collectStatistics → precomputeDependencyCache → readSbomEnd
```

### FillUpLicenseStep 替换映射

| ORT API                                  | 替代                                                                       |
| ---------------------------------------- | -------------------------------------------------------------------------- |
| `SpdxConstants.INSTANCE.isNotPresent(s)` | `SpdxLicenseExpressionUtil.isNotPresent(s)`（blank/NOASSERTION/NONE）      |
| `SpdxExpression.parse(s)`                | `LicenseExpressionFactory.parseLicenseExpression(s, 不校验 listed)`        |
| `spdxExpression.licenses()`              | `SpdxLicenseExpressionUtil.parseAndCollectLicenseIds(s)`（visitor 收叶子） |
| `catch (SpdxException)`                  | `catch (SpdxLicenseParseException)`（自定义 RuntimeException）             |

两处 try-catch 与 fallback（`and` 拆分）控制流不变。license 合法性校验仍由项目自有 `licenseInfoMap` 完成，不引入 SPDX license list 数据文件。

已知行为差异：java-spdx-library 解析比 ORT 严格（小写连接符等非规范输入会落入 fallback），缓解：BETA 真实数据回归 + fallback 兜底。

### 异常与边界

| 场景                     | 处理                                                          |
| ------------------------ | ------------------------------------------------------------- |
| 请求已删除 type          | Validator 抛异常 → 400，消息含合法类型列表                    |
| 存量两类 WAIT 记录       | 查询白名单过滤，不被调度                                      |
| 新库解析失败             | 走既有 fallback，仍失败记 invalidLicenses 并 warn，不阻断 job |
| 私仓无 java-spdx-library | 实施第一步验证，不可达即升级用户                              |

## 3. 类设计

### 新增

```java
// org.opensourceway.sbom.batch.utils.SpdxLicenseExpressionUtil（纯静态工具）
public static boolean isNotPresent(String spdxLicense)
public static Set<String> parseAndCollectLicenseIds(String spdxLicense)  // 失败抛 SpdxLicenseParseException
```

### 删除

analyzer 模块 27 文件（25 个 Java + pom.xml + build.gradle.kts）；batch：AnalyzeTraceDataStep/AnalyzeDefinitionFileStep/SkipAnalyzeSbomContentDecider；interface：SbomContentAnalyzer；model：ProcessData/ProcessIdentifier/PublishSbomConstants；sbom-web 测试：TraceDataAnalyzerTest/PythonPackageGeneratorTest/SkipAnalyzeSbomContentDeciderTest。

### 修改

SbomContentType（删 2 值）、BatchContextConstants（删 1 常量）、BatchFlowExecConstants（删 2 常量）、PublishSbomRequestValidator（删内容校验）、SbomController（删 uploadSbomTraceData）、SbomService/SbomServiceImpl（删 persistSbomFromTraceData）、SelectWaitRawSbomStep（删 content type 写入）、FillUpLicenseStep（换库）、RawSbom 查询 SQL（加白名单）。

## 4. 数据模型设计

不涉及表结构变更。`raw_sbom` 表与唯一索引 `raw_sbom_uk(value_type, product_id)` 不动；存量清理为发布后手工 SQL（WAIT 两类记录置 FAILED_FINISH），不进代码。

## 5. 性能设计

不涉及新增性能敏感路径；删除的恰是重 CPU/IO 链路（解包/ORT 扫描/trace 解析），batch 单任务资源占用下降；依赖树缩减降低启动时间与镜像体积。

## 6. API 接口设计

| 接口                                  | 变化                                                                                                                                                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `POST /uploadSbomTraceData`           | 移除（404）                                                                                                                                                                                            |
| `POST /publishSbomFile(WithCompress)` | 最终行为：`definition_file`/`sbom_tracer_data`/`spdx_3.0.1_json_sbom` 三类 type 均 400 + `Invalid sbomContentType: ..., allowed types: [spdx_2.2_json_sbom]`（SPDX 3.0.1 type 随 `c9f9d4f4` 一并拒绝） |
| `GET /fetchOpenEulerRepoMeta`         | 保留手动触发；对应 quartz 定时任务随 `c9f9d4f4` 下线                                                                                                                                                   |

无新增接口，springdoc 文档自动更新。

## 7. 安全设计

- 攻击面缩减：API 层不再解包用户 tar 数据（原校验逻辑涉及解压外部包）；
- 无新增输入面/鉴权变化/凭证处理变化；
- java-spdx-library 为 SPDX 官方维护，引入需过私仓安全扫描。

## 8. 跨仓影响

无。单仓（openlibing-sbom）改动，无接口消费方受影响（两类任务当前无调用方，已用户确认）。

## 9. 测试策略

1. 编译：`mvn clean compile` 全模块；
2. 依赖断言：`mvn dependency:tree -Dincludes=org.ossreviewtoolkit` 全模块为空 + 全局 grep 0 命中；
3. 单测：SpdxLicenseExpressionUtilTest（语法/嵌套/WITH/LicenseRef/NOASSERTION/非法输入）、FillUpLicenseStepTest（主路径+fallback+invalidLicenses）；
4. BETA 验证（用户手动部署）：发布 SPDX SBOM 全流程回归 + 两类 type 拒绝 + 接口 404。
