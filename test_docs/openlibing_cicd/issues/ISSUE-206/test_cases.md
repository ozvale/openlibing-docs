# ISSUE-206 测试用例

> **Issue编号**: ISSUE-206
> **Issue标题**: [需求]:【openlibing】机机接口下线切换apig
> **创建日期**: 2026-08-25
> **用例总数**: 9
> **手工用例**: 1
> **自动化用例**: 8
> **复用旧用例**: 0
> **新设计用例**: 9

### 执行信息

> 由**测试人员**填写。自动化用例的 Action 链接在此**统一填写一个**，无需每条用例重复填写。

| 字段                 | 内容                                                                                                                                                                        |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 自动化执行Action链接 | —（本次为本地直连生产 APIG 域名执行，经测试人员 2026-08-26 确认以本地执行结果为准；原因见 test_strategy.md §7.5：APIG 凭证仅存本地 .env.local 不入库，beta 域名不便于测试） |
| 手工执行人           | liudongfang                                                                                                                                                                 |
| 执行日期             | 2026-08-26                                                                                                                                                                  |

---

## 用例列表

| 用例编号        | 用例标题                            | 所属功能点                     | 用例类型 | 用例来源 | 用例等级 | 脚本位置                                                                            | 状态   |
| --------------- | ----------------------------------- | ------------------------------ | -------- | -------- | -------- | ----------------------------------------------------------------------------------- | ------ |
| TC-ISSUE206-001 | recordPipelineInfo 合法凭证调用通过 | FP1 recordPipelineInfo 新路径  | auto_api | new      | L0       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_record_pipeline_001.py      | active |
| TC-ISSUE206-002 | pipLineDetailInfo 合法凭证查询通过  | FP2 pipLineDetailInfo 新路径   | auto_api | new      | L1       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_pipeline_detail_001.py      | active |
| TC-ISSUE206-003 | code-cooperate-url 合法凭证调用通过 | FP3 code-cooperate-url 新路径  | auto_api | new      | L1       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_code_cooperate_001.py       | active |
| TC-ISSUE206-004 | 无认证访问 APIG 接口被拒            | FP4 APIG App 认证校验          | auto_api | new      | L1       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_auth_no_credential_001.py   | active |
| TC-ISSUE206-005 | 错误 AppCode 认证被拒               | FP4 APIG App 认证校验          | auto_api | new      | L1       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_auth_invalid_appcode_001.py | active |
| TC-ISSUE206-006 | 伪造 AK/SK 签名认证被拒             | FP4 APIG App 认证校验          | auto_api | new      | L1       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_auth_fake_signature_001.py  | active |
| TC-ISSUE206-007 | 旧路径双跑回归验证                  | FP5 旧路径双跑回归             | auto_api | new      | L2       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_legacy_regression_001.py    | active |
| TC-ISSUE206-008 | 异常参数容错校验                    | FP6 异常参数容错               | auto_api | new      | L2       | src/tests/openlibing/openlibing-cicd/pipeline/test_apig_invalid_params_001.py       | active |
| TC-ISSUE206-009 | machine_interface 冗余登记清理验证  | FP7 machine_interface 登记清理 | manual   | new      | L1       | —（手工用例）                                                                       | active |

> **用例来源说明**：
>
> - `reuse`：复用已有用例，引用已有用例编号（在详情中"引用已有用例"字段标注），不重新归档
> - `new`：新设计用例，必须按规则 5.3 归档到模块用例文件与 case_list.md
>
> **模块归档编号对照**：8 条 auto_api 用例已归档至 `pipeline/auto_test_cases.md`（模块级编号 `openlibing-cicd_pipeline_202608_001` ~ `008`，与 TC-ISSUE206-001~008 一一对应）；1 条 manual 用例归档至 `pipeline/manual_test_cases.md`（模块级编号 `openlibing-cicd_pipeline_202608_009`，对应 TC-ISSUE206-009）。

---

## 执行结果记录

> 本节由**测试人员**填写，AI 不得代填。执行结果未填写完整前，AI 不得生成测试报告（见规则 03 第4节）。

| 用例编号        | 用例类型 | 执行结果 | 缺陷issue | 备注                                                                                  |
| --------------- | -------- | -------- | --------- | ------------------------------------------------------------------------------------- |
| TC-ISSUE206-001 | auto_api | pass     | —         | 本地执行 2026-08-26（17 测试项全通过）；真实业务数据 code 200 success                 |
| TC-ISSUE206-002 | auto_api | pass     | —         | 真实数据 code 200；projectId 参数为华为云项目ID（参数语义见 test_strategy.md §7.6-d） |
| TC-ISSUE206-003 | auto_api | pass     | —         | 真实业务数据 code 200 success                                                         |
| TC-ISSUE206-004 | auto_api | pass     | —         | 3 接口无认证均被拒（401）                                                             |
| TC-ISSUE206-005 | auto_api | pass     | —         | 3 接口错误 AppCode 均被拒（401）                                                      |
| TC-ISSUE206-006 | auto_api | pass     | —         | 伪造签名被拒                                                                          |
| TC-ISSUE206-007 | auto_api | pass     | —         | 3 接口旧路径过渡期可用，无回归                                                        |
| TC-ISSUE206-008 | auto_api | pass     | —         | 空body/非法类型均无 500                                                               |
| TC-ISSUE206-009 | manual   | pass     | —         | 测试人员 2026-08-26 人工核验：machine_interface 冗余登记已清理                        |

> **执行结果取值**：pass（通过）/ fail（失败）/ block（阻塞）/ skip（跳过）
> **填写要求**：
>
> - 自动化用例的 Action 链接在头部"执行信息"中统一填写，此处不重复
> - **fail 用例必须创建并填写缺陷issue**（gitcode 缺陷 issue 链接），否则不得生成报告
> - fail/block 用例必须填写 备注 说明原因

---

## 自动化用例详情

### TC-ISSUE206-001: recordPipelineInfo 合法凭证调用通过

- **所属功能点**: FP1 recordPipelineInfo 新路径功能
- **测试设计方法**: 场景法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_record_pipeline_001.py`
- **用例等级**: L0
- **前置条件**: 1. APIG 网关 `https://apig.openlibing.com` 可达；2. APIG App 凭证已配置于 `.env.local`；3. 合法请求参数样例已获取（开发提供或脚本阶段探测确认）
- **测试步骤**:
  1. 构造合法认证请求头（认证方式按探测结果：优先 AppCode 头部认证，备选 AK/SK 签名）
  2. POST `https://apig.openlibing.com/openlibing-cicd/v1/project/recordPipelineInfo`，携带有效请求体
  3. 校验 HTTP 状态码与业务响应码
- **预期结果**: HTTP 200；业务响应码表示成功（具体业务码脚本阶段固化）；不出现 401/403/404/5xx

### TC-ISSUE206-002: pipLineDetailInfo 合法凭证查询通过

- **所属功能点**: FP2 pipLineDetailInfo 新路径功能
- **测试设计方法**: 场景法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_pipeline_detail_001.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE206-001；存在可查询的流水线数据
- **测试步骤**:
  1. 构造合法认证请求头
  2. GET `https://apig.openlibing.com/openlibing-cicd/v1/project/pipLineDetailInfo`，携带合法查询参数
  3. 校验 HTTP 状态码与响应数据结构
- **预期结果**: HTTP 200；返回流水线详情数据结构；不出现 401/403/404/5xx

### TC-ISSUE206-003: code-cooperate-url 合法凭证调用通过

- **所属功能点**: FP3 code-cooperate-url 新路径功能
- **测试设计方法**: 场景法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_code_cooperate_001.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE206-001
- **测试步骤**:
  1. 构造合法认证请求头
  2. POST `https://apig.openlibing.com/openlibing-cicd/v1/cross-region/pr/code-cooperate-url`，携带有效请求体
  3. 校验 HTTP 状态码与业务响应码
- **预期结果**: HTTP 200；业务响应正常；不出现 401/403/404/5xx

### TC-ISSUE206-004: 无认证访问 APIG 接口被拒

- **所属功能点**: FP4 APIG App 认证校验
- **测试设计方法**: 等价类划分（无效等价类：认证缺失）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_auth_no_credential_001.py`
- **用例等级**: L1
- **前置条件**: APIG 网关可达
- **测试步骤**:
  1. 分别对 3 个 APIG 接口发起不携带任何认证头的请求
  2. 校验 HTTP 状态码
- **预期结果**: 3 个接口均被拒绝（401/403），请求不进入业务逻辑

### TC-ISSUE206-005: 错误 AppCode 认证被拒

- **所属功能点**: FP4 APIG App 认证校验
- **测试设计方法**: 等价类划分（无效等价类：凭证错误）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_auth_invalid_appcode_001.py`
- **用例等级**: L1
- **前置条件**: APIG 网关可达；已确认接口采用 AppCode 头部认证（若探测确认仅支持 AK/SK 签名，本用例改为错误 AK 构造签名）
- **测试步骤**:
  1. 携带错误 AppCode（伪造值）分别调用 3 个 APIG 接口
  2. 校验 HTTP 状态码
- **预期结果**: 3 个接口均被拒绝（401/403）

### TC-ISSUE206-006: 伪造 AK/SK 签名认证被拒

- **所属功能点**: FP4 APIG App 认证校验
- **测试设计方法**: 错误推测法（伪造签名）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_auth_fake_signature_001.py`
- **用例等级**: L1
- **前置条件**: APIG 网关可达；已确认接口支持 AK/SK 签名认证（若探测确认仅支持 AppCode 认证，本用例改为格式合法但值随机的签名头）
- **测试步骤**:
  1. 使用合法 AK 但错误 SK（或完全伪造的 AK/SK 对）按签名算法构造请求
  2. 调用 APIG 接口（至少覆盖有流量的 recordPipelineInfo）
  3. 校验 HTTP 状态码
- **预期结果**: 请求被拒绝（401/403），签名校验生效

### TC-ISSUE206-007: 旧路径双跑回归验证

- **所属功能点**: FP5 旧路径双跑回归
- **测试设计方法**: 场景法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_legacy_regression_001.py`
- **用例等级**: L2
- **前置条件**: 1. 双跑过渡期未结束；2. 旧路径调用方式（原认证机制）已确认——当前未知，需开发补充；若无法确认，执行时标记 block
- **测试步骤**:
  1. 通过原路径（`POST /project/recordPipelineInfo`、`GET /project/pipLineDetailInfo`、`POST /cross-region/pr/code-cooperate-url`）发起调用
  2. 校验响应
- **预期结果**: 过渡期内旧路径仍正常响应，不因 APIG 切换而回归

### TC-ISSUE206-008: 异常参数容错校验

- **所属功能点**: FP6 异常参数容错
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_apig_invalid_params_001.py`
- **用例等级**: L2
- **前置条件**: APIG 网关可达；合法认证构造方式已确认
- **测试步骤**:
  1. 携带合法认证但空请求体调用 2 个 POST 接口
  2. 携带合法认证但非法字段类型（必填字段传非法值）调用 POST 接口
  3. 校验响应
- **预期结果**: 业务层参数校验拒绝（4xx 或业务错误码），不出现 500 内部错误

---

## 手工用例详情

### TC-ISSUE206-009: machine_interface 冗余登记清理验证

- **所属功能点**: FP7 machine_interface 登记清理（Issue 206 目标 2）
- **测试设计方法**: 场景法
- **用例类型**: 手工 (manual)
- **用例来源**: new（归档：pipeline/manual_test_cases.md，openlibing-cicd_pipeline_202608_009）
- **引用已有用例**: —
- **脚本位置**: —（手工用例）
- **用例等级**: L1
- **前置条件**: 机机接口管理页可访问（或开发提供 machine_interface 查询方式）
- **测试步骤**:
  1. 打开机机接口管理页（或通过开发指定的查询方式）
  2. 查询本次 3 个接口（recordPipelineInfo / pipLineDetailInfo / code-cooperate-url）的登记记录
  3. 核对登记状态
- **预期结果**:
  - machine_interface 中这 3 个接口的冗余登记已清理（清理口径——删除记录或迁移标记——需与开发确认）
  - 管理页展示与实际登记状态一致

---

## 用例汇总

| 类型        | 数量  | 通过  | 失败  | 阻塞  | 跳过  |
| ----------- | ----- | ----- | ----- | ----- | ----- |
| 手工用例    | 1     | 1     | 0     | 0     | 0     |
| 自动化-UI   | 0     | 0     | 0     | 0     | 0     |
| 自动化-API  | 8     | 8     | 0     | 0     | 0     |
| 自动化-性能 | 0     | 0     | 0     | 0     | 0     |
| 自动化-安全 | 0     | 0     | 0     | 0     | 0     |
| **合计**    | **9** | **9** | **0** | **0** | **0** |

| 用例来源            | 数量 |
| ------------------- | ---- |
| reuse（复用旧用例） | 0    |
| new（新设计用例）   | 9    |

---

## 版本历史

| 版本 | 日期       | 修改人      | 修改内容                                                                                                                                                                                                                           |
| ---- | ---------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-25 | liudongfang | 初始版本：8 条 auto_api 用例（全部 new），归档至 pipeline 模块（openlibing-cicd_pipeline_202608_001~008）                                                                                                                          |
| v1.1 | 2026-08-25 | liudongfang | 一致性检查补充：新增 TC-ISSUE206-009 手工用例（FP7 machine_interface 登记清理，Issue 206 目标 2），归档至 pipeline/manual_test_cases.md（openlibing-cicd_pipeline_202608_009）                                                     |
| v1.2 | 2026-08-26 | liudongfang | 补齐 TC-ISSUE206-009 的用例列表行、执行结果行与手工用例详情章节（v1.1 漏填表行）；回填自动化执行结果（测试人员 2026-08-26 确认：本地直连生产 APIG 执行，17 测试项全部通过，8 条 auto_api 用例均 pass）；TC-ISSUE206-009 待人工执行 |
| v1.3 | 2026-08-26 | liudongfang | TC-ISSUE206-009 人工核验通过回填 pass（machine_interface 冗余登记已清理）；手工执行人 liudongfang；9/9 用例全部通过，具备报告生成条件                                                                                              |
