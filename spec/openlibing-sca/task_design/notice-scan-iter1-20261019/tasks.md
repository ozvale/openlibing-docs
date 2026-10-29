# NOTICE 扫描大版本迭代（20261019 iter1）— 实现任务

## 进度: 6/8 complete

- [x] 新增接口：scanStatusByMultiFilter（分页状态查询 + 依赖拆解统计）、startBatch（批量发起）、exportBatch（批量导出）、clear（异步清空）、dependencyType/supplement（存量回填）；增强 /export（exportScope）与 /info（明细分页 + dependencyTypes 过滤 + 2×2 拆解统计）
- [x] 依赖类型：明细表新增 dependency_type（Liquibase changeset 1），SBOM 解析仅展开 PACKAGE_MANAGER externalRefs，统计口径 dependency_type=2 仅计直接依赖，回填后重建直接依赖合并 NOTICE
- [x] 下载链路：GitHub 镜像多前缀候选 + codeload 兜底、gitee 归档 URL 重建（issue #122）、瞬时失败指数退避重试、OBS 按 objectKey 读缓存、签名 URL 脱敏（issue #96 残留面）、JVM 代理生效、ossinfo 超时 20→60min
- [x] purl 解析：无版本 purl 各生态最新版本解析（Go/Maven/npm/PyPI）、versionless go purl 兜底链、下载产物反解真实版本回填（issue #123）、跳过间接/Python 依赖
- [x] NOTICE 生成：直接依赖合并 NOTICE 预生成并回填 direct_merged_oss_url（Liquibase changeset 2），新增 NoticeBatchMerger 与 NoticeExportScope 枚举
- [x] 工程治理：Dockerfile pluggy 钉住 + 构建期冒烟、SpotBugs 修复 3 处、amqp-client 显式引入；10 个测试类新增/更新
- [x] 创建 PR #329（`ms_notice` → `release_20261019_iter1`，41 commits），已打 `ai-assisted` 标签
- [ ] CI 流水线通过确认（创建时为 `ci-pipeline-running`）
- [ ] 手动验证：批量导出与多过滤状态查询结果正确

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/329
- 分支: `ms_notice` → `release_20261019_iter1`
- 关联 Issue: openlibing/openlibing-sca#88
- PR 内引用: #122（gitee 归档 URL）、#123（无版本 purl 版本回填）、#96（签名 URL 脱敏残留面）
- 关联子需求 spec: notice-scan-batch-export / notice-scan-status-multifilter / notice-scan-query-api / notice-dependency-type / ossinfo-extraction-notice
