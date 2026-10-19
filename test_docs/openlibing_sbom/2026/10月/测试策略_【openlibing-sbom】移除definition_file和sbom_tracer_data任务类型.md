# 【openlibing-sbom】移除definition_file和sbom_tracer_data任务类型 测试策略设计说明书

## 1. 基本信息

- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-sbom/issues/112
- **需求名称**: 【openlibing-sbom】移除definition_file和sbom_tracer_data任务类型
- **核心目标**:
  移除 openlibing-sbom 中 definition_file 与 sbom_tracer_data 两类任务类型的解析支持，实现全仓 ossreviewtoolkit（ORT）依赖清零：analyzer 整模块删除、SbomContentType 删 2 枚举值、/uploadSbomTraceData 接口移除（404）、batch 删 2 个 Analyze Step + Decider（job XML 直连）、RawSbom 查询 SQL 加 value_type 白名单（存量两类 WAIT 记录不被调度）；两类 type 发布请求由"建任务"变为 400 + allowed types 提示。同时 FillUpLicenseStep 的 license 解析由 ORT spdx-utils 替换为 SPDX 官方 java-spdx-library（两处 try-catch 与 fallback 逻辑保持不变，非规范 license 解析失败不阻断 job）；保留 SPDX 2.2/3.0.1 发布主链路行为与改前一致。
- **开发责任人**: xxx
- **测试责任人**: 赵威

---

## 2. 测试维度确认

- [x] **功能自检测试**

> - **测试重点:** SBOM 发布任务类型收敛、发布主链路零回归、license 解析一致性。
> - **目的:** 确保已移除任务类型在发布入口被正确拒绝（400 + 合法类型列表）与 trace 接口下线（404）生效，保留主链路（发布 → 落库 → 调度 → 解析 → license 填充 → 统计）端到端零回归，license 解析替换 java-spdx-library 后行为一致（含 2026.10.13 评审关注的 license 名大小写一致）。
> - **触发条件:** 强制执行。

- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.已移除任务类型请求拒绝与接口下线验证**:

- 前置条件: beta 环境可访问；API 账号具备 SBOM 发布权限；合法 SPDX 2.2/3.0.1 JSON SBOM 样本各 1（有效类对照用）
- 测试步骤:
  1. POST /publishSbomFile，sbomContentType=definition_file → 断言 HTTP 400，响应为 SbomRuntimeException 语义，消息含 `allowed types: [spdx_2.2_json_sbom, spdx_3.0.1_json_sbom]`
  2. POST /publishSbomFile，sbomContentType=sbom_tracer_data → 断言同步骤 1（400 + 合法类型列表）
  3. POST /publishSbomFileWithCompress，两类 type 各发一次（压缩包体）→ 断言解压后复用前者校验：同样 400 + 合法类型列表
  4. POST /uploadSbomTraceData（历史接口）→ 断言 404（接口已移除，非 200/500）
  5. 有效类对照：POST /publishSbomFile，sbomContentType=spdx_2.2_json_sbom 与 spdx_3.0.1_json_sbom → 断言建任务成功（raw_sbom 落库 WAIT），不受拒绝逻辑影响
  6. 顺检 springdoc OpenAPI 文档不再包含 /uploadSbomTraceData（随 Controller 删除自动更新）
- 预期结果: 两类已删除 type 在两个发布入口均 400 且异常消息自带合法类型列表；/uploadSbomTraceData 404；合法类型发布正常不受影响；OpenAPI 文档同步

**2.SPDX SBOM 发布主链路端到端零回归验证**:

- 前置条件: beta 环境可访问；API 账号具备 SBOM 发布权限；合法 SPDX 2.2 JSON SBOM 样本（含多 package、license_concluded/license_declared、依赖关系）且改前同样本解析/统计结果已知（基线）；raw_sbom 表无两类已删除 type 的存量记录（2026-10-16 确认两类类型从未有数据，无存量干扰，使用独立 product_id 隔离）
- 测试步骤:
  1. POST /publishSbomFile 发布 SPDX 2.2 样本 → 断言成功，raw_sbom 落库 task_status=WAIT、value_type=spdx_2.2_json_sbom
  2. 等待 readSbomJob 调度 → 断言 selectWaitRawSbomTask 白名单捞起该记录置 RUNNING（调度查询白名单只含合法类型，不误伤）
  3. 断言 parseSbomMetadataTask：SpdxReader 正常读取 SPDX JSON → SbomDocument，元数据（name/version/供应商等）与样本一致
  4. 断言 openHarmonySpecialTaskDecision 分支与 persistSbomMetadataTask 持久化正常（SPDX 2.2 非鸿蒙特例走默认分支）
  5. 断言 split 分支：extractLicense → fillUpLicense（java-spdx-library）完成，license 填充结果与改前基线一致；resolveMavenDep + extractUvp 正常
  6. 断言 collectStatistics 统计结果（package 数/license 分布）与改前基线一致；precomputeDependencyCache → readSbomEnd 任务状态流转完整无卡死
  7. SBOM 页面查看该产物 → 断言列表/详情数据正常展示无报错（页面级确认）
  8. 换 SPDX 3.0.1 样本重复步骤 1-6 → 断言同样通过
- 预期结果: 保留主链路端到端行为与改前完全一致：落库/调度/解析/持久化/license 填充/依赖解析/统计/状态流转全部正常，页面展示无异常，两种合法类型均通过

**3.license 解析 java-spdx-library 替换行为一致性验证**:

- 前置条件: beta 环境可访问；改前（ORT）BETA 真实数据的 license 填充结果已导出为基线（样本集 S）；样本集覆盖常规表达式（`MIT`、`Apache-2.0 AND GPL-2.0-only` 等）、大小写敏感样本、小写连接符非规范表达式（`mit and apache-2.0`）、LicenseRef- 前缀自定义 license、WITH 例外（`Apache-2.0 WITH Classpath-exception-2.0`）、NOASSERTION/NONE；license 合法性校验依赖项目自有 licenseInfoMap 缓存（方案确认不引入 SPDX license list 数据文件）
- 测试步骤:
  1. 常规样本：构造含标准 SPDX 表达式的 SBOM 发布 → 断言 fillUpLicense 填充结果与改前基线逐条一致，license 名大小写完全一致（2026.10.13 评审关注点，diff 区分大小写）
  2. 复合表达式（AND/OR/WITH）：断言叶子 license-id 集合与基线一致；WITH 例外节点被忽略（visitor 收集叶子，忽略 WITH 例外节点）
  3. LicenseRef- 样本：断言 ExtractedLicenseInfo 叶子被正确收集，不被当作非法值丢弃
  4. NOASSERTION / NONE / blank：断言 isNotPresent 语义与 ORT 等价（视为不展示，不参与填充）
  5. 非规范表达式（小写 and/or 等）：断言落入 fallback 分支（按 and 拆分逐个解析）且兜底结果正确；记录与 ORT 直解结果的差异清单（方案已知行为差异，逐条评估记录，不默认当 bug）
  6. 构造无法解析的非法表达式 → 通过结果查询断言记入 invalidLicenses、job 状态正常完成（readSbomEnd 结束，不中断）
  7. 样本集 S 全量回放 → 断言填充结果 diff 仅出现在"非规范表达式落 fallback"类样本，无其他类型差异
- 预期结果: 常规与复合表达式填充结果与改前基线一致且大小写一致；LicenseRef-/NOASSERTION/NONE 语义等价；非规范表达式落 fallback 且兜底正确；解析失败不阻断 job；全量 diff 差异仅限方案声明的行为差异类
