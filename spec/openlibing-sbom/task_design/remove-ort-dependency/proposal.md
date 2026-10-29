# Proposal: remove-ort-dependency

- 仓库: openlibing-sbom
- 分支: `feat-remove-ort-dependency`（基于源仓 prod/master 最新）
- 模式: Full

## 需求背景

openlibing-sbom 为 `definition_file` / `sbom_tracer_data` 两类任务引入了 `org.ossreviewtoolkit`（ORT，私有 fork 1.0.0，model/analyzer/reporter/spdx-utils 四 artifact）依赖。当前业务对这两类解析无需求，ORT 依赖树庞大且仅服务于死链路，希望彻底移除。

链路分析结论（ORT 引用 22 文件）：

- analyzer 模块 27 文件（25 个 Java + pom.xml + build.gradle.kts）全部属于两类链路（分析器/parser/handler/pkggen/vcs），可整模块删除；
- batch 的 `FillUpLicenseStep` 仅借用 ORT 的 3 个 SPDX 工具类（SpdxConstants/SpdxExpression/SpdxException），是唯一不随两类下线消失的引用；
- API 入口 `/uploadSbomTraceData`（Controller 直调 TraceDataAnalyzer）是 batch 之外的第二个 tracer 入口，需一并下线。

## 方案概述

1. 下线两类任务支持：删 analyzer 模块、相关 Step/Decider/job 节点、API、Validator 内容校验、枚举值与专属 POJO/常量、3 个测试；
2. `FillUpLicenseStep` 换用 SPDX 官方 `org.spdx:java-spdx-library`，新增 `SpdxLicenseExpressionUtil`（isNotPresent + parseAndCollectLicenseIds），fallback 逻辑不变；
3. `SelectWaitRawSbomStep` 查询 SQL 加 value_type 白名单，存量两类 WAIT 记录不被调度。

## 验收标准

1. 全仓源码（排除 sbom-tools 子模块）`org.ossreviewtoolkit` import 为 0；
2. `mvn dependency:tree` 全模块无 `org.ossreviewtoolkit` 组依赖；
3. analyzer 模块移除后 `mvn clean package` 编译通过；
4. SPDX SBOM 主链路行为不变，FillUpLicenseStep 行为兼容（BETA 真实数据回归）；
5. `/uploadSbomTraceData` 移除（404）；`/publishSbomFile(WithCompress)` 拒绝两类 type 返回 400；
6. raw_sbom 存量数据不导致 job 卡死。

## 决策记录

| 决策点                     | 结论                                  |
| -------------------------- | ------------------------------------- |
| FillUpLicenseStep 替换方式 | java-spdx-library（非自写解析器）     |
| `/uploadSbomTraceData`     | 直接删除接口                          |
| 存量数据                   | 查询白名单过滤，不动表数据            |
| 解析行为差异               | 接受（fallback 兜底 + BETA 回归验证） |
