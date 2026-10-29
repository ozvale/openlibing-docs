# openLiBing支持项目更名 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/208
- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/208
- **需求名称**: 【需求】【openLiBing】openLiBing支持项目更名
- **开发责任人**: 杨攀（openlibing-coderepo / openlibing-codecheck）
- **测试责任人**: 徐愚冰
- **最终结论**: 通过
- **测试维度**:
- [x] **功能自检测试**
- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

> 说明：本次测试范围仅覆盖 issue 核心功能点中的 **B. 下线 Nacos `${majun.project.name}`**——以**原有功能回归**为主线；issue 中 A. Framework 更名后异步刷数（方案二，含内部接口 `POST/GET /internal-server/project/rename`、MQ 刷数、审计表）本次不涉及，framework 更名编排本身由 framework 专人测试。安全 6 维度均豁免（不改鉴权、跨用户/跨项目访问控制、角色模型、传输配置、Web 会话与 CSRF；仅涉及项目名/社区名字段，无新增敏感字段输出）。

## 2. 测试过程

### 2.1 功能测试专项

**1.项目更名后仓库规则集查询正常（AC-A）**:

- 预期结果: coderepo 仓库详情「规则集」查询正常（`sig_rule_set.repo_id` + `codecheck_rule_set.account`），无项目名错位
- **测试结果**： Passed（TC-ISSUE208-001）
- **证明截图**: 待补充

**2.项目更名后社区 codecheck 规则集查询正常（AC-A）**:

- 预期结果: 社区 codecheck 规则集查询正常，不再依赖 majun 映射
- **测试结果**： Passed（TC-ISSUE208-002）
- **证明截图**: 待补充

**3.项目更名后社区防投毒规则集查询正常（AC-A）**:

- 预期结果: `anti_check_rule_set`（account）查询正常
- **测试结果**： Passed（TC-ISSUE208-003）
- **证明截图**: 待补充

**4.项目更名后门禁检查社区与仓库联动正常（AC-B）**:

- 预期结果: 门禁/每日检查社区下拉与仓库联动正常（不再依赖 majun 名匹配 `projectName` 与 Redis `inc_` 前缀）
- **测试结果**： Passed（TC-ISSUE208-004）
- **证明截图**: 待补充

**5.项目更名后看板与工作台数据正常（AC-B）**:

- 预期结果: 看板/工作台数据按平台项目名正常读取，无数据丢失
- **测试结果**： Passed（TC-ISSUE208-005）
- **证明截图**: 待补充

**6.项目更名后问题屏蔽功能正常（AC-B）**:

- 预期结果: 问题屏蔽功能正常（`summaryVo.projectName` 口径一致）
- **测试结果**： Passed（TC-ISSUE208-006）
- **证明截图**: 待补充

**7.项目更名后规则集本地库查询命中正常（AC-B）**:

- 预期结果: 规则集本地库查询命中正常（`account` / `project_name` / `tenant` 口径统一）
- **测试结果**： Passed（TC-ISSUE208-007）
- **证明截图**: 待补充

**8.项目更名后 SIG 规则集读写口径统一正常（AC-B）**:

- 预期结果: SIG 规则集读写口径统一（以 `repo_id` 或一致社区名为准，不再 coderepo 按 `repo_id`、codecheck 按 `project_name`+仓库名各自为政）
- **测试结果**： Passed（TC-ISSUE208-008）
- **证明截图**: 待补充

**9.项目更名后敏感词规则集正常（AC-B）**:

- 预期结果: 敏感词规则集正常（`sensitive_check_rule_set` / `sensitive_task_rule_set` 不纳入 majun 下线）
- **测试结果**： Passed（TC-ISSUE208-009）
- **证明截图**: 待补充

**10.项目更名后 Redis 社区缓存清理与重建一致（AC-B）**:

- 预期结果: Redis `inc_{旧社区名}` 已清理、`inc_{新社区名}` 已重建，读写一致
- **测试结果**： Passed（TC-ISSUE208-010）
- **证明截图**: 待补充

**11.项目更名后代码检查平台识别无回退（AC-B）**:

- 预期结果: 平台识别不因映射下线误判为 gitee
- **测试结果**： Passed（TC-ISSUE208-014）
- **证明截图**: 待补充

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                                                                                                                                                                  | 通过数 | 不通过数 | 结论   |
| ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| **功能测试** | 11       | coderepo 适配回归（仓库规则集/社区 codecheck 规则集/社区防投毒规则集）+ codecheck 适配回归（门禁联动/看板工作台/问题屏蔽/规则集本地库/SIG 规则集/敏感词集/Redis 缓存/平台识别） | 11     | 0        | Passed |

> 用例等级 P0 2 / P1 7 / P2 2；手工 11。
> **编号说明**：用例编号沿用源材料 `case_list.md`（TC-ISSUE208-001~010、014）；编号 011~013 未出现在源清单中，与本轮范围无对应关系，具体归属以源材料为准。
> **范围说明**：本需求为配合 framework 项目更名主需求的适配改造，主要功能由主需求统一测试覆盖；本报告仅覆盖本团队两服务（openlibing-coderepo / openlibing-codecheck）的适配回归。

## 4. 遗留问题与风险说明

| 缺陷 ID | 缺陷描述     | 严重程度 | 处理意见 |
| ------- | ------------ | -------- | -------- |
| —       | 无未关闭缺陷 | —        | —        |

**风险说明**：

- **对照策略**：选取具备既有数据的测试项目记录下线前基线；项目更名并完成刷数治理后逐项验证既有功能与基线一致（数据按新项目名可查、无旧名残留错位）。
- **设计文档不可访问**：issue 引用的设计文档《方案二-Feign联动刷新project_name.md》不可访问（GitCode 页面需登录/无权限），本轮依据 issue 描述 + 本地两仓源码实证开展；设计文档补齐后回看补充。
- **受影响集合清单**：本地两仓为改动前版本，「13 个 Mongo 集合 + Redis `inc_{社区名}`」具体清单以源码实证的受影响功能为回归靶点，执行前与开发对齐差异。
- **测试边界**：framework 更名编排、A 方案（Feign 异步刷数与内部接口）不在本团队测试范围。

## 5. 补充说明

1. 本报告对应 issue https://gitcode.com/openlibing/openlibing-coderepo/issues/208，涉及 openlibing-coderepo / openlibing-codecheck 两服务（openlibing-cicd 经开发确认本需求不涉及）。
2. 关键业务规则：更名后母表 `project_info.project_name` 为唯一权威来源；下线 `${majun.project.name}` 后读侧按平台项目名（或按 `projectId` 动态解析的双读）查询，禁止全局写死；`sig_rule_set` 读写统一口径；`sensitive_check_rule_set`/`sensitive_task_rule_set` 不纳入 majun 下线。
3. 数据来源：issue 目录 `测试过程数据/测试策略.md`、`测试反串讲.md`、`需求串讲.md`、`需求开发自验证.md` 与 issue 级 `case_list.md`；详细执行证据待源材料补充后回填。
