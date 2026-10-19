# 【openlibing-sbom】移除definition_file和sbom_tracer_data任务类型 测试报告

## 1. 基本信息

- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-sbom/issues/112
- **需求名称**: 【openlibing-sbom】移除definition_file和sbom_tracer_data任务类型
- **开发责任人**: xxx
- **测试责任人**: 赵威
- **最终结论**: 通过
- **测试维度**:
- [x] **功能自检测试**
- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.已移除任务类型请求拒绝与接口下线验证**:

- 预期结果: 两类已删除 type 在两个发布入口均 400 且异常消息自带合法类型列表；/uploadSbomTraceData 404；合法类型发布正常不受影响；OpenAPI 文档同步
- **测试结果**： Passed
- **证明截图**: xxx

**2.SPDX SBOM 发布主链路端到端零回归验证**:

- 预期结果: 保留主链路端到端行为与改前完全一致：落库/调度/解析/持久化/license 填充/依赖解析/统计/状态流转全部正常，页面展示无异常，两种合法类型均通过
- **测试结果**： Passed
- **证明截图**: xxx

**3.license 解析 java-spdx-library 替换行为一致性验证**:

- 预期结果: 常规与复合表达式填充结果与改前基线一致且大小写一致；LicenseRef-/NOASSERTION/NONE 语义等价；非规范表达式落 fallback 且兜底正确；解析失败不阻断 job；全量 diff 差异仅限方案声明的行为差异类
- **测试结果**： Passed
- **证明截图**: xxx

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                                                                                                                                                                                          | 通过数 | 不通过数 | 结论 |
| ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ---- |
| **功能测试** | 3        | 覆盖已移除任务类型请求拒绝与接口下线（两个入口 400 + allowed types 提示、/uploadSbomTraceData 404、合法类型对照）、SPDX 2.2/3.0.1 发布主链路端到端零回归、license 解析 java-spdx-library 替换行为一致性 | 3      | 0        | Pass |

## 4. 遗留问题记录

| 序号 | 问题描述 | 严重程度 | 负责人 | 状态 | 备注 |
| ---- | -------- | -------- | ------ | ---- | ---- |
|      |          |          |        |      |      |

## 5. 补充说明

移除 definition_file 与 sbom_tracer_data 两类任务类型以清除 ossreviewtoolkit（ORT）依赖：analyzer 整模块删除、SbomContentType 删 2 枚举值、batch 删 2 个 Analyze Step + Decider（job XML 直连，selectWaitRawSbomTask 直接指向 parseSbomMetadataTask，STOPPED 分支保留）；两类 type 在 /publishSbomFile 与 /publishSbomFileWithCompress 两个发布入口均由"建任务"变为 400 + `Invalid sbomContentType: ..., allowed types: [spdx_2.2_json_sbom, spdx_3.0.1_json_sbom]` 提示；/uploadSbomTraceData 接口移除返回 404，OpenAPI（springdoc）随 Controller 删除自动更新；保留 SPDX 2.2/3.0.1 两类合法类型，发布主链路（落库 WAIT → 白名单调度 → SpdxReader 解析 → license 填充/依赖解析 → 统计 → readSbomEnd）行为与改前一致；FillUpLicenseStep 的 license 解析由 ORT spdx-utils 迁移至 SPDX 官方 java-spdx-library，license 名大小写与改前一致（2026.10.13 评审关注点），非规范 license（如小写 and/or 连接符）落 fallback 分支兜底（按 and 拆分逐个解析），仍失败记入 invalidLicenses 并 warn，不阻断 job；license 合法性校验仍由项目自有 licenseInfoMap 缓存完成，不引入 SPDX license list 数据文件依赖；RawSbom 查询 SQL 增加 value_type IN 白名单（存量两类 WAIT 记录不被调度），2026-10-16 确认两类类型从未有数据、无存量干扰；不涉及表结构变更，raw_sbom 表结构与唯一索引不动，存量清理不进代码与迁移脚本。
