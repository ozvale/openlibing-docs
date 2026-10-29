# 【openlibing-sbom】数据看板上报 — EDEVOPS 设计文档

---

## 1. 方案设计

### 1.1 背景

openlibing 已提供运营数据看板（feature-dashboard），其他特性（门禁检查、流水线、测试框架等）已完成数据上报接入。sbom 服务已积累各社区的 SBOM 解析统计数据，但未向看板上报，运营看板缺少 SBOM 维度的运营指标。

### 1.2 方案概述

在 openlibing-sbom 服务中新增定时任务，每日凌晨遍历所有激活的社区（ProductType），统计已走完全流程的 SBOM 扫描制品数量，通过 Feign 远程调用 openlibing-framework 的 `/manage/feature-dashboard/report` 接口上报。同时提供手动触发端点供运维按需调用。

### 1.3 方案架构

```
openlibing-sbom                              openlibing-framework
┌─────────────────────────┐                  ┌──────────────────────────┐
│ SbomDashboardReportJob  │ ──Quartz触发──▶  │                          │
│ (每日凌晨1点)           │                  │ FeatureOpsDashboard      │
│                         │                  │ Controller               │
│ SbomController          │                  │ /manage/feature-         │
│ GET /reportDashboard    │ ──手动触发──▶    │ dashboard/report         │
│                         │                  │                          │
│         │               │                  │         │                │
│         ▼               │                  │         ▼                │
│ SbomDashboardReport     │                  │ reportData()             │
│ ServiceImpl             │    Feign(Eureka) │   → upsert DB            │
│         │               │ ═══════════════▶ │                          │
│         ▼               │                  │ feature_ops_dashboard    │
│ ProductStatistics       │                  │ _report (MySQL)          │
│ Repository              │                  │                          │
│ (PostgreSQL)            │                  │                          │
└─────────────────────────┘                  └──────────────────────────┘
```

### 1.4 关键技术决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 统计口径 | `product_statistics` 表 | `CollectStatisticsStep` 走完全流程（解析+漏洞+统计）才写入，不受 `raw_sbom.task_status` 重新触发覆盖影响 |
| 去重方式 | `COUNT(DISTINCT product_id)` | 同一 product 多次扫描产生多条 `product_statistics` 记录，按 product 去重统计 |
| 分布式锁 | 按 `lockName` + `FOR UPDATE` | 查询不带 `lockBy`，按锁名全量查所有实例，配合行锁防并发竞态 |
| Feign 调用 | Eureka 服务发现 | 与已有 `VulViewClient` 同模式，不直连 URL |
| metric 格式 | key=`involved_product_count`，值=Long | `last_value` 类型接受 bare number |
| componentCount=0 | 跳过上报 | 减少无效请求 |

---

## 2. 实现逻辑设计

### 2.1 主流程

```
SbomDashboardReportJob.executeInternal()
  │
  ├─ 1. 获取 HOSTNAME
  │
  ├─ 2. acquireLock(lockName, hostname, expireMinutes)
  │     ├─ SELECT ... FOR UPDATE WHERE lock_name = ?
  │     ├─ 未过期 → 返回 false（跳过）
  │     └─ 过期/null → DELETE 旧锁 → INSERT 新锁 → 返回 true
  │
  ├─ 3. SbomDashboardReportService.report()
  │     │
  │     ├─ 3.1 ProductTypeRepository.findAll()
  │     │     └─ filter: active == true
  │     │
  │     └─ 3.2 for each productType:
  │           │
  │           ├─ ProductStatisticsRepository.countByProductType()
  │           │   SQL: COUNT(DISTINCT ps.product_id) FROM product_statistics ps
  │           │        JOIN product p ON ps.product_id = p.id
  │           │        WHERE p.attribute ->> 'productType' = :productType
  │           │
  │           ├─ componentCount == 0 → skip
  │           │
  │           ├─ 组装 DashboardReportRequest
  │           │   { community, feature="SBOM", userMetrics={},
  │           │     businessMetrics={involved_product_count: N},
  │           │     timestamp: LocalDateTime.now(UTC) }
  │           │
  │           ├─ FrameworkClient.reportFeatureDashboard(request)
  │           │
  │           └─ result.getCode() == 200 ? log success : log warn
  │
  └─ 4. finally: releaseLock(lockName, hostname)
```

### 2.2 分布式锁流程

```
事务1 (实例A)
acquireLock("sbom_dashboard_report_quartz_lock", "pod-a", 60)
  │
  ├─ SELECT ... FOR UPDATE WHERE lock_name = 'sbom_dashboard_report_quartz_lock'
  │   → 无记录或已过期
  │
  ├─ DELETE (清过期)
  │
  └─ INSERT (lock_by='pod-a', expire=NOW()+60min)
      → commit

事务1 (实例B，同时)
acquireLock("sbom_dashboard_report_quartz_lock", "pod-b", 60)
  │
  ├─ SELECT ... FOR UPDATE WHERE lock_name = 'sbom_dashboard_report_quartz_lock'
  │   → 阻塞等待事务1 commit
  │   → 读到 pod-a 的记录，未过期
  │
  └─ 返回 false（跳过执行）
```

### 2.3 异常处理

| 场景 | 处理 |
|------|------|
| 单社区统计/上报失败 | `catch (Exception e)` → `logger.error` → 继续下一个社区 |
| Feign 返回非 200 | `logger.warn` → 继续下一个社区 |
| acquireLock 返回 false | `logger.info` → 跳过本次执行 |
| Job 主体抛异常 | `catch (Exception e)` → `logger.error` → finally 释放锁 |
| 锁过期时间解析失败 | `isExpired` → 返回 true（视为过期，可重入） |

---

## 3. 类设计

### 3.1 新增类

#### SbomDashboardReportService (接口)

```
package: org.opensourceway.sbom.api.dashboard
路径: interface/.../api/dashboard/SbomDashboardReportService.java

方法:
  void report()
  职责: 上报接口定义
```

#### SbomDashboardReportServiceImpl

```
package: org.opensourceway.sbom.service.dashboard.impl
路径: sbom-web/.../service/dashboard/impl/SbomDashboardReportServiceImpl.java

依赖:
  ProductTypeRepository    (查询激活社区)
  ProductStatisticsRepository (统计制品数)
  FrameworkClient          (Feign 上报)

方法:
  void report()                        — 主流程
  void reportForProductType(String)    — 单社区处理
```

#### FrameworkClient (Feign)

```
package: org.opensourceway.sbom.util.feign
路径: sbom-web/.../util/feign/FrameworkClient.java

注解: @FeignClient(name = "${feign.framework.name:openlibing-framework}")

方法:
  @PostMapping("/manage/feature-dashboard/report")
  DataResult<Map<String, Object>> reportFeatureDashboard(
      @RequestBody DashboardReportRequest request)
```

#### DashboardReportRequest (DTO)

```
package: org.opensourceway.sbom.model.pojo.request.dashboard
路径: model/.../pojo/request/dashboard/DashboardReportRequest.java

注解: @Data

字段:
  String community
  String repo
  String feature
  Map<String, Object> userMetrics
  Map<String, Object> businessMetrics
  String timestamp
  Boolean isInvolved
```

#### SbomDashboardReportJob (Quartz Job)

```
package: org.opensourceway.sbom.quartz.jobs
路径: quartz/.../jobs/SbomDashboardReportJob.java

继承: QuartzJobBean

依赖:
  SbomDashboardReportService
  QuartzLockManager

方法:
  void executeInternal(JobExecutionContext)
```

### 3.2 修改类

| 类 | 变更 |
|----|------|
| `ScheduleBatchJobConfig` | 新增 `sbomDashboardReportJobDetail` + `sbomDashboardReportJobTrigger` |
| `SbomController` | 新增 `GET /sbom-api/reportDashboard` |
| `ProductStatisticsRepository` | 新增 `countByProductType(String)` |
| `QuartzLockManager` (接口) | `acquireLock` 加 `expireMinutes` 参数，删除 `renewLock` |
| `QuartzLockManagerImpl` | `acquireLock` 用 `queryLockByLockName` + `FOR UPDATE`，删除 `renewLock` |
| `QuartzLockRepository` | 新增 `queryLockByLockName`、`deleteLock`，SQL 支持动态过期时间 |
| `FetchMajunCveJob` | 适配新 `acquireLock` 签名，删除 `renewLock` 死代码 |

---

## 4. 数据模型设计

### 4.1 涉及的数据库表

| 表 | 数据库 | 用途 |
|----|--------|------|
| `product_type` | PostgreSQL (sbom) | 查询激活社区列表 |
| `product_statistics` | PostgreSQL (sbom) | 统计已扫描制品数（`COUNT(DISTINCT product_id)`） |
| `product` | PostgreSQL (sbom) | JOIN 获取 `attribute ->> 'productType'` 过滤社区 |
| `quartz_lock` | PostgreSQL (sbom) | 分布式锁表 |
| `feature_ops_dashboard_report` | MySQL (framework) | 看板上报数据存储（framework 侧，不改动） |

### 4.2 核心查询 SQL

```sql
-- 按社区统计已扫描制品数
SELECT COUNT(DISTINCT ps.product_id)
FROM product_statistics ps
JOIN product p ON ps.product_id = p.id
WHERE p.attribute ->> 'productType' = :productType
```

### 4.3 分布式锁 SQL

```sql
-- 查询锁（带行锁）
SELECT * FROM quartz_lock WHERE lock_name = :lockName FOR UPDATE

-- 插入锁（动态过期时间）
INSERT INTO quartz_lock (lock_name, lock_by, lock_expire_time)
VALUES (:lockName, :lockBy,
    TO_CHAR(NOW() + CAST(:expireMinutes || ' MINUTES' AS INTERVAL),
    'YYYY-MM-DD HH24:MI:SS'))

-- 释放锁（仅持有者可释放）
DELETE FROM quartz_lock WHERE lock_name = :lockName AND lock_by = :lockBy

-- 清过期锁
DELETE FROM quartz_lock WHERE lock_name = :lockName
```

### 4.4 上报数据结构

```json
{
  "community": "openEuler",
  "feature": "SBOM",
  "userMetrics": {},
  "businessMetrics": {
    "involved_product_count": 500
  },
  "timestamp": "2026-07-07T12:00:00"
}
```

---

## 5. 性能设计

### 5.1 数据库查询优化

| 优化点 | 说明 |
|--------|------|
| 查询频率 | 定时任务每日执行一次，非高频查询 |
| JSONB 操作符 | `attribute ->> 'productType'` 取 Text 比较，非 `@>` 包含查询，减少解析开销 |
| COUNT DISTINCT | `product_statistics.product_id` 建议建索引加速去重计数 |
| 锁查询行锁 | `FOR UPDATE` 仅在 `acquireLock` 时短暂持锁，之后 commit 释放 |

### 5.2 并发控制

| 场景 | 处理 |
|------|------|
| 多实例定时触发 | `FOR UPDATE` 串行化抢锁，只有一个实例获得执行权 |
| 定时与手动同时触发 | 同一 `lockName`，先到先得 |
| 单个社区失败 | 独立 try-catch，不阻塞后续社区 |

### 5.3 请求量评估

| 指标 | 估算 |
|------|------|
| 激活社区数 | ~6 个（OpenHarmony/openEuler/openUBMC/CANN/MindIE/MindCluster） |
| 单次 SQL 查询 | 6 次 COUNT（各社区 1 次） |
| 单次 Feign 调用 | ≤6 次（0 则跳过） |
| 执行时长 | <5 秒（无大数据量操作） |

---

## 6. API 接口设计

### 6.1 新增接口

#### `GET /sbom-api/reportDashboard`

- **功能**：手动触发 SBOM 数据看板上报
- **鉴权**：继承 `/sbom-api` 原有鉴权逻辑，无额外鉴权
- **请求参数**：无
- **成功响应**：`200 "success"`
- **失败响应**：`417 "failed"`

### 6.2 依赖的外部接口

#### `POST /manage/feature-dashboard/report` (framework)

- **调用方**：openlibing-sbom → openlibing-framework
- **调用方式**：Feign（Eureka 服务发现）
- **请求体**：`DashboardReportRequest` JSON
- **响应体**：`DataResult<Map<String,Object>>`（`code=200` 表示成功）
- **频率限制**：单社区每日至多 1 次

| 请求字段 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| `community` | String | 否 | 社区名称 |
| `feature` | String | 是 | 特性名（"SBOM"） |
| `userMetrics` | Map | 是 | 用户指标（{}） |
| `businessMetrics` | Map | 是 | `{"involved_product_count": <Long>}` |
| `timestamp` | String | 否 | ISO 8601 时间 |

---

## 7. 安全设计

### 7.1 鉴权

继承原有鉴权逻辑。Controller 手动触发端点复用 `/sbom-api` 路径，由网关统一鉴权。Feign 调用 framework 走内部 Eureka 服务发现，无 session 透传。

### 7.2 敏感信息

- 上报数据仅包含社区名称、特性名称、统计数字，不包含用户信息或敏感数据
- 无 appkey/token/cookie 硬编码

### 7.3 审计日志

| 日志点 | 内容 |
|--------|------|
| Job 启动 | `start sbom dashboard report job, time: {}` |
| Job 完成 | `finish sbom dashboard report job, coast: {} ms` |
| 获取锁 | `acquire lock success, lockName: {}, lockBy: {}, expireMinutes: {}` |
| 锁跳过 | `acquire lock not expire, lockName: {}, held by: {}` |
| 锁失败 | `acquire lock failed, lockName: {}, lockBy: {}` |
| 释放锁 | `release lock success, lockName: {}, lockBy: {}` |
| 各社区上报成功 | `sbom dashboard report success for product type: {}` |
| 各社区上报异常 | `sbom dashboard report unexpected response for product type: {}, response: {}` |
| 各社区处理失败 | `sbom dashboard report failed for product type: {}` |
| 0 跳过 | `sbom dashboard report skip for product type: {}, no finished tasks` |

### 7.4 硬编码检查

- 无硬编码凭证、Token、appkey
- Feign 服务名通过 `${feign.framework.name}` 配置
- 锁过期时间通过 `${sbom.dashboard.report.lock.expire-minutes}` 配置
