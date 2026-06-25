# repo-query-multi-select

## 需求背景

`/project-repo/query-repo` 接口当前 `purpose` / `visibility` / `repoLanguage` 是单值精确匹配，且 `status` 字段还未作为过滤维度透出。运营场景下经常需要"按多个用途组合筛选"或"按多种可见性组合筛选"等，仅靠前端多次请求拼接显然不满足实时性需求。

前置依赖：
- filter/sort 能力（[#56](https://gitcode.com/openlibing/openlibing-coderepo/issues/56)）已在 `feat-repo-query-filter-sort` 分支
- 排序白名单与 Mapper 动态排序已就位

## 功能描述

为 `QueryRepoDTO` 新增多选过滤字段（JSON List，OR 语义），同时新增 `status` 单值过滤字段，原单值字段保留以兼容旧调用方。

### 新增多选字段

| 中文 | DTO 新增 List 字段 | DTO 保留 String 字段 | Mapper 列 |
|------|-------------------|----------------------|----------|
| 用途 | `purposes` | `purpose` | `purpose` |
| 可见性 | `visibilities` | `visibility` | `visibility` |
| 语言 | `repoLanguages` | `repoLanguage` | `repo_language` |
| 状态 | `statuses` | `status`（新增） | `status` |

### 语义与优先级

- 多选语义：OR（任一命中即返回）
- 优先级：List 字段非空时走 `IN (...)`；List 为空/null/空串时回退到单值字段；两者都为空则不加该过滤条件

## 验收标准

- [ ] `QueryRepoDTO` 新增 `purposes` / `visibilities` / `repoLanguages` / `statuses` 四个 List 字段，并新增 `status` 单值字段
- [ ] `RepoInfoEntity` 新增对应 4 个 `@TableField(exist=false)` List 字段
- [ ] `RepoServiceImpl.queryRepoInfo` 透传新字段
- [ ] `RepoInfoMapper.xml` 三处 SQL（`queryRepoInfoByLimit` / `queryRepoInfo` / `count`）将 4 个过滤条件改为 `<choose>/<when>/<otherwise>`：先判 List，非空走 `IN (...)`，否则回退到单值
- [ ] 旧的单值调用 `purpose=...` / `visibility=...` / `repoLanguage=...` 行为不变（向后兼容）
- [ ] 补充/更新单元测试覆盖：多选命中、List 空回退单值、单值命中
- [ ] 更新 `doc/api/repo-management.md` 接口文档

## 影响范围

- 修改文件：
  - `QueryRepoDTO.java`（新增 4 个 List 字段 + status 单值字段）
  - `RepoInfoEntity.java`（新增 4 个 `@TableField(exist=false)` List 字段）
  - `RepoServiceImpl.java`（透传新字段）
  - `RepoInfoMapper.xml`（3 处 SQL 改 `<choose>`）
  - `RepoServiceImplTest.java`（新增/更新测试）
  - `doc/api/repo-management.md`（接口文档）
- 影响接口：`/project-repo/query-repo`
- 无数据库 schema 变更
- 无破坏性变更（全部为新增参数）

## 关联

- 依赖：openlibing/openlibing-coderepo#56
- 关联业务 Issue：openlibing/openlibing-coderepo#57
- 关联 PR：openlibing/openlibing-coderepo#76（与 #56 合并出）

Co-authored-by: Trae <noreply@trae.ai>
Generated-by: claude-sonnet-4-6
