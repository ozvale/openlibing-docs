# 结果展示新增包语言列 — package-language-column

## 业务 Issue

- openlibing/openlibing-sbom#75 — 【openlibing-sbom】结果展示新增包语言列
- https://gitcode.com/openlibing/openlibing-sbom/issues/75

## 需求背景

当前 SBOM 结果展示页面显示软件名、版本号、依赖类型、漏洞风险数值等，缺少依赖的**语言类型**。需要在查询以及详情页面显示每个依赖的语言类型，并支持筛选、多选。

## 功能描述

- 包语言类型从 `PACKAGE_MANAGER` 类别 purl 的 `type` 推导（maven/gradle→Java、npm→JavaScript、pypi→Python、composer→PHP、gem→Ruby、golang→Go、cargo→Rust、pub→Dart、dotnet→Dotnet、其余→Others），与 openlibing-sbom-tools 的 `LanguageFromPURL` 映射保持一致；语言值统一驼峰。
- 源码仓包（purl type ∈ {gitcode, gitee, github, atomgit}）调用平台 languages 接口取占比最高语言；C/C++ 统一为 `C/C++`；平台调用失败或无语言数据时默认 `C/C++`；未收录语言一律 `Others`。
- 查询结果缓存：`repo_language_cache` 表记录 repoUrl → language，先查表命中直接返回，miss 才请求远端并写回，避免重复调用平台 API。
- 在 `PackageStatistics` 预计算落库 `language` / `pkgManagerType` / `purl` 三个字段（`CollectStatisticsStep` 统计阶段计算，推导逻辑提取到 `PackageLanguageUtils` 工具类供导入/回填共用），新增/重新导入的 SBOM 自动填充。
- `PackageStatisticsVo` / 详情接口返回 `language` / `pkgManagerType` / `purl` 字段。
- `/querySbomPackagesMultiFilter` 请求新增 `languages` / `pkgManagerTypes` 多选过滤（组内 OR），漏洞数量汇总接口 `/querySbomPackagesVulCountSummary`（共享同一 DTO）同步生效，保证列表与汇总计数一致。
- `/querySbomPackagesVulCountSummary` 出参新增三个分布统计：`dependencyTypeCounts` / `languageCounts` / `pkgManagerTypeCounts`（参照 code-repo `queryRepoFilterMeta` 模式：分布查询排除自身维度过滤；`dependencyTypeCounts` 固定返回 DIRECT/INDIRECT/DIRECT_INDIRECT 三项，language/pkgManagerType 合并产品内候选值全集保证 0 计数选项也展示；均按 key 字典序排序）。
- 提供存量数据回填 REST 接口 `refreshPackageLanguage?pageNum=N`：以 product 为准（FINISH 状态产品全集按名称排序分页，每页 50 个 product），单 product 一次性加载全部包、内存填充后 `saveAll` 批量落库；单个 product 失败不阻断整体任务；三层耗时日志（load/fill/save + 慢包定位）。

## 不做

- 不修改旧接口 `querySbomPackages` / `querySbomPackageList` 行为
- 不修改前端代码（由前端后续切换）
- 不修改其他表结构（repo_language_cache 为本需求新增表，生产环境 `ddl-auto=none` 需手动建表）

## 验收标准

- [x] 新导入 SBOM 的每个包 statistics 含 language / pkgManagerType / purl（无 PACKAGE_MANAGER purl 时为 Others）
- [x] `querySbomPackagesMultiFilter` 支持 `languages` / `pkgManagerTypes` 多选过滤（组内 OR，组间 AND）
- [x] `querySbomPackagesVulCountSummary` 同样按 languages / pkgManagerTypes 过滤
- [x] `querySbomPackagesVulCountSummary` 返回三个分布统计 Map（全量选项含 0 计数，字典序）
- [x] 列表与详情出参含 language / pkgManagerType / purl 字段
- [x] 回填 REST 接口可按 pageNum 分批刷新存量数据，单 product 失败不阻断
- [x] repo_language_cache 缓存生效（重复回填/统计不再重复调平台 API）
- [x] 旧接口行为不受影响

## 影响范围

- 业务仓：`openlibing-sbom`（model / batch / dao / sbom-web）
- 无跨仓影响

## 流程模式

Standard 模式：proposal + design + tasks，UT 按 ai_memory 规则在 Phase 4 生成。
