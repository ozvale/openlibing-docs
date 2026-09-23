# 实现任务：tag 校验下线与 token 权限校验增强

## 任务清单

### 1. Tag 校验下线

- [x] 1.1 `SafeScanServiceImpl.executeVirusScan` 删除 `validateTagCommitIdForRelease` 调用
- [x] 1.2 删除 `tagValidationResult`/`tagValidationDetail` 字段更新逻辑
- [x] 1.3 删除 `MATCH_SUCCESS` 时置 `releaseTagStatus = SUCCESS` 的联动逻辑
- [x] 1.4 删除 `validateTagCommitIdForRelease` 私有方法定义
- [x] 1.5 清理多余导入（`TagValidationResultEnum`、`TagInfoVO`、`Optional`、`JSONObject` 等）
- [x] 1.6 确认 `queryRepoTagList` 方法保留（供 searchTags/createTags 使用）

### 2. Token 权限前置校验

- [x] 2.1 `ReleaseRepoTagHandleServiceImpl` 新增 `validateGitcodeToken(String accessToken)`
  - [x] 空值校验（400）
  - [x] `GET /user?access_token=` 校验，200/201 有效返回
  - [x] 401 → 「令牌无效或已过期」
  - [x] 403 → 「权限不足，请确认已勾选仓库读写(write_repository)权限」
  - [x] 其他非 200 → 「校验失败」
  - [x] 异常包装为 500「校验Gitcode访问令牌时发生未知错误」
  - [x] try-with-resources 关闭响应体
- [x] 2.2 `createTags` gitcode 分支：`SecurityManagerUtil.decrypt` 解密后调用 `validateGitcodeToken`
- [x] 2.3 `ReleaseBaseServiceImpl` 新增 `validateGitcodeTokenOnSubmit(dto, projectId)`：
  - [x] 遍历制品列表识别 gitcode/atomgit 仓库
  - [x] 无 gitcode 仓库则跳过校验
  - [x] 项目未配置 token → 「项目未配置gitcode访问令牌」
  - [x] `SecurityUtil.decrypt(token, part1)` 解密后校验
  - [x] 仅在 operation=submit 触发，save 不校验
- [x] 2.4 `ReleaseDecisionServiceImpl.handleArtifactGitcodeRelease` 发布前调用 `validateGitcodeToken`

### 3. createTags 兜底增强

- [x] 3.1 删除「tag 已校验成功则跳过创建」逻辑（不依赖病毒扫描）
- [x] 3.2 gitcode 分支遍历时改用 `queryRepoTagList` 查全量 tag 列表
- [x] 3.3 同名 tag 已存在 → 跳过创建，置 `releaseTagStatus = SUCCESS`
- [x] 3.4 创建异常 → 置 FAIL 并抛 `IllegalStateException`
- [x] 3.5 gitee 分支逻辑保持不变

### 4. 验证

- [ ] 4.1 编译通过（`mvn compile -q`）
- [ ] 4.2 提交评审（submit，含 gitcode 制品 + 有效 token）→ 正常提交
- [ ] 4.3 提交评审（submit，token 无效/未配置）→ 明确报错，评审单不落库
- [ ] 4.4 保存评审（save，token 无效）→ 不校验，正常保存
- [ ] 4.5 createTags：同名 tag 已存在 → 跳过创建、状态 SUCCESS
- [ ] 4.6 createTags：token 无效 → 前置失败，不进入 tag 创建
- [ ] 4.7 GitCode Release 发布：token 无效 → 阻断并给出原因
- [ ] 4.8 executeVirusScan 全流程：不再产生 tagValidationResult，发布不被 tag 不匹配阻断
- [ ] 4.9 grep 确认全仓无 `validateTagCommitIdForRelease`、`TagValidationResultEnum` 残留引用

## 提交记录

| Commit     | 说明                                                           |
| ---------- | -------------------------------------------------------------- |
| `223ef442` | feat(release): 新增gitcode token校验并优化tag创建逻辑          |
| `8e2cb009` | feat(release): 发布时自动生成软件包SHA256校验文件并上传Release |
| `eac76100` | build(deps): 升级 openlibing-common SDK 至 1.0.21.0            |

## 关联 Issue

- [https://gitcode.com/openlibing/openlibing-platform-release/issues/79](https://gitcode.com/openlibing/openlibing-platform-release/issues/79)
