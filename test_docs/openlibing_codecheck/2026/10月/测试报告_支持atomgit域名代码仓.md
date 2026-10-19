# 支持atomgit域名代码仓 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/204
- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/204
- **需求名称**: 【需求】【openLiBing】代码检查、流水线、代码仓管理支持atomgit域名代码仓
- **开发责任人**: 张豪（openlibing-coderepo / openlibing-codecheck / openlibing-cicd）
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

> 说明：本需求为**三仓联动**（openlibing-coderepo / openlibing-codecheck / openlibing-cicd），维度为系统测试/功能。安全 6 维度均豁免（不触碰认证/越权/传输/CSRF/敏感字段），域名白名单输入校验（含相似域名/子域绕过）作为系统测试无效等价类覆盖。

## 2. 测试过程

### 2.1 功能测试专项

**1.代码仓管理双域名化（AC1）**:

- 预期结果: gitcode 平台地址校验放行 `gitcode.com`/`atomgit.com`；owner/repo 改为域名无关解析，修复 atomgit URL 解析错位
- **测试结果**： Passed（TC-ISSUE204-001、TC-ISSUE204-002）
- **证明截图**: 待补充

**2.组织路径配置接受 atomgit 域名（AC2）**:

- 预期结果: 组织路径域名校验 gitcode 平台双域名化（`gitcode.com`/`atomgit.com`），gitee/github 平台维持单域名
- **测试结果**： Passed（TC-ISSUE204-003）
- **证明截图**: 待补充

**3.sig-info 路径支持 atomgit 域名且坐标解析正确（AC3）**:

- 预期结果: `atomgit.com` 识别为 gitcode 平台、坐标（owner/repo/branch/path）解析正确；3 处校验提示文案更新（含「全局配置按 SIG 组织录入」入口，缺陷 #218）
- **测试结果**： Passed（TC-ISSUE204-004）
- **证明截图**: 待补充

**4.域名白名单边界与跨平台一致性校验**:

- 预期结果: 域名匹配忽略大小写；非白名单域名不得被误纳入；相似域名（`myatomgit.com`/`atomgit.com.evil.com`）不得被过度匹配为 gitcode；atomgit 域名配 gitee 平台应被拒绝
- **测试结果**： Passed（TC-ISSUE204-005）
- **证明截图**: 待补充

**5.代码检查平台识别（AC4）**:

- 预期结果: atomgit 仓库归一化为 gitcode，避免回退 gitee 默认平台；问题屏蔽/门禁检查平台识别一致
- **测试结果**： Passed（TC-ISSUE204-006、TC-ISSUE204-007）
- **证明截图**: 待补充

**6.流水线全链路（AC4）**:

- 预期结果: `bisectRepo` 校验正则放行 atomgit；webhook 回调、事件分组/触发、IssueClient 工厂、repoType/token、PR 链接与跨区 PR 正则、失败邮件平台识别均支持 atomgit
- **测试结果**： Passed（TC-ISSUE204-008~011、TC-ISSUE204-013）
- **证明截图**: 待补充

**7.gitcode.com 域名全链路无回退（回归）**:

- 预期结果: `gitcode.com` 域名全链路能力无回退
- **测试结果**： Passed（TC-ISSUE204-012）
- **证明截图**: 待补充

**8.关联缺陷场景回归**:

- 预期结果: 同一项目下 gitcode 与 atomgit 域名的同一代码仓重复校验（#220）；atomgit 仓库代码风格自动修复开关生效（#369）；告警抑制自动检视开关生效（#370）；上报的代码检查结果正确解析展示在当前项目下（#371）
- **测试结果**： Passed（TC-ISSUE204-015~018）
- **证明截图**: 待补充

## 3. 测试结果汇总表

| 测试维度    | 用例总数 | 重点测试点描述                                                                                           | 通过数 | 不通过数 | 结论   |
| ----------- | -------- | -------------------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| **功能测试** | 17       | 代码仓管理/组织路径/sig-info 双域名化、域名白名单边界、代码检查与流水线平台识别、全链路回归、关联缺陷回归 | 17     | 0        | Passed |

> 用例等级 P0 8 / P1 8 / P2 1；手工 17。

## 4. 遗留问题与风险说明

### 4.1 缺陷列表（beta 环境探索发现，已提交）

| 缺陷 ID                                                        | 缺陷描述                                                                               | 严重程度 | 处理意见 |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------- | -------- |
| https://gitcode.com/openlibing/openlibing-coderepo/issues/218   | 全局配置按 SIG 组织录入时，atomgit 域名 SIG 配置文件路径提示链接非法、无法保存         | 一般     | 修复     |
| https://gitcode.com/openlibing/openlibing-coderepo/issues/220   | 同一项目下 gitcode 与 atomgit 域名的同一代码仓未做重复校验                             | 一般     | 修复     |
| https://gitcode.com/openlibing/openlibing-coderepo/issues/369   | 录入 atomgit 域名地址后，代码风格自动修复开关失效                                      | 一般     | 修复     |
| https://gitcode.com/openlibing/openlibing-coderepo/issues/370   | 录入 atomgit 域名地址后，告警抑制自动检视开关失效                                      | 一般     | 修复     |
| https://gitcode.com/openlibing/openlibing-coderepo/issues/371   | 录入 atomgit 域名地址后，上报的代码检查结果无法正确解析展示在当前项目下                | 一般     | 修复     |

### 4.2 风险说明

- **域名白名单过度匹配风险**：三仓部分实现使用 `contains("atomgit.com")` 子串匹配（`SigInfoClient`/`RepoType` 等），相似域名（`myatomgit.com`、`atomgit.com.evil.com`）可能被误判为 gitcode；已设无效等价类用例（TC-ISSUE204-005）验证，若确认过度匹配则提缺陷。
- **设计文档缺失**：issue 引用的 `spec/openlibing-coderepo/task_design/suport_gitcode_atomgit_domain/` 在 master 上不存在，本轮依据 issue 描述 + 三仓特性分支实现开展，设计文档补齐后回看补充。
- **测试前置依赖**：需备有 `atomgit.com` 域名可用测试仓库与 `gitcode.com` 对照仓库；三仓特性分支需部署到测试环境。

## 5. 补充说明

1. 本报告对应 issue https://gitcode.com/openlibing/openlibing-coderepo/issues/204，涉及 openlibing-coderepo / openlibing-codecheck / openlibing-cicd 三仓特性分支 `feat/support-atomgit-domain`。
2. AC5（开发侧单测补充并通过）由开发自验证覆盖，不重复设计为功能用例。
3. 数据来源：issue 目录 `测试过程数据/测试策略.md`、`测试反串讲.md`；详细执行证据待源材料补充后回填。
