# 结果展示新增包语言列 — 技术设计

## 方案概述

复用 `dependency-type-identification` 先例：`PackageStatistics` 新增 `language` / `pkgManagerType` / `purl` 三列，`CollectStatisticsStep` 统计阶段双轨推导（包管理器 purl type 映射 + 源码仓包调平台 languages API 取最高占比，命中 repo_language_cache 缓存表优先）并落库；推导逻辑提取到 `PackageLanguageUtils`（导入/回填共用）；查询链路（MultiFilter DAO 方法）新增 `languages` / `pkgManagerTypes` 多选过滤片段；`PackageStatisticsVo` 与详情接口透出三字段；汇总接口返回三个分布统计；新增 `refreshPackageLanguage?pageNum=N` 回填接口（FINISH 状态产品分页 + saveAll 批量落库）。

## 架构决策

### 决策 1：双轨语言推导（purl type 映射 + 源码仓 languages API），枚举落库

包语言未存储，按包来源分两轨推导：

**轨 A — 包管理器包**：`external_purl_ref`（category=PACKAGE_MANAGER）的 `purl->>'type'` 确定性映射语言，映射表与 openlibing-sbom-tools `LanguageByName` 一致。**存储与展示值（displayName）统一驼峰**（与平台 languages API 返回值风格一致，如 `JavaScript`、`TypeScript`、`Others`）：

| purl type                      | 语言       |
| ------------------------------ | ---------- |
| maven / gradle / java          | Java       |
| npm                            | JavaScript |
| pypi                           | Python     |
| composer                       | PHP        |
| gem                            | Ruby       |
| golang                         | Go         |
| cargo                          | Rust       |
| pub                            | Dart       |
| dotnet                         | Dotnet     |
| 其他 / 无 PACKAGE_MANAGER purl | Others     |

**轨 B — 源码仓包**：判定条件为**包的第一个 PACKAGE_MANAGER purl 的 `type` ∈ {gitcode, gitee, github, atomgit}**（实现期从 `comment="source_code_url"` 判定改为按 purl type 判定——comment 判定依赖 `SpdxReader` 落库口径，type 判定更直接且覆盖 atomgit）。这类包按 purl 的 type/namespace/name 构造仓库 URL 调用平台 languages 接口取占比最高的语言：

| 平台    | 接口                                         | 返回格式（实测）                                                                       | 已有实现                                     |
| ------- | -------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------- |
| GitCode | `GET /api/v5/repos/{owner}/{repo}/languages` | `{"C++": 36.62, "C": 63.13, "Makefile": 0.26}`（语言→百分比）                          | `GitCodeApi`（带 PRIVATE-TOKEN + 重试 2 次） |
| GitHub  | `GET /repos/{owner}/{repo}/languages`        | `{"C++": 5347064, "C": 782492, ...}`（语言→字节数）                                    | `GithubApi`                                  |
| Gitee   | `GET /api/v5/repos/{owner}/{repo}/languages` | `{"languages": [{"language":"Rust","percent":69.6,"bytes":1530232}, ...]}`（包装数组） | `GiteeApi`                                   |

三平台返回值单位不同（百分比 / 字节 / percent+bytes 对象），但**只取单次响应内 value 最大的语言，单位不影响比较**。统一契约：`VcsApi.getRepoLanguages(owner, repo)` 各实现解析后归一为 `Map<String, Double>`（语言 → 数值），`VcsServiceImpl` 取 value 最大 key。**C / C++ 统一归为 C/C++**；**平台调用失败或仓库无语言数据时默认 `C/C++`**；返回了语言但未收录 → Others。

新增枚举 `PackageLanguage`（`model/enums`），枚举名大写（`JAVA`、`JAVASCRIPT`…），`displayName` 为存储与展示值、统一驼峰（如 `Java`、`JavaScript`、`C/C++`、`C#`、`Others`），提供静态 `fromPurlType(String)` 与 `fromRepoLanguage(String)`（C/C++ 归一；**null/blank 入参即平台调用失败 → 返回 `C_CPP` 兜底**；未收录语言返回 `OTHERS`，displayName `Others`）；`PackageStatistics.language` 存 displayName TEXT，两种轨都推导不出时显式存 `Others`（非 NULL）。同列落库 `pkgManagerType`（purl type）与 `purl`（完整 purl 串），供查询与前端展示。

### 决策 2：预计算在 CollectStatisticsStep 同步调 API（命中缓存优先），回填用 Java 分页批处理

- 新导入：`collectPackageStatistics` 内调 `PackageLanguageUtils.fillLanguageFields`（轨 A/轨 B 统一入口）：轨 B 按 purl 的 type/namespace/name 构造仓库 URL 调 `VcsServiceImpl.getRepoTopLanguage(url)`；否则 `fromPurlType`（轨 A）。推导逻辑提取到 utils 模块 `PackageLanguageUtils`（导入与回填共用一份实现，符合 ai_memory "公用逻辑提取到 utils" 规则）。
- **语言缓存**：新增 `repo_language_cache` 表（repo_url 唯一键 → language）。`getRepoTopLanguage` 先查缓存，命中直接返回；miss 才调远端 API，成功后写回（写缓存失败仅告警不影响主流程），避免存量回填等场景重复调平台 API。
- 存量回填：**不用纯 SQL**（轨 B 语言来自 REST API，SQL 无法推导）。回填接口 `refreshPackageLanguage?pageNum=N`：先查全部 FINISH 状态产品的 productName（排序保证分页稳定），每页固定 50 个 product；单 product 一次性加载全部包（最多约 1 万+ 包，不分页），内存逐包 `fillLanguageFields` 后 `saveAll` 批量落库（避免逐条 save 的 N 次 DB 往返）；单个 product 失败（DB/VCS API 异常）返回 -1 并继续后续 product，不中断整体任务；输出 load/fill/save 三层耗时与慢包（>200ms，多为走远端 API）定位日志。

### 决策 3：多选过滤沿用逗号字符串 + `string_to_array` 模式

请求 DTO 新增 `List<String> languages` 与 `List<String> pkgManagerTypes`（`dependencyTypes` 为 `List<Integer>`）；Service 层拼接逗号分隔字符串；DAO MultiFilter 方法新增同一过滤片段（以 languages 为例）：

```sql
AND (:languages IS NULL OR :languages = ''
  OR COALESCE(ps.language, 'Others') = ANY(string_to_array(:languages, ',')))
```

`COALESCE(..., 'Others')` 兼容回填前的 NULL 存量数据，使选择 Others 也能命中。`pkgManagerTypes` 过滤片段同样统一 `COALESCE(ps.pkg_manager_type, 'Others')`（含分组子查询 `ps2` 在内共 7 处），`PackageStatisticsVo.fromPackage` 对 language / pkgManagerType 空值统一兜底 `Others`，保证 SQL 与 VO 口径一致。`sumVulCountByMultiFilter` 与列表共享 DTO，同步加过滤以保证汇总计数与列表一致。

### 决策 4：汇总接口分布统计（参照 queryRepoFilterMeta 模式）

`getVulCountSummaryMultiFilter` 出参新增三个分布 Map：`dependencyTypeCounts` / `languageCounts` / `pkgManagerTypeCounts`：

- **排除自身维度过滤**：每个分布查询排除该维度自身的入参过滤（如统计 languageCounts 时不带 languages 条件），只保留其余维度过滤，保证面板显示未被当前选择"过滤掉"的选项计数。
- **全量选项含 0 计数**：`dependencyTypeCounts` 固定返回 `DependencyType` 枚举三项（DIRECT=0 / INDIRECT=1 / DIRECT_INDIRECT=2），无数据的项计 0；language / pkgManagerType 通过 `findDistributionCandidatesByProduct` 查询产品内该维度去重候选值全集，与查询结果合并补 0，保证选中过滤后其余选项仍展示。
- **字典序排序**：三个 Map 均按 key 字典序（`Map.Entry.comparingByKey()`）返回，前端渲染稳定。
- 分布 SQL 同时带上漏洞严重级（includeVulSeverities / excludeVulSeverities）过滤，与汇总数值口径一致。

### 决策 5：出参透出

- `PackageStatisticsVo` 新增 `language` / `pkgManagerType` / `purl` 三字段：statistics 存在时取对应值（language / pkgManagerType null 兜底 Others），statistics 为 null 时 language 返回 Others。
- 详情接口 `getPackageInfoById` 直接返回 `Package` 实体，实体序列化含 `packageStatistics`，新增字段自动透出，无需额外改动。

### 决策 6：publishSbom 附带优化（搭车改动）

- 已有 rawSbom 且 taskStatus 为 WAIT（尚未被调度捞起）时允许**直接覆盖重发**；仅 FINISH / FAILED_FINISH / WAIT（及历史无状态记录）允许覆盖，RUNNING 等执行中状态拒绝发布。
- 覆盖采用**原子条件 UPDATE**（`RawSbomRepository.updateRawSbomIfStatusAllowed`）：`UPDATE raw_sbom SET value/task_id/task_status ... WHERE id = :id AND (task_status IS NULL OR task_status IN (:allowed))`，更新行数为 0 即状态已被并发修改（如调度器捞起置 RUNNING），抛 `SbomRuntimeException`——关闭 check-then-save 期间任务被调起的时序窗口；无历史记录时直接插入，唯一索引 `raw_sbom_uk(value_type, product_id)` 防并发重复插入。
- 状态判断用 `queryRawSbomMeta` 轻量投影查询（`RawSbomMetaVo`：id / taskStatus / createTime），避免加载 `value` 大字段；product 不存在改抛 `SbomRuntimeException`（可透出给调用方）。
- Controller 错误消息分级透出：`SbomRuntimeException`（参数校验 / 任务冲突等业务消息）附带到 errorInfo 便于定位冲突原因；其余异常仅记日志、对外固定文案 `publish sbom failed!`，避免内部细节泄露。

## 涉及文件

| 文件                                                              | 操作 | 说明                                                                                                                                   |
| ----------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `model/.../enums/PackageLanguage.java`                            | 新增 | 语言枚举（displayName）+ `fromPurlType` + `fromRepoLanguage`（C/C++ 归一）                                                             |
| `model/.../entity/PackageStatistics.java`                         | 修改 | 新增 `language` / `pkgManagerType` / `purl` 三列                                                                                       |
| `model/.../entity/RepoLanguageCache.java`                         | 新增 | 仓库语言缓存表实体（repo_url 唯一键 → language）                                                                                       |
| `model/.../vo/sbom/PackageStatisticsVo.java`                      | 修改 | 新增 `language` / `pkgManagerType` / `purl` 字段 + `fromPackage` 填充（language / pkgManagerType 空值兜底 Others）                     |
| `model/.../vo/sbom/VulCountSummaryVo.java`                        | 修改 | 新增 `dependencyTypeCounts` / `languageCounts` / `pkgManagerTypeCounts` 三个 Map 字段                                                  |
| `model/.../vo/sbom/RawSbomMetaVo.java`                            | 新增 | RawSbom 元信息投影 DTO（不含 value 大字段）                                                                                            |
| `model/.../request/sbom/QuerySbomPackagesMultiFilterRequest.java` | 修改 | 新增 `languages` / `pkgManagerTypes` 字段                                                                                              |
| `utils/.../PackageLanguageUtils.java`                             | 新增 | `fillLanguageFields` 双轨推导统一入口（轨 B 判定 purl type ∈ 四平台），导入/回填共用                                                   |
| `batch/.../step/CollectStatisticsStep.java`                       | 修改 | 统计阶段调 `PackageLanguageUtils.fillLanguageFields` 落库三字段                                                                        |
| `interface/.../api/vcs/VcsApi.java`                               | 修改 | 新增 `default Map<String, Double> getRepoLanguages(owner, repo)`（归一契约：语言→数值）                                                |
| `clients/.../vcs/GitCodeApi.java`                                 | 修改 | 实现 `getRepoLanguages`：解析 `{"C++": 36.62, ...}`（百分比 map），retry 2 次                                                          |
| `clients/.../vcs/GithubApi.java`                                  | 修改 | 实现 `getRepoLanguages`：解析 `{"C++": 5347064, ...}`（字节 map）                                                                      |
| `clients/.../vcs/GiteeApi.java`                                   | 修改 | 实现 `getRepoLanguages`：解析 `{"languages": [{"language":..,"bytes":..}, ...]}` 包装数组                                              |
| `clients/.../vcs/VcsServiceImpl.java`                             | 修改 | 新增 `getRepoTopLanguage(url)`：先查 `repo_language_cache`，miss 调远端并写回缓存                                                      |
| `dao/PackageRepository.java`                                      | 修改 | MultiFilter DAO 新增 languages / pkgManagerTypes 过滤 + 3 个分布统计查询 + `findDistributionCandidatesByProduct`                       |
| `dao/RepoLanguageCacheRepository.java`                            | 新增 | 缓存表 DAO（findByRepoUrl）                                                                                                            |
| `dao/RawSbomRepository.java`                                      | 修改 | 新增 `queryRawSbomMeta` 轻量投影查询 + `updateRawSbomIfStatusAllowed` 原子条件更新                                                     |
| `api/sbom/SbomService.java`                                       | 修改 | 新增 `refreshPackageLanguage(Integer pageNum)` 接口方法                                                                                |
| `service/sbom/impl/SbomServiceImpl.java`                          | 修改 | MultiFilter 链路透传 languages / pkgManagerTypes + 分布统计合并 + `refreshPackageLanguage` 分页批处理实现 + `publishSbom` 原子条件覆盖 |
| `controller/SbomController.java`                                  | 修改 | 新增 `refreshPackageLanguage` 端点；`publishSbom` 错误消息分级透出（`SbomRuntimeException` 附带 message，其余固定文案）                |

## 风险 & 缓解

| 风险                                                       | 缓解                                                                                                                       |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 存量数据 language 为 NULL                                  | SQL 过滤用 `COALESCE(language,'Others')`；提供回填接口                                                                     |
| Hibernate 数组绑定缺陷                                     | 沿用逗号字符串 + `string_to_array`，不绑定 List                                                                            |
| 多包多 PACKAGE_MANAGER purl 取值不一致                     | 取第一个 PACKAGE_MANAGER purl（稳定顺序），与导入期/回填期口径一致                                                         |
| 源码包多导致统计/回填耗时长（逐包同步调 REST）             | 仅 git 托管 type 包触达 API；`repo_language_cache` 缓存去重远端调用；WebClient retry 2 次与超时；单包失败返回 C/C++ 不阻断 |
| 生产环境 `ddl-auto=none` 不自动建 `repo_language_cache` 表 | 提供建表 SQL，发布时手动执行                                                                                               |
| 源码仓 purl 的 type 无对应域名                             | 仅 gitcode/gitee/github/atomgit 四类型走轨 B，其余按轨 A/Others                                                            |
| 覆盖 WAIT 任务时被调度器并发捞起（RUNNING）                | 原子条件 UPDATE 仅允许 NULL/FINISH/FAILED_FINISH/WAIT 命中，0 行即抛异常拒绝发布                                           |

## 跨仓影响

无。仅 `openlibing-sbom` 仓内部变更。
