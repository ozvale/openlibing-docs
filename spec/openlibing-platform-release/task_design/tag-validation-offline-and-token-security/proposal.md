# 需求提案：tag 校验下线与 token 权限校验增强

## 需求背景

openlibing-platform-release 发布流程中存在两类问题：

1. **tag 校验机制失效且造成误阻断**：`SafeScanServiceImpl.executeVirusScan` 在病毒扫描完成后执行 Tag/commitId 一致性校验，将制品包构建 commitId 与仓库 tag commitId 比对。实际运行中发现该比对逻辑不可靠（制品 commitId 与 tag commitId 语义不一致），导致发布被错误阻断或产生误导性的 `tagValidationResult`/`tagValidationDetail` 展示，且校验成功后还会将 `releaseTagStatus` 置为 SUCCESS 影响后续状态流转。该校验应整体下线。
2. **GitCode token 权限校验缺失**：打 tag 与发布 Release 依赖项目公共账号的 GitCode token。此前仅在实际调用 GitCode API 时因 401/403 失败而报错，问题暴露滞后，且无法区分「token 无效」与「token 权限不足」。需要在提交评审、创建 tag、发布 Release 三个环节前置校验 token 有效性及权限。

## 目标

1. **tag 校验完全下线**：从 `SafeScanServiceImpl` 删除 Tag/commitId 一致性校验逻辑、`tagValidationResult`/`tagValidationDetail` 字段更新及相关枚举/常量，发布不再因 tag 不匹配被阻断。
2. **token 权限前置校验**：新增 `validateGitcodeToken`，在提交评审（operation=submit）、创建 tag、GitCode Release 发布三处前置校验，200/201 有效、401 无效、403 权限不足（提示勾选 `write_repository`）。
3. **tag 创建逻辑兜底增强**：`createTags` 改用查全量 tag 列表判断同名 tag 是否存在，已存在则跳过创建并将状态置 SUCCESS，避免误报失败。

## 验收标准

### 功能验收

| 功能点          | 验收标准                                                                                                             |
| --------------- | -------------------------------------------------------------------------------------------------------------------- |
| tag 校验下线    | `executeVirusScan` 不再调用 `validateTagCommitIdForRelease`，无 `tagValidationResult`/`tagValidationDetail` 更新逻辑 |
| 字段清理        | `ReleaseReviewVirusScanEntity` 中 tag 校验相关字段更新代码删除，前后端无残留引用                                     |
| 提交评审校验    | 提交评审（submit）时若含 gitcode/atomgit 仓库制品，校验 token，无效/无权限直接拒绝                                   |
| 保存不校验      | 仅保存（非 submit）不触发 token 校验，不阻断草稿                                                                     |
| createTags 校验 | 创建 tag 前置校验 token，无效/无权限时失败并给出明确原因                                                             |
| Release 校验    | GitCode Release 发布前校验 token                                                                                     |
| tag 已存在处理  | `createTags` 用全量 tag 列表判断，同名 tag 存在则跳过创建、状态置 SUCCESS                                            |
| 错误语义        | 401 报「令牌无效或已过期」，403 报「权限不足，请确认已勾选仓库读写(write_repository)权限」                           |

### 质量验收

| 质量指标 | 目标                                                                         |
| -------- | ---------------------------------------------------------------------------- |
| 代码规范 | 通过 checkstyle 检查                                                         |
| 无死代码 | 全仓库无 `validateTagCommitIdForRelease`、`TagValidationResultEnum` 残留引用 |
| 兼容性   | 提交评审接口入参/出参结构不变，前端无需改动                                  |

## 影响范围

- **业务仓**：`openlibing-platform-release`
- **核心改动文件**：
  - `SafeScanServiceImpl.java`（删除 tag 校验）
  - `ReleaseRepoTagHandleServiceImpl.java`（新增 validateGitcodeToken、createTags 优化）
  - `ReleaseBaseServiceImpl.java`（提交评审触发 token 校验）
  - `ReleaseDecisionServiceImpl.java`（GitCode Release 发布校验 token）
- **涉及外部接口**：新增调用 GitCode `GET /user?access_token=`、`GET /repos/{owner}/{repo}/tags`、`POST /repos/{owner}/{repo}/tags`（均已有使用，无契约变化）
- **无 DB 结构变更**（tag 校验字段仅停止更新，不物理删除列，避免迁移风险）
- **安全设计**：详见同目录 [threat-model.md](./threat-model.md) 与 [security-design.md](./security-design.md)

## 关联 Issue

- [https://gitcode.com/openlibing/openlibing-platform-release/issues/79](https://gitcode.com/openlibing/openlibing-platform-release/issues/79)（tag 验证场景修复属于该综合需求范围）
