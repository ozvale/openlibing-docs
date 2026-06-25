# repo-query-multi-select — 实现任务

## 进度: 0/7 complete

- [ ] Task 1: `QueryRepoDTO.java` 新增 4 个 List 字段（`purposes` / `visibilities` / `repoLanguages` / `statuses`）+ 1 个 `status` 单值字段
- [ ] Task 2: `RepoInfoEntity.java` 新增 4 个 `@TableField(exist=false)` List 字段
- [ ] Task 3: `RepoServiceImpl.queryRepoInfo` 透传新 List 字段 + `status` 字段
- [ ] Task 4: `RepoInfoMapper.xml` 三处 SQL（`queryRepoInfoByLimit` / `queryRepoInfo` / `count`）改 `<choose>/<when>/<otherwise>`
- [ ] Task 5: `RepoServiceImplTest.java` 覆盖多选命中、List 空回退单值、单值命中、status 过滤
- [ ] Task 6: 更新 `doc/api/repo-management.md` 接口文档
- [ ] Task 7: 运行 `mvn test` 验证相关测试通过，commit 并更新 PR #76
