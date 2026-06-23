# language-optional — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 移除 `RepoDTO.repoLanguage` 上的 `@NotBlank` 校验注解
- [x] Task 2: 移除 `ExternalRepoDTO.repoLanguage` 上的 `@NotBlank` 校验注解
- [x] Task 3: 移除 `RepoServiceImpl` 中 3 处判空报错逻辑
  - `createAndSaveRepoInfo`（/add-repo 路径）：移除 `if (StringUtils.isEmpty(language))` 报错
  - `updateRepoInfo`（/update-repo 路径）：移除 `if (StringUtils.isEmpty(language))` 报错
  - `externalAddRepoInfo`（/external/add-repo 路径）：移除 `if (StringUtils.isEmpty(language))` 报错
- [x] Task 4: 更新 `RepoServiceImplTest` 中 2 个断言旧报错的测试用例
  - `updateRepoInfo_InvalidLanguage`：改为验证无效语言不再报错，更新成功
  - `externalAddRepoInfo_LanguageError`：改为验证不再返回 "language error"
