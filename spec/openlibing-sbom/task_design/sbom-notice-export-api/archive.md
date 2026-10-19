# Archive: sbom-notice-export-api

> 归档日期：2026-10-19 ｜ 需求：notice增加版本级导出功能 ｜ 模式：Standard（页面功能开发流程）

## 需求与交付

【openlibing-sbom】notice增加版本级导出功能（[issue #113](https://gitcode.com/openlibing/openlibing-sbom/issues/113)）：sca 侧在 SBOM 页面新增"全量声明文档导出"，通过 Feign 调用 openlibing-sbom 获取数据。本需求交付 openlibing-sbom 侧 5 个 `/internal-api` 接口（feign 机机接口）：

| 接口                                                | 类型     | 说明                                        |
| --------------------------------------------------- | -------- | ------------------------------------------- |
| POST `/internal-api/queryProductNamesByMultiFilter` | 新增     | 按页面同条件（filters 同构）返回全量制品名  |
| POST `/internal-api/queryPackageDependencyTypes`    | 新增     | 制品下全部软件包依赖类型原始数据透传        |
| GET `/internal-api/queryProductConfig`              | 并行副本 | 旧接口不变，差异仅前缀/去横向鉴权/去 userId |
| POST `/internal-api/queryProduct`                   | 并行副本 | 同上                                        |
| `/internal-api/exportSbom`                          | 并行副本 | 同上（tar.gz 流响应）                       |

## 交付物

- 业务 PR：openlibing/openlibing-sbom#157（base：release_20261019_iter1，head：Chenmingxu:feat-sbom-notice-export-api）
- 提交：`77d3a34f`（5 接口初版）+ `828dc564`（v3 原始数据透传口径）
- 分支：feat-sbom-notice-export-api（基于 master 401b3d44 + release_20261013 合入 cf1af919）
- 测试环境：已合入源仓 sbom-dev（140dfafd），gamma 部署实测通过
- 设计文档（完整版）：D:\work\design\202610\sbom-notice-export-api.md
- 联调契约与验证用例：D:\work\design\202610\sbom-internal-api-contract.md

## 关键决策与演进

1. **feign 专用 controller**：新增 `InternalController`（`/internal-api`），参照 `ApigController`（`/apig-api`）机机接口先例——无横向鉴权、无 userId 入参；既有 3 接口以并行副本迁移，旧接口零改动，待 sca 切换后统一下线。
2. **接口 2 口径三次演进**（见 design.md 决策记录）：
   - v1：计算 downloadKey（NOASSERTION→purl）+ (name, version, downloadKey) 去重 + 0>2>1 优先级归并、null→-1；
   - v2：NONE 同样回退 purl；
   - v3（最终）：**只提供原始数据**——downloadLocation/purl/dependencyType 逐列透传，不去重、不归一化，取舍逻辑全部由 sca 侧处理。
3. **迁移副本原则**：方法体与原实现逐行同构（便于 diff 对比与统一下线），仅三处差异。

## 验证结论

- SbomServiceImplTest 89 用例全绿（含 8 个新增：filters 透传/非法 key/空参、原始透传、不去重、空制品边界）
- pre-commit 全部通过（Spotless/CheckStyle/SpotBugs/PMD/secrets）
- gamma 实测：两新接口验证通过

## 过程问题与修复（经验）

| 问题                                                                               | 根因                                                                                              | 修复                                                                                                        |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 接口 1 运行时报 `SELECT DISTINCT, ORDER BY expressions must appear in select list` | PostgreSQL 要求 DISTINCT 时 ORDER BY 表达式与 SELECT 列表一致，`p.name COLLATE "C"` ≠ 裸 `p.name` | COLLATE 收敛进 SELECT 列（`SELECT DISTINCT p.name COLLATE "C"`），ORDER BY 以输出列位置引用（`ORDER BY 1`） |
| 接口 2 运行时 `Long cannot be cast to Integer`                                     | PG native 标量投影中 int 列可能按 Long 返回                                                       | 经 `Number` 统一转换（null 安全）                                                                           |
| gamma 部署失败 `couldn't find remote ref refs/heads/sbom_dev`                      | 部署 job 分支名配置为下划线 `sbom_dev`，源仓实际为连字符 `sbom-dev`                               | 修正流水线分支配置；教训：**配置部署 job 时从源仓分支列表复制名称，避免连字符/下划线混写**                  |
| merge commit 被 pre-commit 反复回滚                                                | 钩子 stash 未暂存改动与 Spotless 自动格式化恢复冲突                                               | 先隔离本地无关改动（stash）→ commit 落地钩子格式化 → add 后重试                                             |

## 遗留事项

- 3 个旧接口（/sbom-api/queryProductConfig、queryProduct、exportSbom）待 sca 完成切换后统一下线（另行需求）
- sca 侧全量导出按钮与编排逻辑由 sca 团队交付（跨仓，不在本 spec 范围）
