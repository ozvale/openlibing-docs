# 技术设计：tag 校验下线与 token 权限校验增强

## 1. 总体方案

本需求分三块改造：

1. **Tag 校验下线**：删除 `SafeScanServiceImpl.executeVirusScan` 中的 Tag/commitId 一致性校验（含 `validateTagCommitIdForRelease` 方法、`TagValidationResultEnum`、`TagInfoVO` 相关导入与调用），`tagValidationResult`/`tagValidationDetail` 字段停止更新，不再因 tag 不匹配阻断发布。
2. **Token 权限前置校验**：在 `ReleaseRepoTagHandleServiceImpl` 新增 `validateGitcodeToken(accessToken)`，通过 `GET /user?access_token=` 校验 token 状态（200/201 有效、401 无效、403 权限不足）；在提交评审（submit）、创建 tag、GitCode Release 发布三处调用。
3. **createTags 兜底增强**：从「校验成功后跳过创建」改为「查全量 tag 列表，同名已存在则跳过创建并将状态置 SUCCESS」。

## 2. Tag 校验下线设计

### 2.1 删除范围

| 位置                                   | 删除内容                                                                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `SafeScanServiceImpl.executeVirusScan` | `validateTagCommitIdForRelease` 调用、`tagValidationResult`/`tagValidationDetail` 更新、`MATCH_SUCCESS` 时置 SUCCESS 逻辑 |
| `SafeScanServiceImpl`                  | `validateTagCommitIdForRelease` 私有方法定义（含 queryRepoTagList/compare 逻辑）                                          |
| 导入                                   | `TagValidationResultEnum`、`TagInfoVO`、`Optional`、`JSONObject` 等仅用于 tag 校验的导入                                  |
| 字段更新                               | `ReleaseReviewVirusScanEntity` 不再 set `tagValidationResult`/`tagValidationDetail`                                       |

**注意**：`queryRepoTagList` 方法本身保留（`searchTags` 分页搜索与 `createTags` 全量判断仍使用），仅删除校验专用逻辑。

### 2.2 下线后的风险与兜底

| 风险                                    | 兜底控制                                                                               |
| --------------------------------------- | -------------------------------------------------------------------------------------- |
| tag 与制品 commitId 不一致不再阻断      | `createTags` 仍会创建/校验 tag；GitCode 对已存在同名 tag 会报错；SHA256 完整性校验保留 |
| 旧数据残留 `tagValidationResult` 字段值 | 仅停止更新，字段不物理删除，历史数据保持只读，不影响查询                               |

## 3. Token 权限前置校验设计

### 3.1 校验方法

```java
public void validateGitcodeToken(String accessToken) throws BusinessException {
  // 1. 空值校验
  if (StringUtils.isBlank(accessToken)) {
    throw new BusinessException("Gitcode访问令牌获取失败", 400);
  }
  // 2. GET /user?access_token=<token> 校验
  String validateUrl = GITCODE_URL_PREFIX + "user?access_token=" + accessToken;
  try (Response validateResponse = HttpRequestUtil.getResponse(validateUrl)) {
    // 200/201 → 有效，直接返回
    // 401 → BusinessException("Gitcode访问令牌无效或已过期: <errorMessage>")
    // 403 → BusinessException("Gitcode访问令牌权限不足，请确认访问令牌已勾选仓库读写(write_repository)权限: <errorMessage>")
    // 其他 → BusinessException("Gitcode访问令牌校验失败: <errorMessage>")
  } catch (BusinessException e) {
    throw e;
  } catch (Exception e) {
    throw new BusinessException("校验Gitcode访问令牌时发生未知错误: " + e.getMessage(), 500);
  }
}
```

**要点**：

- `errorMessage` 从响应体 `error_message` 或 `message` 字段解析，解析失败回退 "Unknown error"
- 401/403 分别给出明确语义，便于用户定位 token 问题
- 响应体关闭用 try-with-resources，避免连接泄漏

### 3.2 三个调用点

| 调用点          | 位置                                                      | 时机                 | 触发条件                                                                                                    |
| --------------- | --------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------- |
| 提交评审        | `ReleaseBaseServiceImpl` → `validateGitcodeTokenOnSubmit` | operation=submit     | 制品含 gitcode/atomgit 仓库（遍历 `dto.getReleaseArtifactInfoList()`，`repoUrl` 含 gitcode/atomgit 则校验） |
| 创建 tag        | `ReleaseRepoTagHandleServiceImpl.createTags`              | gitcode/atomgit 分支 | `repoUrl` 含 gitcode/atomgit 时，用 `SecurityManagerUtil.decrypt` 解密项目 token 后校验                     |
| GitCode Release | `ReleaseDecisionServiceImpl.handleArtifactGitcodeRelease` | 发布前               | `repoUrl` 含 gitcode 时校验                                                                                 |

**token 解密差异说明**：

| 调用点          | 解密方式                                                     |
| --------------- | ------------------------------------------------------------ |
| 提交评审        | `SecurityUtil.decrypt(accountInfo.getGitcodeToken(), part1)` |
| 创建 tag        | `SecurityManagerUtil.decrypt(accountInfo.getGitcodeToken())` |
| GitCode Release | 同提交评审（`SecurityUtil.decrypt(token, part1)`）           |

> 双解密路径不一致属于既有现状，本需求不统一改造（详见 security-design.md 轮换策略评估），仅在其各自解密路径上追加 `validateGitcodeToken` 校验。

### 3.3 提交评审校验细节

`validateGitcodeTokenOnSubmit(ReleaseReviewDTO dto, String projectId)`：

```java
// 1. 遍历制品列表，repoId 非空则查 RepoVo
// 2. 只要存在 repoUrl 含 gitcode/atomgit 的仓库 → hasGitcodeRepo = true
// 3. 无 gitcode 仓库 → return（不校验，兼容纯 gitee 或 OBS 发布）
// 4. 查询项目公共账号信息 queryProjectCommonAccountInfoEntity(projectId)
// 5. accountInfo 为空或 gitcodeToken 为空 → BusinessException("项目未配置gitcode访问令牌", 400)
// 6. SecurityUtil.decrypt(token, part1) → validateGitcodeToken(accessToken)
```

**设计决策**：仅 submit 校验、save 不校验，避免用户保存草稿时因 token 未配置被阻断；校验放行/失败不持久化 token 状态到评审单（保持评审单数据结构不变）。

## 4. createTags 兜底增强设计

### 4.1 原逻辑与问题

| 版本 | 逻辑                                                                         | 问题                                                                        |
| ---- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 原   | 若病毒扫描 tag 校验已 MATCH_SUCCESS 则跳过 tag 创建                          | 依赖已下线的 tag 校验；跳过时 `releaseTagStatus` 可能仍为执行中，状态不闭环 |
| 新   | 前置 `validateGitcodeToken`；查全量 tag 列表，同名存在则跳过创建并置 SUCCESS | 不依赖病毒扫描；全量判断避免分页漏判；状态闭环                              |

### 4.2 新流程

```text
createTags(releaseArtifactInfoVO, projectId, repoTagVos)
  ├─ 读取项目公共账号信息
  ├─ repoUrl 含 gitcode/atomgit:
  │    ├─ SecurityManagerUtil.decrypt(gitcodeToken)
  │    ├─ validateGitcodeToken(accessToken)          # 前置校验
  │    ├─ 置 releaseTagStatus = EXECUTING
  │    └─ 遍历 repoTagVos:
  │         ├─ queryRepoTagList(projectId, repoUrl)  # 查全量（不用分页，避免漏判）
  │         ├─ 同名 tag 存在 → 跳过创建，置 SUCCESS
  │         └─ 不存在 → createGitcodeSingleTag(...) → 置 SUCCESS；异常置 FAIL 并抛 IllegalStateException
  └─ repoUrl 含 gitee: 原有逻辑保留（不校验 gitcode token）
```

## 5. 涉及文件清单

| 文件                                   | 类型 | 说明                                                                        |
| -------------------------------------- | ---- | --------------------------------------------------------------------------- |
| `SafeScanServiceImpl.java`             | M    | 删除 tag 校验调用、字段更新、`validateTagCommitIdForRelease` 方法及多余导入 |
| `ReleaseRepoTagHandleServiceImpl.java` | M    | 新增 `validateGitcodeToken`；`createTags` 改全量判断 + 前置校验 + 状态闭环  |
| `ReleaseBaseServiceImpl.java`          | M    | 新增 `validateGitcodeTokenOnSubmit`，submit 时触发                          |
| `ReleaseDecisionServiceImpl.java`      | M    | `handleArtifactGitcodeRelease` 前置 token 校验                              |
| `pom.xml`                              | M    | openlibing-common SDK 升级至 1.0.21.0（关联变更）                           |

## 6. 风险与回滚

| 风险                                              | 应对                                                                                                             |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| token 校验误杀（token 有效但 GitCode 偶发非 200） | 仅 401/403/其他非 200 判定失败，其余走未知错误分支；可在配置侧开关灰度（本需求未引入开关，若线上误伤需紧急回滚） |
| 双解密路径不一致                                  | 不统一改造，保持各调用点现有解密，仅追加校验                                                                     |
| 全量 tag 查询性能                                 | `queryRepoTagList` 全量拉取，超大仓库 tag 多时耗时有增加；发布频率低，可接受                                     |
| tag 校验下线导致误发布                            | createTags 兜底 + SHA256 校验保留，风险可控                                                                      |

## 7. 安全设计衔接

- 威胁建模与 STRIDE 评估：见 [threat-model.md](./threat-model.md)
- 认证授权、token 加密存储评估、轮换手册、日志脱敏、验证计划：见 [security-design.md](./security-design.md)
