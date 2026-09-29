# 威胁模型：tag 校验下线与 token 权限校验增强

## 变更概述

| 变更项                  | 范围                                                                                                                   | 安全影响                                                                                                               |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Tag/commitId 校验下线   | 从 `SafeScanServiceImpl.executeVirusScan` 完全删除校验逻辑、`tagValidationResult`/`tagValidationDetail` 字段、前端展示 | 中：失去发布前 tag 与制品包的一致性校验，需评估替代控制                                                                |
| Token 权限范围校验增强  | `validateGitcodeToken` 增加显式 scope 校验                                                                             | 高：现有校验仅判断 token 有效（200）+ 403 区分，但未显式校验 `write_repository` scope，存在权限不足 token 被误用的风险 |
| Token 加密存储/轮换评估 | 评估 `SecurityUtil.decrypt(token, part1)` 和 `SecurityManagerUtil.decrypt` 双解密路径 + 轮换策略                       | 高：token 通过 URL query 传输（access log 残留），且无轮换机制，泄露后无法快速吊销                                     |

## 资产清单

| 资产                                 | 分类 | 责任域                            | 备注                                           |
| ------------------------------------ | ---- | --------------------------------- | ---------------------------------------------- |
| GitCode 用户访问令牌（access_token） | 机密 | `ReleaseRepoTagHandleServiceImpl` | 用于 tag 创建/release 发布，存 DB 加密         |
| 制品包 commitId                      | 敏感 | `ReleaseSoftwareBuildDataEntity`  | 校验下线后不再参与发布阻断                     |
| Tag commitId                         | 内部 | GitCode API 返回                  | 校验下线后不再查询对比                         |
| 仓库写权限（write_repository scope） | 机密 | GitCode 平台                      | token 必须有此 scope 才能创建 tag              |
| 发布评审单                           | 敏感 | `ReleaseBaseServiceImpl`          | 含 repoUrl + token 配对，提交时触发 token 校验 |
| token 校验响应体                     | 内部 | `validateGitcodeToken`            | 401/403 错误信息可能泄露 token 状态            |

## 信任边界

```
用户 → API 网关 → ReleaseBaseController → ReleaseBaseServiceImpl（提交评审，触发 token 校验）
                                              ↓
                                     ReleaseRepoTagHandleServiceImpl.validateGitcodeToken
                                              ↓
                                     GitCode /user 接口（token 在 URL query 中传输）⬅ 信任边界穿越点
                                              ↓
                                     GitCode /repos/.../tags 接口（打 tag）⬅ 信任边界穿越点
                                              ↓
                                     SafeScanServiceImpl.executeVirusScan（tag 校验下线后此环节移除）
                                              ↓
                                     ReleaseDecisionServiceImpl.runRelease（发布决策）
```

**关键边界穿越点**：

1. **业务服务 → GitCode API**：token 在 URL query 中传输（`GET /user?access_token=<token>`），会出现在网关 access log、GitCode 服务日志、可能的代理链路中
2. **DB → 业务服务**：token 从 DB 读取后经 `SecurityUtil.decrypt` 解密，解密后的明文 token 在内存流转
3. **业务服务 → 前端**：401/403 错误信息返回前端，可能暴露 token 有效性状态

## 数据流

### 流 1：Token 校验流（本次增强重点）

```
1. 用户提交评审单 → addReleaseReview（submit）
2. 从 ReleaseReviewEntity 读取 repoUrl + 加密 token
3. SecurityUtil.decrypt(token, part1) → 明文 token
4. validateGitcodeToken(明文 token)
   a. GET https://gitcode.com/api/v5/user?access_token=<明文token>  ⬅ 风险点
   b. 200/201 → 有效，但未校验 scope
   c. 401 → 无效/过期
   d. 403 → 权限不足（但错误信息可能不精确）
5. 异步打 tag 时 createTags 再次校验（兜底）
6. gitcode Release 时 handleArtifactGitcodeRelease 第三次校验
```

### 流 2：Tag 校验流（本次下线）

```
1. SafeScanServiceImpl.executeVirusScan
2. 病毒扫描完成后
3. 【本次删除】获取制品包 commitId（ReleaseSoftwareBuildDataEntity）
4. 【本次删除】queryRepoTagList 查询 tag 是否存在
5. 【本次删除】比较 tag.commitId 与 artifact.commitId
6. 【本次删除】记录 tagValidationResult + tagValidationDetail
7. SHA256 完整性校验（保留）
```

## STRIDE 评估

### 流 1：Token 校验流（增强后）

| 资产                         | S   | T   | R   | I   | D   | E   | 缓解措施                                                                                                                 |
| ---------------------------- | --- | --- | --- | --- | --- | --- | ------------------------------------------------------------------------------------------------------------------------ |
| 明文 token（URL query 传输） | 高  | 中  | 中  | 高  | 低  | 低  | **现状**：token 在 URL，access log 残留。**增强**：本次不改传输方式，但增加 scope 显式校验；后续迭代改 Header            |
| token 有效性校验             | 高  | 低  | 中  | 中  | 低  | 高  | **现状**：仅 200/201 判有效。**增强**：增加 scope 显式校验（write_repository），403 时明确区分"无权限"而非"无效"         |
| token 加密存储               | 高  | 中  | 中  | 高  | 低  | 中  | **现状**：双解密路径（SecurityUtil + SecurityManagerUtil），part1 作为密钥分量。**增强**：评估轮换策略，泄露后可快速吊销 |
| 401/403 错误响应             | 中  | 低  | 中  | 中  | 低  | 低  | **现状**：错误信息直接返回前端。**保持**：错误信息已脱敏（不含 token），但需避免泄露 GitCode 内部错误细节                |

### 流 2：Tag 校验流（下线后）

| 资产                            | S   | T   | R   | I   | D   | E   | 缓解措施                                                                                                                                                          |
| ------------------------------- | --- | --- | --- | --- | --- | --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 制品包 commitId（不再校验）     | 低  | 中  | 低  | 中  | 低  | 低  | **下线后风险**：tag 与制品包 commitId 不一致时不再阻断发布。**缓解**：发布前 tag 创建（`createTags`）仍存在，GitCode 会在 tag 已存在时报错；SHA256 完整性校验保留 |
| tagValidationResult/Detail 字段 | 低  | 低  | 中  | 中  | 低  | 低  | **下线后**：字段从 DB 移除，历史数据需迁移或保留只读。审计日志需记录"何时空下线"                                                                                  |

## 关键决策

1. **Tag 校验完全删除**：用户明确要求完全删除。安全影响：失去发布前一致性校验，但发布时 `createTags` 仍会因 tag 已存在而报错（兜底控制），且 SHA256 完整性校验保留，风险可控。
2. **Token 不改 Header 传输**：用户未选此项。本次保留 URL query 传输方式，但增加 scope 显式校验。**后续迭代建议**改为 `Authorization: Bearer` Header，消除日志泄露风险。
3. **Token 加密存储评估而非重构**：用户选"评估"而非重构。本次评估现有 `SecurityUtil.decrypt(token, part1)` 双路径，输出轮换策略建议，不改动加解密实现。
4. **不抽取统一 token 校验入口**：用户未选。保留 4 个调用点（提交评审/打Tag/gitcode Release/gitee Release）各自校验，但在 `validateGitcodeToken` 内部增强 scope 校验，所有调用点自动受益。

## 与事后审查的衔接

| 安全约束             | 事前设计                                                | 事后验证（gitcode-security-check）                        |
| -------------------- | ------------------------------------------------------- | --------------------------------------------------------- |
| scope 显式校验       | 在 `validateGitcodeToken` 增加 scope 检查逻辑           | 验证实现是否覆盖所有 4 个调用点                           |
| token 不在日志打印   | 设计约束：解密后 token 仅在内存流转，日志只记录校验结果 | 验证 LogInjection 防护 + 搜索 access log 中是否残留 token |
| tag 校验字段彻底清除 | 设计约束：DB 字段 + Entity + 前端展示全删除             | 验证无残留引用、无死代码                                  |
| 轮换策略文档化       | 输出轮换操作手册                                        | 验证策略文档存在且可执行                                  |
