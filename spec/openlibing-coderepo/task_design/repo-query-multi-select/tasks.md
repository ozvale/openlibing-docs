# repo-query-multi-select — 实现任务

## 进度: 14/14 complete

### 首批 4 字段多选（commit `47ace31`）

- [x] Task 1: `QueryRepoDTO.java` 新增 4 个 List 字段（`purposes` / `visibilities` / `repoLanguages` / `statuses`）+ 1 个 `status` 单值字段
- [x] Task 2: `RepoInfoEntity.java` 新增 4 个 `@TableField(exist=false)` List 字段
- [x] Task 3: `RepoServiceImpl.queryRepoInfo` 透传新 List 字段 + `status` 字段
- [x] Task 4: `RepoInfoMapper.xml` 三处 SQL（`queryRepoInfoByLimit` / `queryRepoInfo` / `count`）改 `<choose>/<when>/<otherwise>`
- [x] Task 5: `RepoServiceImplTest.java` 覆盖多选命中、List 空回退单值、单值命中、status 过滤
- [x] Task 6: 更新 `doc/api/repo-management.md` 接口文档
- [x] Task 7: 运行 `mvn test` 验证相关测试通过，commit 并推送

### 扩展 5 字段多选（commit `3ce1d1f`，沿用 PR #76，未新建 Issue）

- [x] Task 8: `QueryRepoDTO.java` 新增 5 个 List 字段（`platforms` / `assumePrs` / `autoTriggers` / `openSources` / `webhookStatuses`）
- [x] Task 9: `RepoInfoEntity.java` 新增 5 个 `@TableField(exist=false)` List 字段
- [x] Task 10: `RepoServiceImpl.queryRepoInfo` 透传 5 个新 List 字段
- [x] Task 11: `RepoInfoMapper.xml` 三处 SQL 的 5 个新过滤条件改 `<choose>/<when>/<otherwise>`（`open_source` 仅 List 单分支）
- [x] Task 12: `RepoServiceImplTest.java` 新增 3 个测试覆盖 5 字段多选命中 / 空 List 回退 / 多选覆盖单值
- [x] Task 13: 更新 `doc/api/repo-management.md` 接口文档（5 字段说明 + 多选示例）
- [x] Task 14: 推送 `3ce1d1f` 到 fork、刷新 PR #76 描述、发布跟进评论
