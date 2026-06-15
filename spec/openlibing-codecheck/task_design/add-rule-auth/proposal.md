# add-rule-auth

## 需求背景

规则集相关接口缺少项目级别角色（project_manager、project_cie 等）的横向鉴权，存在越权访问风险。当前仅有部分接口具备鉴权，大部分接口可被任意已登录用户访问，无法按项目维度隔离权限。

## 功能描述

为以下 14 个规则集相关接口补充 `authUtils.checkPermission(url, projectId, userId)` 编程式横向鉴权：

**RuleController 接口（8个）**：
- `/ci-portal/v2/grant/auth/rules-account`
- `/ci-portal/v2/grant/auth/rules/group-account`
- `/ci-portal/v2/grant/auth/rules/setting/account`
- `/ci-portal/v2/grant/auth/rules/setting/group-account`
- `/ci-portal/v2/grant/auth/project/ruleSet`
- `/ci-portal/v2/grant/auth/modify/createUser`
- `/ci-portal/v2/grant/auth/query/template/threshold`
- `/ci-portal/v2/grant/auth/default/template`

**FileDownLoadController 接口（2个）**：
- `/ci-portal/excel/v1/rule/set`
- `/ci-portal/excel/v1/rule/set/export`

**RuleSetListController 接口（4个）**：
- `/codecheck/operate/project/ruleSetList`
- `/codecheck/operate/personal/ruleSetList`
- `/codecheck/operate/project/single/ruleSetList`
- `/codecheck/ruleSetList/getCommunityManager`

同时将 `/codecheck/authCommunity` 接口标注为 `@Deprecated`。

不做：不修改已有鉴权的接口、不修改无 projectId 的接口、不修改数据库鉴权配置。

## 验收标准

- [ ] 上述 14 个接口均具备项目级别角色横向鉴权
- [ ] admin/platform_operator 角色直接放行
- [ ] 项目级角色（project_manager、project_cie）仅能访问其 projectId 匹配的项目接口
- [ ] 鉴权失败返回 `code:403, result:"no permission"`
- [ ] `/codecheck/authCommunity` 标注 `@Deprecated`
- [ ] 编译通过，IDE 诊断零错误

## 影响范围

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| RuleDelegate.java | 修改 | 8个方法签名添加 userId 参数 |
| RuleDelegateImpl.java | 修改 | 9个方法添加 checkPermission 鉴权 |
| RuleController.java | 修改 | 8个方法添加 userId 请求参数 |
| RuleSetListController.java | 修改 | 3个方法添加 userId + @Deprecated |
| RuleSetListImpl.java | 修改 | 4个方法添加鉴权逻辑 |
| FileDownLoadController.java | 修改 | 2个方法添加鉴权 + 注入 AuthUtils |
