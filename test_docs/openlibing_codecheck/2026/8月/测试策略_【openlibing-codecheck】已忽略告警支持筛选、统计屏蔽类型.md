# 代码检查模块-已忽略告警支持筛选、统计屏蔽类型 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/162
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/162
* **需求名称**: 代码检查模块-已忽略告警支持筛选、统计屏蔽类型
* **核心目标**:
  已忽略告警支持按状态筛选、按屏蔽类型（list_state）统计；静态告警列表查询优化，引入 project_ids 数组字段 + is_default_visible 派生字段 + 8 个 project_ids 索引，将多值 repo_key $in 替换为单值 project_ids $in，消除大项目（70+ 仓库）深页查询的 MongoDB 32MB 内存排序限制（errorCode 96）；通过启动回填、定时对账保障 project_ids / is_default_visible 数据一致性；同时支持导出 snippet 超长截断与 source 筛选多选。
* **开发责任人**: 杨宇萌
* **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

* [x] **功能自检测试**
> * **测试重点:** 已忽略告警按状态筛选、"查看全部"场景默认可见性（is_default_visible）、按屏蔽类型（list_state）分组统计、5 处查询入口（getStaticAlarmList / getIssueCount / filter-options / exportStaticAlarm / batch validate）切换到 project_ids 路径后结果正确性、source 筛选多选、导出 snippet 超长截断。
> * **目的:** 确保优化后筛选、统计、可见性、导出等功能行为正确，各查询入口结果与优化前一致。
> * **触发条件:** 强制执行。

* [ ] **体验测试**
* [x] **集成测试**
> * **测试重点:** 启动回填（ProjectIdsBackfillRunner）→ 查询入口端到端链路、定时对账兜底（XxlJobHandler staticAlarmProjectIdsReconcileHandler）与查询链路一致性。
> * **目的:** 消除数据回填、对账与查询多环节集成的级联影响风险，保证各环节数据一致。
> * **触发条件:** 需求标签含 `need_itest`。

* [ ] **安全与隐私测试**
* [x] **可靠性与韧性测试**
> * **测试重点:** 启动回填幂等性（$set 覆盖写入、重复启动 modifiedCount=0）、MySQL repo_info 与 MongoDB project_ids 数据一致性对账、对账任务异常场景兜底。
> * **目的:** 确保回填/对账机制可靠，数据漂移可被定时任务收敛，业务不受影响。
> * **触发条件:** 涉及核心Core服务变更，且架构设计含可靠性与韧性设计。

* [ ] **可服务性与可观测性测试**
* [x] **性能与伸缩性测试**
> * **测试重点:** 大项目（70+ 仓库）深页查询不再触发 MongoDB 32MB 内存排序限制（errorCode 96）、深页查询响应时间、8 个 project_ids 索引生效情况。
> * **目的:** 消除笛卡尔积导致的查询退化，确保深页查询性能达标、无内存排序限制报错。
> * **触发条件:** 涉及核心Core服务变更，且架构设计含性能与伸缩性设计。

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1. 已忽略告警按状态筛选验证**:
* 前置条件:代码检查页面存在多种 list_state 状态的静态告警数据
* 测试步骤:
    1. 进入代码检查模块已忽略告警列表页
    2. 依次按 IGNORED_FALSE_POSITIVE / IGNORED_TEST_USAGE / IGNORED_WONT_FIX 等状态进行筛选
    3. 验证筛选结果只包含对应 list_state 的告警
    4. 验证筛选后列表与统计数字一致
* 预期结果: 各状态筛选结果正确，列表与统计一致

**2. "查看全部"场景默认可见性（is_default_visible）验证**:
* 前置条件:代码检查页面存在包含后端保留状态的静态告警数据
* 测试步骤:
    1. 进入"查看全部"（无 tab）场景的告警列表
    2. 验证 OPEN / IGNORED_FALSE_POSITIVE / IGNORED_TEST_USAGE / IGNORED_WONT_FIX / RESOLVED_AUTO 状态的告警默认可见
    3. 验证 PENDING_REVIEW / SUPPRESSED_BY_COMMENT 状态的告警不展示
    4. 通过接口直接校验 is_default_visible 字段派生值是否符合规则
* 预期结果: is_default_visible 派生规则正确，"查看全部"场景仅展示默认可见状态

**3. 按屏蔽类型（list_state）统计验证**:
* 前置条件:代码检查页面存在多种 list_state 状态的静态告警数据
* 测试步骤:
    1. 进入代码检查页面统计区域
    2. 按 list_state 分组查看各屏蔽类型（OPEN / IGNORED_FALSE_POSITIVE / IGNORED_TEST_USAGE / IGNORED_WONT_FIX / RESOLVED_AUTO / PENDING_REVIEW / SUPPRESSED_BY_COMMENT）的告警数量
    3. 将统计数量与实际告警列表进行比对
* 预期结果: 各屏蔽类型统计数量正确，与实际数据一致

**4. 5 处查询入口切换到 project_ids 路径后结果正确性验证**:
* 前置条件:代码检查页面存在静态告警数据，project_ids 已回填
* 测试步骤:
    1. 分别调用 getStaticAlarmList / getIssueCount / filter-options / exportStaticAlarm / batch validate 五个查询入口
    2. 验证各入口在 project_ids 单值 $in 路径下返回结果正确
    3. 与优化前结果比对，验证筛选、统计、导出、校验结果一致
* 预期结果: 5 处查询入口在 project_ids 路径下结果正确，与优化前一致

**5. source 筛选多选验证**:
* 前置条件:代码检查页面存在多个 source 来源的静态告警数据
* 测试步骤:
    1. 进入代码检查页面 source 筛选区域
    2. 选择多个 source 来源进行筛选
    3. 验证筛选结果正确包含所选 source 的告警
    4. 验证与其他筛选项（repoTypes / owners / repos）组合筛选结果正确
* 预期结果: source 多选筛选结果正确，组合筛选正常

**6. 导出 snippet 超长截断验证**:
* 前置条件:存在 contextSnippet 跨度极大的告警（如 start_line 到 end_line 跨 1000 行）
* 测试步骤:
    1. 触发导出包含超长 contextSnippet 告警的静态告警结果
    2. 验证导出文件成功生成，未因 Base64 解码后超过 Excel 单元格 32767 字符限制而失败
    3. 检查服务端日志中记录了含 issueId / 仓库 / 规则 / 行号 / 长度 / 来源的 WARN 日志
    4. 验证导出内容不因截断导致文件损坏
* 预期结果: 超长 snippet 被正确截断，导出成功，WARN 日志记录完整

### 3.2 集成测试专项

**7. 数据回填→查询入口端到端链路验证**:
* 前置条件:服务已部署，Spring 启动完成
* 测试步骤:
    1. 服务启动后确认 ProjectIdsBackfillRunner 自动执行
    2. 验证 static_alarm_issue.project_ids / is_default_visible 与 static_alarm_scan_run.project_ids 已按 MySQL repo_info 反查回填
    3. 回填后调用各查询入口，验证查询均走 project_ids 路径且结果正确
* 预期结果: 启动回填完成，查询链路数据一致，结果正确

**8. 定时对账兜底任务验证**:
* 前置条件:XXL Job admin 已配置 staticAlarmProjectIdsReconcileHandler（cron: 0 0 3 * * ?）
* 测试步骤:
    1. 在 XXL Job admin 确认任务已创建，执行器为 openlibing-codecheck
    2. 构造 MySQL repo_info 与 MongoDB project_ids 不一致的数据
    3. 手动触发对账任务，验证以 MySQL repo_info 为准修正 MongoDB project_ids
    4. 使用参数 {"projectId": N} 验证单项目对账
    5. 验证每日 3 点 cron 定时执行
* 预期结果: 对账任务正确收敛数据漂移，全量与单项目对账均正常

### 3.3 可靠性与韧性测试专项

**9. 回填幂等性与数据一致性验证**:
* 前置条件:服务已完成首次回填
* 测试步骤:
    1. 重启服务，再次触发 ProjectIdsBackfillRunner
    2. 验证重复回填使用 $set 覆盖写入，相同值时 modifiedCount=0，无重复数据
    3. 抽样比对 MySQL repo_info 与 MongoDB static_alarm_issue.project_ids 数据一致性
* 预期结果: 回填幂等，重复执行无副作用，MySQL 与 MongoDB 数据一致

### 3.4 性能测试专项

**10. 大项目深页查询性能验证（消除 errorCode 96）**:
* 前置条件:存在 70+ 仓库的大项目静态告警数据
* 测试步骤:
    1. 在大项目中进入告警列表深页查询（多仓库 + 多状态组合）
    2. 验证查询不再触发 MongoDB 32MB 内存排序限制（errorCode 96）
    3. 记录深页查询响应时间，验证在可接受范围内
* 预期结果: 深页查询无 errorCode 96 报错，响应时间达标

**11. project_ids 索引生效验证**:
* 前置条件:已部署 8 个 project_ids 索引（4 个有 tab + 4 个无 tab）
* 测试步骤:
    1. 确认 8 个索引（idx_project_ids_state_* / idx_project_ids_visible_*）已创建
    2. 确认 4 个旧索引（idx_issue_repo_key_state_*）已删除
    3. 使用 explain 查看有 tab / 无 tab（查看全部）场景查询计划，验证走 project_ids 索引
    4. 验证查询无内存排序（SORT_MERGE 正常）
* 预期结果: 索引治理正确，查询均走 project_ids 索引，无内存排序退化
