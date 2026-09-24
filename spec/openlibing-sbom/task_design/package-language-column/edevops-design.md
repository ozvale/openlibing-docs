# 【openlibing-sbom】结果展示新增包语言列 — EDEVOPS 设计文档

---

## 1. 方案设计

### 1.1 背景

当前 SBOM 结果展示页面显示软件名、版本号、依赖类型、漏洞风险数值等，缺少依赖的**语言类型**。需在查询以及详情页面显示每个依赖的语言类型，并支持筛选、多选。

关联 Issue: [#75](https://gitcode.com/openlibing/openlibing-sbom/issues/75)

### 1.2 方案概述

包语言未单独存储，按包来源双轨推导：

1. **包管理器包**：`PACKAGE_MANAGER` 类别 purl 的 `type` 确定性映射语言（与 openlibing-sbom-tools `LanguageFromPURL` 一致）。
2. **源码仓包**（包的第一个 PACKAGE_MANAGER purl 的 `type` ∈ {gitcode, gitee, github, atomgit}，实现期从 `comment="source_code_url"` 判定改为按 purl type 判定）：调用平台 languages 接口（GitCode / GitHub / Gitee）取占比最高的语言，**C / C++ 统一写为 C/C++**；结果以 `repo_language_cache` 表按 repoUrl 缓存，命中不再调远端。

复用 `dependency-type-identification` 先例：

1. `PackageStatistics` 新增 `language` / `pkgManagerType` / `purl` 三列（TEXT），`CollectStatisticsStep` 统计阶段经 `PackageLanguageUtils.fillLanguageFields`（utils 模块公共工具类，导入/回填共用）推导落库，新导入 SBOM 自动填充
2. 提供回填 REST 接口 `refreshPackageLanguage?pageNum=N`（FINISH 状态产品按名称排序分页，每页 50 个 product，单 product 全量加载 + saveAll 批量落库 + 失败隔离），刷新存量数据
3. `PackageStatisticsVo` / 详情接口返回 `language` / `pkgManagerType` / `purl`
4. `/querySbomPackagesMultiFilter` 入参新增 `languages` / `pkgManagerTypes` 多选过滤（组内 OR），`/querySbomPackagesVulCountSummary` 共享 DTO 同步生效
5. `/querySbomPackagesVulCountSummary` 出参新增三个分布统计 `dependencyTypeCounts` / `languageCounts` / `pkgManagerTypeCounts`（排除自身维度过滤、全量选项含 0 计数、字典序）

### 1.3 方案架构

```
openlibing-sbom
┌──────────────────────────┐
│ SpdxReader                │ ← 导入时持久化 external_purl_ref（JSONB purl）
│ (已有，不改动)           │    源码仓引用 → PACKAGE_MANAGER + comment=source_code_url
│          │               │
│          ▼               │
│ CollectStatisticsStep     │
│ ┌──────────────────────┐ │
│ │ collectPackageLanguage│ │
│ │  轨A: PackageLanguage │ │ ← 普通 purl: type 映射枚举
│ │    .fromPurlType(type)│ │
│ │  轨B: source_code_url │ │ ← 源码仓包: 构造 URL → VcsServiceImpl
│ │    → getRepoTopLanguage  │    .getRepoTopLanguage(url)
│ │    → fromRepoLanguage │ │    三平台 languages API → 最高占比
│ └──────────────────────┘ │
│          │               │
│          ▼               │
│ PackageStatistics         │ ← 新增 language 列 (TEXT)
│ (PostgreSQL)             │
└──────────────────────────┘
      │                            │
      ▼                            ▼
 PackageStatisticsVo          PackageRepository
  .language (列表/详情出参)     4 个 MultiFilter SQL
      ▲                     + :languages 过滤片段
      │                            ▲
      │                            │
 refreshPackageLanguage       QuerySbomPackagesMultiFilterRequest
 (回填 REST，Java 循环)         .languages (多选，组内 OR)

 clients 模块（轨 B 支撑）:
 VcsApi.getRepoLanguages(owner, repo)  ← 新增 default 方法，归一为 Map<String, Double>
   ├─ GitCodeApi: /api/v5/repos/{org}/{repo}/languages
   │     返回 {"C++": 36.62, "C": 63.13}        → 语言→百分比 map
   ├─ GithubApi:  /repos/{org}/{repo}/languages
   │     返回 {"C++": 5347064, "C": 782492}     → 语言→字节 map
   └─ GiteeApi:   /api/v5/repos/{org}/{repo}/languages
         返回 {"languages": [{"language":"Rust","bytes":1530232}, ...]} → 拆包装数组
 VcsServiceImpl.getRepoTopLanguage(url) ← 新增，复用 getOwnerRepo/getApiByUrl
                                          取 value 最大 key（单位不影响单次比较）
```

### 1.4 关键技术决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 语言数据源（轨 A） | `external_purl_ref`（category=PACKAGE_MANAGER）的 `purl->>'type'` | 确定性映射，与 sbom-tools `LanguageByName` 口径一致 |
| 语言数据源（轨 B） | 源码仓包调平台 languages API 取占比最高 | 用户需求；comment="source_code_url" 是已落库的可靠判据 |
| 三平台返回差异归一 | GitCode 百分比 map / GitHub 字节 map / Gitee 包装数组，各实现解析后统一返回 `Map<String, Double>`，取单次响应内 value 最大 key | 单位（百分比/字节）不影响单次响应内的最大值比较；Gitee 取数组元素 `bytes` 字段 |
| 平台范围 | GitCode / GitHub / Gitee 三大平台 | 用户确认；`VcsApi` 接口统一抽象，`getApiByUrl` 已按域名匹配 |
| API 调用时机 | `CollectStatisticsStep` 同步逐包调用 | 用户确认；与 language 落库同处一步，统计重跑可自动补语言 |
| 存储位置 | `package_statistics.language`（TEXT，存枚举 displayName） | 复用 dependency_type 先例；查询/筛选均在 SQL 层完成 |
| C / C++ 归一 | 统一枚举 `C_CPP`，displayName `C/C++` | 用户需求；`fromRepoLanguage` 内归一 |
| 轨 B 失败兜底 | API 失败/空数据 → `C_CPP`；返回语言但未收录 → `Others` | 用户需求：平台调用失败语言默认 C/C++ |
| 映射实现 | 枚举 `PackageLanguage`（displayName 字段）+ 静态 `fromPurlType` / `fromRepoLanguage` | 避免反射（项目约束），静态映射可单测 |
| 未知值 | 推导不出 → 显式存 `Others`（非 NULL） | SQL 过滤可直接等值匹配，前端可展示 |
| 存量回填 | Java 循环逐包复用推导逻辑（非 SQL） | 轨 B 语言来自 REST API，SQL 无法推导；仅 source_code_url 包触达 API |
| 多选过滤 | 逗号字符串 + `string_to_array`（不绑 List） | 规避 Hibernate 6 + PG JDBC `malformed array literal` 历史坑 |
| 存量 NULL 兼容 | SQL 过滤用 `COALESCE(ps.language, 'Others') = ANY(...)` | 回填前选 Others 也能命中存量行 |
| V3 汇总接口 | `sumVulCountByMultiFilter` 同步加 languages 过滤 | 共享 DTO，保证列表与汇总计数口径一致 |
| DDL 方式 | Hibernate auto DDL | 与项目既有字段新增方式一致 |

---

## 2. 实现逻辑设计

### 2.1 语言映射表

**轨 A — purl type → 语言**（displayName 统一驼峰，含 `Others`）：

| purl type | 语言 displayName |
|-----------|-----------------|
| maven / gradle / java | Java |
| npm | JavaScript |
| pypi | Python |
| composer | PHP |
| gem | Ruby |
| golang | Go |
| cargo | Rust |
| pub | Dart |
| dotnet | Dotnet |
| 其他 / 无 PACKAGE_MANAGER purl | Others |

**轨 B — 平台 languages API 返回语言名 → 枚举**（displayName 与 API 返回值驼峰风格一致）：

| API 返回 | displayName | 说明 |
|----------|-------------|------|
| C / C++ | C/C++ | 统一归一 |
| Java | Java | |
| JavaScript | JavaScript | |
| TypeScript | TypeScript | |
| Python | Python | |
| Go | Go | |
| Rust | Rust | |
| PHP | PHP | |
| Ruby | Ruby | |
| Kotlin | Kotlin | |
| Swift | Swift | |
| Dart | Dart | |
| C# | C# | |
| Shell | Shell | |
| HTML / CSS / Vue 等 | HTML / CSS / Vue | 常见前端语言 |
| 其他未收录语言 | Others | 未收录语言一律 Others |
| API 失败 / 空数据（null/blank） | C/C++ | **平台调用失败兜底为 C/C++** |

### 2.2 导入期预计算流程（CollectStatisticsStep）

```
collectPackageStatistics(sbom)
  └─ for each pkg in sbom.packages:
       PackageLanguageUtils.fillLanguageFields(statistics, pkg, vcsService::getRepoTopLanguage)
         1. pkgManagerRef = pkg.externalPurlRefs 中第一个
            category == PACKAGE_MANAGER 的引用
         2. 无 pkgManagerRef
            → statistics.language = Others
         3. purl.type ∈ {gitcode, gitee, github, atomgit}
            （轨 B，源码仓包；实现期从 comment="source_code_url" 判定改为按 type 判定）
            → url = "https://" + purl.type + ".com/" + purl.namespace + "/" + purl.name
            → topLang = vcsServiceImpl.getRepoTopLanguage(url)
                 内部: ① findByRepoUrl 查 repo_language_cache，命中直接返回
                       ② getOwnerRepo(url) → getApiByUrl(url)
                          → vcsApi.getRepoLanguages(owner, repo)
                          → 取 value 最大的 key；失败/空返回 null
                       ③ 成功后写回 repo_language_cache（写失败仅告警）
            → statistics.language = PackageLanguage.fromRepoLanguage(topLang)
                 （topLang 为 null → C_CPP 兜底；未收录 → Others）
         4. 其他（轨 A，包管理器包）
            → statistics.language = PackageLanguage.fromPurlType(purl.type)
         5. 同步填充 statistics.pkgManagerType（purl type）与 statistics.purl（完整 purl 串）
```

### 2.3 存量回填流程（Java 分页批处理）

```
POST /sbom-api/refreshPackageLanguage?pageNum=N
  └─ SbomServiceImpl.refreshPackageLanguage(pageNum)
       1. findDistinctProductNamesByTaskStatus(FINISH) → 全部产品名，sorted() 排序
       2. 按页切分：每页固定 50 个 product（排序保证翻页稳定）
       3. for each product in 当前页:
            - product / sbom 不存在 → skip 计数，继续
            - refreshPackageLanguageForProduct(productName, sbom):
                a. 一次性加载 sbom.packages（单 product 最多 1 万+ 包，不分页）
                b. for each pkg: fillLanguageFields（与导入期同一工具类）
                   慢包（>200ms，多为走 VCS API）单独打点
                c. packageStatisticsRepository.saveAll(statisticsList) 批量落库
                d. 任意异常 → 返回 -1（failed 计数），继续下一个 product
       4. 汇总日志: page/totalPages/processed/skipped/failed/refreshed/cost
```

> 轨 B 语言来自 REST API，无法用单条 SQL 推导，故回填不用 `@Modifying` SQL，改为 Java 循环；`repo_language_cache` 缓存保证同 repo 只调一次远端。

### 2.4 查询过滤流程

```
POST /sbom-api/querySbomPackagesMultiFilter  body: {"languages": ["Java","Python"]}
  ├─ SbomController.querySbomPackagesMultiFilter(req)
  ├─ SbomServiceImpl.joinLanguages(req.getLanguages())  → "Java,Python"
  └─ PackageRepository 4 个方法新增参数与片段：
       AND (:languages IS NULL OR :languages = ''
         OR COALESCE(ps.language, 'Others') = ANY(string_to_array(:languages, ',')))
```

组内 OR（命中任一选中语言即筛选出）、组间 AND（与其他过滤条件叠加）。

### 2.5 异常处理

| 场景 | 处理 |
|------|------|
| 包无任何 externalPurlRefs | `fromPurlType(null)` → Others |
| 无 PACKAGE_MANAGER purl | → Others |
| source_code_url 包的 purl type 无对应域名（非 git 托管） | 不走轨 B，按轨 A 映射（多为 Others） |
| 平台 languages API 调用失败（网络/限流/404） | `getRepoTopLanguage` 捕获返回 null → `fromRepoLanguage(null)` → C/C++，不阻断统计 |
| API 返回空 map（空仓库） | 无最高占比 → C/C++（失败/空数据兜底） |
| API 返回语言未收录枚举 | `fromRepoLanguage` default → Others |
| 回填 pageNum 无效（null / <1） | 抛 `IllegalArgumentException`，由 Controller 兜底返回错误 |
| languages 传空列表 | joinLanguages 返回 null → SQL 短路，无过滤 |
| publishSbom 已有任务 RUNNING 等执行中 | 原子条件 UPDATE 影响 0 行 → 抛 `SbomRuntimeException`（"has sbom import job in running"），不覆盖执行中任务 |
| publishSbom 并发时序窗口（读 meta 为 WAIT、UPDATE 前被调度器捞起） | 原子条件 UPDATE 状态不满足即 0 行，天然互斥，无需额外锁 |
| publishSbom product 不存在 | 抛 `SbomRuntimeException`（业务消息可透出） |
| publishSbom 非业务异常（DB 连接等） | Controller 仅记日志，对外固定文案 `publish sbom failed!`；仅 `SbomRuntimeException` 消息透出到 errorInfo |

---

## 3. 类设计

### 3.1 新增类

| 类 | 模块 | 路径 | 职责 |
|----|------|------|------|
| `PackageLanguage` | model | `model/.../enums/PackageLanguage.java` | 语言枚举（枚举名大写如 `JAVA`/`C_CPP`/`SHELL`/`OTHERS`，displayName 统一驼峰如 `Java`/`C/C++`/`Shell`/`Others`）+ 静态 `fromPurlType`（轨 A）+ `fromRepoLanguage`（轨 B，C/C++ 归一 + 失败兜底 C_CPP），switch 实现，无反射 |
| `RepoLanguageCache` | model | `model/.../entity/RepoLanguageCache.java` | 仓库语言缓存表实体（repo_url 唯一索引 → language），避免重复调平台 API |
| `RawSbomMetaVo` | model | `model/.../vo/sbom/RawSbomMetaVo.java` | RawSbom 元信息投影 DTO（id/taskStatus/createTime/taskId，不含 value 大字段），`publishSbom` 状态判断用 |
| `PackageLanguageUtils` | utils | `utils/.../PackageLanguageUtils.java` | `fillLanguageFields(statistics, pkg, topLanguageFetcher)` 双轨推导统一入口（轨 B 判定 purl type ∈ 四平台），导入/回填共用（ai_memory "公用逻辑提取到 utils" 规则） |

### 3.2 修改类

| 类 | 模块 | 路径 | 变更 |
|----|------|------|------|
| `PackageStatistics` | model | `model/.../entity/PackageStatistics.java` | 新增 `language` / `pkgManagerType` / `purl` 三字段（String）+ getter/setter |
| `PackageStatisticsVo` | model | `model/.../vo/sbom/PackageStatisticsVo.java` | 新增 `language` / `pkgManagerType` / `purl` 字段 + `fromPackage` 填充（language / pkgManagerType 为 null 时兜底 Others） |
| `VulCountSummaryVo` | model | `model/.../vo/sbom/VulCountSummaryVo.java` | 新增 `dependencyTypeCounts` / `languageCounts` / `pkgManagerTypeCounts`（`Map<String, Long>`，字典序） |
| `QuerySbomPackagesMultiFilterRequest` | model | `model/.../request/sbom/QuerySbomPackagesMultiFilterRequest.java` | 新增 `languages` / `pkgManagerTypes`（`List<String>`）+ getter/setter + toString |
| `CollectStatisticsStep` | batch | `batch/.../step/CollectStatisticsStep.java` | 注入 `VcsServiceImpl`；统计阶段调 `PackageLanguageUtils.fillLanguageFields` 落库三字段 |
| `VcsApi` | interface | `interface/.../api/vcs/VcsApi.java` | 新增 `default Map<String, Double> getRepoLanguages(owner, repo)`（default 空 map；归一契约：语言→数值） |
| `GitCodeApi` | clients | `clients/.../vcs/GitCodeApi.java` | 实现 `getRepoLanguages`：`/api/v5/repos/{org}/{repo}/languages`，解析百分比 map（retry 2 次） |
| `GithubApi` | clients | `clients/.../vcs/GithubApi.java` | 实现 `getRepoLanguages`：`/repos/{org}/{repo}/languages`，解析字节 map |
| `GiteeApi` | clients | `clients/.../vcs/GiteeApi.java` | 实现 `getRepoLanguages`：`/api/v5/repos/{org}/{repo}/languages`，解析 `{"languages":[...]}` 包装数组，取元素 `language` + `bytes` |
| `VcsServiceImpl` | clients | `clients/.../vcs/VcsServiceImpl.java` | 新增 `getRepoTopLanguage(String url)`：**先查 `repo_language_cache`，miss 时**复用 `getOwnerRepo` / `getApiByUrl` 取 languages map 中 value 最大 key，成功写回缓存，异常返回 null（由 `fromRepoLanguage` 兜底 C/C++） |
| `PackageRepository` | dao | `dao/.../PackageRepository.java` | MultiFilter 方法新增 `languages` / `pkgManagerTypes` 参数与过滤片段；新增 3 个分布统计查询（`countDependencyTypeDistributionByMultiFilter` / `countLanguageDistributionByMultiFilter` / `countPkgManagerTypeDistributionByMultiFilter`，排除自身维度过滤）+ `findDistributionCandidatesByProduct` 候选值全集查询 |
| `RepoLanguageCacheRepository` | dao | `dao/.../RepoLanguageCacheRepository.java` | 新增（`findByRepoUrl`） |
| `RawSbomRepository` | dao | `dao/.../RawSbomRepository.java` | 新增 `queryRawSbomMeta` JPQL 投影查询（构造 `RawSbomMetaVo`，不加载 value 大字段）+ `updateRawSbomIfStatusAllowed` 原子条件更新（`@Modifying`，仅 NULL/FINISH/FAILED_FINISH/WAIT 状态命中，0 行即并发冲突） |
| `SbomService` | sbom-web | `sbom-web/.../api/sbom/SbomService.java` | 新增 `refreshPackageLanguage(Integer pageNum)` 接口方法 |
| `SbomServiceImpl` | sbom-web | `sbom-web/.../service/sbom/impl/SbomServiceImpl.java` | MultiFilter 链路新增 `joinLanguages` / `joinPkgManagerTypes` 透传；`getVulCountSummaryMultiFilter` 合并候选值与分布结果（全量选项 + 字典序，`dependencyTypeCounts` 固定 `DependencyType` 三项）；实现 `refreshPackageLanguage` 分页批处理 + `refreshPackageLanguageForProduct`（saveAll + 失败隔离 + 三层耗时日志）；`publishSbom` 原子条件覆盖重发（搭车改动：`updateRawSbomIfStatusAllowed` 0 行抛 `SbomRuntimeException`） |
| `SbomController` | sbom-web | `sbom-web/.../controller/SbomController.java` | 新增 `refreshPackageLanguage` 端点（pageNum 参数）；`publishSbom` 错误消息分级透出（`SbomRuntimeException` 附带 message，其余异常固定文案 `publish sbom failed!`） |

---

## 4. 数据模型设计

### 4.1 涉及的数据库表

| 表 | 数据库 | 用途 |
|----|--------|------|
| `package_statistics` | PostgreSQL (sbom) | 新增 `language` / `pkg_manager_type` / `purl` 三列（Hibernate auto DDL 自动建列） |
| `repo_language_cache` | PostgreSQL (sbom) | **本需求新增表**：repo_url → language 缓存，避免重复调平台 API |
| `external_purl_ref` | PostgreSQL (sbom) | 已存在，JSONB `purl` 列 + `comment` 列，轨 A/轨 B 判据来源 |

### 4.2 新增列

```sql
-- Hibernate auto DDL 自动生成，此处仅示意
ALTER TABLE package_statistics ADD COLUMN language TEXT;
ALTER TABLE package_statistics ADD COLUMN pkg_manager_type TEXT;
ALTER TABLE package_statistics ADD COLUMN purl TEXT;

-- language 取值: Java / JavaScript / TypeScript / Python / Go / Rust / PHP / Ruby / Dart /
--       Dotnet / Kotlin / Swift / C# / Shell / HTML / CSS / Vue / C/C++ / Others
-- 新数据: CollectStatisticsStep 显式写 Others，非 NULL
-- 存量数据: 回填前为 NULL，查询侧 COALESCE 兜底
```

### 4.3 新增表 repo_language_cache

```sql
CREATE TABLE repo_language_cache (
    id UUID PRIMARY KEY,
    repo_url TEXT NOT NULL,
    language TEXT,
    CONSTRAINT repo_url_uk UNIQUE (repo_url)
);
CREATE UNIQUE INDEX repo_url_uk ON repo_language_cache (repo_url);
```

> 生产环境 `ddl-auto=none`，发布时需手动执行建表 SQL。

### 4.4 核心查询 SQL（过滤片段）

```sql
AND (:languages IS NULL OR :languages = ''
  OR COALESCE(ps.language, 'Others') = ANY(string_to_array(:languages, ',')))
```

### 4.5 API 返回数据结构（新增字段）

```json
{
  "name": "some-c-library",
  "version": "1.0.0",
  "statistics": {
    "language": "C/C++",
    "dependencyType": 1,
    "criticalVulCount": 0,
    "highVulCount": 1
  }
}
```

详情接口 `getPackageInfoById` 返回 `Package` 实体，`packageStatistics` 随实体序列化，新增字段自动透出。

---

## 5. 性能设计

### 5.1 导入期预计算

| 优化点 | 说明 |
|--------|------|
| 轨 A 纯内存 | 普通 purl 包仅 switch 映射，无 I/O |
| 轨 B 限流控制 | 仅 `comment="source_code_url"` 包调 REST；WebClient 已有 retry（backoff）与 token |
| 失败兜底 | 单包 API 失败返回 C/C++，不重试风暴、不阻断整批统计 |
| 复杂度 | O(P) 内存映射 + O(S) 次 REST 调用（P=包数，S=源码包数） |

### 5.2 查询与回填

| 优化点 | 说明 |
|--------|------|
| `IS NULL OR` 短路 | 不传 languages 时 PostgreSQL 短路，行为与变更前一致 |
| `= ANY(string_to_array(...))` | 固定单参数，规避长 IN list 的解析开销（ai_memory 规则） |
| 回填逐包更新 | 仅运维触发、低频；仅 source_code_url 包触达 API |
| 回填幂等 | 重复执行结果一致，可安全重试 |

---

## 6. API 接口设计

### 6.1 变更概述

| 接口 | HTTP 方法 | 路径 | 变更类型 |
|------|-----------|------|----------|
| `querySbomPackagesMultiFilter` | POST | `/sbom-api/querySbomPackagesMultiFilter` | 入参新增 `languages` / `pkgManagerTypes` + 出参 statistics 新增 `language` / `pkgManagerType` / `purl` |
| `querySbomPackagesVulCountSummary` | POST | `/sbom-api/querySbomPackagesVulCountSummary` | 共享 DTO，入参同步支持；**出参新增三个分布统计 Map** |
| `refreshPackageLanguage` | POST | `/sbom-api/refreshPackageLanguage` | **新增**，存量数据分页回填 |
| `getPackageInfoById` | GET | `/sbom-api/getPackageInfoById` | 出参 statistics 自动新增三字段（无代码改动） |

### 6.2 `POST /sbom-api/querySbomPackagesMultiFilter` 入参变更

| 参数名 | 类型 | 必填 | 默认值 | 变更 | 说明 |
|--------|------|------|--------|------|------|
| `languages` | List&lt;String&gt; | 否 | null | **新增** | 语言多选（组内 OR）：Java / JavaScript / TypeScript / Python / Go / Rust / PHP / Ruby / Dart / Dotnet / Kotlin / Swift / C# / Shell / HTML / CSS / Vue / C/C++ / Others；不传 = 全部 |
| `pkgManagerTypes` | List&lt;String&gt; | 否 | null | **新增** | 包管理器类型多选（组内 OR）：maven / npm / pypi / golang / cargo 等 purl type |

### 6.3 `POST /sbom-api/querySbomPackagesVulCountSummary` 出参新增分布统计

```json
{
  "criticalVulCount": 0,
  "highVulCount": 12,
  "dependencyTypeCounts": { "0": 100, "1": 250, "2": 30 },
  "languageCounts": { "C/C++": 0, "Java": 274, "Python": 0 },
  "pkgManagerTypeCounts": { "cargo": 5, "maven": 274 }
}
```

- `dependencyTypeCounts`：固定返回 `DependencyType` 枚举三项（"0"=DIRECT / "1"=INDIRECT / "2"=DIRECT_INDIRECT），无数据计 0
- `languageCounts` / `pkgManagerTypeCounts`：产品内候选值全集 + 过滤命中计数合并，0 计数选项也展示
- 三个 Map 均按 key 字典序排序；分布查询排除自身维度过滤（选中 Java 后 C/C++ 仍显示其真实计数）

### 6.4 新增接口 `POST /sbom-api/refreshPackageLanguage`

```
POST /sbom-api/refreshPackageLanguage?pageNum=1

响应:
{
  "code": 200,
  "msg": "success",
  "data": "success"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `pageNum` | Integer | 是（>=1） | 页码。按 FINISH 状态产品名排序后每页 50 个 product，逐页调用完成全量回填 |

### 6.5 向后兼容性

| 场景 | 行为 |
|------|------|
| 不传 `languages` | SQL 短路，返回全部（与变更前一致） |
| 旧接口 `querySbomPackages` / `querySbomPackageList` | 完全不动 |
| 前端未升级 | Jackson 忽略新字段，不崩溃 |
| 存量数据 language 为 NULL | 查询侧 `COALESCE` 兜底 Others；回填接口刷新 |

---

## 7. 安全设计

### 7.1 鉴权

继承原有网关统一鉴权，不新增鉴权点。

### 7.2 输入安全

| 输入点 | 风险 | 缓解 |
|--------|------|------|
| `languages` 参数 | 非法枚举值 | 非法值在 SQL 中匹配不到结果；`string_to_array` 参数化绑定，无注入风险 |
| `productName` | 恶意输入 | 参数化 SQL 绑定，与既有回填接口（refreshDependencyCache）一致 |
| 平台 languages API | token 泄露 | 复用既有 `gitcode.api.token` 等环境变量注入，不硬编码 |

### 7.3 敏感信息

无硬编码凭证；语言枚举非敏感数据。

---

## 8. 测试设计

### 8.1 测试策略

按 `ai_memory.md` 规则，UT 在 Phase 4 阶段补充到 `sbom-web/src/test/java`（Mockito 风格）。

### 8.2 测试场景

| 场景 | 输入 | 预期 |
|------|------|------|
| 轨 A-maven | fromPurlType("maven") | Java |
| 轨 A-npm | fromPurlType("npm") | JavaScript |
| 轨 A-未知类型 | fromPurlType("rpm") | Others |
| 轨 B-C 占比最高 | getRepoLanguages 返回 {"C":100,"C++":50} | C/C++ |
| 轨 B-C++ 占比最高 | getRepoLanguages 返回 {"C++":100,"C":50} | C/C++ |
| 轨 B-正常语言 | getRepoLanguages 返回 {"Rust":100,"Shell":10} | Rust |
| 轨 B-Gitee 包装数组 | Gitee 返回 {"languages":[{"language":"Rust","bytes":1530232},{"language":"Lua","bytes":1198}]} | Rust（取 bytes 最大） |
| 轨 B-GitCode 百分比 map | GitCode 返回 {"C++": 36.62, "C": 63.13, "Makefile": 0.26} | C/C++（取百分比最大） |
| 轨 B-未收录语言 | getRepoLanguages 返回 {"Nix":100} | Others |
| 轨 B-API 失败 | WebClientException | getRepoTopLanguage 返回 null → C/C++ |
| 轨 B-空仓库 | getRepoLanguages 返回 {} | C/C++（失败/空数据兜底） |
| 导入期-源码包 | pkg 含 comment=source_code_url 的 PACKAGE_MANAGER purl | 触达 getRepoTopLanguage |
| 导入期-普通包 | pkg 含 maven purl | statistics.language = Java，不触达 API |
| 导入期-无 PACKAGE_MANAGER purl | pkg 仅 SECURITY purl | statistics.language = Others |
| 过滤-单语言 | languages=["Java"] | 仅返回 Java 包 |
| 过滤-多语言 | languages=["Java","Python"] | Java 或 Python 包（组内 OR） |
| 过滤-C/C++ 值含斜杠 | languages=["C/C++"] | 正确匹配 language="C/C++" 行 |
| 过滤-Others 命中存量 | languages=[Others]，存量行 language=NULL | 命中（COALESCE 兜底） |
| 过滤-不传 | languages=null | 返回全部（向后兼容） |
| 回填 | pageNum 有效 | 该页 50 个 product 全部刷新，返回 success |
| 回填-pageNum 无效 | pageNum=null 或 <1 | 抛 IllegalArgumentException |
| 回填-单 product 失败 | product 刷新抛异常 | 记 failed 计数，继续后续 product，整体任务不中断 |
| 回填-命中缓存 | repoUrl 已在 repo_language_cache | 直接返回缓存语言，不调平台 API |
| VO 填充 | statistics.language = null | vo.language = Others |
| VO 填充-pkgManagerType 兜底 | statistics.pkgManagerType = null | vo.pkgManagerType = Others（与 SQL COALESCE 口径一致） |
| publishSbom-覆盖 WAIT | 已有 WAIT 记录，原子条件 UPDATE 命中 1 行 | 返回新 taskId，不再走 save |
| publishSbom-覆盖历史无状态 | 旧记录 task_status 为 NULL | 允许覆盖（历史完成记录） |
| publishSbom-并发窗口 | meta 读到 WAIT，UPDATE 执行时已被置 RUNNING（0 行） | 抛 SbomRuntimeException（"has sbom import job in running"） |
| publishSbom-错误消息分级 | 业务异常（任务冲突）/ 非业务异常（DB） | 业务异常 message 透出 errorInfo；非业务异常固定文案 |
| PackageLanguageUtils-源码仓远端调用 | gitcode purl + 远端返回 Java | language=Java，URL 构造/调用正确 |
| PackageLanguageUtils-远端失败/抛异常 | 远端返回 null / 抛异常 | language 兜底 C/C++ / Others，不阻断 |
| PackageLanguageUtils-URL 构造 | 有/无 namespace、空 type | 正确拼 URL 或返回 null |
| 分布统计合并 | 选中 Java，候选全集含 Python/C/C++ | 0 计数选项合并展示，key 字典序 |

---

## 9. 与代码实现的一致性核对

| 设计项 | 代码对应 | 状态 |
|--------|---------|------|
| PackageLanguage 枚举（fromPurlType / fromRepoLanguage，C/C++ 归一） | `model/enums/PackageLanguage.java` | 已核对一致 |
| language / pkgManagerType / purl 三列 | `PackageStatistics` | 已核对一致 |
| 导入期双轨预计算（轨 B 判定 purl type ∈ 四平台） | `CollectStatisticsStep` + `PackageLanguageUtils.fillLanguageFields` | 已核对一致 |
| VcsApi.getRepoLanguages（三平台实现，retry 2 次） | `VcsApi` / `GitCodeApi` / `GithubApi` / `GiteeApi` | 已核对一致 |
| getRepoTopLanguage（先查 repo_language_cache） | `VcsServiceImpl` + `RepoLanguageCacheRepository` | 已核对一致 |
| languages / pkgManagerTypes 过滤片段 | `PackageRepository` MultiFilter 方法 | 已核对一致 |
| 分布统计（排除自身维度 + 候选值全集 + 字典序） | `PackageRepository` 3 个分布查询 + `findDistributionCandidatesByProduct` + `SbomServiceImpl` | 已核对一致 |
| 回填 REST（pageNum 分页 + saveAll + 失败隔离） | `SbomController.refreshPackageLanguage` / `SbomServiceImpl` | 已核对一致 |
| 出参透出 | `PackageStatisticsVo` / `VulCountSummaryVo` | 已核对一致 |
| publishSbom 原子条件覆盖 + 轻量投影查询 + 错误消息分级 | `updateRawSbomIfStatusAllowed` + `RawSbomMetaVo` + `queryRawSbomMeta` + Controller 分级 | 已核对一致（搭车改动） |
| pkgManagerTypes COALESCE + VO 空值兜底 | `PackageRepository` 7 处过滤片段 + `PackageStatisticsVo.fromPackage` | 已核对一致 |
