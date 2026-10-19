# Tasks: remove-ort-dependency

## 准备

- [ ] 基于 prod/master 最新创建特性分支 `feat-remove-ort-dependency`
- [ ] 验证私仓可解析 `org.spdx:java-spdx-library`（implementation 第一步，不可达即阻塞升级）

## 模块删除与清理

- [ ] 删除 analyzer 模块目录 + 根 pom `<modules>` 移除 + sbom-web pom 依赖移除
- [ ] interface：删 `SbomContentAnalyzer`、`SbomService#persistSbomFromTraceData` 声明
- [ ] model：`SbomContentType` 删 2 枚举值；删 ProcessData/ProcessIdentifier/PublishSbomConstants/BATCH_SBOM_CONTENT_TYPE_KEY/2 个 INORDER 常量
- [ ] utils：`PublishSbomRequestValidator` 删内容校验段，保留 validateParam
- [ ] sbom-web：删 `/uploadSbomTraceData` + `persistSbomFromTraceData` + TraceDataAnalyzer 注入 + 3 个测试文件

## batch 改造

- [ ] 删 AnalyzeTraceDataStep / AnalyzeDefinitionFileStep / SkipAnalyzeSbomContentDecider + job XML 直连改造
- [ ] SelectWaitRawSbomStep 删 content type 写入；RawSbom 查询 SQL 加 value_type 白名单
- [ ] batch pom：2 个 ORT 依赖 → java-spdx-library；根 pom dependencyManagement 同步

## FillUpLicenseStep 替换

- [ ] 新增 `SpdxLicenseExpressionUtil`（isNotPresent + parseAndCollectLicenseIds）
- [ ] FillUpLicenseStep 切换到新工具类，try-catch/fallback 控制流不变
- [ ] 新增 SpdxLicenseExpressionUtilTest + FillUpLicenseStepTest

## 验证

- [ ] `mvn clean compile` 全模块通过
- [ ] `mvn dependency:tree -Dincludes=org.ossreviewtoolkit` 全模块为空
- [ ] 全局 `rg "org.ossreviewtoolkit"`（排除 sbom-tools）命中 0
- [ ] 相关模块 `mvn test` 通过

## 交付

- [ ] pre-commit 检测修复全部通过（改动文件）
- [ ] 向用户报告：分支/文件清单/验证结果/pre-commit 结果（暂不 commit，等用户确认）
- [ ] 用户自测/反馈循环 → 测试环境合入验证 → PR 交付（后续阶段）
- [ ] 文档同步：sbom-read-job-documentation.md、制品发布两篇 API 文档（随编码一并修改）
