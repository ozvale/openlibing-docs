# ISSUE-177 测试策略

## 1. Issue 信息

| 字段           | 内容                                                                |
| -------------- | ------------------------------------------------------------------- |
| Issue编号      | ISSUE-177                                                           |
| Issue标题      | 【openLiBing】新增《我的导出》功能，统一平台导出入口                |
| 关联需求       | https://gitcode.com/openlibing/openlibing-codecheck/issues/177      |
| Issue 所在仓   | openlibing-codecheck（涉及多服务：framework / cicd / codecheck）    |
| 测试归属微服务 | openlibing-cicd（测试人员确认：涉及多服务，在 cicd 模块下开展工作） |
| 负责人         | liudongfang                                                         |
| 创建日期       | 2026-08-27                                                          |
| 状态           | 进行中                                                              |

## 2. 需求摘要

> 提炼自 Issue 177 开发设计文档，禁止超出文档范围。

统一导出能力底座下沉到 **framework** 服务：framework 作为统一导出中心，提供 `obs_file` 数据模型与统一导出接口（用户侧 `list/detail/download-url` + 内部 `internal-server/create|update|query`）。**codecheck**（静态告警导出）与 **cicd**（流水线文件 / exec 日志导出）不再各自维护导出记录表、OBS 上传与清理逻辑，改为通过 Feign 调用 framework 内部接口完成导出任务的创建、状态流转与记录查询。

**范围确认（测试人员 2026-08-27 确认）**：

- 纳入：① framework 统一导出接口验证 ② cicd 导出迁移验证 ③ codecheck 静态告警导出适配验证
- 不纳入：配置与清理策略专项验证（OBS 桶配置继承、CleanObsFileJob 3 天过期清理——清理任务依赖跨天调度，人工等待成本高）
- 不纳入：**构建子任务导出场景**——仅一个社区用户涉及，由测试人员手工验证
- 测试环境：**beta**（`https://beta.openlibing.com`，TEST_ENV=test），三仓均已发布 beta
- 测试分支：test-0827（基于 main 9fac715）

**关联开发分支**：

| 仓        | 分支                                                | beta 发布状态 |
| --------- | --------------------------------------------------- | ------------- |
| framework | feat/obs-file-zjy                                   | 已发布 beta   |
| cicd      | feat/export-file-zjy（已合入 develop_202608_iter2） | 已发布 beta   |
| codecheck | feat/obs-file-zjy（PR #318）                        | 已发布 beta   |

**接口清单（测试人员 2026-08-27 提供，实际网关路径）**：

| #   | 服务      | 接口             | 网关路径                                                                  | 类型     |
| --- | --------- | ---------------- | ------------------------------------------------------------------------- | -------- |
| 1   | framework | 《我的导出》列表 | GET /gateway/openlibing-framework/export/list                             | 用户侧   |
| 2   | framework | 导出详情         | GET /gateway/openlibing-framework/export/detail?id={id}                   | 用户侧   |
| 3   | framework | 临时下载签名 URL | GET /gateway/openlibing-framework/export/download-url?id={id}             | 用户侧   |
| 4   | cicd      | exec 日志导出    | /gateway/openlibing-cicd/project/pipeline/exec-log/export                 | 业务触发 |
| 5   | cicd      | 调度日志导出     | /gateway/openlibing-cicd/project/pipeline/sched-log/export                | 业务触发 |
| 6   | cicd      | 测试报告导出     | /gateway/openlibing-cicd/project/pipeline/test-report/export              | 业务触发 |
| 7   | codecheck | 静态告警导出     | /gateway/openlibing-codecheck/static-alarm/v1/list/export?userId={userId} | 业务触发 |

> 内部接口（/export/internal-server/create|update|query）为服务间 Feign 调用，不直接暴露网关；通过业务链路间接验证其行为。

## 3. 测试目标

1. 验证 framework 统一导出用户侧接口功能正常：《我的导出》列表（`GET /export/list`）、详情（`GET /export/detail`）、临时下载签名 URL（`GET /export/download-url`，有效期 1 小时）
2. 验证 framework 内部接口契约：`create`（创建导出任务）/ `update`（状态与 objectKey 更新，含 expectedMessages 条件更新语义）/ `query`（条件查询，limit 默认 1、创建时间倒序）
3. 验证 cicd 导出迁移：流水线文件导出、exec 日志导出走 framework 统一导出，导出记录可查询、状态流转正确
4. 验证 codecheck 静态告警导出适配：导出走框架统一导出接口，导出记录可查询、可复用
5. 验证导出状态枚举流转：INITIALIZED → UPLOADING → SUCCESS / FAILED
6. （P2）objectKey 随机化：同名文件重复导出不互相覆盖

## 4. 测试范围

| 测试类型    | 是否覆盖 | 说明                                                                                                                          |
| ----------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| UI功能测试  | 否       | 设计文档明确《我的导出》前端页面"后续前端接入"，本期无页面入口；如执行阶段发现前端已就绪，补充手工冒烟（入口可见、列表加载）  |
| API接口测试 | 是       | 核心维度：framework 用户侧 3 接口 + 内部 3 接口契约 + cicd/codecheck 业务侧导出全链路                                         |
| 性能测试    | 否       | 功能迁移验证，非性能敏感变更（测试人员确认）                                                                                  |
| 安全测试    | 部分     | 不单独展开六维度；由 API 反向用例覆盖基础项：无认证访问用户侧接口被拒、内部接口外部直访被服务间鉴权拦截（设计文档第七节要求） |

### 覆盖矩阵

| 功能点                                                | UI  | API    | 性能 | 安全              |
| ----------------------------------------------------- | --- | ------ | ---- | ----------------- |
| framework /export/list 用户导出列表                   | -   | ✓      | -    | ✓（无认证被拒）   |
| framework /export/detail 导出详情                     | -   | ✓      | -    | -                 |
| framework /export/download-url 临时下载签名 URL       | -   | ✓      | -    | -                 |
| framework internal-server/create 契约                 | -   | ✓      | -    | ✓（外部直访被拒） |
| framework internal-server/update 契约（含任务锁语义） | -   | ✓ (P2) | -    | -                 |
| framework internal-server/query 契约                  | -   | ✓      | -    | -                 |
| cicd 流水线文件 / exec 日志导出迁移全链路             | -   | ✓      | -    | -                 |
| codecheck 静态告警导出适配全链路                      | -   | ✓      | -    | -                 |
| 导出状态流转（INITIALIZED→UPLOADING→SUCCESS/FAILED）  | -   | ✓      | -    | -                 |
| objectKey 随机化防覆盖                                | -   | ✓ (P2) | -    | -                 |

## 5. 测试策略

### 5.1 手工测试

- 《我的导出》前端入口冒烟（条件执行：仅当 beta 前端已接入入口时）
- cicd / codecheck 导出文件内容抽查（下载后文件可打开、内容与导出范围一致）

### 5.2 自动化测试

- API 层为主，按两条业务链路组织：
  - **链路 A（codecheck 静态告警导出）**：触发静态告警导出 → framework 任务创建（INITIALIZED）→ 状态流转（UPLOADING→SUCCESS）→ `/export/list` 可查 → `/export/detail` 字段校验 → `/export/download-url` 获取签名 URL 并验证可下载
  - **链路 B（cicd 导出迁移）**：触发流水线文件 / exec 日志导出 → 同上验证记录进 framework、可查询、可下载
- framework 内部接口契约验证：结合业务触发后通过 query 接口校验记录字段；internal-server 接口的外部直访鉴权行为探测
- 自动化用例归档位置：`assets/docs/openlibing/openlibing-cicd/export/`（新建 export 功能目录）
- 自动化脚本位置：`src/tests/openlibing/openlibing-cicd/export/`
- 认证模型：复用 `CodecheckApiClient` 模式（Cookie token + CSRF 头直连 beta 网关，凭证 `.env.local` 的 `CODECHECK_USER_TOKEN`）；内部接口为服务间 Feign 调用，外部访问方式与鉴权行为待探测确认

### 优先级

- **P0（冒烟）**：codecheck 静态告警导出全链路（触发→创建→SUCCESS→列表可查→下载有效）；cicd 导出全链路（流水线文件或 exec 日志任一）；`GET /export/list` 按用户返回导出记录
- **P1（核心）**：`/export/detail` 详情字段；`/export/download-url` 签名 URL 有效性；导出状态流转记录；内部接口 query 契约（条件筛选、limit、倒序）；无认证访问用户接口被拒
- **P2（补充）**：objectKey 随机化（两次导出不覆盖）；expectedMessages 任务锁语义；内部接口外部直访鉴权；异常参数容错；FAILED 状态路径（如可构造）

## 6. 风险与约束

| 风险                                                                          | 影响                              | 缓解措施                                                                                                        |
| ----------------------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| ~~framework `/export/*` 在 beta 网关的完整路径前缀未知~~                      | —                                 | **已解决**：`/gateway/openlibing-framework/export/*`（测试人员 2026-08-27 提供）                                |
| ~~cicd / codecheck 触发导出的业务接口路径未在 Issue 中给出~~                  | —                                 | **已解决**：cicd 3 个导出接口 + codecheck 静态告警导出接口路径已提供（见 §2 接口清单）                          |
| ~~beta 环境发布状态未确认~~                                                   | —                                 | **已解决**：三仓均已发布 beta（测试人员 2026-08-27 确认）                                                       |
| internal-server 为服务间 Feign 接口，不暴露网关，无法外部直测                 | 内部接口契约仅能间接验证          | 经业务链路触发后通过 `/export/list`、`/export/detail` 验证 create/update 行为；query 行为经导出记录查询链路验证 |
| cicd 3 个导出接口（exec-log / sched-log / test-report）的请求方法与参数未提供 | 业务触发用例无法构造请求          | 脚本开发前向测试人员单独询问参数（测试人员已确认可提供）                                                        |
| 导出为异步任务（INITIALIZED→UPLOADING→SUCCESS）                               | 用例需轮询等待，存在时长不稳定    | 参照框架 `retry_until` 模式封装轮询断言，超时阈值待执行阶段标定                                                 |
| 下载签名 URL 有效期 1 小时                                                    | 过期行为验证需等待 1 小时，成本高 | 过期行为不纳入自动化（P2 降级为手工/抽检）；仅验证有效期内可下载                                                |

## 7. 依赖与前置条件

1. beta 网关用户凭证：**已具备**（`CODECHECK_USER_TOKEN`，`.env.local` 不入库，CodecheckApiClient 复用）
2. framework 用户侧接口网关路径：**已确认** `/gateway/openlibing-framework/export/*`（2026-08-27）
3. cicd / codecheck 导出触发接口路径：**已确认**（见 §2 接口清单；请求方法与参数待询问测试人员）
4. beta 环境三仓发布状态：**已确认**，均已发布（2026-08-27）
5. 测试数据：beta 环境需存在可导出的静态告警数据与流水线数据（含 exec 日志 / 调度日志 / 测试报告）；静态告警导出已见真实记录（detail?id=79）
6. 内部接口（internal-server）不暴露网关：经业务链路间接验证

## 8. 版本历史

| 版本 | 日期       | 修改人      | 修改内容                                                                                                                                                                                                    |
| ---- | ---------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-27 | liudongfang | 初始版本：测试范围（framework 接口 + cicd 迁移 + codecheck 适配，不含配置清理专项）、beta 环境、export 功能目录规划                                                                                         |
| v1.1 | 2026-08-27 | liudongfang | 按测试人员反馈修订：三仓 beta 发布确认；补充实际网关接口清单（framework 3 个用户侧 + cicd 3 个导出 + codecheck 1 个导出）；构建子任务导出场景不纳入（测试人员手工验证）；剩余风险收敛为 cicd 接口参数待提供 |
