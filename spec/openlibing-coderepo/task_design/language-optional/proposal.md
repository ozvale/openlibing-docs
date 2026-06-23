# language-optional

## 需求背景

`/add-repo`、`/external/add-repo`、`/update-repo` 三个接口的入参中，`repoLanguage`（语言）字段当前为必填项，传入空值或无法匹配配置中心语言列表时会报错"仓库语言不能为空"或"language error"，导致仓库无法创建/更新，影响外部接入流程。

经核查整个 Java 工作区所有项目，`repoLanguage` 字段仅用于以下两类场景：

1. **记录用途**：入库 `RepoInfoEntity.repoLanguage`，并复制到 `ProjectDTO.codeLanguage`、`TaskEntity.language` 等供展示和跨服务传递
2. **规则集语言匹配**：`setupDefaultRuleSetsAndTriggerCodecheck` 根据语言设置默认 codecheck/防投毒规则集（空值时已 return 保护）；`openlibing-codecheck` 从实体读取做规则集匹配

该字段不涉及鉴权、关键业务分支、安全校验等实际作用，适合改为非必传。

## 功能描述

- 移除 `RepoDTO`、`ExternalRepoDTO` 上 `repoLanguage` 的 `@NotBlank` 校验
- 移除 `RepoServiceImpl` 中 3 处判空报错逻辑（`createAndSaveRepoInfo`、`updateRepoInfo`、`externalAddRepoInfo`）
- 保留 `getRepoLanguage()` 归一化逻辑（传值时仍做大小写适配如 `JAVA→Java`、`C++→cpp`），未传或未匹配时存空字符串
- 后续 `setupDefaultRuleSetsAndTriggerCodecheck` 自行判空跳过规则集设置，不影响流程

## 验收标准

- [ ] `/add-repo` 不传 `repoLanguage` 时能正常创建仓库
- [ ] `/external/add-repo` 不传 `repoLanguage` 时能正常创建仓库
- [ ] `/update-repo` 不传 `repoLanguage` 时能正常更新仓库
- [ ] 传无效语言时不再报错（存空字符串）
- [ ] 传有效语言时规则集设置功能正常

## 影响范围

- 修改文件：
  - `RepoDTO.java`（移除 `@NotBlank`）
  - `ExternalRepoDTO.java`（移除 `@NotBlank`）
  - `RepoServiceImpl.java`（移除 3 处判空报错）
  - `RepoServiceImplTest.java`（更新 2 个测试用例）
- 影响接口：`/project-repo/add-repo`、`/project-repo/external/add-repo`、`/project-repo/update-repo`

## 关联 Issue

openlibing/openlibing-coderepo#49
