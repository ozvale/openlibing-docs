# 代码问题屏蔽「全部处理」设计文档

---

# 1、方案设计

## 1.1 背景与目标

代码问题详情页（门禁、版本级检查）有五个 Tab：全部问题、我的申请、待我审批、审批历史、撤销历史。五个 Tab 走同一套分页查询，靠 Body 字段区分数据。

现有提交、审批、转审、撤销接口要调用方传入 `detailsId`，只能处理请求里点名的那几条。

本期目标：在**现有写接口**上增加「全部处理」。调用方不传 `detailsId`，改为传入和当前列表相同的查询条件以及列表条数 `count`；后端校验条数一致后入队异步执行。覆盖：

- 提交全部
- 审批全部
- 转审全部
- 待审撤销全部
- 通过后撤销全部

门禁（`type=inc`）与版本级检查（`type=full`）共用同一套写接口。

## 1.2 范围界定


| 维度   | 说明                                                                                  |
| ---- | ----------------------------------------------------------------------------------- |
| 本期做  | 改造现有 5 个写接口；无 `detailsId` 时按列表条件全部处理；`count` 校验；校验通过后入 RabbitMQ 异步分批执行 |
| 本期不做 | 不新增 `*-all` 路径；不改现有分页查询接口；有 `detailsId` 时的批量语义不变；不做 StaticAlarm、FossScan；撤销历史无写操作   |
| 数据   | 不新增业务表，不改现有文档结构                                                                     |




## 1.3 和现有批量处理的差别

同一条 URL，靠是否传入 `detailsId` 分流：


|                   | 批量处理（现网）                | 全部处理                                              |
| ----------------- | ----------------------- | ------------------------------------------------- |
| `detailsId`       | **有**（非空）。处理范围完全由 ID 决定 | **无**（空或不传）。传了非空 ID 仍走批量                          |
| `query` / `count` | 不需要                     | **必填**。`query` 与当前详情列表 Body 一致；`count` 为当前列表可处理条数 |
| 处理范围              | 调用方点名的 ID，通常是当前页勾选      | 列表查询条件 ∩ 本操作硬条件下的全部记录                             |
| 执行方式              | 同步处理本批 ID               | 校验通过后入队，异步分批处理                                    |
| 条数变化              | 不校验                     | 后端按同样条件 count，与入参 `count` 不一致则 `409`              |


---



# 2、实现逻辑设计



## 2.1 分流

现有 `POST /ci-portal/shield/submit|audit|referral|revoke|auditRevoke`：

1. `detailsId` 非空 → 现网批量逻辑，同步返回。
2. `detailsId` 为空（或不传）且带了 `query` → 全部处理（见 2.2）。
3. `detailsId` 为空且没有 `query` → `50002`（度量类 cmetrics 提交仍走原逻辑）。



## 2.2 全部处理步骤



### 步骤 1：校验入参

- `userId` 与现网完全一致，不改 URL：submit / audit / referral 继续用现有 Query `userId`；revoke 用 Body 里 IdArray 已有的 `userId`；auditRevoke 现网没有操作人参数，全部处理也不加。
- `type` 必填：`inc` 或 `full`。
- 门禁：`uuid`、`taskId` 必填。
- 版本级：`summaryId` 必填，等于详情列表 URL 上的 `id`。
- `query` 必填，字段与当前详情列表 Body 一致。
- `count` 必填，非负整数，表示调用方看到的可处理条数。
- 提交全部 / 转审全部：审核人、原因等业务字段与现网相同。



### 步骤 2：按条件 count，与入参比对

筛选条件复用现有列表方法，不新写一套 Mongo 条件：

- `getDetailCriteria(query)` + `shieldQuery(query, userId)`（门禁再带 `uuid+taskId`，版本级带 `summaryId`）
- 再叠加本操作硬条件（见 2.6）

对上述条件 `count`。与入参 `count` **必须相等**：

- 不相等：列表已变化（筛选结果变了、别人刚处理过等），返回 `409 条数已变化，请刷新后重试`，不入队。
- 相等且为 0：与现网空结果一致（提交 `50001 No problem found`，撤销类 `200`），不入队。



### 步骤 3：占用任务并入队

同一用户、同一任务、同一操作只允许一个进行中的全部处理（Redis SET NX，TTL 2 小时）。占用失败返回 `409 正在处理中，请稍后再试`。

占用成功后把请求（操作类型、userId、作用域、原 Body）发到 RabbitMQ，HTTP **立即**返回 `200 success`。发送失败则释放占用并返回 `500`。

占用期间，同一用户同一任务同一操作的**勾选提交**（带 `detailsId`）同样返回 `409 正在处理中，请稍后再试`。MQ 消费者分批调用现有写方法时走 `ShieldAllRequestContext`，不挡自己。不在屏蔽表按业务字段去重：详情改成审核中后会退出候选，MQ 重投不会再捞到已处理行。

### 步骤 4：消费者分批调用现有方法


| 操作      | 每批调用                             |
| ------- | -------------------------------- |
| 提交全部    | `shieldSubmit`（写入本批 `detailsId`） |
| 审批全部    | `shieldAudit`                    |
| 转审全部    | `shieldReferral`                 |
| 待审撤销全部  | `shieldRevoke`                   |
| 通过后撤销全部 | `shieldPassRevoke`               |


每批 100 条：按当前仍满足「列表条件 ∩ 硬条件」的 `_id` 升序 `limit=100` 再查，不用 skip。处理完的记录会退出硬条件，下一拍自然是下一批。

某批非 200（如 429）：已成功批次保留，停止后续批次，打错误日志。HTTP 已返回 200，调用方以刷新列表为准。

额外约束：

- 提交全部：本批文件路径合并后做一次 Committer 校验；整次共用一条待办（每审核人 1 条 `message_apply`），结束时同一审核人一条汇总通知。
- 转审全部：每批清理旧待办；新待办整次共用一条，结束时一条汇总通知。
- 审批全部：继续现网或签，先抢占成功者生效。
- 门禁：全部批次结束后按 uuid 刷新一次汇总缓存。



### 步骤 5：不在屏蔽表猜重

插入前按 `defectId` / 文件 / 行号 / 甚至详情 `_id` 去查屏蔽表再跳过，都会让「我的申请」比详情行少。详情表一行一个 `_id`，业务字段不是唯一键；屏蔽表插入前又 `setId(null)` 生成新 `_id`，屏蔽表自己的主键也不能拿来对详情行。

防重复靠这三层，不再在 `saveShieldDetail` 里过滤：

1. **count**：入队前按「列表条件 ∩ 硬条件」计数，和前端不一致则 `409`，不入队。你提交后详情变成审核中，别人再点全部处理，count 对不上。
2. **占用**：同一用户同一任务同一操作进行中，再点全部处理或勾选提交 `409`。
3. **硬条件 `defectStatus = 0`**：提交成功后详情已是审核中，MQ 重投、下一拍候选都捞不到这行，不会再插一次。

仍可能双插的窗口：两人几乎同时点全部处理，count 都还是旧值，占用键带了 `userId` 互不挡住。结果是多申请，不是少条。少条比偶发双插更不能接受，所以不在屏蔽表跳过插入。若以后要堵双人同时提交，应把占用改成按任务而不是按用户，不要再加插入过滤。

## 2.3 为什么异步 + 每批 100

三万、四万条不能在一次 HTTP 里跑完。校验只做 count（不拉全量文档），真正处理放到队列里分批执行，与现网 `shieldAllAudit` 批大小一致。

## 2.4 查询条件如何对应五个 Tab

与现网详情列表相同，后端沿用现有切表逻辑：


| Tab  | `query` 关键字段                                   | 查哪张表      |
| ---- | ---------------------------------------------- | --------- |
| 全部问题 | `reviewerStatus`、`isDelay`、`applyId` 为空        | 问题详情表     |
| 我的申请 | `reviewerStatus = "1"`，并带申请人标识（现网 `applicant`） | 屏蔽表       |
| 待我审批 | `reviewerStatus = "1"`，不带申请人标识                 | 屏蔽表       |
| 审批历史 | `reviewerStatus = "2"`                         | 屏蔽表       |
| 撤销历史 | `reviewerStatus = "4"`                         | 屏蔽表（无写操作） |


`flag`、`fileName`、`defectLevel` 等其它筛选字段与列表相同。空字符串视为未筛选。

## 2.5 门禁与版本级


| 点      | 门禁                                        | 版本级检查                                                  |
| ------ | ----------------------------------------- | ------------------------------------------------------ |
| 列表接口   | `POST /ci-portal/v1/event/codecheck/task` | `POST /ci-portal/v1/codecheck/inc/task/result/details` |
| 列表作用域  | URL 参数 `uuid`、`taskId`                    | URL 参数 `id`（即 summaryId）                               |
| `type` | `inc`                                     | `full`                                                 |
| 详情表    | `TASK_INC_RESULT_DETAILS`                 | `TASK_RESULT_DETAILS`                                  |
| 屏蔽表    | `INC_SHIELD_DETAIL`                       | `FULL_SHIELD_DETAIL`                                   |
| 写接口    | 同一套                                       | 同一套                                                    |




## 2.6 操作硬条件


| 操作      | 硬条件（在列表条件之上）         |
| ------- | -------------------- |
| 提交全部    | `defectStatus = 0`   |
| 审批全部    | 待审、审核中、未抢占、当前用户是审核人  |
| 转审全部    | 待审、当前用户是审核人          |
| 待审撤销全部  | 待审、当前用户是申请人          |
| 通过后撤销全部 | `reviewerStatus = 2` |


`count` 校验用的就是「列表条件 ∩ 硬条件」的条数，调用方应传这个数（不是未叠加硬条件的列表总数）。

---



# 4、数据模型设计



## 4.1 请求体

全部处理 = **现有写接口字段** + `query` **+** `count`，且 **不传 / 传空** `detailsId`。批量处理仍只传 `detailsId`。


| 接口                    | 全部处理必增                                             |
| --------------------- | -------------------------------------------------- |
| `/shield/submit`      | `query`、`count`；版本级 `summaryId`；门禁 `uuid`、`taskId` |
| `/shield/audit`       | 同上                                                 |
| `/shield/referral`    | 同上                                                 |
| `/shield/revoke`      | 同上；Query 新增 `userId`                               |
| `/shield/auditRevoke` | 同上；Query 新增 `userId`                               |


`detailsId`、`query.ids` 不作为全部处理的范围。

## 4.2 响应

与现有写接口相同：`code`、`message`，不新增成功数 / 失败数。


| 场景                    | 返回                   |
| --------------------- | -------------------- |
| 批量（有 `detailsId`）     | 与现网完全一致              |
| 全部处理：count 一致且入队成功    | `200 success`（处理在后台） |
| 全部处理：count 与库不一致      | `409 条数已变化，请刷新后重试`   |
| 没有可处理记录（count 双方都为 0） | 与现网空结果相同，如提交 `50001` |
| 同一任务同一操作已在全部处理（含勾选提交） | `409 正在处理中，请稍后再试`    |
| 入队失败                  | `500`                |


---



# 5、性能设计


| 项       | 方案                                 |
| ------- | ---------------------------------- |
| 同步阶段    | 只 count，不加载全量文档、不预取全量 ID           |
| 异步阶段    | RabbitMQ；每批 `_id` 升序 + `limit=100` |
| 批大小     | 100                                |
| 上限      | 无。3～4 万条按批处理完                      |
| 通知 / 待办 | 提交、转审对同一审核人一条；待办一条挂全部已成功详情 ID      |
| 缓存      | 门禁同一 uuid 一次任务只刷新一次                |
| 并发      | 同一用户同一任务同一操作：全部处理互斥；占用期间勾选提交也 409  |
| 外部限流    | 429 停止后续批次，已成功保留                   |
| 幂等      | count 校验 + 占用 + 详情改为审核中后退出候选；不在屏蔽表跳过插入 |


---



# 6、API接口设计



## 6.1 接口列表（不新增路径）


| 场景              | 方法   | 路径                                                   |
| --------------- | ---- | ---------------------------------------------------- |
| 门禁问题详情          | POST | `/ci-portal/v1/event/codecheck/task`                 |
| 版本级问题详情         | POST | `/ci-portal/v1/codecheck/inc/task/result/details`    |
| 提交 / 提交全部       | POST | `/ci-portal/shield/submit`                           |
| 审批 / 审批全部       | POST | `/ci-portal/shield/audit`                            |
| 转审 / 转审全部       | POST | `/ci-portal/shield/referral`                         |
| 待审撤销 / 待审撤销全部   | POST | `/ci-portal/shield/revoke`                           |
| 通过后撤销 / 通过后撤销全部 | POST | `/ci-portal/shield/auditRevoke`                      |
| 现有审核全部（旧）       | POST | `/ci-portal/v1/codecheck/inc/task/shield-all-result` |


不新增 `submit-all` 等路径。`shield-all-result` 本期不删。

## 6.2 请求示例

版本级「全部问题」提交全部。不传 `detailsId`，`query` 与列表 Body 一致，`count` 为当前可提交条数。

```text
POST /ci-portal/shield/submit?userId=4e9c9435aa1d4943a0e497c50d495e8b
```

```json
{
  "userId": "4e9c9435aa1d4943a0e497c50d495e8b",
  "reviewerIds": [
    "7e41058df19a400fb329364138436b7c",
    "4e9c9435aa1d4943a0e497c50d495e8b"
  ],
  "shieldType": 0,
  "reason": "1111111",
  "type": "full",
  "repoUrl": "https://gitcode.com/openlibing/openlibing-codecheck.git",
  "notifyType": "",
  "summaryId": "这里填列表 URL 上的 id",
  "count": 128,
  "query": {
    "pageNum": 1,
    "pageSize": 20,
    "defectLevel": "",
    "fileName": "",
    "applicant": "",
    "reviewerStatus": "",
    "isDelay": "",
    "defectStatus": "",
    "flag": "1",
    "projectName": "openLiBing",
    "projectId": "3",
    "repoUrl": "https://gitcode.com/openlibing/openlibing-codecheck.git",
    "repoName": "openlibing-codecheck",
    "branchName": "dev"
  }
}
```

门禁待我审批「审批全部」：同一 `/shield/audit?userId=`，`detailsId` 为空，`query.reviewerStatus` 为 `"1"`，带 `count`、`uuid`、`taskId`。

待审撤销全部：同一 `/shield/revoke?userId=`，`query.reviewerStatus` 为 `"1"`，带 `count`。操作人只认 Query `userId`，与提交/审核相同。

通过后撤销全部：同一 `/shield/auditRevoke?userId=`，`query.reviewerStatus` 为 `"2"`，带 `count`。操作人同样只认 Query `userId`。

## 6.3 响应示例

入队成功：

```json
{
  "code": 200,
  "message": "success"
}
```

列表已变化：

```json
{
  "code": 409,
  "message": "条数已变化，请刷新后重试"
}
```

---



# 7、安全设计

1. 全部处理范围由「`query` 筛选 ∩ 硬条件」决定，不按调用方传入的 ID。
2. 门禁绑定 `uuid + taskId`，版本级绑定 `summaryId`，禁止跨任务处理。
3. 权限与现网一致。
4. `count` 必须与当前库内可处理条数一致，防止按过期列表误处理。
5. 同一用户同一任务同一操作同时只允许一个全部处理。
6. 不在屏蔽表按业务字段去重。提交幂等靠 count、占用、详情状态；双人同时提交若要再收，改占用键而不是插入过滤。
7. 记录操作人、操作类型、作用域、筛选摘要、校验 count。
8. 全量提交、转审对同一审核人只发一条通知，待办只保留一条。
