# 软件成分数据页「漏洞刷新」功能 — sbom-vul-refresh

## 业务 Issue

- 待创建（业务 issue 建在 openlibing-sbom 源仓，Phase 7 功能验证/交付前补齐）
- 注：#71 曾提前创建，已关闭作废（https://gitcode.com/openlibing/openlibing-sbom/issues/71）

## 需求背景

gamma 环境 openlibing-web 软件成分数据页（CompositionAnalysis）中，各依赖包的漏洞数量（致命/高/中/低/无风险/未知）来自 `package_statistics` 预计算缓存，仅在 SBOM 批处理导入时计算，且漏洞关联写入为 upsert 语义（只增不删），导致页面漏洞数字长期无法更新。

用户诉求：提供"漏洞刷新"能力，点击后二次确认（提示刷新后当前漏洞信息将被覆盖），确认后制品级全量重新拉取 UVP 漏洞数据并覆盖旧数据、重算统计。

配套交互（评审确定）：

- 前端移除既有"漏洞依赖刷新"按钮（后端接口保留可直调），新增"漏洞刷新"按钮占据其位置
- 解析状态非完成态（非 FINISH/FAILED_FINISH）时轮询 `queryScanStatus`，按钮置灰 + loading
- 状态进入完成态停止轮询，右上角通知"漏洞已刷新完成，请刷新页面"（仅会话内经历过漏洞刷新时弹出）
- 按钮带问号图标悬浮提示刷新覆盖语义

## 功能描述

新增 `POST /sbom-api/refresh`（`productName` + `refreshType`，默认 VUL）：

| 返回 status           | 说明                                 |
| --------------------- | ------------------------------------ |
| `ACCEPTED`            | 受理成功，已提交专用线程池异步执行   |
| `ALREADY_IN_PROGRESS` | 同制品同类型刷新任务进行中（去重锁） |
| `NOT_FINISH`          | rawSbom 非 FINISH，终止触发          |
| `BUSY`                | 线程池队列满                         |

后端核心流程（方案 B：自研刷新服务 + 策略模式）：

1. 同步校验：product/sbom/rawSbom 加载，rawSbom 必须为 FINISH
2. 去重锁 → rawSbom 置 `VUL_REFRESHING`（新增状态值，页面映射"漏洞信息刷新中"）
3. 专用线程池（queueCapacity=64）异步执行 `VulRefreshStrategy`：
   - 事务外按 16/批调 UVP 拉取漏洞
   - REQUIRES_NEW 事务内：删旧 `external_vul_ref`（真覆盖）→ 写新关联 → 重算 `package_statistics` 漏洞字段
   - finally：rawSbom 恢复 FINISH、释放去重锁
4. 扩展性：策略模式（`SbomRefreshStrategy`），后续可扩展 license 等刷新类型（各自独立状态值）

## 不做

- 不修改既有批处理作业 `readSbomJob` 及其状态机消费点（SelectWaitRawSbomStep / RestartFailedReadJob / publishSbom 互斥）
- 不移除后端 `dependencyCache/refresh` 接口（仅前端入口移除）
- 不做刷新请求持久化与重启重放（服务重启丢内存任务，由启动状态恢复兜底，用户可重新触发）
- 不重算依赖类型 / License 统计字段（保持不变）

## 验收标准

- [ ] 后端：`POST /sbom-api/refresh` 按 status 契约返回（ACCEPTED / ALREADY_IN_PROGRESS / NOT_FINISH / BUSY）
- [ ] 后端：rawSbom 非 FINISH 时拒绝触发；刷新期间置 VUL_REFRESHING，结束（成败均）恢复 FINISH
- [ ] 后端：UVP 不可用/拉取失败时旧漏洞数据不丢失（删旧发生在拉取成功之后）
- [ ] 后端：刷新完成后漏洞可增可减（真覆盖），package_statistics 漏洞字段同步更新
- [ ] 后端：服务重启后遗留 VUL_REFRESHING 自动复位 FINISH
- [ ] 前端：移除"漏洞依赖刷新"按钮；"漏洞刷新"按钮（含问号 tooltip、二次确认、权限控制）占据其位置
- [ ] 前端：非完成态轮询联动按钮 loading；完成态停止轮询并按场景通知
- [ ] 单元测试覆盖编排服务、漏洞策略、Controller

## 影响范围

| 文件                                                            | 操作      | 说明                          |
| --------------------------------------------------------------- | --------- | ----------------------------- |
| `model/.../constants/SbomConstants.java`                        | 修改      | +`TASK_STATUS_VUL_REFRESHING` |
| `sbom-web/.../controller/SbomController.java`                   | 修改      | +`POST /refresh`              |
| `interface/.../api/sbom/SbomService.java`                       | 修改      | +`refreshSbom`                |
| `sbom-web/.../impl/SbomServiceImpl.java`                        | 修改      | 委托编排服务                  |
| `sbom-web/.../service/sbom/refresh/*`（6 个新类）               | 新增      | 策略框架 + 编排 + 漏洞策略    |
| `sbom-web/.../config/SbomRefreshExecutorConfig.java`            | 新增      | 专用线程池                    |
| `sbom-web/.../config/SbomRefreshStartupRecovery.java`（或同类） | 新增      | 启动状态恢复                  |
| `dao/.../ExternalVulRefRepository.java`                         | 修改      | +`deleteBySbomId`             |
| `test/.../SbomRefreshServiceTest.java` 等                       | 新增/修改 | 单元测试                      |
| openlibing-web `CompositionAnalysis/index.vue`                  | 修改      | 按钮/轮询/通知（跨仓）        |
| openlibing-web `api/sbom/url.ts`、`api.ts`                      | 修改      | 新增刷新 API（跨仓）          |

- 业务仓：`openlibing-sbom`（主）、`openlibing-web`（跨仓）
- 数据模型：不涉及表结构变更（复用 raw_sbom.taskStatus 新增字符串值）
- 所属分支：两仓均为 `feat-sbom-vul-refresh`

## 流程模式

Full 模式：跨两仓、后端新增类较多、含异步/状态机/事务边界 → proposal + design + tasks + 完整单测 + 两仓 pre-commit。
