# 静态告警列表异步导出 — 需求设计文档

> 关联 Issue: openlibing/openlibing-codecheck#148

---

## 1. 方案设计

为静态告警问题列表新增异步导出 Excel 功能。用户在问题列表页点击导出，后端落库一条导出记录后通过 RabbitMQ 发消息触发异步生成，立即返回记录 ID；前端轮询导出状态，完成后通过 OBS 签名 URL 触发浏览器下载。

核心选型：

| 维度 | 选型 | 说明 |
| ---- | ---- | ---- |
| 异步 | RabbitMQ | 导出接口直接生产消息，Consumer 异步消费生成 Excel |
| 大数据量 | 分批流式查写 + 超限切 Sheet | 单 Sheet 上限 SHARD_SIZE 行，超限自动切换新 Sheet 继续写入，不截断丢弃数据 |
| 存储 | MySQL 记录任务状态 + OBS 存文件 | MySQL 做状态机与审计，OBS 做文件持久化 |
| 并发控制 | CAS 抢占 + 同用户拦截 | 防同一任务重复消费；防同一用户短时间内重复提交 |
| 兜底 | xxl-job 定时任务扫描异常记录 | 仅处理 ACK 失败、MQ 丢消息等异常场景，不参与主流程 |
| 清理 | xxl-job 定时任务 | 每天清理过期导出记录及对应 OBS 对象 |

导出条件与列表查询入参一致，**强制走 `projectId` 路径**（前端调用时固定传入 `projectId`），多仓由项目维度天然聚合，`repoType/owner/repo` 作为项目内额外过滤条件。

**关键参数**：

| 参数 | 值 | 说明 |
| ---- | ---- | ---- |
| SHARD_SIZE | 50000 | 单 Sheet 最大行数（Excel 单 Sheet 行数上限 1048576，5 万为兼顾性能与可读性的折中） |
| BATCH_SIZE | 10000 | 分批查询 MongoDB 的每批行数（控制单次查询内存占用与响应时间） |
| MQ concurrency | 5 | Consumer 并发线程数 |

---

## 2. 实现逻辑设计

### 2.1 状态机

```
 导出任务已创建INITIALIZED ──CAS──▶ 导出文件生成中BUILDING ──▶正在上传文件UPLOADING──成功──▶ 导出成功SUCCESS
                            │
                            └──失败──▶ 导出失败FAILED：xxx

终态: 导出成功 / 导出失败：xxx（不再流转）
重入: 仅 导出任务已创建 → 导出文件生成中（CAS 条件更新）
```
注：应使用enum管理状态类型

### 2.2 主流程

#### 提交导出（POST /list/export）

1. 参数校验（`dto` 非空、`userId` 非空、`projectId` 非空）
2. 重复导出检查：对当前查询条件计算 `queryDtoHash = MD5(JSON.toJSONString(dto))`，查询该用户近 **5 分钟**内是否存在 `queryDtoHash` 相同且 `message IN ('导出任务已创建','导出文件生成中')` 的记录，存在则拒绝（防止短时间内重复点击同一导出，不同查询条件不受限制）
3. `applyDefaultStatuses`（与列表查询口径一致：未传 statuses 时填充可展示状态列表，过滤掉内部状态 RESOLVED）
4. 构建导出记录实体：`type = STATIC_ALARM_EXPORT`，`message = 导出任务已创建`，`queryDto = JSON.toJSONString(dto)`，`queryDtoHash = MD5(queryDto)`
5. MySQL INSERT（`useGeneratedKeys` 回填 `id`）
6. RabbitMQ 发送 `PERSISTENT` 消息（内容为 `recordId`）
7. 返回 `recordId`

#### 消费导出事件（MQ Consumer，concurrency = 2）

1. 解析 `recordId` → `int id`
2. CAS 抢占：`UPDATE SET message='导出文件生成中' WHERE id=? AND message='导出任务已创建'`，影响行 ≤ 0 则跳过（已被消费或已完成）
3. `selectById` 查询导出记录，**返回 null 时回写 `导出失败：记录不存在`**，禁止静默跳过
4. 反序列化 `queryDto` → `StaticAlarmQueryDTO`，`applyDefaultStatuses`
5. 通过 `projectId` 反查项目下的代码仓坐标列表（`resolveRepoCoordinates`）
6. **分批流式查询 + 写入 Excel**（详见 §2.3）
7. OBS 上传最终 Excel：`objectKey = yyyy-MM-dd/{recordId}.xlsx`，`Content-Disposition = attachment; filename="编码后的文件名"`
8. MySQL 更新：`message = 导出成功`，`objectKey`，`totalCount`（实际写入行数）
9. `finally`：删除临时 Excel 文件
10. `catch`：按具体异常类型捕获（`DataAccessException`、`IOException`、`JsonProcessingException` 等），回写 `导出失败：xxx`（截断至 500 字符）

### 2.3 分批流式查询与多 Sheet 写入

核心思路：通过 MongoDB `_id` 游标分批拉取数据，每批 `BATCH_SIZE` 行，流式追加写入当前 Sheet；当前 Sheet 行数达到 `SHARD_SIZE` 时切换新 Sheet 继续写入，直到数据全部写完。**不截断丢弃数据**。

```
输入：查询条件 dto，代码仓坐标列表 coordinates
输出：临时 Excel 文件路径，实际总行数 totalCount

1. EasyExcel 写入器打开临时文件，创建 Sheet 0（Sheet 名 "告警(1)"）
2. lastId = null, sheetIndex = 0, sheetRowCount = 0, totalCount = 0
3. 循环：
     a. 查询 MongoDB：
        - lastId == null → findIssuesByRepoCoordinates(coordinates, dto).sort(_id: 1).limit(BATCH_SIZE + 1)
        - lastId != null → 追加条件 {_id: {$gt: lastId}}，其余同上
        - 多查 1 条（limit = BATCH_SIZE + 1）用于判断是否还有下一批
     b. 如果结果为空 → 跳出循环
     c. hasMore = (结果.size > BATCH_SIZE)
     d. batch = hasMore ? 结果前 BATCH_SIZE 条 : 结果全部
     e. lastId = batch 最后一条的 _id
     f. 转换为 StaticAlarmIssueExportVO 列表
     g. 如果 sheetRowCount + batch.size > SHARD_SIZE：
        - 先写入当前 Sheet 能容纳的行（SHARD_SIZE - sheetRowCount）
        - 切换新 Sheet：sheetIndex++，Sheet 名 "告警(sheetIndex+1)"，sheetRowCount = 0
        - 剩余行写入新 Sheet
        - 否则：直接写入当前 Sheet
     h. sheetRowCount += 本次写入行数
     i. totalCount += 本次写入行数
     j. 如果 !hasMore → 跳出循环
4. writer.finish()
5. 返回临时文件路径和 totalCount
```

**`_id` 游标的优势**（相比 `skip + limit`）：
- 避免大偏移量 skip 性能问题（skip 10 万需跳过 10 万条文档，`_id` 游标用范围查询 `{_id: {$gt: lastId}}` 直接定位，毫秒级）
- 每批查询耗时稳定，不受已处理行数影响
- 对告警数据（离线扫描入库，导出期间基本不变）能保证不重复不遗漏

### 2.4 查询导出结果（GET /list/export/result）

1. 校验 `id` 和 `userId` 非空
2. `selectById` 查询记录，不存在返回错误
3. 鉴权：`entity.creator != userId` 返回无权访问
4. 构建 VO：当 `message = 导出成功` 且 `objectKey` 非空时，调用 `obsBucketService.getSignedUrl(objectKey, 7, TimeUnit.DAYS)` 生成签名 URL 填入 `url` 字段
5. 返回 VO

### 2.5 前端轮询

`setInterval` 5 秒：

- `message === 导出成功` → `clearInterval` + `downloadFile(url)`
- `message.startsWith(导出失败)` → `clearInterval` + `ElMessage.error`
- 其他 → 继续轮询

### 2.6 兜底恢复任务（xxl-job）

定时扫描导出记录表中异常状态的记录，处理 ACK 失败、MQ 丢消息等场景：

1. 查询 `message IN ('导出任务已创建','导出文件生成中')` 且 `update_time < now - 2 小时` 的记录
2. 对 `导出任务已创建` 的记录：重发 MQ 消息（给一次重试机会）
3. 对 `导出文件生成中` 的记录（已被 CAS 抢占但未完成）：直接置 `导出失败：任务超时，已自动回收`
4. 同一记录重试超过 2 次仍卡死，直接置失败
5. 该任务仅消费异常记录，日志用于定位服务或消息队列异常

### 2.7 过期清理任务（xxl-job）

每天 01:00 执行：

1. 查询 `create_time < now - 3 天` 的导出记录
2. 对有 `object_key` 的记录，删除 DB 记录

---

## 3. 类设计

### 3.1 新增类

| 类名 | 包路径 | 说明 |
| ---- | ---- | ---- |
| `StaticAlarmExportEntity` | `entity.alarm` | MySQL 实体（表 `static_alarm_export`） |
| `StaticAlarmExportMapper` | `mapper` | MyBatis 映射接口 + XML |
| `StaticAlarmExportProducer` | `service.producer` | RabbitMQ 生产者（PERSISTENT 消息） |
| `StaticAlarmExportConsumer` | `service.consumer` | RabbitMQ 消费者（concurrency = 2，死信兜底 24h TTL） |
| `StaticAlarmExportRecordVO` | `vo.alarm` | 导出结果查询返回 VO（id/taskName/url/message/totalCount/createTime/updateTime） |
| `StaticAlarmIssueExportVO` | `vo.alarm` | Excel 导出专用 VO（`@ExcelProperty` 中文表头 + `@ColumnWidth` 列宽 + 字段过滤） |
| `ObsBucketService` | `service` | OBS 桶操作接口（uploadFile / getSignedUrl） |
| `ObsBucketServiceImpl` | `service.impl` | OBS 实现类 |

### 3.2 修改类

| 类名 | 变更内容 |
| ---- | ---- |
| `StaticAlarmController` | 新增 `POST /list/export`、`GET /list/export/result` 两个接口 |
| `StaticAlarmService` | 接口新增 `exportStaticAlarmList`、`getExportResult`、`processExport` |
| `StaticAlarmServiceImpl` | 实现导出主逻辑：同用户拦截 + CAS 抢占 + 分批流式查询 + 多 Sheet 写入 + OBS 上传 + 临时文件清理 + 具体异常捕获 |
| `StaticAlarmOperation` | 新增 `findIssuesByRepoCoordinatesAfterId(coordinates, dto, lastId, limit)` 支持 `_id` 游标分批查询；已有 `countIssuesByRepoCoordinates` 支持 count |
| `CodeCheckEventRabbitConfig` | 新增 `static_alarm_export_*` exchange / queue / binding（死信交换机 24h TTL） |
| `XxlJobHandler`（codecheck） | 新增兜底恢复任务 + 过期清理任务 |

### 3.3 StaticAlarmIssueExportVO 字段定义

| 字段 | ExcelProperty | ColumnWidth | 说明 |
| ---- | ---- | ---- | ---- |
| `repoType` | 代码托管平台 | 15 | |
| `owner` | 仓库所属空间 | 25 | |
| `repo` | 仓库名 | 30 | |
| `branch` | 分支 | 20 | |
| `pipelineName` | 流水线名称 | 20 | |
| `tool` | 扫描工具 | 15 | |
| `language` | 编程语言 | 12 | |
| `ruleId` | 规则标识 | 30 | |
| `ruleName` | 规则名称 | 40 | |
| `severity` | 问题级别 | 12 | |
| `filePath` | 文件路径 | 60 | |
| `contextSnippet` | 代码片段 | 100 | 将其中的startLine到endLine进行格式处理，用于表示有问题的snippet部分 |
| `startLine` | 起始行号 | 10 | |
| `message` | 问题描述 | 60 | |
| `status` | 问题状态 | 12 | |
| `lastSeenAt` | 最近出现时间 | 22 | `@DateTimeFormat("yyyy-MM-dd HH:mm:ss")` |

---

## 4. 数据模型设计

### 4.1 导出记录表 `static_alarm_export`

| 字段 | 类型 | 约束 | 说明 |
| ---- | ---- | ---- | ---- |
| `id` | INT(32) | PK, AUTO_INCREMENT | 主键 |
| `type` | VARCHAR(50) | NOT NULL | 导出类型，固定 `STATIC_ALARM_EXPORT` |
| `task_name` | VARCHAR(255) | NULL | 任务名称（文件名） |
| `object_key` | VARCHAR(500) | NULL | OBS 对象 key |
| `creator` | VARCHAR(100) | NOT NULL | 创建人 |
| `message` | VARCHAR(500) | NOT NULL | 状态信息：导出任务已创建 / 导出文件生成中 / 导出成功 / 导出失败：xxx |
| `create_time` | DATETIME | NOT NULL | 创建时间 |
| `update_time` | DATETIME | NULL | 更新时间 |
| `total_count` | INT(11) | NULL | 命中问题总数（实际写入行数，非 count 值） |
| `query_dto` | TEXT | NULL | 导出条件 JSON（审计与重放） |
| `query_dto_hash` | VARCHAR(32) | NULL | 导出条件 MD5 摘要（用于重复导出检查） |

### 4.2 索引

| 索引名 | 字段 | 用途 |
| ---- | ---- | ---- |
| `idx_creator_hash` | `creator`, `query_dto_hash` | 重复导出检查（同用户 + 同条件） |
| `idx_create_time` | `create_time` | 清理任务范围删除 |

### 4.3 Liquibase DDL

```xml
<changeSet id="create-static-alarm-export-table" author="ai-assisted">
    <preConditions onFail="MARK_RAN">
        <not><tableExists tableName="static_alarm_export"/></not>
    </preConditions>
    <createTable tableName="static_alarm_export" remarks="静态告警导出记录表">
        <column name="id" type="INT(32)" autoIncrement="true" remarks="主键自增">
            <constraints primaryKey="true" nullable="false"/></column>
        <column name="type" type="VARCHAR(50)" remarks="导出类型">
            <constraints nullable="false"/></column>
        <column name="task_name" type="VARCHAR(255)" remarks="任务名称（文件名）"/>
        <column name="object_key" type="VARCHAR(500)" remarks="OBS 对象 key"/>
        <column name="creator" type="VARCHAR(100)" remarks="创建人">
            <constraints nullable="false"/></column>
        <column name="message" type="VARCHAR(500)" remarks="状态信息">
            <constraints nullable="false"/></column>
        <column name="create_time" type="datetime" remarks="创建时间">
            <constraints nullable="false"/></column>
        <column name="update_time" type="datetime" remarks="更新时间"/>
        <column name="total_count" type="INT(11)" remarks="命中问题总数"/>
        <column name="query_dto" type="TEXT" remarks="导出条件 JSON"/>
        <column name="query_dto_hash" type="VARCHAR(32)" remarks="导出条件 MD5 摘要"/>
    </createTable>
    <createIndex indexName="idx_creator_hash" tableName="static_alarm_export">
        <column name="creator"/><column name="query_dto_hash"/></createIndex>
    <createIndex indexName="idx_create_time" tableName="static_alarm_export">
        <column name="create_time"/></createIndex>
    <rollback><dropTable tableName="static_alarm_export"/></rollback>
</changeSet>
```

### 4.4 OBS 存储

- 桶：复用 `openlibing-export-{beta,gama,prod}`（与 cicd 共用，objectKey 按文件扩展名 `.xlsx` / `.txt` 天然隔离，不会冲突）
- objectKey 格式：`yyyy-MM-dd/{recordId}.xlsx`（日期目录 + recordId 防重复）
- 签名 URL 有效期：7 天（本地计算零成本，自然过期）
- 对象生命周期：由清理任务 3 天删除；建议 OBS 侧同时配 7 天生命周期规则作为兜底

---

## 5. 性能设计

| 场景 | 措施 |
| ---- | ---- |
| MongoDB 分批查询 | 用 `_id` 游标（`{_id: {$gt: lastId}}`）代替 `skip + limit`，避免大偏移量性能问题，每批耗时稳定 |
| Excel 流式写入 | EasyExcel 逐批 `write()`，不要求内存中全量展开；单 Sheet 满 SHARD_SIZE 行自动切换新 Sheet |
| 多 Sheet 支持 | 超过 SHARD_SIZE 行的数据写入新 Sheet（Sheet 名 "告警(1)"、"告警(2)"...），不截断丢弃 |
| 临时文件 | 上传 OBS 后 `finally` 块立即删除 |
| MQ 消费并发 | `concurrency = 2`，避免过多消费者同时查询 MongoDB |
| 重复提交 | 同用户 + 同查询条件（queryDtoHash）近 5 分钟内有未完成记录才拒绝，不同查询条件不受限制 |
| 签名 URL | 本地计算不请求远端，7 天有效；DB 记录 + OBS 对象 3 天清理 |
| 典型耗时 | 5 万行（1 Sheet）：15-30 秒；20 万行（4 Sheet）：1-2 分钟；50 万行（10 Sheet）：3-5 分钟 |

---

## 6. API 接口设计

### 6.1 提交导出

```
POST /static-alarm/v1/list/export?userId={userId}
Content-Type: application/json

Body: StaticAlarmQueryDTO（与列表查询入参一致，projectId 必传）
```

**返回示例（提交成功）**：
```json
{ "code": 0, "data": "42" }
```

**返回示例（重复提交）**：
```json
{ "code": 1, "msg": "已有导出任务正在进行中，请等待完成后再试。" }
```

### 6.2 查询导出结果

```
GET /static-alarm/v1/list/export/result?id={id}&userId={userId}
```

**处理中**：
```json
{
  "code": 0,
  "data": {
    "id": 42,
    "message": "导出文件生成中",
    "url": null,
    "totalCount": null
  }
}
```

**导出成功**：
```json
{
  "code": 0,
  "data": {
    "id": 42,
    "message": "导出成功",
    "url": "https://obs.example.com/...",
    "totalCount": 123456,
    "taskName": "static_alarm_1721577600000.xlsx",
    "createTime": "2026-07-22 10:00:00",
    "updateTime": "2026-07-22 10:01:30"
  }
}
```

**导出失败**：
```json
{
  "code": 0,
  "data": {
    "id": 42,
    "message": "导出失败：OBS 上传失败",
    "url": null
  }
}
```

### 6.3 鉴权

- `getExportResult` 校验 `entity.creator == userId`，不匹配返回无权访问
- 签名 URL 由 OBS 本身保障时效性，不依赖用户鉴权

---

## 7. 安全设计

| 维度 | 措施 |
| ---- | ---- |
| 越权访问 | `getExportResult` 校验 `entity.creator == userId` |
| 查询注入 | MyBatis `#{}` 参数化查询 |
| 重复消费 | CAS `UPDATE WHERE message = '导出任务已创建'` 条件更新，只有一个 Consumer 能抢占成功 |
| 消息持久化 | RabbitMQ `PERSISTENT` 消息 + 死信队列（24h TTL），消息丢失由兜底恢复任务收尾 |
| 凭证安全 | OBS AK/SK 经 `SecurityUtil.decrypt` 解密后使用，不明文落盘 |
| 文件泄露 | OBS 签名 URL 7 天自动过期；不返回 `objectKey` 给前端；DB 记录 + OBS 对象 3 天清理 |
| 内部字段泄露 | 导出 Excel 使用专用 VO（`StaticAlarmIssueExportVO`），仅包含用户关心的列，内部字段（projectId/commitId/snippet 等）不导出 |
| DDL 安全 | Liquibase `preConditions` 判表存在则跳过，幂等执行 |
| 异常处理 | 按具体异常类型捕获（`DataAccessException`、`IOException`、`JsonProcessingException` 等），失败回写 `导出失败：xxx`；禁止捕获 `Exception/RuntimeException/Throwable` 基类 |
