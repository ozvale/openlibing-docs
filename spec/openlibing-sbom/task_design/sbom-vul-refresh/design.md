# 软件成分数据页「漏洞刷新」功能 — 技术方案

> 完整设计文档（七大方面定稿版）：本地 `D:\work\design\202609\sbom-vul-refresh.md`；本文档为自包含精简版。

## 1. 方案设计

- 整体思路：REST 同步派发 + 专用线程池异步执行 + 策略模式。编排服务负责公共流程（校验/去重/状态占用与恢复/线程池），策略只实现"刷什么"。
- 职责划分：前端负责按钮/权限/二次确认/轮询联动/通知；后端负责触发校验、状态机、异步调度、UVP 拉取、删旧写新、统计重算。
- 涉及服务：`openlibing-sbom`（主，本 spec 名下）、`openlibing-web`（跨仓，见 §7）。

### 核心时序

```
POST /sbom-api/refresh (productName, VUL)
  └─ SbomRefreshService.refresh（HTTP 线程）
       1. product/sbom/rawSbom 加载；rawSbom != FINISH → NOT_FINISH 终止
       2. 去重锁 putIfAbsent(productName:type) 失败 → ALREADY_IN_PROGRESS
       3. rawSbom = VUL_REFRESHING
       4. strategyFactory.getStrategy(type) → refreshExecutor.execute(worker)
       5. 返回 {status, refreshId=UUID, message}
worker（sbomRefreshExecutor 线程）：
  try { strategy.doRefresh(ctx) } catch { log } finally { rawSbom=FINISH; 锁释放 }
```

## 2. 实现逻辑设计

### 关键规则

- **触发前校验**：rawSbom.taskStatus 严格等于 FINISH 才放行（WAIT/RUNNING/FINISH_PARSE/FAILED/FAILED_FINISH/VUL_REFRESHING 全拒）。
- **状态占用**：派发时置 `TASK_STATUS_VUL_REFRESHING = "VUL_REFRESHING"`（SbomConstants 新增）；结束（成败均 finally）恢复 FINISH——不可恢复为 FAILED，否则 `RestartFailedReadJob` 会用旧 jobExecutionId 重启导入作业。
- **状态消费点零改动核查**：SelectWaitRawSbomStep 只取 WAIT；RestartFailedReadJob 只取 FAILED；publishSbom 互斥非 {FINISH, FAILED_FINISH} 拒绝（刷新期间导入被拦截）；getSbomPublishResult else 分支=处理中；queryScanStatus 透传（前端补映射）。
- **启动恢复**：ApplicationRunner 将遗留 VUL_REFRESHING 复位 FINISH（服务重启丢内存任务的兜底）。
- **领域逻辑（VulRefreshStrategy.doRefresh）**：
  1. `needRequest()` 检查（UVP 不可用直接结束，与批处理一致）；
  2. 收集 sbom 全部 package 的 externalPurlRefs（category ∈ COORDINATES_TYPE_NAME_LIST）；
  3. 事务外按 16/批调 `uvpService.extractVulForPurlRefChunk(sbomId, chunk, productType)`，productType 取 `product.attribute.get("productType")`（与批处理一致）；
  4. REQUIRES_NEW 事务：`deleteBySbomId` 删旧 → flush → `persistExternalVulRefChunk` 写新 → 重算全部 `package_statistics` 漏洞字段（算法对齐 CollectStatisticsStep：vulCount = distinct vulnerability 数；6 级计数按 CvssSeverity；severity 取最高级，无漏洞 NA；依赖/License 字段不动）。
- **覆盖语义保证**：先拉取（事务外）成功后才进事务删旧写新——拉取失败旧数据不丢；删旧+写新+重算同一事务，页面无中间态。

### 异常与边界

| 场景                 | 处理                                                             |
| -------------------- | ---------------------------------------------------------------- |
| product/sbom 不存在  | 抛 `SbomRuntimeException`                                        |
| rawSbom 非 FINISH    | `NOT_FINISH` 终止                                                |
| 同制品同类型重复触发 | 去重锁 → `ALREADY_IN_PROGRESS`                                   |
| 线程池队列满         | AbortPolicy → 派发层捕获 → 恢复 FINISH + 释放锁 → `BUSY`         |
| UVP 异常/返回空      | 任务捕获告警，finally 恢复 FINISH；空结果 = 计数归 0（覆盖语义） |
| 统计重算异常         | 事务回滚，finally 恢复 FINISH                                    |
| 服务重启             | 启动恢复复位状态，用户重新触发                                   |

## 3. 类设计（openlibing-sbom）

新增（`sbom-web/service/sbom/refresh/` + config）：

- `RefreshType`（enum：VUL；预留 LICENSE）
- `RefreshContext`（productName/sbomId/product/productType）
- `SbomRefreshStrategy`（接口：`supportType()` / `occupyingStatus()` / `doRefresh(ctx)`）
- `SbomRefreshStrategyFactory`（构造注入全部策略建 Map，未注册类型抛异常）
- `SbomRefreshService`（编排：`refresh(String, RefreshType)`；持有 `inProgressKeys: ConcurrentHashMap`）
- `VulRefreshStrategy`（VUL 实现，occupyingStatus=VUL_REFRESHING）
- `SbomRefreshExecutorConfig`（`@Bean("sbomRefreshExecutor")` ThreadPoolTaskExecutor：core=2/max=4/queue=64/keepAlive=60s/allowCoreThreadTimeOut/AbortPolicy/waitForTasksToCompleteOnShutdown）
- 启动恢复 ApplicationRunner（复位遗留 VUL_REFRESHING → FINISH）

修改：

- `model/.../constants/SbomConstants.java`：+`TASK_STATUS_VUL_REFRESHING`
- `sbom-web/.../controller/SbomController.java`：+`POST /refresh`（`@LogApi`）
- `interface/.../api/sbom/SbomService.java` + `sbom-web/.../impl/SbomServiceImpl.java`：+`refreshSbom(productName, refreshType)`
- `dao/.../ExternalVulRefRepository.java`：+`@Modifying` native `deleteBySbomId(UUID)`

## 4. 数据模型设计

不涉及表结构/字段变更与迁移：

1. raw_sbom.taskStatus 复用既有字符串列，仅新增值 `VUL_REFRESHING`（无枚举约束）；
2. external_vul_ref 仅数据级 DELETE+INSERT（按 sbomId 经 package 关联）；
3. package_statistics 仅既有漏洞字段 UPDATE（orphanRemoval 删旧插新为既有机制）。

## 5. 性能设计

- UVP 分批 16/批，事务外网络调用不占 DB 连接；
- 删除 set-based 单条 native（与批处理级联删除同路径，依赖既有索引），无逐行循环；
- 统计重算加载 product 级联聚合，内存峰值与批处理 collectStatisticsTask 同量级；
- 线程池并发受控（2~4 线程），队列 64（I/O 密集型分钟级任务，排队为主要缓冲；单任务 KB 级内存；平台并发个位数 → 实际不会触发拒绝；AbortPolicy + 派发层捕获恢复 → 任务不静默丢失、状态不卡死）。

## 6. API 接口设计

```
POST /gateway/openlibing-sbom/sbom-api/refresh
入参：productName（必填）、refreshType（默认 VUL，枚举白名单）
出参：{ code:200, data:{ status: ACCEPTED|ALREADY_IN_PROGRESS|NOT_FINISH|BUSY, refreshId, message } }
错误码：复用 DataResult 异常体系
```

关联既有接口（零改动）：`queryScanStatus`（前端新增 5s 轮询消费）、`querySbomPublishResult`、`dependencyCache/refresh`（保留，前端入口移除）、`querySbomPackagesMultiFilter` 等。

## 7. 跨仓影响（openlibing-web）

- `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`：
  - 移除"漏洞依赖刷新"按钮及其处理（后端接口保留）；
  - 新增"漏洞刷新"按钮（占位"全量导出"左侧、NoPermissionPopover + refreshDependency 权限、QuestionFilled 问号 el-tooltip"点击按钮后会刷新并覆盖当前制品下的依赖包漏洞信息"、ElMessageBox.confirm 二次确认）；
  - 解析状态轮询（完成态集合 {FINISH, FAILED_FINISH}，5s setInterval，onUnmounted 清理）：非完成态按钮 disabled+loading；进入完成态停止轮询并通知——会话内经历过 VUL_REFRESHING 且到 FINISH：ElNotification success"漏洞已刷新完成，请刷新页面"；到 FAILED_FINISH：warning"制品解析任务已结束（失败），可重新触发漏洞刷新"；普通解析完成不弹通知；
  - `scanStatusMap` 补 `VUL_REFRESHING: { label: '漏洞信息刷新中', type: 'warning' }`；
  - status→提示映射：ACCEPTED=success"开始处理"、ALREADY_IN_PROGRESS="正在处理中"、NOT_FINISH=透传文案、BUSY="系统繁忙，请稍后再试"。
- `api/sbom/url.ts`：+`REFRESH_SBOM_URL = SBOM + '/sbom-api/refresh'`；
- `api/sbom/api.ts`：+`refreshSbom(params)`（POST，productName + refreshType）。
- 前端仓分支：`feat-sbom-vul-refresh`（spec 归档在 openlibing-sbom 名下）。

## 8. 测试策略

- 单测（openlibing-sbom）：SbomRefreshServiceTest（校验/去重/状态占用恢复/线程池拒绝/启动恢复）、VulRefreshStrategyTest（needRequest 跳过/删旧写新/拉取失败旧数据保留/统计重算/空漏洞归 0/回滚）、SbomControllerTest 补 /refresh 用例；
- 验证：后端相关模块 `mvn` 编译 + 单测；前端 gamma 环境合并测试分支人工部署验证（本地沙箱无 node 环境）。
