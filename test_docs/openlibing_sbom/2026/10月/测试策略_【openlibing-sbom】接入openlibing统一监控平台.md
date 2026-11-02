# 接入openlibing统一监控平台 测试策略设计说明书

## 1. 基本信息

- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-sbom/issues/145
- **需求名称**: 【openlibing-sbom】接入openlibing统一监控平台
- **核心目标**:
  SRE 侧要求 sbom 服务接入 openlibing 统一监控平台，监控 SBOM 解析任务执行情况。服务接入共 4 步，本需求只覆盖代码侧步骤①：服务生成 Prometheus 自定义监控指标并暴露访问点。链路为 Micrometer Gauge（注册于 MeterRegistry）← Prometheus 抓取 `GET /actuator/prometheus`（scrape 周期触发 Gauge 求值）← CCE 云原生监控插件（集群内抓取）← 上报 AOM；Gauge 为懒求值，每次抓取时才执行 Provider 查询，无后台轮询线程。需交付 4 项指标：`sbom_task_running`（`raw_sbom.task_status='RUNNING'` 记录数）、`sbom_task_queued`（`task_status='WAIT'` 记录数）、`sbom_task_success_rate`（按 `update_time` 倒序最近 100 条，`FINISH / (FINISH + FAILED + FAILED_FINISH)`，值域 0~1，分母为 0 返回 0）、`sbom_task_duration_p99`（`sbom_batch_job_execution` JOIN `raw_sbom` 取 `end_time - start_time`，Java 侧转毫秒排序取 `index = ceil(0.99×n) - 1`，无样本返回 NaN）；统一标签 `scenario=sbom` 与 `application=${spring.application.name}`，Provider 异常经 `safeValue` 兜底为 NaN 且不阻断其他指标与端点（端点不返回 5xx）；配置 `exposure.include=health,prometheus`、`prometheus.enabled=true`、`metrics.tags.application` 全环境生效；前后端职责为纯后端改造，业务 REST 接口零变化。
- **开发责任人**: 陈明旭
- **测试责任人**: 赵威

---

## 2. 测试维度确认

- [x] **功能自检测试**

> - **测试重点:** `/actuator/prometheus` 端点可访问与 Prometheus 文本格式、4 项 `sbom_task_*` Gauge 契约与统一标签；running/queued 的 `task_status` 口径（RUNNING / WAIT，其余状态不计入，空态 0）；success_rate 的「最近 100 条 + 仅三类终态」口径、0~1 值域与分母为 0 边界；duration_p99 的 JOIN 取数、`start_time`/`end_time` 空值过滤、`ceil(0.99n)-1` 下标公式与无样本 NaN；Provider 异常兜底 NaN、error 日志与指标隔离；三项 management 配置生效、标签维度与业务接口零变化；抓取周期下的查询开销与无后台轮询特征；测试环境部署后云原生监控插件抓取与 AOM 上报。
> - **目的:** 确保服务侧改造交付的指标契约、口径、边界与异常处理符合设计要求，且云原生监控插件可在测试环境抓取并上报 AOM。
> - **触发条件:** 强制执行。

- [ ] **体验测试**
- [x] **集成测试**

> - **测试重点:** 测试环境 CCE 云原生监控插件抓取 Pod `/actuator/prometheus` 端点并上报 AOM，4 项指标可查、标签可作筛选维度、解析任务状态变化在 AOM 侧可见，AOM 取值与端点一致。
> - **目的:** 确认服务侧指标能沿「插件抓取 → AOM 上报」链路完整到达统一监控平台，接入链路末端可用。
> - **触发条件:** 强制执行。

- [x] **安全与隐私测试**

> - **测试重点:** 指标输出、标签与查询日志无凭证（password/secret/token/AK/SK/jdbc）与业务敏感信息；SQL 为固定语句、无外部入参拼接；异常日志不泄漏连接串/口令；依赖版本受 BOM 管理、未引入外部服务调用与第三方凭证。
> - **目的:** 确保新增指标能力不引入敏感信息泄漏面与注入面。
> - **触发条件:** 强制执行。

- [ ] **可靠性与韧性测试**
- [x] **可服务性与可观测性测试**

> - **测试重点:** `/actuator/prometheus` 端点可访问与 4 项 Gauge 输出、`scenario`/`application` 标签维度、AOM 指标可见性与任务状态变化可观测。
> - **目的:** 确保服务接入后的指标可采集、可筛选、可观测。
> - **触发条件:** 强制执行。

- [x] **性能与伸缩性测试**

> - **测试重点:** 抓取周期下的查询开销（单次抓取耗时、固定 4 组查询）、无后台轮询、无连接泄漏与内存累积；数据量放大 10 倍后的耗时变化。
> - **目的:** 确认指标求值不引入额外资源开销与性能回归。
> - **触发条件:** 强制执行（需求未给硬阈值，记录观察值）。

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.端点暴露与4项指标契约验证**:

- 前置条件: openlibing-sbom 已合入本需求代码并可启动（本地默认端口 13331，或测试环境 Pod）；数据库中存在至少 1 条 `raw_sbom` 记录与至少 1 条带 `start_time`/`end_time` 的 `sbom_batch_job_execution`；具备 `curl` 与文本检索能力
- 测试步骤:
  1. 执行 `curl -i http://localhost:13331/actuator/prometheus`，断言 HTTP 200 与 Prometheus 文本格式
  2. grep `^# HELP sbom_task_` 断言命中 4 条；grep `^# TYPE sbom_task_` 断言 4 条均为 gauge
  3. grep `^sbom_task_` 断言 4 项指标均存在
  4. 断言标签包含 `scenario="sbom"` 与 `application="openlibing-sbom"`
  5. 断言指标值为合法浮点数；断言不存在 `ops_task_*` 前缀
  6. 访问 `/actuator/health`，断言 200 且 UP
  7. 连续抓取 3 次，断言稳定输出
- 预期结果: 端点 200 且为 Prometheus 文本格式，4 项 Gauge 全部存在；标签、前缀与数值格式符合设计；health 可用

**2.运行中与排队数量口径验证**:

- 前置条件: 服务可启动且可直连 PostgreSQL 测试库，具备 `raw_sbom` 造数与清理权限；记录基线数量，执行后还原；仅在本地或独立测试库执行
- 测试步骤:
  1. 记录各状态基线数量
  2. 插入 RUNNING×3、WAIT×2；再插入 FINISH_PARSE / VUL_REFRESHING / FINISH / FAILED / FAILED_FINISH 各 2 条
  3. 抓取并断言 running = 基线+3、queued = 基线+2，其他状态未影响两项指标
  4. 状态迁移：RUNNING→FINISH ×2，断言 running 减 2；WAIT→RUNNING ×1，断言 queued 减 1、running 加 1
  5. 删除测试数据，断言回到基线
  6. 边界：无 RUNNING / 无 WAIT / 空表 → 输出 0.0；断言值为整数形态
- 预期结果: running / queued 严格按 RUNNING / WAIT 统计；其他状态不计入；无数据输出 0.0

**3.最近100条成功率终态口径验证**:

- 前置条件: 可直连本地或独立测试库/独立 schema 造数与清理（禁止在共享测试库执行清表操作），可精确控制 `update_time` 递增；清表前导出备份或使用事务回滚，执行后还原
- 测试步骤:
  1. 构造 120 条：最新 100 条中 FINISH=60、FAILED=20、FAILED_FINISH=10、其余中间/运行态 10 条；最早 20 条全 FAILED
  2. 抓取并断言成功率 ≈ 0.6667（容差 1e-4）；断言最早 20 条未进入分母
  3. 断言值域 0~1
  4. 判定表边界：最新 100 条全 FINISH → 1.0；全 FAILED/FAILED_FINISH → 0.0；全非终态 → 0；清空表 → 0
  5. 边界值：100 / 101 条；断言中间态不计入分子分母
- 预期结果: 成功率按最近 100 条三类终态计算；值域 0~1；分母为 0 返回 0

**4.任务耗时P99计算与样本过滤验证**:

- 前置条件: 可直连本地或独立测试库/独立 schema 对 `sbom_batch_job_execution` 与 `raw_sbom` 造数（禁止在共享测试库执行清表操作）；已确认 `job_execution_id` 关联字段与时间字段类型
- 测试步骤:
  1. n=10，耗时 100~1000ms，断言 P99 = 1000
  2. n=100，耗时 1~100ms 升序，断言取第 99 个（index=98）
  3. n=1，断言等于唯一样本
  4. 插入 `start_time`/`end_time` 为空各 1 条，断言不计入
  5. 插入无 `job_execution_id` 与 JOIN 不命中记录，断言排除
  6. 清空有效样本，断言字面量 `NaN`
  7. 断言单位为毫秒（允许科学计数法）；恢复数据后断言指标恢复
- 预期结果: 按 `ceil(0.99×n)-1` 取值；空时间与 JOIN 不命中样本排除；无样本 NaN

**5.Provider异常兜底NaN与指标隔离验证**:

- 前置条件: 可直连独立测试库并执行可逆故障注入（重命名表/回收权限）；已记录 4 项指标基线
- 测试步骤:
  1. 记录 4 项指标基线
  2. 注入全量查询异常（重命名 `raw_sbom` 或回收 SELECT）
  3. 抓取端点，断言 200 且 4 项均为 NaN；断言 error 日志含 `scenario=sbom`，日志无连接串/口令
  4. 恢复后断言无需重启即恢复正常值
  5. 单独注入 P99 异常，断言仅 `duration_p99` 为 NaN
  6. 断言端点无 4xx/5xx；清理并复核表结构
- 预期结果: 异常被 `safeValue` 捕获为 NaN；其他指标不受影响；恢复后自动复原；端点始终 200

**6.监控配置生效与标签维度验证**:

- 前置条件: 各环境配置可查阅；可修改本地配置并重启；已获取改动前业务接口清单
- 测试步骤:
  1. 断言三项配置（`exposure.include=health,prometheus`、`prometheus.enabled=true`、`metrics.tags.application`）存在且生效
  2. 断言位于全环境 `application.properties`
  3. 断言 4 项指标均带 `scenario="sbom"`，`application` 标签等于 `spring.application.name`
  4. 临时修改服务名重启，断言标签随之变化后恢复
  5. 断言指标前缀为 `sbom_task_`
  6. 对比业务 REST 接口清单，断言零变化；回归业务接口访问正常
- 预期结果: 配置全环境生效；标签取自配置；前缀正确；业务接口零变化

**7.抓取周期性能与无后台轮询验证**:

- 前置条件: 服务可启动，可查询表行数、获取线程栈；记录当前数据规模
- 测试步骤:
  1. 记录 `raw_sbom` / `sbom_batch_job_execution` 行数
  2. 连续抓取 ≥20 次（间隔 1s），记录耗时并计算 P95 与 max，断言无超时、无 5xx
  3. jstack 多次采样，断言无周期性指标求值线程
  4. 开启 SQL 日志，断言每次抓取仅 4 组查询
  5. 停止抓取 60s，断言无指标查询
  6. 数据量放大 10 倍后重复步骤 2
  7. 连续抓取 100 次，断言无连接泄漏与内存累积
  8. 与 15~30s 抓取周期对比
- 预期结果: 仅抓取时查询、固定 4 组；单次抓取耗时毫秒级（≥20 样本下记录 P95 与 max，需求未给硬阈值）；无后台轮询、无泄漏

**8.测试环境监控插件抓取与AOM上报验证**:

- 前置条件: 测试环境已部署本需求版本；deployment 已配置 prometheus 访问地址/形式；集群已安装云原生监控插件；已拉通监控平台方（如博云）；具备集群内访问与 AOM 查询权限
- 测试步骤:
  1. 确认 deployment 配置与 Pod 已更新
  2. 集群内 curl Pod 端点，断言 4 项指标存在
  3. 等待至少 2 个抓取周期后，AOM 查询 4 项指标，断言有数据点
  4. 断言标签可作为筛选维度
  5. 提交一个解析任务，观察 queued/running 在 AOM 侧变化
  6. 断言 AOM 数值与端点取值一致
  7. 回归业务接口，断言 `/actuator` 未对外暴露
- 预期结果: 插件抓取成功并上报 AOM；标签可筛选；状态变化可见；业务不受影响

### 3.2 安全与隐私测试专项

**9.指标与日志敏感信息检查验证**:

- 前置条件: 可获取完整指标输出与服务日志；具备代码只读审查权限；可触发一次指标查询异常
- 测试步骤:
  1. 保存完整指标输出
  2. 检索 password/secret/token/AK/SK/jdbc 等关键字，断言无命中
  3. 检查标签，断言仅固定标签
  4. 检查日志，断言无连接串/口令/SQL 参数
  5. 触发异常，断言异常日志无敏感信息
  6. 代码审查固定 SQL、常量、无用户输入
  7. 检查依赖版本由 BOM 管理
  8. 断言未引入外部服务调用与第三方凭证
- 预期结果: 指标与日志无凭证与业务敏感信息；SQL 无注入面；依赖受 BOM 治理
