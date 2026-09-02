# ISSUE-177 测试设计

## 1. 设计信息

| 字段         | 内容                                                                |
| ------------ | ------------------------------------------------------------------- |
| Issue编号    | ISSUE-177                                                           |
| 模块         | export（新建功能目录）                                              |
| 微服务       | openlibing-cicd（跨 framework/cicd/codecheck 三服务，统一导出能力） |
| 策略版本     | v1.1                                                                |
| 设计日期     | 2026-08-27                                                          |
| 用例编号前缀 | TC-ISSUE177-NNN（归档编号 openlibing-cicd_export_202608_NNN）       |

## 2. 功能点与设计方法

| #    | 功能点                         | 设计方法         | 用例数 | 说明                                    |
| ---- | ------------------------------ | ---------------- | ------ | --------------------------------------- |
| FP1  | codecheck 静态告警导出全链路   | 场景法           | 1      | 触发→创建→SUCCESS→列表→详情→下载 端到端 |
| FP2  | cicd exec 日志导出全链路       | 场景法           | 1      | 同上                                    |
| FP3  | cicd 调度日志导出全链路        | 场景法           | 1      | 同上                                    |
| FP4  | cicd 测试报告导出全链路        | 场景法           | 1      | 同上                                    |
| FP5  | framework /export/list         | 等价类 + 反向    | 2      | 正向列表结构与 creator 归属；无认证被拒 |
| FP6  | framework /export/detail       | 等价类 + 边界值  | 2      | 字段完整性；不存在 id 容错              |
| FP7  | framework /export/download-url | 场景法 + 边界值  | 2      | 签名 URL 可下载；非法 id 容错           |
| FP8  | 导出状态流转                   | 状态迁移         | 1      | INITIALIZED→UPLOADING→SUCCESS 序列观察  |
| FP9  | objectKey 随机化               | 场景法           | 1      | 两次导出 objectKey 不同                 |
| FP10 | 业务接口异常参数容错           | 等价类（无效类） | 2      | cicd/codecheck 导出接口非法参数         |
| FP11 | 构建子任务导出（社区用户场景） | 手工             | 1      | 测试人员手工验证，不自动化              |

## 3. 接口请求模板

> 认证模型：beta 网关用户态（Cookie `token` + CSRF 头），复用 `CodecheckApiClient`。
> 全部接口基址 `https://beta.openlibing.com`（TEST_ENV=test）。

### 3.1 codecheck 静态告警导出（链路 A 触发点）

- **URL**: `POST /gateway/openlibing-codecheck/static-alarm/v1/list/export?userId={userId}`
- **请求体**（测试人员 2026-08-27 提供样例）：

```json
{
  "projectId": "3",
  "pageNo": 1,
  "pageSize": 10,
  "tab": "PENDING",
  "isIncludeSnippet": false
}
```

- **断言**: HTTP 200；业务 code 成功；导出任务创建（后续经 list/detail 观察状态与记录）

### 3.2 cicd exec 日志导出（链路 B-1 触发点）

- **URL**: `POST /gateway/openlibing-cicd/project/pipeline/exec-log/export`
- **请求体**（真实测试数据）：

```json
{
  "projectId": 3,
  "pipelineId": "26d070774c6844a0bc8b36804895ee7c",
  "pipelineRunId": "e9a45535d2a4420b8017f01155ca182f",
  "jobRunId": "b51630ffca4d4cef90649b30022cc46e",
  "stepRunId": "521839c61cf1478590a1030d7d6d9c1d",
  "taskName": "Build构建",
  "lastDispatchId": "419675f93d7144c08eb61e3d6f0d5c66"
}
```

- **断言**: HTTP 200；业务 code 成功

### 3.3 cicd 调度日志导出（链路 B-2 触发点）

- **URL**: `POST /gateway/openlibing-cicd/project/pipeline/sched-log/export`
- **请求体**: 同 3.2（同为 projectId=3 流水线数据）

### 3.4 cicd 测试报告导出（链路 B-3 触发点）

- **URL**: `POST /gateway/openlibing-cicd/project/pipeline/test-report/export`
- **请求体**（真实测试数据）：

```json
{
  "pipelineId": "26d070774c6844a0bc8b36804895ee7c",
  "pipelineRunId": "e9a45535d2a4420b8017f01155ca182f",
  "projectId": 3,
  "stepRunId": "",
  "buildNumber": 2979,
  "pipelineName": "test-ldf-ababa",
  "jobName": "",
  "jobRunId": "",
  "exportType": "FULL"
}
```

### 3.5 framework《我的导出》列表

- **URL**: `GET /gateway/openlibing-framework/export/list`
- **响应**: 当前用户全部导出记录（obs_file 列表）
- **断言**: HTTP 200；记录数组结构；关键字段存在（id/type/file_name/message/creator/create_time）；触发的导出记录可在列表中找到

### 3.6 framework 导出详情

- **URL**: `GET /gateway/openlibing-framework/export/detail?id={id}`
- **断言**: HTTP 200；obs_file 完整字段（id/type/file_name/object_key/identifier/creator/message/data/create_time/update_time）；SUCCESS 记录 message == SUCCESS

### 3.7 framework 临时下载签名 URL

- **URL**: `GET /gateway/openlibing-framework/export/download-url?id={id}`
- **断言**: HTTP 200；返回 OBS 签名 URL（响应结构执行阶段探测）；对返回 URL 发起 GET（无认证头，签名自带鉴权）返回 200 且内容非空
- **约束**: 有效期 1 小时，过期行为不纳入自动化（策略 §6）

### 3.8 触发类接口的响应结构

> static-alarm / cicd 三个导出接口的触发响应（同步返回任务信息或仅受理成功）在执行阶段探测确认，用例以「触发成功 + 经 list/detail 轮询验证终态」为准，不依赖触发响应的具体结构（防发散）。

## 4. Fixture 设计

```python
# src/tests/openlibing/openlibing-cicd/export/conftest.py
@pytest.fixture(scope="module")
def gw_client():
    """beta 网关客户端（Cookie token + CSRF，复用 CodecheckApiClient）。"""
    # 校验 TEST_ENV=test；遮蔽根 conftest 浏览器 autouse fixtures
    ...

@pytest.fixture(scope="module")
def export_test_data():
    """真实测试数据（测试人员 2026-08-27 提供）。"""
    return {
        "userId": "bebe1c1a5bc240708d98d909c836a74f",
        "projectId": 3,
        "pipelineId": "26d070774c6844a0bc8b36804895ee7c",
        "pipelineRunId": "e9a45535d2a4420b8017f01155ca182f",
        "jobRunId": "b51630ffca4d4cef90649b30022cc46e",
        "stepRunId": "521839c61cf1478590a1030d7d6d9c1d",
        "taskName": "Build构建",
        "lastDispatchId": "419675f93d7144c08eb61e3d6f0d5c66",
        "buildNumber": 2979,
        "pipelineName": "test-ldf-ababa",
        "exportType": "FULL",
    }
```

轮询策略：`gw_client.retry_until`（业务级轮询，间隔 3s，上限 20 次 / 60s，执行阶段按实际导出时长标定）；终态断言 SUCCESS。

## 5. 脚本规划

| 脚本                                  | 用例           | 说明                    |
| ------------------------------------- | -------------- | ----------------------- |
| test_export_codecheck_alarm_001.py    | TC-001         | 链路 A 全链路           |
| test_export_cicd_execlog_001.py       | TC-002         | 链路 B-1 全链路         |
| test_export_cicd_schedlog_001.py      | TC-003         | 链路 B-2 全链路         |
| test_export_cicd_testreport_001.py    | TC-004         | 链路 B-3 全链路         |
| test_export_framework_list_001.py     | TC-005, TC-009 | 列表正向 + 无认证反向   |
| test_export_framework_detail_001.py   | TC-006, TC-010 | 详情字段 + 不存在 id    |
| test_export_framework_download_001.py | TC-007, TC-011 | 下载 URL 有效 + 非法 id |
| test_export_status_flow_001.py        | TC-008         | 状态流转观察            |
| test_export_objectkey_random_001.py   | TC-012         | objectKey 随机化        |
| test_export_invalid_params_001.py     | TC-013, TC-014 | 异常参数容错            |

## 6. 断言规则汇总

1. 全部接口断言 HTTP 状态码 + 业务 code（双校验）
2. 全链路用例断言终态 SUCCESS + 列表可查 + 详情字段 + 下载内容非空
3. 状态流转：终态必须 SUCCESS；INITIALIZED/UPLOADING 中间态"尽力捕获"（记录观察序列，不强制断言捕获到每个中间态，避免 flaky）
4. 容错用例断言：业务错误码（非 5xx 崩溃）
5. 认证反向用例断言：无 Cookie 访问被拒（401/403 或网关拦截响应）

## 7. 安全维度覆盖声明

> 一致性检查（2026-08-27 第一轮）发现横向越权与 CSRF 两维度缺失，已补充用例 TC-016/TC-017；其余维度覆盖或豁免声明如下。

| 安全维度     | 状态      | 覆盖用例 / 豁免原因                                                                    |
| ------------ | --------- | -------------------------------------------------------------------------------------- |
| 认证校验     | ✅ 已覆盖 | TC-009（无 Cookie 访问 /export/list 被拒）                                             |
| 横向越权     | ✅ 已覆盖 | TC-016（B 账号访问 A 账号导出记录 detail/download-url，预期拒绝或空数据）              |
| CSRF 防护    | ✅ 已覆盖 | TC-017（无 CSRF 头 POST 触发导出接口，预期被拒）                                       |
| 纵向越权     | ⚠️ 豁免   | 导出用户侧接口无管理角色分层语义，不存在高低权限角色对                                 |
| 传输安全     | ⚠️ 豁免   | beta 网关全链路强制 HTTPS，属基础设施保障，无代码层可测点                              |
| 敏感信息防护 | ⚠️ 豁免   | 下载走 OBS 临时签名 URL（自带鉴权、1 小时过期），不暴露 AK/SK；签名 URL 本身即授权凭据 |

## 8. 业务规则豁免声明（一致性检查第一轮补充）

| 规则                                                           | 豁免原因                                                                                                               |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| BR3 expectedMessages 任务锁（internal-server/update 条件更新） | internal-server 为服务间 Feign 接口，不暴露网关；并发抢占行为外部不可观测，无法构造稳定断言                            |
| BR4 query limit 默认 1 / 创建时间倒序                          | 同上，internal-server 不暴露网关；倒序行为经 /export/list 轮询"最新记录"间接体现                                       |
| FAILED 状态路径                                                | 需构造 OBS 上传失败等异常，无法稳定复现（策略 §5 P2 已声明"如可构造"）；经异常参数用例（TC-013/014）验证失败不产生记录 |
| 镜像源匹配逻辑优化                                             | 内部实现优化，无对外可观测接口；策略范围确认时未纳入（测试人员确认三项范围）                                           |
| 静态告警导出文件名修改                                         | Issue 未给出命名规格；经 TC-001 detail 校验 file_name 字段存在与非空做部分覆盖                                         |

## 9. 版本历史

| 版本 | 日期       | 修改人      | 修改内容                                                                                                                                                   |
| ---- | ---------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-27 | liudongfang | 初始版本：11 个功能点、7 个接口模板、14 条自动化用例 + 1 条手工用例                                                                                        |
| v1.1 | 2026-08-27 | liudongfang | 一致性检查修复：补充安全维度覆盖声明（§7）与业务规则豁免声明（§8）；新增 TC-016 横向越权、TC-017 CSRF 用例；脚本规划补充 test_export_security_001.py       |
| v1.2 | 2026-08-27 | liudongfang | 执行后定性更新：CSRF 维度声明补充低敏导出接口设计上不强校验的结论（TC-017 预期同步调整为"正常受理"）；实测记录字段为驼峰命名、message 为中文状态"导出成功" |
