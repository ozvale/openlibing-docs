# 支持atomgit域名代码仓 测试策略设计说明书

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/204
- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/204
- **需求名称**: 【需求】【openLiBing】代码检查、流水线、代码仓管理支持atomgit域名代码仓
- **核心目标**: 验证 openlibing-coderepo / openlibing-codecheck / openlibing-cicd 三仓完成 atomgit 域名适配——使 `atomgit.com` 域名代码仓获得与 `gitcode.com` 一致的能力（地址校验、owner/repo 解析、组织路径与 sig-info 路径、代码检查平台识别、流水线全链路），且既有 `gitcode.com` 能力无回退。
- **开发责任人**: 张豪（openlibing-coderepo / openlibing-codecheck / openlibing-cicd）
- **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

> **操作指南**：依据需求分析阶段的标签勾选。勾选后，必须在"第 3 节"提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点:** 代码仓管理双域名化（地址校验、域名无关解析、组织路径）、sig-info 路径识别与坐标解析、域名白名单边界与跨平台一致性、代码检查平台归一化、流水线全链路（bisectRepo/webhook/事件分组/IssueClient/token/PR 链接/失败邮件）、gitcode.com 全链路无回退。
> - **目的:** 确保 atomgit 域名仓库与 gitcode 域名能力一致，且不引入过度匹配与回退风险。
> - **触发条件:** 强制执行。

- [ ] **体验测试**

- [ ] **集成测试**

- [ ] **安全与隐私测试**：

> 本次均豁免：不改鉴权逻辑；不改跨用户资源访问控制；不改角色/权限模型；不改 HTTPS/Cookie 传输配置；不改 Web 会话与 CSRF 机制；输入为仓库 URL，无新增敏感字段输出，token 获取链路沿用既有加解密。域名白名单输入校验（含相似域名/子域绕过）已作为系统测试无效等价类覆盖，不单列安全用例。

- [ ] **可靠性与韧性测试**

- [ ] **可服务性与可观测性测试**

- [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.代码仓管理双域名化（AC1）**:

- 前置条件: 备有 `atomgit.com` 域名测试仓库与 `gitcode.com` 对照仓库；三仓特性分支已部署测试环境
- 测试步骤: 添加 `https://atomgit.com/{owner}/{repo}` 仓库地址；核对地址校验通过；核对 owner/repo 解析与同结构 `gitcode.com` URL 结果一致
- 预期结果: 地址校验通过、owner/repo 解析正确（无错位）

**2.组织路径配置接受 atomgit 域名（AC2）**:

- 测试步骤: 配置组织主页 `https://atomgit.com/{org}/`；核对域名校验结果
- 预期结果: gitcode 平台接受双域名；gitee/github 平台维持单域名

**3.sig-info 路径支持 atomgit 域名且坐标解析正确（AC3）**:

- 测试步骤: 配置 `https://atomgit.com/{owner}/{repo}/blob/{branch}/{path}`；核对平台识别与坐标解析；核对校验提示文案
- 预期结果: 识别为 gitcode 平台、坐标解析正确

**4.域名白名单边界与跨平台一致性校验**:

- 测试步骤: 输入大小写混用（`AtomGit.com`）、非白名单域名（`example.com`）、相似域名（`myatomgit.com`/`atomgit.com.evil.com`）、atomgit 域名配 gitee 平台
- 预期结果: 大小写不敏感；非白名单/相似域名不被误纳入；跨平台不一致被拒绝

**5.代码检查平台识别（AC4）**:

- 测试步骤: 录入 atomgit 仓库地址后进入代码检查/问题屏蔽/门禁检查
- 预期结果: 平台识别为 gitcode（不回退 gitee 默认），问题屏蔽与门禁检查平台识别一致

**6.流水线全链路（AC4）**:

- 测试步骤: 核对 `bisectRepo` 校验、webhook 回调平台识别、事件分组与触发平台识别、向 atomgit 仓库建 Issue、repoType/token 获取、PR 链接与跨区 PR 解析、失败邮件平台识别
- 预期结果: atomgit 均识别为 gitcode，链路功能正常

**7.gitcode.com 域名全链路无回退（回归）**:

- 测试步骤: 以 `gitcode.com` 域名重复上述链路
- 预期结果: 既有能力无回退

**8.关联缺陷场景回归**:

- 测试步骤: 同一项目下 gitcode 与 atomgit 同代码仓重复录入；atomgit 仓库代码风格自动修复开关；告警抑制自动检视开关；代码检查结果上报后解析展示
- 预期结果: 重复校验生效、各开关生效、结果正确展示（对应缺陷 #220/#369/#370/#371 回归）

---

## 4. 依赖与前置条件

- openLiBing 平台测试环境（beta）可访问，具备代码仓管理 / 项目配置 / 代码检查 / 流水线操作权限的测试账号
- 一个 `atomgit.com` 域名下可访问测试仓库（owner/repo 已知），以及一个 `gitcode.com` 对照仓库
- `code.platform.address` 配置中心 gitcode 值已追加 `https://atomgit.com`（双保险，需部署验证）
- 三仓特性分支 `feat/support-atomgit-domain` 已部署到测试环境

## 5. 补充说明

1. 本测试策略对应 issue https://gitcode.com/openlibing/openlibing-coderepo/issues/204。
2. AC5（开发侧单测）由开发自验证覆盖，不在测试用例范围。
3. 数据来源：issue 目录 `测试过程数据/测试策略.md`。
4. 测试结果与风险说明见同目录《支持atomgit域名代码仓 测试报告》。
