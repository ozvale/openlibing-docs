# pending-vul-statistics — 技术设计

## 方案概述

isPending 判定完全收敛在 openlibing-vulnerability 服务（`cve/details` 接口按完整口径计算并透出），openlibing-sbom 纯透传落表（`vulnerability_lifecycle`）+ 聚合物化（`external_vul_ref.is_pending` → `product_statistics`/`package_statistics` 的 pending 7 列），查询侧扩 SELECT/ORDER BY 即得；openlibing-web 纯展示与筛选联动（下钻联动复用既有漏洞级别筛选链路）。

## 架构决策

1. **口径唯一实现点在 vulnerability 服务**：cve_details 文档 issue 级字段齐全，口径可与漏洞修复列表 100% 对齐，未来口径变更只改一处；sbom 侧零口径逻辑（issue→漏洞的关联匹配复用既有 `getSuitableVulnerabilityLifecycle`，是关联匹配而非口径判断）。
2. **双落表**：`vulnerability_lifecycle.is_pending`（issue 级，弹窗行内展示）+ `external_vul_ref.is_pending`（漏洞级聚合，任一匹配 issue 待闭环即 true；无 lifecycle 记录 = 未提单 = false），筛选/排序/统计一律用漏洞级标志。
3. **重算路径 3 个**：解析跑批 `CollectStatisticsStep`（流水线本就遍历包×漏洞，顺路聚合）；漏洞刷新 `VulRefreshStrategy`（修复存量不对称：顺带重算 product_statistics）；xxl-job 每日清洗任务（兜底 lifecycle 每夜刷新后的滞后窗口）。
4. **sbom 接入 xxl-job**：对齐 coderepo/codecheck 模式（xxl-job-core 3.2.0、`XxlJobSpringExecutor`、appname=`openlibing-sbom-executor`、Nacos `optional:nacos:xxl-job`）。quartz `FetchMajunCveJob` 保持现状不停用；xxl 侧 `fetchMajunCveHandler` 复制同步逻辑但默认停用（防双跑），`pendingVulCleanHandler` 为清洗任务。
5. **弹窗默认排序 SQL 下推**：`external_vul_ref.is_pending` 物化后即排序键，`ORDER BY evf.is_pending DESC NULLS LAST, score DESC NULLS LAST, ...`（未闭环置顶、组内评分倒序，DB 分页语义不变）；行内折叠 issue 优先未闭环由 sbom 组装时按 isPending 降序稳定排序实现（每漏洞 lifecycle 本就全量取出，内存零成本，前端折叠取首条逻辑零改动）。
6. **下钻为筛选联动（非排序）**：复用既有「漏洞级别筛选」（IncludeExcludeFilter / `INCLUDE_VUL_SEVERITIES` 后端参数），制品块点击由前端写入筛选条件，无后端改动；成分列表漏洞总数/级别的表头手动排序能力保留（`PackageSortField` 扩展 pending 排序枚举）。
7. **DDL 手工执行**：生产 `ddl-auto=none`，全部为 `ADD COLUMN IF NOT EXISTS` 可空列，秒级执行。

## 数据模型

PostgreSQL（sbom 库）：

```sql
ALTER TABLE vulnerability_lifecycle ADD COLUMN IF NOT EXISTS issue_state TEXT;
ALTER TABLE vulnerability_lifecycle ADD COLUMN IF NOT EXISTS is_pending BOOLEAN;

ALTER TABLE external_vul_ref ADD COLUMN IF NOT EXISTS is_pending BOOLEAN;

-- product_statistics / package_statistics 各 7 列（pending_vul_count + 六级 pending_*_vul_count）
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_vul_count BIGINT;
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_critical_vul_count BIGINT;
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_high_vul_count BIGINT;
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_medium_vul_count BIGINT;
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_low_vul_count BIGINT;
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_none_vul_count BIGINT;
ALTER TABLE product_statistics ADD COLUMN IF NOT EXISTS pending_unknown_vul_count BIGINT;

ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_vul_count BIGINT;
ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_critical_vul_count BIGINT;
ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_high_vul_count BIGINT;
ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_medium_vul_count BIGINT;
ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_low_vul_count BIGINT;
ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_none_vul_count BIGINT;
ALTER TABLE package_statistics ADD COLUMN IF NOT EXISTS pending_unknown_vul_count BIGINT;
```

- isPending 口径（vulnerability 服务实现）：`issue_customize_state NOT IN (已挂起,已拒绝,已完成)（社区适配值）AND issue_state != 'rejected' AND issue_labels 不含 UNAFFECTED AND cvss_score ∈ [0,100)`。cvss 边界与漏洞运营平台既有过滤（`OverdueScreeningStrategy`：`gte(0).lt(100)`，MongoDB 数值比较对缺失字段同样不匹配）完全一致——cvss=100 或缺失判非待闭环，与平台现状对齐，单测以 100/NULL 边界用例固定该行为；
- 漏洞级聚合：该包×漏洞下任一匹配 issue 的 isPending=true → evf.is_pending=true；
- 存量行为 NULL：未重算前查询按 NULL 兜底，由解析跑批/漏洞刷新/每日清洗首跑回刷。展示语义：pending 列为 NULL 时主数字展示 `--`（区别于真 0「确实无待闭环」），悬浮气泡标注「待重算」，避免发布窗口期被误读为"已全部闭环"；NULL 不参与排序置顶（`NULLS LAST`）；
- 弹窗「是否闭环」筛选对 NULL 安全：SQL 使用 `COALESCE(evf.is_pending, false)`，存量 NULL 行在筛选「否」时可见，与行内展示口径（false/null→否）一致；
- 快照模式（product_statistics 追加式 + DISTINCT ON 取最新）与加列兼容；
- 无新增索引：evf 筛选在 pkg_id 过滤后的小结果集上进行，lifecycle 关联走内存索引。

## 涉及文件

### openlibing-vulnerability

| 文件                                                                  | 操作 | 说明                                                                                                                     |
| --------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------ |
| `src/main/java/com/openlibing/common/entity/vo/CveDetailToSbom.java`  | 修改 | +`issueState`、+`isPending`（Boolean）                                                                                   |
| `src/main/java/com/openlibing/business/operation/AdminOperation.java` | 修改 | `queryCveDetailsToSbom` include 追加 `issue_state`/`issue_labels`/`cvss_score`；新增 isPending 计算（口径唯一实现点）    |
| `src/test/java/...`（对应单测）                                       | 新增 | 四条件 × 边界断言（已完成/rejected/挂起/UNAFFECTED/cvss 越界，含 cvss=100 与缺失两个边界用例，固定与平台口径一致的行为） |

### openlibing-sbom（主仓）

| 文件                                                                                                          | 操作 | 说明                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `model/src/main/java/org/opensourceway/sbom/model/entity/VulnerabilityLifecycle.java`                         | 修改 | +`issueState`、+`isPending`                                                                                                                                                                                                                                          |
| `model/src/main/java/org/opensourceway/sbom/model/entity/ExternalVulRef.java`                                 | 修改 | +`isPending`（Boolean）                                                                                                                                                                                                                                              |
| `model/src/main/java/org/opensourceway/sbom/model/entity/ProductStatistics.java` / `PackageStatistics.java`   | 修改 | 各 +7 pending 列                                                                                                                                                                                                                                                     |
| `model/.../pojo/vo/sbom/ProductWithStatisticsVo.java` / `PackageStatisticsVo.java` / `VulCountSummaryVo.java` | 修改 | +pending 字段                                                                                                                                                                                                                                                        |
| `model/.../pojo/vo/sbom/VulnerabilityVo.java`                                                                 | 修改 | +`issueState`、+`isPending`                                                                                                                                                                                                                                          |
| `dao/.../dao/ProductWithStatisticsView.java`                                                                  | 修改 | +7 getter                                                                                                                                                                                                                                                            |
| `dao/.../dao/ProductRepository.java` / `PackageRepository.java`                                               | 修改 | SELECT/SUM/排序白名单扩 pending；弹窗主 SQL 加 evf.is_pending 筛选 + `is_pending DESC` 排序；分组 SQL 行展示 dependency_type 取命中值（顺带修复 1）                                                                                                                  |
| `dao/.../dao/ExternalVulRefRepository.java`                                                                   | 修改 | `findByPackageIdsInAndSeverityAndVulId` 加 isPending 筛选 + `is_pending DESC` 排序（软件包详情路径）                                                                                                                                                                 |
| `model/.../enums/PackageSortField.java`                                                                       | 修改 | +`VUL_COUNT` + 6 个 pending 枚举                                                                                                                                                                                                                                     |
| `sbom-web/.../service/vul/impl/MajunVulServiceImpl.java`                                                      | 修改 | 同步透传 issueState/isPending                                                                                                                                                                                                                                        |
| `batch/.../step/CollectStatisticsStep.java`                                                                   | 修改 | 写入点①：遍历包×漏洞聚合 lifecycle.is_pending → evf 标志 + 统计列                                                                                                                                                                                                    |
| `sbom-web/.../service/sbom/refresh/VulRefreshStrategy.java`                                                   | 修改 | 写入点②：同上 + 制品级重算                                                                                                                                                                                                                                           |
| `sbom-web/.../common/config/XxlJobConfig.java`                                                                | 新增 | `XxlJobSpringExecutor` Bean（appname=openlibing-sbom-executor）；启动校验 adminAddresses/accessToken 非空，缺失输出 ERROR 日志告警（防 optional 配置缺失静默不注册）                                                                                                 |
| xxl handler（新增类）                                                                                         | 新增 | `fetchMajunCveHandler`（复制 quartz 同步逻辑）、`pendingVulCleanHandler`（清洗任务，SQL 预圈定 + lifecycle 内存索引 + 只 UPDATE 变化行）                                                                                                                             |
| `sbom-web/.../service/sbom/impl/SbomServiceImpl.java`                                                         | 修改 | `getSuitableVulnerabilityLifecycle` 抽公共供聚合复用；`getVulnerabilityStatus` 透传 issueState/isPending 并按 isPending 降序组装 data；`queryVulnerability` 加筛选参数；`queryPackageVulnerability` 适配（筛选 + 行内补漏洞级 isPending 与优先 issue 的 issueState） |
| `sbom-web/.../controller/SbomController.java`                                                                 | 修改 | queryVulnerability / queryPackageVulnerability 签名透传调整                                                                                                                                                                                                          |
| Nacos 配置                                                                                                    | 修改 | profile 追加 `optional:nacos:xxl-job`（对齐 coderepo/codecheck 平台接入模式）；admin 地址/accessToken 复用平台级 `xxl.job.admin.*` 配置，新增 sbom executor 段（port/logpath/retentiondays）                                                                         |

### openlibing-web

| 文件                                                                                              | 操作 | 说明                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`                      | 修改 | 表头更名；主数字/悬浮气泡/表头气泡提示；制品级别块点击 → 展开成分 + 漏洞级别筛选联动选中该类型 + 漏斗旁 3 秒气泡提示（× 手动关闭）；总数块 → 筛选选「全部类型」；成分列表加「漏洞总数」块（主数字=待闭环总数，不支持跳转）+ 表头手动排序；导出下拉菜单更名与新增 xlsx 直导出项 |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/sbomExportDialog.vue` | 修改 | 移除「类型」radio，固定 SBOM 导出（恢复原形态）                                                                                                                                                                                                                                |
| `apps/web-openlibing/src/views/SbomManagement/components/SbomVulnerabilityTable.vue`              | 修改 | columns1 加「是否闭环」「Issue 状态」列与「是否闭环」下拉筛选；columns2（软件包详情模式）适配同款                                                                                                                                                                              |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/detail.vue`                     | 修改 | 软件包详情页传参与筛选联动                                                                                                                                                                                                                                                     |

## 实现逻辑（核心流程）

1. **vulnerability 侧计算**：`AdminOperation.queryCveDetailsToSbom` 拉 MongoDB cve_details，逐 issue 按四条件算 isPending，返回模型 +`issueState` +`isPending`（同 issue 多文档字段与分支无关，取值一致）。
2. **sbom 透传**：`MajunVulServiceImpl.syncMajunVulData` 既有 deleteByType + saveAll 流程透传落 `vulnerability_lifecycle`；存量由下一轮全量刷新补齐。
3. **写入点①（解析跑批）**：`CollectStatisticsStep` 按 `cveNum + productType` 建 lifecycle 内存索引（全表 9 万行可承受），复用 `getSuitableVulnerabilityLifecycle` 匹配，任一匹配行 isPending=true → evf 标志，同遍历聚合 pending 统计列。
4. **写入点②（漏洞刷新）**：`VulRefreshStrategy` 写新 evf 时聚合 lifecycle.is_pending；`recalculatePackageStatistics` 聚合 pending 列；同批 lifecycle 索引下聚合 product_statistics pending 列（修复存量不对称）。
5. **写入点③（每日清洗，xxl-job）**：cron 晚于 quartz lifecycle 同步完成 ≥30 分钟；SQL 预圈定 `package_statistics.vul_count>0` 的包（gamma 实测 172 万包 → 6.7 万，evf 199 万 → 144 万）；lifecycle 全量加载预解析 versions 为 Set；只 UPDATE 变化行、JDBC batch。**快照一致性防护**：任务开始记录 lifecycle 当前最大更新时间，分批写入前校验其未变化（期间发生手动重同步/其它写入则中止本轮并告警，下一轮收敛），杜绝旧快照反写覆盖新值。耗时估算：首轮约 4~6 分钟、日常约 1 分钟。
6. **查询与排序**：制品/包列表、summary 扩 pending 列（LEFT JOIN 已存在）；弹窗 `queryVulnerability` 主 SQL `all_vul` CTE 加 `AND (:isPending IS NULL OR COALESCE(evf.is_pending, false) = :isPending)`（NULL 安全，存量未重算行在筛选「否」时可见，与展示口径一致）并带出 is_pending 列，排序 `is_pending DESC → score DESC`；`getVulnerabilityStatus` 组装 data 按 isPending 降序稳定排序（折叠首条即未闭环）；软件包详情 `queryPackageVulnerability` 走 ExternalVulRef 实体查询（`evf.*` 已含 is_pending），同款筛选排序，行内补漏洞级 isPending 与优先未闭环 issue 的 issueState（每页 10 条 N+1 可接受）。
7. **下钻筛选联动（纯前端）**：点级别块/总数块 → 写入 `queryInfo.includeVulSeverities`（既有 IncludeExcludeFilter 模型）→ 既有 `INCLUDE_VUL_SEVERITIES` 后端筛选；漏斗旁 3 秒气泡（自动消失 + × 关闭）。

## API 接口契约变化

全部增量字段/增量参数，向后兼容：

| 接口                                                                    | 变化                                                                                                                                |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `GET .../ci-admin/cve/details?org=`（vulnerability，服务间 admin 接口） | 返回项 +`issueState: string` +`isPending: boolean`                                                                                  |
| `POST /sbom-api/queryProductListMultiFilter`                            | 行 +7 pending 字段                                                                                                                  |
| `POST /sbom-api/querySbomPackagesMultiFilter`                           | statistics +7 pending 字段；sortField 白名单扩展                                                                                    |
| `POST /sbom-api/querySbomPackagesVulCountSummary`                       | +7 pending 汇总字段                                                                                                                 |
| `GET /sbom-api/queryVulnerability`                                      | +`isPending` 筛选参数（Boolean 可空）；VulnerabilityVo +`issueState` +`isPending`；默认排序行为变化（is_pending DESC → score DESC） |
| `GET /sbom-api/queryPackageVulnerability`                               | 同款适配（软件包详情页）；行内 +漏洞级 isPending、优先 issue 的 issueState                                                          |

前端展示映射（仅前端）：issue_state：open→已开启、progressing→进行中、closed→已关闭、rejected→已拒绝、其他→`--`；is_pending：true→是、false/null→否（NULL 视同否，与筛选 COALESCE 口径一致）。下钻筛选联动复用既有 `INCLUDE_VUL_SEVERITIES` 参数，无新增接口参数。

Excel 导出字段对应（防实现误接）：列表「漏洞总数」块悬浮双值与导出两列一一对应——「漏洞总数」列 = `vul_count`（全量），「待闭环漏洞数」列 = `pending_vul_count`；`PackageSortField.VUL_COUNT` 排序对应 `vul_count`，pending 枚举对应 pending 列，勿交叉。

## 性能设计

| 场景                     | 策略                                              | 量级（gamma 实测）                               |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------ |
| isPending 计算（Vul 侧） | 全量同步逐 issue 纯内存四条件                     | lifecycle 全表 90,952 行，毫秒级/条              |
| evf 聚合（写入点①②）     | 遍历包×漏洞 + lifecycle 内存索引                  | 全库 evf 199 万行、单制品最大 2.2 万行；分批串行 |
| 每日清洗（写入点③）      | 预圈定有漏洞包 + 只 UPDATE 变化行                 | 首轮 4~6 分钟；日常约 1 分钟                     |
| 弹窗筛选/排序            | evf.is_pending 条件与排序键在 pkg_id 过滤后小集上 | 单包最大 11,500 行，DB 层完成                    |
| 列表查询                 | LEFT JOIN 已存在扩列                              | 零增长                                           |

## 安全设计

- **鉴权**：不新增接口；制品/包/弹窗查询沿用 master 已有横向鉴权（`checkPermissionByProductType`）；cve/details 为服务间 admin 接口维持现状；
- **输入校验**：唯一新增输入为 isPending 筛选参数（Boolean 可空），无注入面；issueState/isPending 为上游透传，前端白名单映射（非白名单值显示 `--`）；
- **SQL 注入**：native SQL 改动均为追加 SELECT 列/常量条件/参数化排序键映射，`:param` 参数化不变；
- **敏感信息**：issue_state/is_pending 非敏感；issueUrl 展示逻辑不变；
- **权限越权**：不改变任何接口鉴权范围；
- **xxl-job executor 暴露面**：executor 监听 HTTP 端口（`/run`/`/kill`/`/beat`/`/log` 端点），accessToken 复用平台级 `xxl.job.admin.accessToken` 非空配置（与 coderepo/codecheck 一致），端口仅限平台内网访问（与既有服务部署网络策略相同）；启动时校验 adminAddresses/accessToken 非空并输出 ERROR 日志，防 `optional:nacos:xxl-job` 缺失时以空 token 静默启动。

## 风险 & 缓解

| 风险                                           | 缓解                                                                                                                                                                  |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| quartz 与 xxl 同步任务双跑                     | `fetchMajunCveHandler` 复用同一把分布式锁 `majun_fetch_quartz_lock`（quartz 跑批中手动触发 xxl 会被锁挡住，天然互斥）；且 xxl 侧默认停用，仅管理台手动触发作应急/补偿 |
| 清洗任务与解析跑批/漏洞刷新并发写 evf          | 最终一致：清洗启动记录 lifecycle 最大更新时间，写入前校验未变化（变化则中止本轮告警，下一轮收敛）；xxl 阻塞策略丢弃后续、路由单实例                                   |
| quartz 分布式锁 TTL 5 分钟 < 同步耗时 3~9 分钟 | 存量隐患，本次不动 quartz；xxl 侧超时上限设 30 分钟                                                                                                                   |
| 存量 NULL 展示                                 | 主数字展示 `--`（区别于 0）+ 气泡标注待重算；筛选 COALESCE NULL 安全；三条重算路径回刷                                                                                |
| 下钻筛选语义与"待闭环"口径解耦                 | 漏洞级别筛选语义=「包含该级别的漏洞」（既有机制），不引入新筛选参数；气泡提示明示已按类型筛选                                                                         |

## 跨仓影响

- **openlibing-vulnerability → openlibing-sbom**：`cve/details` 返回模型增量字段 issueState/isPending（向后兼容，sbom 侧同步逻辑适配）；口径变更只发生在 vulnerability 仓。
- **openlibing-sbom → openlibing-web**：本 design「API 接口契约变化」表的三个查询接口增量字段/参数；前端按增量字段适配，字段名以此为准。
- 特性分支建议：vulnerability `feat-cve-details-issue-state`、sbom `feat-pending-vul-statistics`、web `feat-vul-pending-display`。

## 顺带修复项

### 依赖类型筛选结果包含范围外类型

根因：软件成分数据默认 `groupByPackage=true` 分组查询中，过滤条件 `ps2.dependency_type IN (选中值)` 作用于组内任一包实例（整组返回），而组行展示的 dependency_type 为组内聚合值（MAX），导致行展示超出筛选范围。修复：分组行展示值取组内**命中过滤条件的值**（如 MIN(命中值)），实现"筛选直接 → 行展示直接"；单包模式不受影响，汇总/导出链路口径同步核对。

### 全量导出类型入口位置调整

1. 导出弹窗（sbomExportDialog.vue）移除「类型」radio，固定为软件物料清单（SBOM）导出，仅保留「规范/版本/格式」；
2. 「导出」下拉菜单：原「全量导出」更名「全量软件物料清单（SBOM）」；新增「全量软件成分数据（.xlsx）」入口，点击直接提交 xlsx 导出任务（承接原 exportType=xlsx 分支：仅依赖制品名，无需表单）；「声明文档」项维持不变；
3. 「全量软件物料清单（SBOM）」项 tooltip 同步移除 xlsx 相关描述。
