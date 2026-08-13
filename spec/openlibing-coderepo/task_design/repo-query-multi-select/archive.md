# repo-query-multi-select — 最终归档

## 概要

- **业务 Issue**：[openlibing/openlibing-coderepo#57](https://gitcode.com/openlibing/openlibing-coderepo/issues/57)
- **业务 PR**：[openlibing/openlibing-coderepo#76](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/76)
- **目标接口**：`POST /project-repo/query-repo`
- **变更性质**：纯新增（无破坏性变更，向后兼容）
- **落地分支**：`feat-repo-query-filter-sort` → `release_20260630_iter2`

## 业务目标

`/project-repo/query-repo` 接口的筛选维度从 4 个（用途 / 可见性 / 语言 / 状态）扩展到 9 个，并支持多选（OR 语义），提升运营 / 管理场景下的查询灵活性。

## 落地范围

### 9 个多选字段

| 中文 | DTO List | DTO 单值 | Mapper 列 |
|------|----------|----------|-----------|
| 用途 | `purposes` | `purpose` | `purpose` |
| 可见性 | `visibilities` | `visibility` | `visibility` |
| 语言 | `repoLanguages` | `repoLanguage` | `repo_language` |
| 状态 | `statuses` | `status`（新增） | `status` |
| 平台 | `platforms` | `platform` | `platform` |
| 接管 PR | `assumePrs` | `assumePr` | `assume_pr` |
| 自动触发 | `autoTriggers` | `autoTrigger` | `auto_trigger` |
| 开源类型 | `openSources` | — | `open_source` |
| Webhook 状态 | `webhookStatuses` | `webhookStatus` | `webhook_status` |

### 关键设计

- **优先级**：List 非空走 `IN (...)`；List 为 null/空时回退到单值；两者都为空则不加该条件
- **SQL 安全**：`#{}` 预编译，无 `${}` 拼接，不存在注入风险
- **实现一致性**：三处 SQL（`queryRepoInfoByLimit` / `queryRepoInfo` / `count`）全部使用 `<choose>/<when>/<otherwise>` 模式
- **`openSources` 例外**：DTO 仅暴露 List 形态（`open_source` 原本不作为过滤维度，零回归）

## 关联 Commit

| Commit | 描述 |
|--------|------|
| `5f7b495` | feat(repo): support filter and time field sort in query-repo（前置 #56） |
| `042614f` | chore(repo): import List for upcoming multi-select filter work |
| `47ace31` | feat(repo): support multi-select filter for purpose/visibility/repoLanguage/status（首批 4 字段） |
| `3ce1d1f` | feat(repo): extend multi-select filter to platform/assumePr/autoTrigger/openSource/webhookStatus（扩展 5 字段） |

## 修改文件

业务仓 `openlibing-coderepo`：

- `QueryRepoDTO.java` — 新增 9 个 List 字段 + `status` 单值字段
- `RepoInfoEntity.java` — 新增 9 个 `@TableField(exist=false)` List 字段
- `RepoServiceImpl.java` — 透传 9 个 List + `status` 字段
- `RepoInfoMapper.xml` — 三处 SQL 共 9 个过滤维度改 `<choose>/<when>/<otherwise>`
- `RepoServiceImplTest.java` — 累计 117 个测试全通过（含本批次新增 3 个）
- `doc/api/repo-management.md` — 接口文档（多选示例 + 字段说明）

docs 仓 `openlibing-docs`（本 PR）：

- `spec/openlibing-coderepo/task_design/repo-query-multi-select/proposal.md`
- `spec/openlibing-coderepo/task_design/repo-query-multi-select/design.md`
- `spec/openlibing-coderepo/task_design/repo-query-multi-select/tasks.md`
- `spec/openlibing-coderepo/task_design/repo-query-multi-select/archive.md`（本文件）

## 关键决策与权衡

1. **多选 OR 语义**：符合"任一命中"运营直觉，未引入 AND 维度（多选 + 单值混合仅单值之间 AND）
2. **双轨保留 List + String**：保证旧调用方零回归，新调用方可分阶段切换
3. **MyBatis `<choose>` 而非拼接**：语义清晰、性能等价
4. **不开新 Issue / PR**：按业务侧要求扩展，沿用 PR #76 + 1 个增量 commit（`3ce1d1f`）

## 验证情况

- **功能测试**：`RepoServiceImplTest` 117 个测试全通过
- **兼容性**：旧字段（`purpose` / `visibility` / `repoLanguage` / `platform` / `assumePr` / `autoTrigger` / `webhookStatus`）行为不变
- **流水线**：`PR-pipeline_openlibing-coderepo` 在 4 个 commit 上各运行一次，codecheck 历史问题（非本 PR 范围）在提交前已存在
- **检视意见**：PR #76 收到 7 条 review 意见（1 条 P3 unused import 已在 `47ace31` 自动修复，6 条为 pre-existing code 范围外问题）；AI 已在 14:12 评论内给出逐条处理结论

## 复盘与可沉淀经验

### 经验 1：MyBatis 动态过滤统一用 `<choose>/<when>/<otherwise>` 而非多个 `<if>`

**问题**：若用多个并列 `<if>` 写"List 非空 OR String 非空"，SQL 条件会同时命中（产生 `field IN (...) OR field = ...` 的退化形式），既冗余又影响执行计划。

**对策**：用 `<choose>` 表达"先 List 后 String"的两段式短路语义，逻辑下沉到 SQL 层。

**建议沉淀**：当 DTO 出现"List + String 双轨"场景时，统一用 `<choose>`；不要拆成两个 `<if>`。

### 经验 2：单值回退到 List 的优先级文档化

**问题**：多选 + 单值同时传时，行为由实现决定而非 API 文档约定，容易让调用方误用。

**对策**：在 `doc/api/repo-management.md` 显式标注"多选字段非空时优先于单值字段"，并配合示例覆盖混合调用。

**建议沉淀**：每个新增 List 字段在 PR 描述中明确写"List 优先于 String"。

### 经验 3：扩展字段的"零单值"模式

**场景**：`openSources` 没有历史单值字段，直接新增 List 形态。

**建议**：对原本不在 DTO 过滤维度的字段，直接暴露 List 即可；不要为对齐"List+String"双轨而强行造一个单值字段。

## 后续可选优化（非本 PR 范围）

- 引入 `IN (...)` 长度上限（>100 项时改临时表 join）
- 9 个过滤维度统一用 `@QueryFilter` 自定义注解简化 DTO
- 前端联动：`openSource` 与 `assumePr` 灰显联动
- `count` 查询的 `info.` 前缀统一（当前混用 bare 与 `info.`）

## 关联资源

- 业务 PR：https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/76
- 业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/57
- 前置依赖：https://gitcode.com/openlibing/openlibing-coderepo/issues/56
- 业务 API 文档：`openlibing-coderepo/doc/api/repo-management.md`（1. 查询仓库信息）

Co-authored-by: Trae <noreply@trae.ai>
Generated-by: claude-sonnet-4-6
