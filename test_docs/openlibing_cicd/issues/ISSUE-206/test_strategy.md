# ISSUE-206 测试策略

## 1. Issue 信息

| 字段       | 内容                                                      |
| ---------- | --------------------------------------------------------- |
| Issue编号  | ISSUE-206                                                 |
| Issue标题  | [需求]:【openlibing】机机接口下线切换apig                 |
| 关联需求   | https://gitcode.com/openlibing/openlibing-cicd/issues/206 |
| 所属微服务 | openlibing-cicd                                           |
| 所属模块   | pipeline（既有模块）                                      |
| 负责人     | liudongfang                                               |
| 创建日期   | 2026-08-25                                                |
| 状态       | 进行中                                                    |

## 2. 需求摘要

> 提炼自 Issue 206 开发设计文档，禁止超出文档范围。

openlibing-cicd 机机接口从原路径迁移至 APIG 网关。本次自动化测试范围为**第 2 类业务接口共 3 个**（APIG App 认证）：调用方改走 APIG，清理 `machine_interface` 冗余登记。

**范围确认（测试人员 2026-08-25 确认）**：

- 第 1 类（无调用/已废弃接口下线与管理页登记删除）**不纳入**本次测试
- **gitee 相关 4 个 webhook 接口不纳入**本次测试（已无用户使用）
- **gitcode 3 个 webhook 接口本次省略**：测试人员已于 2026-08-25 手工完成端到端验证
- 旧路径处于**双跑过渡期仍可用**，不测试下线断言
- 本期仅覆盖 **API 接口测试**维度，安全/UI/性能维度不单独覆盖（原因见 §4）

**接口清单（原路径 → APIG 路径）**：

| #   | 类别  | 原路径                                   | APIG 路径                                                   | 是否纳入 | 说明             |
| --- | ----- | ---------------------------------------- | ----------------------------------------------------------- | -------- | ---------------- |
| 1   | 第2类 | POST /project/recordPipelineInfo         | POST /openlibing-cicd/v1/project/recordPipelineInfo         | ✓        | 已配，**有流量** |
| 2   | 第2类 | GET /project/pipLineDetailInfo           | GET /openlibing-cicd/v1/project/pipLineDetailInfo           | ✓        | 已配，无流量     |
| 3   | 第2类 | POST /cross-region/pr/code-cooperate-url | POST /openlibing-cicd/v1/cross-region/pr/code-cooperate-url | ✓        | 已配，无流量     |

> **实际部署路径说明（2026-08-26 确认）**：Issue 中的 `/apig/v1` 为模板前缀，实际部署时 `apig` 替换为各微服务名——openlibing-cicd 的 APIG 调用路径为 `https://apig.openlibing.com/openlibing-cicd/v1/...`。上表新路径列已按实际部署路径更新。
> | 4 | 第3类 | POST /cross-region/hooks/gitee | POST /apig/webhook/gitee/pipeline/cross-region | ✗ | 无用户使用，不测 |
> | 5 | 第3类 | POST /cross-region/hooks/gitee/pr/comment/jump-openlibing | POST /apig/webhook/gitee/pipeline/cross-region/pr/comment/jump-openlibing | ✗ | 无用户使用，不测 |
> | 6 | 第3类 | POST /cross-region/hooks/gitee/pr/comment/jump-openlibing/detail | POST /apig/webhook/gitee/pipeline/cross-region/pr/comment/jump-openlibing/detail | ✗ | 无用户使用，不测 |
> | 7 | 第3类 | POST /webhookEvent/hooks/gitee/{pipelineId} | POST /apig/webhook/gitee/pipeline/{pipelineId} | ✗ | 无用户使用，不测 |
> | 8 | 第3类 | POST /cross-region/hooks/gitcode | POST /apig/webhook/gitcode/pipeline/cross-region | ✗ | 手工端到端已验证，本次省略 |
> | 9 | 第3类 | POST /cross-region/hooks/gitcode/pr/comment/jump-openlibing/detail | POST /apig/webhook/gitcode/pipeline/cross-region/pr/comment/jump-openlibing/detail | ✗ | 手工端到端已验证，本次省略 |
> | 10 | 第3类 | POST /webhookEvent/hooks/gitcode/{pipelineId} | POST /apig/webhook/gitcode/pipeline/{pipelineId} | ✗ | 手工端到端已验证，本次省略 |

## 3. 测试目标

1. 验证 3 个第 2 类接口的 APIG 新路径功能正常（可调用、响应符合预期）
2. 验证 APIG App 认证生效：无认证/错误凭证被拒，合法凭证通过
3. （P2）双跑过渡期内旧路径不回归

## 4. 测试范围

| 测试类型    | 是否覆盖 | 说明                                                                                                                                                      |
| ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI功能测试  | 否       | 本需求无页面变更；第 1 类管理页登记删除不纳入本次范围（测试人员确认）                                                                                     |
| API接口测试 | 是       | 核心：3 个第 2 类接口 APIG 新路径功能验证 + App 认证正反向校验                                                                                            |
| 性能测试    | 否       | 接口迁移验证，非性能敏感变更（测试人员确认）                                                                                                              |
| 安全测试    | 否       | 安全六维度不单独覆盖（规则04声明）：认证校验→由 API 用例正反向覆盖；CSRF/横向越权/纵向越权/传输安全/敏感信息→机机接口无用户会话上下文且经测试人员确认跳过 |

### 覆盖矩阵

| 功能点                                    | UI  | API    | 性能 | 安全                             |
| ----------------------------------------- | --- | ------ | ---- | -------------------------------- |
| 第2类接口 APIG 新路径功能验证（3 个接口） | -   | ✓      | -    | -                                |
| 第2类 APIG App 认证正反向校验             | -   | ✓      | -    | -（认证维度由 API 反向用例覆盖） |
| 旧路径双跑回归（过渡期）                  | -   | ✓ (P2) | -    | -                                |

## 5. 测试策略

### 5.1 手工测试

- 无新增手工用例。gitcode webhook 端到端链路已由测试人员于 2026-08-25 手工验证完成，本次省略（测试人员确认）。

### 5.2 自动化测试

- API 层：3 个第 2 类接口新路径正反向用例（合法凭证请求通过 / 无认证被拒 / 错误凭证被拒）
- 自动化用例归档位置: `assets/docs/openlibing/openlibing-cicd/pipeline/auto_test_cases.md`
- 自动化脚本位置: `src/tests/openlibing/openlibing-cicd/pipeline/`
- 认证模型与既有会话型 API 用例不同（APIG App 认证），需新增独立请求构造工具与配置项；凭证已写入 `.env.local`（不入库），配置键见 `.env.example` APIG 段

### 优先级

- **P0（冒烟）**：有流量的 `POST /openlibing-cicd/v1/project/recordPipelineInfo` 合法凭证调用通过
- **P1（核心）**：其余 2 个接口正向验证；无认证请求被拒；错误凭证被拒
- **P2（补充）**：旧路径双跑回归；异常参数容错

## 6. 风险与约束

| 风险                                                                          | 影响                              | 缓解措施                                                                                        |
| ----------------------------------------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------- |
| APIG App 认证构造方式未在文档中明确（AppCode 头部认证 / AK-SK 签名认证）      | 无法构造合法认证请求，P0 用例阻塞 | 脚本开发阶段优先探测 AppCode 头部认证（凭证已具备），必要时按 APIG 通用签名方案实现并与开发确认 |
| 各接口合法请求参数样例缺失                                                    | 正向用例无法构造有效 payload      | 向开发获取样例；或在脚本阶段通过响应校验错误信息探测字段结构（探测结果需测试人员确认）          |
| APIG 网关为独立域名（apig.openlibing.com），`recordPipelineInfo` 已有生产流量 | 写入类正向用例可能产生生产数据    | 设计评审时与测试人员确认数据影响；正向写入用例使用最小化测试数据                                |
| 双跑期窗口变化                                                                | 旧路径下线后回归用例失效          | 回归用例标记过渡期专用，下线后置 deprecated                                                     |

## 7. 依赖与前置条件

1. AK/SK/AppCode 凭证：**已具备**，已写入 `.env.local`（2026-08-25，不入库）
2. APIG base URL：**已确认** `https://apig.openlibing.com`（测试人员 2026-08-25 提供）
3. APIG App 认证构造方式：AppCode 头部认证与 AK/SK 签名认证两种候选，脚本开发阶段探测确认（见 §6 风险1）
4. 各接口合法请求参数样例：仍缺失，需开发提供或脚本阶段探测（见 §6 风险2）
5. 测试执行说明（2026-08-26 修订）：beta 环境 APIG 域名为网关自动生成的乱码域名，不便于测试；经测试人员确认，APIG 用例直接对生产 APIG 域名（https://apig.openlibing.com）验证。为此 APIG 用例使用独立 `apig` 标记（不使用 `api` 标记，避免 prod 环境自动跳过逻辑）；APIG 为 App 认证（AK/SK/AppCode），不涉及用户会话与生产数据变更操作
6. **路径阻塞项已解决 + 执行发现（2026-08-26，同日多轮更新）**：原 404 阻塞原因为路径前缀未按服务名替换（见 §5 接口清单说明），网关 API 已发布。执行过程发现与处理结果：
   - **a. recordPipelineInfo → 403 APIG.0304（已解决）**：该接口绑定的 App 与其他 2 个接口不同——开发提供独立凭证（AK/SK/AppCode），已配置为 `record` 凭证组（settings + .env.local），脚本已切换
   - **b. pipLineDetailInfo → 业务码 5010501"不支持的方法调用"（已解决）**：开发确认为网关配置问题并已修改，修复后 GET 请求正常穿透并执行业务逻辑
   - **c. code-cooperate-url → 业务码 5010403"数字格式转换异常"（已解决）**：真实 org/repo 数据复测返回 code 200 success
   - **d. pipLineDetailInfo → code 500"未找到关联的华为云项目信息"（已解决）**：读服务源码（PipelineServiceImpl）确认——该接口 projectId 参数实际要求传**华为云项目ID**（源码以传入值匹配 `HwProjectInfoEntity.hwProjectId` 字段），而非 openlibing 平台项目 ID；recordPipelineInfo 内部则以 `HwProjectInfoEntity.projectId`（openlibing 项目 ID）匹配。projectId="3" 在 recordPipelineInfo 成功（反证项目 3 已对接华为云），在 pipLineDetailInfo 因按 hwProjectId="3" 查不到而拒绝。测试人员提供绑定的华为云项目ID 后复测**返回 code 200 success**，根因闭环。附带发现：同批迁移接口间 projectId 语义不一致（一个要 openlibing 项目ID、一个要华为云项目ID），对调用方切换 APIG 有误导风险，建议向开发提出
   - **正向业务功能验证（2026-08-26 真实数据复测，全部通过）**：3 个接口以真实参数调用均返回 code 200 success；全量复跑 APIG 套件 **17 passed / 0 failed / 0 skipped**（含正向验证 3、认证反向 7、异常参数容错 4、旧路径双跑回归 3）
     另：网关强制校验请求体与 Content-Type 匹配（GET 亦需携带 JSON body，缺 body 报 400 APIG.0602），客户端已适配

## 8. 版本历史

| 版本 | 日期       | 修改人      | 修改内容                                                                                                                                                                                                                              |
| ---- | ---------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-25 | liudongfang | 初始版本                                                                                                                                                                                                                              |
| v1.1 | 2026-08-25 | liudongfang | 按审核意见修订：gitee 相关 4 个接口不纳入（无用户使用）；模块归属调整为 pipeline                                                                                                                                                      |
| v1.2 | 2026-08-25 | liudongfang | 按测试人员反馈修订：gitcode webhook 手工端到端已验证，本次省略，范围缩小为第 2 类 3 个接口；确认 APIG base URL；凭证写入 .env.local                                                                                                   |
| v1.3 | 2026-08-26 | liudongfang | 执行环境决策：beta APIG 域名为乱码自动生成域名，直接验证生产 APIG；APIG 用例改用独立 apig 标记；记录探测发现的路径/发布状态阻塞项（404 APIG.0101）                                                                                    |
| v1.4 | 2026-08-26 | liudongfang | 路径阻塞解决：确认实际部署路径为服务名前缀（/openlibing-cicd/v1/...，Issue 中 /apig 为模板）；首轮执行 12 passed / 5 failed，发现 App 授权缺口、pipLineDetailInfo 方法不一致、code-cooperate-url 参数异常 3 项问题（详见 §7 第 6 条） |
| v1.5 | 2026-08-26 | liudongfang | 3 项发现闭环：a 项新增 record 凭证组（recordPipelineInfo 独立 App）已配置；b 项网关修复验证通过；c 项 prId 类型排除；复跑 13 passed / 1 skipped / 3 failed，剩余 3 fail 均为真实数据依赖（待参数样例）                                |
| v1.6 | 2026-08-26 | liudongfang | 真实数据复测：recordPipelineInfo / code-cooperate-url 均 code 200 success；pipLineDetailInfo 失败根因定位为 projectId 参数语义（要求华为云项目ID，源码按 hwProjectId 匹配），待华为云项目ID 复测；发现接口间 projectId 语义不一致风险 |
| v1.7 | 2026-08-26 | liudongfang | d 项闭环：测试人员提供华为云项目ID，pipLineDetailInfo 复测 code 200 success；全量复跑 APIG 套件 17 passed / 0 failed / 0 skipped（正向 3、认证反向 7、容错 4、旧路径回归 3），API 维度全部通过                                        |
