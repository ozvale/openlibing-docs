# ISSUE-177 测试用例

> 策略版本 v1.1 · 设计版本 v1.0 · 生成日期 2026-08-27
> 用例编号：TC-ISSUE177-NNN（Issue 级） / openlibing-cicd_export_202608_NNN（模块归档级）

## 执行信息

| 字段 | 值 |
|------|-----|
| 自动化执行Action链接 | —（网关 token 由测试人员实时提供且服务端轮换，无法在 gitcode action 稳定执行，经测试人员同意本地 pytest 执行，test-0827 分支，2026-08-27 16:16–16:30） |
| 手工执行人 | liudongfang |
| 执行日期 | 2026-08-27 |

## 执行结果汇总

| 用例编号 | 执行结果 | 备注 |
|---------|---------|------|
| TC-ISSUE177-001 | pass | 全链路通过，objectKey 随机化正常 |
| TC-ISSUE177-002 | pass | 全链路通过 |
| TC-ISSUE177-003 | pass | 全链路通过 |
| TC-ISSUE177-004 | pass | 全链路通过 |
| TC-ISSUE177-005 | pass | 记录字段完整（实测驼峰命名 fileName/createTime） |
| TC-ISSUE177-006 | pass | obs_file 字段完整，message=导出成功（中文状态，已映射 SUCCESS） |
| TC-ISSUE177-007 | pass | 签名 URL 下载 200 且内容非空 |
| TC-ISSUE177-008 | pass | 导出任务 ~1 秒完成，仅观察到终态 SUCCESS，无非法状态 |
| TC-ISSUE177-009 | pass | 无认证访问被拒 |
| TC-ISSUE177-010 | pass | 不存在 id 业务错误，不 5xx |
| TC-ISSUE177-011 | pass | 非法 id 业务错误，不 5xx |
| TC-ISSUE177-012 | pass | 两次导出 objectKey 不同（11146128… / 144e77e5…） |
| TC-ISSUE177-013 | pass | pipelineId 空串/不存在均业务错误，不 5xx |
| TC-ISSUE177-014 | pass | tab 为历史遗留参数无校验，宽松受理（测试人员 2026-08-27 确认非缺陷，预期已调整）；pageSize=-1 不 5xx |
| TC-ISSUE177-015 | pass | 测试人员 2026-08-27 确认：构建子任务导出验证通过（手工验证；验证过程另行发现缺陷 #214，见缺陷记录） |
| TC-ISSUE177-016 | skip | CODECHECK_USER_TOKEN2（B 账号）未配置，横向越权未执行 |
| TC-ISSUE177-017 | pass | 低敏导出接口为适配无登录导出不强校验 CSRF（测试人员 2026-08-27 确认为设计决定，预期已调整） |

### 缺陷记录

| 缺陷 Issue | 发现场景 | 说明 |
|-----------|---------|------|
| [openlibing-cicd #214](https://gitcode.com/openlibing/openlibing-cicd/issues/214) | 测试人员手工验证发现（2026-08-27） | 无登录模式下测试用例导出提示缺少参数，无法导出；预期应导出成功。仅作缺陷登记，不新增用例（测试人员决定） |

## 用例统计

| 类型 | 数量 | 等级分布 |
|------|------|----------|
| auto_api | 16 | L0×5 / L1×5 / L2×6 |
| manual | 1 | L1×1 |
| **合计** | **17** | reuse×0 / new×17 |

> 复用检查（2026-08-27）：openlibing-cicd 已有 15 条用例（pipeline/sbom）无 export 相关；openlibing_ops nightly_dashboard 导出用例为报表导出，与本需求无关。本次全部 new。

## 自动化用例（auto_api）

### L0 冒烟（全链路场景）

| 用例编号 | 模块 | 功能 | 用例标题 | 等级 | 类型 | 来源 | 脚本位置 | is_auto | 前置条件 | 测试步骤 | 预期结果 |
| --------- | ------ | ------ | --------- | ------ | ------ | ------ | ---------- | --------- | --------- | --------- | --------- |
| TC-ISSUE177-001 | export | codecheck_alarm_export | codecheck 静态告警导出全链路（创建→SUCCESS→列表→详情→下载） | L0 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_codecheck_alarm_001.py | True | beta 可达；CODECHECK_USER_TOKEN 有效；userId 已配置；存在 PENDING 静态告警数据 | 1. POST /gateway/openlibing-codecheck/static-alarm/v1/list/export?userId={userId}，携带 projectId=3/tab=PENDING 请求体 2. retry_until 轮询 /export/list，直到出现本次导出记录且 message=SUCCESS 3. GET /export/detail?id={id} 校验字段 4. GET /export/download-url?id={id} 获取签名 URL 并 GET 下载 | 触发受理成功；终态 SUCCESS；detail 字段完整（type/file_name/object_key/creator 等）；下载返回 200 且内容非空 |
| TC-ISSUE177-002 | export | cicd_execlog_export | cicd exec 日志导出全链路 | L0 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_cicd_execlog_001.py | True | 同上；流水线 26d07077... 存在含 Build构建 步骤的运行记录 | 1. POST /gateway/openlibing-cicd/project/pipeline/exec-log/export（真实 jobRunId/stepRunId 数据） 2-4. 同 TC-001 步骤 2-4 | 同 TC-001 |
| TC-ISSUE177-003 | export | cicd_schedlog_export | cicd 调度日志导出全链路 | L0 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_cicd_schedlog_001.py | True | 同 TC-002 | 1. POST /gateway/openlibing-cicd/project/pipeline/sched-log/export 2-4. 同 TC-001 步骤 2-4 | 同 TC-001 |
| TC-ISSUE177-004 | export | cicd_testreport_export | cicd 测试报告导出全链路 | L0 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_cicd_testreport_001.py | True | 同 TC-002；buildNumber=2979 存在测试报告 | 1. POST /gateway/openlibing-cicd/project/pipeline/test-report/export（exportType=FULL） 2-4. 同 TC-001 步骤 2-4 | 同 TC-001 |
| TC-ISSUE177-005 | export | framework_export_list | 《我的导出》列表按用户返回导出记录 | L0 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_framework_list_001.py | True | 至少已产生 1 条导出记录（TC-001~004 或历史记录） | 1. GET /gateway/openlibing-framework/export/list 2. 校验响应结构与记录字段 | HTTP 200；返回记录数组；记录含 id/type/file_name/message/creator/create_time；creator 为当前用户 |

### L1 核心

| 用例编号 | 模块 | 功能 | 用例标题 | 等级 | 类型 | 来源 | 脚本位置 | is_auto | 前置条件 | 测试步骤 | 预期结果 |
| --------- | ------ | ------ | --------- | ------ | ------ | ------ | ---------- | --------- | --------- | --------- | --------- |
| TC-ISSUE177-006 | export | framework_export_detail | 导出详情 obs_file 字段完整性校验 | L1 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_framework_detail_001.py | True | 存在 SUCCESS 导出记录（本用例触发产生或复用已有记录） | 1. GET /export/detail?id={SUCCESS记录id} 2. 逐字段校验 obs_file 模型 | HTTP 200；含 id/type/file_name/object_key/identifier/creator/message/data/create_time/update_time；message=SUCCESS；object_key 非空 |
| TC-ISSUE177-007 | export | framework_export_download | 临时下载签名 URL 有效期内可下载 | L1 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_framework_download_001.py | True | 存在 SUCCESS 导出记录 | 1. GET /export/download-url?id={id} 2. 对返回的签名 URL 发起 GET（无认证头） | HTTP 200；返回 OBS 签名 URL；GET 该 URL 返回 200 且内容非空 |
| TC-ISSUE177-008 | export | export_status_flow | 导出状态流转（INITIALIZED→UPLOADING→SUCCESS） | L1 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_status_flow_001.py | True | beta 可达；导出链路正常 | 1. 触发任一导出（exec-log） 2. 立即以短间隔轮询 /export/list 或 detail 观察状态序列 3. 等待终态 | 终态必须为 SUCCESS；尽力捕获 INITIALIZED/UPLOADING 中间态并记录序列；状态不出现非法值（如 FAILED） |
| TC-ISSUE177-009 | export | framework_export_auth | 无认证访问 /export/list 被拒 | L1 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_framework_list_001.py | True | — | 1. 以 raw_request（无 Cookie/无 CSRF）GET /gateway/openlibing-framework/export/list | 请求被拒（HTTP 401/403 或网关拦截响应）；不返回导出记录数据 |

### L2 补充

| 用例编号 | 模块 | 功能 | 用例标题 | 等级 | 类型 | 来源 | 脚本位置 | is_auto | 前置条件 | 测试步骤 | 预期结果 |
| --------- | ------ | ------ | --------- | ------ | ------ | ------ | ---------- | --------- | --------- | --------- | --------- |
| TC-ISSUE177-010 | export | framework_export_detail | 导出详情不存在 id 容错 | L2 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_framework_detail_001.py | True | — | 1. GET /export/detail?id=999999999 | HTTP 200/4xx；业务错误码或空 data；不出现 5xx 崩溃 |
| TC-ISSUE177-011 | export | framework_export_download | download-url 非法 id 容错 | L2 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_framework_download_001.py | True | — | 1. GET /export/download-url?id=999999999 | 同 TC-010（业务错误，不 5xx） |
| TC-ISSUE177-012 | export | object_key_random | objectKey 随机化防同名覆盖 | L2 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_objectkey_random_001.py | True | 同一导出源（exec-log 同参数） | 1. 连续触发两次相同参数导出 2. 分别轮询至 SUCCESS 3. 查询两条记录的 object_key | 两次均 SUCCESS；两条记录 object_key 不同（同名文件不覆盖） |
| TC-ISSUE177-013 | export | cicd_export_invalid_params | cicd 导出接口异常参数容错 | L2 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_invalid_params_001.py | True | — | 1. POST exec-log/export 携带 pipelineId=""（空串） 2. POST exec-log/export 携带 pipelineId="not-exist-xxx" | 均返回业务错误码（不 5xx 崩溃）；不产生导出记录 |
| TC-ISSUE177-014 | export | codecheck_export_invalid_params | codecheck 导出接口异常参数容错 | L2 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_invalid_params_001.py | True | — | 1. POST static-alarm export 携带 tab="INVALID_TAB" 2. POST static-alarm export 携带 pageSize=-1 | 均不触发 5xx 崩溃；tab 为历史遗留参数无实际意义，宽松受理为预期（测试人员 2026-08-27 确认，非缺陷） |
| TC-ISSUE177-016 | export | export_horizontal_priv | 横向越权：B 账号访问 A 账号导出记录被拒 | L1 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_security_001.py | True | CODECHECK_USER_TOKEN2 已配置（B 账号）；A 账号存在导出记录 | 1. B 账号 GET /export/detail?id={A账号记录id} 2. B 账号 GET /export/download-url?id={A账号记录id} | 请求被拒或返回空数据（B 账号无法查看/下载 A 账号的导出记录）；不返回 A 的记录内容 |
| TC-ISSUE177-017 | export | export_csrf | 低敏导出接口无 CSRF 强校验（设计决定） | L2 | auto_api | new | src/tests/openlibing/openlibing-cicd/export/test_export_security_001.py | True | CODECHECK_USER_TOKEN 有效 | 1. raw_request 构造仅含 Cookie、无 Csrf-Token-Open-Li-Bing 头的 POST 请求访问 exec-log/export | 正常受理（低敏导出接口为适配无登录访问导出不强校验 CSRF，测试人员 2026-08-27 确认为设计决定） |

## 手工用例（manual）

| 用例编号 | 模块 | 功能 | 用例标题 | 等级 | 类型 | 来源 | 脚本位置 | is_auto | 前置条件 | 测试步骤 | 预期结果 |
| --------- | ------ | ------ | --------- | ------ | ------ | ------ | ---------- | --------- | --------- | --------- | --------- |
| TC-ISSUE177-015 | export | build_subtask_export | 构建子任务导出（社区用户场景） | L1 | manual | new | — | False | beta 存在构建子任务流水线；社区用户数据 | 1. 前端触发构建子任务日志导出 2. 在《我的导出》查看记录 3. 下载验证 | 测试人员手工验证（范围声明：仅一个社区用户涉及，不自动化） |

## 脚本位置

- 自动化脚本：`src/tests/openlibing/openlibing-cicd/export/`
- 用例归档：`assets/docs/openlibing/openlibing-cicd/export/auto_test_cases.md`、`manual_test_cases.md`

## 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-27 | liudongfang | 初始版本：14 条 auto_api + 1 条 manual，全部 new |
| v1.1 | 2026-08-27 | liudongfang | 一致性检查修复：补充 TC-016 横向越权（L1）、TC-017 CSRF（L2）两条安全用例（新增脚本 test_export_security_001.py） |
| v1.2 | 2026-08-27 | liudongfang | 执行结果回填（15 pass / 1 skip）；TC-014 预期按测试人员定性调整（tab 历史遗留参数宽松受理为预期）；TC-017 预期按测试人员定性调整（低敏导出接口不强校验 CSRF 为设计决定）；登记手工验证发现缺陷 issue #214 |
