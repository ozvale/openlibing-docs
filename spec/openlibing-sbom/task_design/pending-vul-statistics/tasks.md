# pending-vul-statistics — 实现任务

> 覆盖三仓：openlibing-vulnerability / openlibing-sbom（主仓）/ openlibing-web。任务按依赖顺序排列（Vul 口径先行 → sbom 落表聚合 → 查询 → 前端 → 顺带修复）。每仓独立特性分支开发，任务内标注验证方式。

## 进度: 0/17 complete

### openlibing-vulnerability（feat-cve-details-issue-state）

- [ ] Task 1: `CveDetailToSbom` +`issueState` +`isPending` 字段
- [ ] Task 2: `AdminOperation#queryCveDetailsToSbom` include 追加 `issue_state`/`issue_labels`/`cvss_score`，新增 isPending 四条件计算（口径唯一实现点）
- [ ] Task 3: 单测：四条件 × 边界（已完成/rejected/挂起/UNAFFECTED/cvss 越界，含 cvss=100 与 cvss 缺失两个边界用例，固定与平台口径一致的行为）断言；本地 `mvn test` 相关用例通过

### openlibing-sbom（feat-pending-vul-statistics）

- [ ] Task 4: DDL 脚本整理（vulnerability_lifecycle 2 列、external_vul_ref 1 列、两级统计表各 7 列，`ADD COLUMN IF NOT EXISTS` 可空）
- [ ] Task 5: 实体/VO/View 扩字段：VulnerabilityLifecycle、ExternalVulRef、ProductStatistics/PackageStatistics、三个 Vo、ProductWithStatisticsView
- [ ] Task 6: `MajunVulServiceImpl.syncMajunVulData` 透传 issueState/isPending 落 lifecycle
- [ ] Task 7: 写入点①：`CollectStatisticsStep` lifecycle 内存索引 + `getSuitableVulnerabilityLifecycle` 匹配聚合 → evf.is_pending + 统计 pending 列
- [ ] Task 8: 写入点②：`VulRefreshStrategy` 聚合 evf 标志 + package_statistics pending 列 + 制品级重算（修复存量不对称）
- [ ] Task 9: xxl-job 接入：XxlJobConfig（appname=openlibing-sbom-executor，admin 地址/accessToken 复用平台级配置，启动校验非空并 ERROR 告警）+ Nacos `optional:nacos:xxl-job` + `fetchMajunCveHandler`（复制 quartz 逻辑，默认停用，复用同一把分布式锁 `majun_fetch_quartz_lock` 实现双轨互斥）+ `pendingVulCleanHandler`（SQL 预圈定有漏洞包、versions 预解析、只 UPDATE 变化行、batch 提交；启动记录 lifecycle 最大更新时间，写入前校验未变化否则中止本轮并告警）
- [ ] Task 10: 弹窗查询：`queryVulnerability` 主 SQL 加 isPending 筛选（`COALESCE(evf.is_pending, false)` NULL 安全）+ `is_pending DESC → score DESC` 默认排序；`getVulnerabilityStatus` 透传并按 isPending 降序组装 data；`queryPackageVulnerability` 同款筛选排序 + 行内补漏洞级 isPending 与优先 issue 的 issueState
- [ ] Task 11: 列表查询扩列：queryProductListMultiFilter / getPackageInfoByNameForPageMultiFilter / getVulCountSummaryMultiFilter SELECT/SUM 扩 pending；`PackageSortField` +VUL_COUNT +6 pending 枚举与排序白名单
- [ ] Task 12: 顺带修复 1：分组 SQL（getPackageGroupByNameForPageMultiFilter）行展示 dependency_type 取命中过滤条件的值；核对单包/汇总/导出链路口径一致
- [ ] Task 13: sbom 单测：口径透传断言、聚合（任一 true 即 true/无记录 false）、清洗任务幂等与变化行判定、弹窗筛选「存量 NULL + 筛选=否」用例；本地 `mvn test` 相关用例通过（先 `mvn clean` 防分支切换假编译错误）

### openlibing-web（feat-vul-pending-display）

- [ ] Task 14: 列表改造：表头更名「待闭环漏洞数」+ 表头气泡提示；主数字=待闭环数（含 0，pending 列 NULL 时展示 `--` 并气泡标注待重算）+ 悬浮整块气泡；成分列表新增「漏洞总数」块（不支持跳转，悬浮展示「漏洞总数 X · 待闭环 Y」与导出两列一一对应）+ 表头手动排序
- [ ] Task 15: 下钻筛选联动：制品级别块/总数块点击 → 展开成分列表 + 写入 includeVulSeverities（对应类型/全部类型）+ 漏斗旁 3 秒气泡（自动消失 + × 手动关闭）
- [ ] Task 16: 弹窗与详情页：SbomVulnerabilityTable columns1 加「是否闭环」「Issue 状态」列与下拉筛选（漏洞级过滤 + tooltip 粒度说明）；columns2（软件包详情）适配同款
- [ ] Task 17: 导出与顺带修复 2：Excel 导出加「待闭环漏洞数」列（=pending_vul_count）、保留「漏洞总数」列（=vul_count 全量）；下拉菜单更名「全量软件物料清单（SBOM）」+ 新增「全量软件成分数据（.xlsx）」直导出；sbomExportDialog 移除「类型」radio；验证方式：`npm run build` 必过（lint 为附加检查），并对列表块/联动筛选/弹窗列/导出入口逐项人工走查

## 验证与交付（流程任务，不属于编码任务清单）

- [ ] 三仓本地验证（编译 + 相关单测/lint）+ pre-commit 全部通过
- [ ] 合入测试环境分支 → 用户部署验证 → issue 回填验证结论
- [ ] 三仓业务 PR（关联业务 issue，ai-assisted 标签、评审人/测试人设置）+ docs 归档 PR
