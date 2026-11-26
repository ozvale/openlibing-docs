# 项目资源效率环比 — 实现计划

> 后续编码时按任务顺序执行；行为变化先写失败测试，再写最小实现。每轮是否提交由用户明确指令决定，本计划不授权自动 commit 或 push。

**目标：** 为 `ops-project-resource-efficiency` 增加紧邻前一等长自然日周期数据，后端保证两期同口径，并直接返回增减值/增减率，前端只做展示。

**架构：** 保留当前期查询和分页，开启环比后仅以当前页 `projectIds` 为边界复用现有 Mapper 查询上一期，再按项目 ID 合并。响应新增 `previousPeriod`，包含上一期窗口、上一期原值以及后端计算好的 `<指标>Delta` / `<指标>ChangeRate`，前端不再计算。

**技术栈：** Java 21、Spring、MyBatis XML、JUnit 5、Mockito、AssertJ、Maven；前端沿用项目现有框架，不新增依赖。

**进度：4/6 complete（Task 1-4 后端完成；Task 5 前端待按 frontend-integration.md 实施）**

---

### Task 1：确定请求和响应契约

**文件：**

- 修改：`openlibing-ops/src/test/java/com/openlibing/ops/domain/mapper/ops/ResourceEfficiencyMapperXmlTest.java`
- 修改：`openlibing-ops/src/main/java/com/openlibing/ops/api/request/common/detail/OpsProjectResourceEfficiencyReq.java`
- 修改：`openlibing-ops/src/main/java/com/openlibing/ops/api/response/common/detail/OpsProjectResourceEfficiencyResp.java`
- 新增：`openlibing-ops/src/main/java/com/openlibing/ops/api/response/common/detail/OpsProjectResourceEfficiencyPreviousPeriodResp.java`

**步骤：**

- [x] 1.1 在现有请求契约测试中新增 `includePreviousPeriod` 属性断言，并为 `previousPeriod` 响应结构增加反射/序列化测试。
- [x] 1.2 运行 `mvn "-Dtest=ResourceEfficiencyMapperXmlTest" test`，确认测试因字段和 DTO 尚不存在而按预期失败。
- [x] 1.3 请求增加可空 `Boolean includePreviousPeriod`；主响应增加 `previousPeriod`；新 DTO 增加 `startTime/endTime` 和 design.md 列出的 10 个数值字段，沿用现有 Lombok、`@JsonFormat` 和版权头风格。
- [x] 1.4 重跑契约测试，确认通过；不修改 Controller 和 `DetailReq` 的 category 注册。

### Task 2：让现有 Mapper 支持可选当前页项目集合

**文件：**

- 修改：`openlibing-ops/src/test/java/com/openlibing/ops/domain/mapper/ops/ResourceEfficiencyMapperXmlTest.java`
- 修改：`openlibing-ops/src/main/java/com/openlibing/ops/domain/mapper/ops/ResourceEfficiencyMapper.java`
- 修改：`openlibing-ops/src/main/resources/mapper/ResourceEfficiencyMapper.xml`

**步骤：**

- [x] 2.1 先增加两组 BoundSql 测试：`projectIds=[100,200]` 时 `proj_pool` 包含项目 ID `IN` 条件；`projectIds=null` 时不包含该条件，且 `engineeringScope` 原 SQL 保持不变。
- [x] 2.2 运行 `mvn "-Dtest=ResourceEfficiencyMapperXmlTest" test`，确认新增测试因方法参数或 SQL 条件缺失而失败。
- [x] 2.3 给 `queryProjectEfficiencyList` 增加 `@Param("projectIds") List<Integer> projectIds`，当前调用传 `null`；XML 仅在 `proj_pool` 添加非空集合 `<foreach>` 条件。
- [x] 2.4 修正现有测试和调用的参数映射后重跑，确认当前期 SQL 兼容、上一期 ID 条件生效。
- [x] 2.5 检查没有复制项目效率 SQL，没有给 count 或资源池名称查询增加不必要的参数。

### Task 3：实现上一期窗口推导且保持默认路径不变

**文件：**

- 修改：`openlibing-ops/src/test/java/com/openlibing/ops/app/service/ops/ResourceEfficiencyServiceTest.java`
- 修改：`openlibing-ops/src/main/java/com/openlibing/ops/app/service/ops/ResourceEfficiencyService.java`

**步骤：**

- [x] 3.1 先写默认路径测试：`includePreviousPeriod=null/false` 时只执行现有一次列表查询，`previousPeriod=null`，不增加 count 或资源池查询。
- [x] 3.2 增加参数化窗口测试：单日、2026-11-20～24、2026-11-01～03、2026-01-01～02，断言上一期起止时间分别为 design.md 中的预期值。
- [x] 3.3 增加工作日测试：上一期按自然日平移，但分别调用节假日查询并使用各自工作日数；原请求对象的时间和分页不被修改。
- [x] 3.4 运行 `mvn "-Dtest=ResourceEfficiencyServiceTest" test`，确认新增断言在实现前失败。
- [x] 3.5 在 Service 中提取小范围窗口推导/请求复制逻辑，使用 `ChronoUnit.DAYS` 和 `minusDays(windowDays)`，逐项复制查询条件，不引入克隆框架。
- [x] 3.6 重跑测试，确认默认路径、跨月/跨年和工作日规则通过。

### Task 4：查询、归一化并合并上一期数据

**文件：**

- 修改：`openlibing-ops/src/test/java/com/openlibing/ops/app/service/ops/ResourceEfficiencyServiceTest.java`
- 修改：`openlibing-ops/src/main/java/com/openlibing/ops/app/service/ops/ResourceEfficiencyService.java`

**步骤：**

- [x] 4.1 先写当前页边界测试：开启环比后，上一期 Mapper 收到当前页全部 `projectIds`、`page=1`、`pageSize=当前页数量`，不执行第二次 count 和资源池查询。
- [x] 4.2 增加乱序合并测试：当前页与上一期返回顺序不同，仍必须按 `projectId` 对应，不能按下标。
- [x] 4.3 增加缺失和归一化测试：上一期缺行时保留窗口且指标为 `null`；两期分钟/卡时保留两位小数，SQL 0～1 比率均转换为 0～100 百分比。
- [x] 4.4 增加 `engineeringScope`、项目过滤和 `isAllDay` 传递断言，以及上一期查询异常不向“无数据”降级测试。
- [x] 4.5 运行 `mvn "-Dtest=ResourceEfficiencyServiceTest" test`，确认新增测试按预期失败。
- [x] 4.6 实现上一期查询和 Map 合并，提取两期共用的响应归一化方法；当前页为空时跳过上一期查询，当前排序分页不变。
- [x] 4.7 重跑 Service 和 Mapper 测试，确认全部通过且无逐项目查询。
- [x] 4.8 按用户要求改为后端计算 `<指标>Delta` / `<指标>ChangeRate`：工厂方法一次完成窗口、上一期原值与增减计算，前端直接展示；空值、零分母与百分点规则由后端保证。

### Task 5：前端按统一规则展示环比

**文件：**

- 前端项目中的项目资源效率列表、指标展示组件及对应测试；实际路径由前端负责人在其仓内定位，本计划不假设前端仓结构。
- 联调依据：本目录 `design.md` 第 8 节。

**步骤：**

- [ ] 5.1 请求开启 `includePreviousPeriod=true`，当前字段和列表顺序保持原逻辑，从同记录的 `previousPeriod` 读取上一期，不发起第二次分页请求。
- [ ] 5.2 直接读取后端返回的 `<指标>Delta` / `<指标>ChangeRate` 展示，不再前端计算；`ChangeRate` 已是百分比数值，不要重复乘 100。
- [ ] 5.3 为 6 个百分比指标使用百分点(pp)展示差值，其他指标使用原单位；Tooltip 展示上一期窗口和原值，不显示 `Infinity/NaN`。
- [ ] 5.4 按指标语义配置趋势颜色，排队时长下降不得套用作恶化的统一红色；本期不增加环比排序。
- [ ] 5.5 用固定样例验证：12.30 对 10.00 展示 `+2.30/+23.00%`；65.40% 对 60.00% 展示 `+5.40pp`；空值和零分母显示 `--`。

### Task 6：回归、性能检查和交付

**文件：**

- 修改：本目录 `frontend-integration.md`（进入联调前补充最终请求/响应示例）。
- 修改：本目录 `tasks.md`（勾选实际完成项）。

**步骤：**

- [x] 6.1 运行 `mvn "-Dtest=ResourceEfficiencyMapperXmlTest,ResourceEfficiencyServiceTest" test`，确认新增和相关现有测试通过。
- [x] 6.2 运行 `mvn "-Dtest=ResourceEfficiencyMapperXmlTest,ResourceEfficiencyServiceTest,NpuUsageMapperXmlTest,NpuUsageServiceTest,NightlyPipelineDashboardMapperXmlTest,NightlyPipelineDashboardRespEfficiencyTest,ResourceOperationServiceTest" test` 和 `mvn spotless:check`，确认看板回归与格式检查通过。
- [x] 6.3 执行 `git diff --check` 并检查 `git status --short`，确认只修改本需求业务文件和文档，不夹带其他需求或数据库变更。
- [ ] 6.4 联调时通过只读 `EXPLAIN`、查询日志或慢查询记录确认上一期 `projectIds` 条件生效，无 N+1、无全项目上一期聚合，并记录两期查询耗时。
- [ ] 6.5 默认不传开关验证旧客户端兼容，再开启开关完成两期窗口、排序分页、空值、零分母和百分点验收。
- [x] 6.6 交付用户自测；未经用户明确要求，不提交、不推送、不创建 Issue/PR。
