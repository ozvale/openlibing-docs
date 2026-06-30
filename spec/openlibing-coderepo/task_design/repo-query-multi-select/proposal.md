# repo-query-multi-select

## 需求背景

`/project-repo/query-repo` 接口当前大部分过滤字段是单值精确匹配，且 `status` / `openSource` 字段还未作为过滤维度透出。运营场景下经常需要"按多个用途组合筛选"或"按多种可见性组合筛选"等，仅靠前端多次请求拼接显然不满足实时性需求。

在 4 个核心字段（用途 / 可见性 / 语言 / 状态）已支持多选后，**业务侧继续提出扩展诉求**：5 个原本仅支持单值的字段也需要多选能力（平台、接管 PR、自动触发、开源类型、Webhook 状态）。本次 spec 在初版基础上扩展到 **9 个多选维度**，与单值字段双轨保留。

前置依赖：
- filter/sort 能力（[#56](https://gitcode.com/openlibing/openlibing-coderepo/issues/56)）已在 `feat-repo-query-filter-sort` 分支
- 排序白名单与 Mapper 动态排序已就位
- 首批 4 字段多选（commit `47ace31`）已落地并通过 PR #76 评审

## 功能描述

为 `QueryRepoDTO` 新增多选过滤字段（JSON List，OR 语义），原单值字段保留以兼容旧调用方。

### 新增多选字段（首批 4 + 扩展 5 = 共 9 个）

| 中文 | DTO 新增 List 字段 | DTO 保留 String 字段 | Mapper 列 | 批次 |
|------|-------------------|----------------------|----------|------|
| 用途 | `purposes` | `purpose` | `purpose` | 首批 |
| 可见性 | `visibilities` | `visibility` | `visibility` | 首批 |
| 语言 | `repoLanguages` | `repoLanguage` | `repo_language` | 首批 |
| 状态 | `statuses` | `status`（新增） | `status` | 首批 |
| 平台 | `platforms` | `platform` | `platform` | 扩展 |
| 接管 PR | `assumePrs` | `assumePr` | `assume_pr` | 扩展 |
| 自动触发 | `autoTriggers` | `autoTrigger` | `auto_trigger` | 扩展 |
| 开源类型 | `openSources` | — | `open_source` | 扩展（仅有 List） |
| Webhook 状态 | `webhookStatuses` | `webhookStatus` | `webhook_status` | 扩展 |

### 语义与优先级

- 多选语义：OR（任一命中即返回）
- 优先级：List 字段非空时走 `IN (...)`；List 为空/null/空串时回退到单值字段；两者都为空则不加该过滤条件
- 扩展字段 `openSources` 没有对应单值字段，DTO 只暴露 List

## 验收标准

- [x] `QueryRepoDTO` 新增 9 个 List 字段（`purposes` / `visibilities` / `repoLanguages` / `statuses` / `platforms` / `assumePrs` / `autoTriggers` / `openSources` / `webhookStatuses`）+ 1 个 `status` 单值字段
- [x] `RepoInfoEntity` 新增对应 9 个 `@TableField(exist=false)` List 字段
- [x] `RepoServiceImpl.queryRepoInfo` 透传新字段
- [x] `RepoInfoMapper.xml` 三处 SQL（`queryRepoInfoByLimit` / `queryRepoInfo` / `count`）将 9 个过滤条件改为 `<choose>/<when>/<otherwise>`：先判 List，非空走 `IN (...)`，否则回退到单值
- [x] 旧的单值调用 `purpose=...` / `visibility=...` / `repoLanguage=...` / `platform=...` / `assumePr=...` / `autoTrigger=...` / `webhookStatus=...` 行为不变（向后兼容）
- [x] 补充/更新单元测试覆盖：多选命中、List 空回退单值、单值命中
- [x] 更新 `doc/api/repo-management.md` 接口文档
- [x] 沿用 PR #76 推送，未新建 Issue / PR（按业务侧要求）

## 影响范围

- 修改文件：
  - `QueryRepoDTO.java`（新增 9 个 List 字段 + status 单值字段）
  - `RepoInfoEntity.java`（新增 9 个 `@TableField(exist=false)` List 字段）
  - `RepoServiceImpl.java`（透传新字段）
  - `RepoInfoMapper.xml`（3 处 SQL 改 `<choose>`，9 个过滤维度）
  - `RepoServiceImplTest.java`（新增/更新测试）
  - `doc/api/repo-management.md`（接口文档）
- 影响接口：`/project-repo/query-repo`
- 无数据库 schema 变更
- 无破坏性变更（全部为新增参数）

## 关联

- 依赖：openlibing/openlibing-coderepo#56（filter/sort 能力）
- 关联业务 Issue：openlibing/openlibing-coderepo#57
- 关联业务 PR：openlibing/openlibing-coderepo#76（与 #56 合并出，沿用本 PR 扩展 5 字段）

Co-authored-by: Trae <noreply@trae.ai>
Generated-by: claude-sonnet-4-6
