# #1 运营指标管理看板建设 设计文档

## 1. 基础信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-metric/issues/7
* **需求名称**: 运营指标管理看板建设
* **开发责任人**: LJPeng

---

## 2. 需求场景说明

> 社区数字化运营看板指标没有统一的管理位置，无法进行管理，需要建设功能。

**[TODO]**

## 3 需求验收标准

> 指标管理、元数据管理展示。


## 4. 需求设计与分解

> 在metric中建立增删改查接口，在sync中建数据同步任务

### 4.1 核心逻辑方案

> 数据每2小时同步Doris的表名字段到Mysql数据库，
> 指标的增删改查放在metric中
> 元数据的增删改查放在metric中实现

### 4.2 任务清单

| 任务 ID | 任务描述 (Task Description) | 预期产出 (Deliverables) | 预期工作量（人天） |
|-------|-------------------------|---------------------|-----------|
| #1    | 新增数据存储表5张               | 代码SQL               | 1         |
| #2    | 新增保存、读取、删除接口            | 代码                  | 3         |
| #3    | 新增xxl-job定时任务           | 核心逻辑代码              | 2         |

## 5. 需求相关性分析

> **操作说明**：根据上述拆解出的 Task，识别其变更行为。任何一项勾选为“是”：打上对应issue标签，必须执行对应的流程门禁。全部未勾选：该需求自动判定为轻量化特性，打上need_light标签。

### A. 安全相关性分析

> *若涉及以下任一项，打标 `need_security`标签，PR 必须关联特性issue的架构设计文档（含安全设计部分）**如勾选需要给出原因**。



* [X] **边界变更**：新增公网端口、修改防火墙规则、变更网关配置。
* [X] **凭证处理**：涉及密钥（Secret/Key）、Token、证书的存储或分发。
* [X] **权限调整**：修改权限模型、服务账号（SA）权限或鉴权逻辑。
* [X] **供应链**：引入新的第三方二进制文件、SDK 或重大版本依赖升级。
* [X] **隐私风险评估**：涉及用户个人数据（Email、手机号、IP、邮箱 等）的处理。
* [X] **AI使用**：涉及AIGC能力应用，并提供服务。

### B. 架构设计相关性分析

> *若涉及以下任一项，打标 `need_design`标签，PR 必须关联特性issue的架构设计文档。 **如勾选需要给出原因**。

* [X] A环节判定需要完成安全设计
* [X] 改变了现有系统的物理/逻辑拓扑
* [X] 新增或大幅修改对外暴露的 API/CLI 接口
* [X] 引入了新的中间件、数据库或三方核心组件

### C. 系统集成测试相关性分析

> *若涉及以下任一项，打标 `need_itest`标签，PR必须关联特性issue的测试策略和测试报告文档。 **如勾选需要给出原因**。

* [X] 上述环节判定需要执行安全设计或架构设计。
* [X] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [X] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [X] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [X] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑。

### D. 用户体验相关性分析

> *若涉及以下任一项，打标 `need_ux`标签，PR必须关联特性issue的用户体验设计文档。 **如勾选需要给出原因**。

* [X] **交互逻辑变更**：涉及 Web 门户、控制台（Dashboard）或命令行工具（CLI）的交互流程调整。
* [X] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。
* [X] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [X] **无障碍与多语种**：涉及国际化（i18n）支持、辅助功能或不同终端（移动端/桌面端）的适配。

### 5.1 需求相关性分析汇总结果

* [X] need_security (需架构设计（含安全威胁分析和安全设计）)
* [√] need_design (需架构设计)
* [√] need_itest (需执行测试策略设计和全链路集成测试)
* [X] need_ux (需架构设计（含UX设计)）
* [X] need_light (上述均未勾选，走快速合入通道)


## 6. 价值识别与业务评估

> **判定准则**：基础设施接纳需求必须具备明确的 ROI（投资回报比）或合规必要性。

| 维度        | 评估问题                            | 结论/说明                        |
|-----------|---------------------------------|------------------------------|
| **范围判定**  | 该需求是否属于基础设施范围内？                 | 是                            |
| **规划一致性** | 该需求是否是否在年度技术规划中？                | 是                            | 
| **优先级**   | 该需求优先级评估（高/中/低）？                | 高                            | 
| **通用性**   | 该需求是否解决 3 个以上业务方的共性痛点？          | 是                            |
| **必要性**   | 现有组件通过配置变更是否无法实现目标或没有不用开发的替代方案？ | 否                            | 
| **工作量**   | 预计总工作量 6 人天                    | 6人天                          | 
| **价值评估**  | 实现后能减少多少手动操作或提升多少系统稳定性？         | scanoss跳过配置项,避免扫描自身开源代码,减少误报 |

> **状态定义：** **Accept (准入)** | **Reject (驳回)** |  **Pending (待议)**

**建议结论**： Accept

**原因描述:** 提供运营管理的能力

附接口说明及SQL:
一、数据资产表管理服务 (DataAssetTableRegistryController)

**基础路径**: `/manage/dataasset/table`

### 1.1 分页查询表列表

**接口地址**: `GET /manage/dataasset/table/query`

**请求参数**:

| 参数  | 类型  | 必填  | 默认值 | 说明  |
| --- | --- | --- | --- | --- |
| pageNum | Integer | 否   | 1   | 页码  |
| pageSize | Integer | 否   | 10  | 每页大小 |

**响应示例**:

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "records": [
      {
        "tableRegistryId": "uuid-string",
        "physicalTableName": "tbl_metric_list",
        "businessTopic": "用户域",
        "dataLayer": "DWD",
        "tableChineseName": "指标列表表",
        "dataClassification": "普通",
        "dataOwner": "张三",
        "lastUpdatedBy": "张三",
        "lastUpdatedDate": "2026-03-06",
        "status": 1
      }
    ],
    "total": 100,
    "size": 10,
    "current": 1,
    "pages": 10
  }
}
```

**返回字段说明**:

| 字段  | 类型  | 说明  |
| --- | --- | --- |
| tableRegistryId | String | 表注册ID（UUID主键） |
| physicalTableName | String | 物理表名（数据库中实际表名） |
| businessTopic | String | 所属业务主题 |
| dataLayer | String | 数据分层（ODS/DWD/DWS/ADS/CDM） |
| tableChineseName | String | 表中文名/业务名称 |
| dataClassification | String | 数据密级/分类（普通/内部/机密/绝密） |
| dataOwner | String | 数据管家/数据负责人 |
| lastUpdatedBy | String | 最后更新人 |
| lastUpdatedDate | LocalDate | 最后更新日期 |
| status | Integer | 表状态（1-正常，0-停用） |

---

### 1.2 更新表注册信息

**接口地址**: `POST /manage/dataasset/table/update`

**请求参数**:

```json
{
    "tableRegistryId": "uuid-string",
    "businessTopic": "用户域",
    "dataLayer": "DWD",
    "tableChineseName": "指标列表表",
    "dataClassification": "普通",
    "dataOwner": "张三",
    "status": 1
}
```

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| tableRegistryId | String | **是** | 表注册ID（UUID主键） |
| businessTopic | String | 否   | 所属业务主题 |
| dataLayer | String | 否   | 数据分层（ODS/DWD/DWS/ADS/CDM） |
| tableChineseName | String | 否   | 表中文名/业务名称 |
| dataClassification | String | 否   | 数据密级/分类（普通/内部/机密/绝密） |
| dataOwner | String | 否   | 数据管家/数据负责人 |
| status | Integer | 否   | 表状态（1-正常，0-停用） |

**响应示例**:

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": true
}
```

**业务逻辑说明**:

1. 根据 `tableRegistryId` 作为条件更新表注册信息
2. `lastUpdatedDate` 由后端自动设置为当前时间，无需前端传入
3. 只更新传入的非空字段

---

## 二、数据资产字段信息管理服务 (DataAssetColumnInfoController)

**基础路径**: `/manage/dataasset/column`

### 2.1 分页查询字段信息

**接口地址**: `GET /manage/dataasset/column/query`

**请求参数**:

| 参数  | 类型  | 必填  | 默认值 | 说明  |
| --- | --- | --- | --- | --- |
| pageNum | Integer | 否   | 1   | 页码  |
| pageSize | Integer | 否   | 10  | 每页大小 |
| tableName | String | 否   | -   | 表名（精确筛选） |

**响应示例**:

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "records": [
      {
        "columnInfoId": 1,
        "tableName": "t_digital_metric_info",
        "columnName": "metric_code",
        "columnType": "int",
        "columnComment": "主键 - 指标 code",
        "columnChineseName": "指标编码",
        "businessDefinition": "指标的唯一标识编码",
        "columnEnglishName": "metric_code",
        "dataClassification": "普通",
        "privacyLabel": "非隐私",
        "lastUpdatedDate": "2026-03-11 10:30:00"
      }
    ],
    "total": 100,
    "size": 10,
    "current": 1,
    "pages": 10
  }
}
```

**返回字段说明**:

| 字段  | 类型  | 说明  |
| --- | --- | --- |
| columnInfoId | Long | 主键ID |
| tableName | String | 表名  |
| columnName | String | 字段名 |
| columnType | String | 字段类型 |
| columnComment | String | 字段注释 |
| columnChineseName | String | 中文名称 |
| businessDefinition | String | 业务定义 |
| columnEnglishName | String | 英文名称 |
| dataClassification | String | 密级（普通/内部/机密/绝密） |
| privacyLabel | String | 隐私标签 |
| lastUpdatedDate | LocalDateTime | 修改时间 |

---

### 2.2 同步所有已注册表的字段信息

**接口地址**: `POST /manage/dataasset/column/sync`

**功能说明**: 同步所有已注册表（status=1）的字段信息到字段信息表。会查询 `INFORMATION_SCHEMA.COLUMNS` 获取字段名、字段类型、字段注释，并写入 `t_digital_data_asset_column_info` 表。

**请求参数**: 无

**响应示例**:

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": true
}
```

**业务逻辑说明**:

1. 查询 `t_digital_data_asset_table_registry` 表中 `status=1` 的所有表
2. 遍历每个表，从 `INFORMATION_SCHEMA.COLUMNS` 查询字段信息
3. 以 `table_name` + `column_name` 为联合主键，使用 `ON DUPLICATE KEY UPDATE` 策略更新数据
4. `last_updated_date` 自动设置为当前时间

---

### 2.3 同步指定表的字段信息

**接口地址**: `POST /manage/dataasset/column/sync/table`

**请求参数**:

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| tableName | String | **是** | 表名  |

**响应示例**:

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": true
}
```

**业务逻辑说明**:

1. 根据传入的表名，从 `INFORMATION_SCHEMA.COLUMNS` 查询字段信息
2. 将字段信息写入 `t_digital_data_asset_column_info` 表
3. 使用 `ON DUPLICATE KEY UPDATE` 策略，确保数据唯一性

---

### 2.4 编辑字段信息

**接口地址**: `POST /manage/dataasset/column/update`

**请求参数**:

```json
{
    "columnInfoId": 1,
    "tableName": "t_digital_metric_info",
    "columnName": "metric_code",
    "columnType": "int",
    "columnComment": "主键 - 指标 code",
    "columnChineseName": "指标编码",
    "businessDefinition": "指标的唯一标识编码",
    "columnEnglishName": "metric_code",
    "dataClassification": "普通",
    "privacyLabel": "非隐私"
}
```

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| columnInfoId | Long | **是** | 主键ID |
| tableName | String | **是** | 表名  |
| columnName | String | 否   | 字段名 |
| columnType | String | 否   | 字段类型 |
| columnComment | String | 否   | 字段注释 |
| columnChineseName | String | 否   | 中文名称 |
| businessDefinition | String | 否   | 业务定义 |
| columnEnglishName | String | 否   | 英文名称 |
| dataClassification | String | 否   | 密级（普通/内部/机密/绝密） |
| privacyLabel | String | 否   | 隐私标签 |

**响应示例**:

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": true
}
```

**业务逻辑说明**:

1. 根据 `columnInfoId` 和 `tableName` 作为联合条件更新字段信息
2. `lastUpdatedDate` 由后端自动设置为当前时间，无需前端传入
3. 只更新传入的非空字段

---

## 三、指标完整信息服务 (DigitalMetricInfoController)

**基础路径**: `/manage/digital/metric`

### 2.1 分页查询指标信息

**接口地址**: `POST /manage/digital/metric/page`

**请求参数**:

```json
{
  "pageNum": 1,
  "pageSize": 10,
  "metricName": "指标名称",
  "appType": "应用类型",
  "metricType": "指标类型",
  "dimensions": "维度",
  "status": 1,
  "owner": "责任人",
  "lastModifier": "最后修改人"
}
```

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| pageNum | Integer | 否   | 页码，默认1 |
| pageSize | Integer | 否   | 每页大小，默认10 |
| metricName | String | 否   | 指标名称（精确查询） |
| appType | String | 否   | 应用类型（精确查询） |
| metricType | String | 否   | 指标类型（精确查询） |
| dimensions | String | 否   | 维度（精确查询） |
| status | Integer | 否   | 状态（精确查询） |
| owner | String | 否   | 责任人（精确查询） |
| lastModifier | String | 否   | 最后修改人（精确查询） |

**响应示例**:

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "records": [
      {
        "metricCode": 123456,
        "metricName": "指标名称",
        "appType": "应用类型",
        "metricType": "指标类型",
        "resultDataApi": "结果数据API",
        "resultDataApiName": "结果数据API名称",
        "detailDataApi": "明细数据API",
        "detailDataApiName": "明细数据API名称",
        "dimensions": "维度",
        "status": 1,
        "owner": "责任人",
        "lastModifier": "最后修改人",
        "metricStatus": "指标状态",
        "purpose": "设置目的",
        "definition": "指标定义",
        "calculationFormula": "计算公式",
        "availableDimensions": "可用维度",
        "availableMetrics": "可用度量",
        "statisticalCycle": "统计周期",
        "refreshFrequency": "刷新频率",
        "scopeAndDefinition": "统计范围及口径",
        "createTime": "2026-03-06T10:30:00",
        "updateTime": "2026-03-06T10:30:00"
      }
    ],
    "total": 100,
    "size": 10,
    "current": 1,
    "pages": 10
  }
}
```

**返回字段说明**:

| 字段  | 类型  | 说明  |
| --- | --- | --- |
| metricCode | Integer | 主键 - 指标 code |
| metricName | String | 指标名称 |
| appType | String | 应用类型 |
| metricType | String | 指标类型 |
| resultDataApi | String | 结果数据 API |
| resultDataApiName | String | 结果数据 API 名称 |
| detailDataApi | String | 明细数据 API |
| detailDataApiName | String | 明细数据 API 名称 |
| dimensions | String | 维度  |
| status | Integer | 状态（0：未启用，1：启用） |
| owner | String | 指标责任人 |
| lastModifier | String | 最后修改人 |
| metricStatus | String | 指标状态 |
| purpose | String | 设置目的 |
| definition | String | 指标定义 |
| calculationFormula | String | 计算公式 |
| availableDimensions | String | 可用维度 |
| availableMetrics | String | 可用度量 |
| statisticalCycle | String | 统计周期 |
| refreshFrequency | String | 刷新频率 |
| scopeAndDefinition | String | 统计范围及口径 |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |

---

### 2.2 根据 metricCode 查询指标信息

**接口地址**: `GET /manage/digital/metric/{metricCode}`

**路径参数**:

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| metricCode | Integer | **是** | 指标 code |

**响应示例**:

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": {
        "metricCode": 123456,
        "metricName": "指标名称",
        "appType": "应用类型",
        ...
    }
}
```

---

### 2.3 新增或编辑指标信息

**接口地址**: `POST /manage/digital/metric/save`

**请求参数**:

```json
{
  "metricCode": 123456,
  "metricName": "指标名称",
  "appType": "应用类型",
  "metricType": "指标类型",
  "resultDataApi": "结果数据API",
  "resultDataApiName": "结果数据API名称",
  "detailDataApi": "明细数据API",
  "detailDataApiName": "明细数据API名称",
  "dimensions": "维度",
  "status": 1,
  "owner": "责任人",
  "lastModifier": "最后修改人",
  "metricStatus": "指标状态",
  "purpose": "设置目的",
  "definition": "指标定义",
  "calculationFormula": "计算公式",
  "availableDimensions": "可用维度",
  "availableMetrics": "可用度量",
  "statisticalCycle": "统计周期",
  "refreshFrequency": "刷新频率",
  "scopeAndDefinition": "统计范围及口径"
}
```

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| metricCode | Integer | **是** | 主键 - 指标 code |
| metricName | String | 否   | 指标名称 |
| appType | String | 否   | 应用类型 |
| metricType | String | 否   | 指标类型 |
| resultDataApi | String | 否   | 结果数据 API |
| resultDataApiName | String | 否   | 结果数据 API 名称 |
| detailDataApi | String | 否   | 明细数据 API |
| detailDataApiName | String | 否   | 明细数据 API 名称 |
| dimensions | String | 否   | 维度  |
| status | Integer | 否   | 状态  |
| owner | String | 否   | 责任人 |
| lastModifier | String | 否   | 最后修改人 |
| metricStatus | String | 否   | 指标状态 |
| purpose | String | 否   | 设置目的 |
| definition | String | 否   | 指标定义 |
| calculationFormula | String | 否   | 计算公式 |
| availableDimensions | String | 否   | 可用维度 |
| availableMetrics | String | 否   | 可用度量 |
| statisticalCycle | String | 否   | 统计周期 |
| refreshFrequency | String | 否   | 刷新频率 |
| scopeAndDefinition | String | 否   | 统计范围及口径 |

**响应示例**:

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": {
        "metricCode": 123456,
        "metricName": "指标名称",
        ...
    }
}
```

---

## 三、领域信息服务 (DigitalOperationDomainController)

**基础路径**: `/digital/domain`

### 3.1 分页查询领域信息

**接口地址**: `GET /digital/domain/page`

**请求参数**:

| 参数  | 类型  | 必填  | 默认值 | 说明  |
| --- | --- | --- | --- | --- |
| pageNum | Integer | 否   | 1   | 页码  |
| pageSize | Integer | 否   | 10  | 每页大小 |

**响应示例**:

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "records": [
      {
        "domainId": "uuid-string",
        "domainNameEn": "user_domain",
        "domainNameCn": "用户域",
        "domainOwner": "张三",
        "updateTime": "2026-03-06T10:30:00",
        "lastUpdater": "张三",
        "domainStatus": 1,
        "domainDesc": "用户相关领域",
        "createTime": "2026-03-06T10:30:00"
      }
    ],
    "total": 100,
    "size": 10,
    "current": 1,
    "pages": 10
  }
}
```

**返回字段说明**:

| 字段  | 类型  | 说明  |
| --- | --- | --- |
| domainId | String | 主键 - UUID |
| domainNameEn | String | 领域名称（英文） |
| domainNameCn | String | 领域名称（中文） |
| domainOwner | String | 领域责任人 |
| updateTime | LocalDateTime | 更新时间 |
| lastUpdater | String | 最后更新人 |
| domainStatus | Integer | 领域状态（1：启用，0：禁用） |
| domainDesc | String | 领域描述 |
| createTime | LocalDateTime | 创建时间 |

---

### 3.2 根据 domainId 查询领域信息

**接口地址**: `GET /digital/domain/{domainId}`

**路径参数**:

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| domainId | String | **是** | 领域ID（UUID） |

**响应示例**:

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": {
        "domainId": "uuid-string",
        "domainNameEn": "user_domain",
        "domainNameCn": "用户域",
        ...
    }
}
```

---

### 3.3 新增或编辑领域信息

**接口地址**: `POST /digital/domain/save`

**请求参数**:

```json
{
  "domainId": "uuid-string",
  "domainNameEn": "user_domain",
  "domainNameCn": "用户域",
  "domainOwner": "张三",
  "lastUpdater": "张三",
  "domainStatus": 1,
  "domainDesc": "用户相关领域"
}
```

| 参数  | 类型  | 必填  | 说明  |
| --- | --- | --- | --- |
| domainId | String | **是** | 主键 - UUID（应用侧生成） |
| domainNameEn | String | **是** | 领域名称（英文） |
| domainNameCn | String | **是** | 领域名称（中文） |
| domainOwner | String | 否   | 领域责任人 |
| lastUpdater | String | 否   | 最后更新人 |
| domainStatus | Integer | 否   | 领域状态（1：启用，0：禁用） |
| domainDesc | String | 否   | 领域描述 |

**响应示例**:

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": {
        "domainId": "uuid-string",
        "domainNameEn": "user_domain",
        "domainNameCn": "用户域",
        ...
    }
}
```

---

## 四、统一响应格式

### 成功响应

```json
{
    "code": 200,
    "messageCn": "成功",
    "messageEn": "success",
    "data": { ... }
}
```

### 失败响应

```json
{
  "code": 500,
  "messageCn": "系统异常",
  "messageEn": "system error",
  "data": null
}
```

---

## 五、响应码说明

| 响应码 | 中文描述 | 英文描述 |
| --- | --- | --- |
| 200 | 成功  | success |
| 400 | 请求异常 | bad request |
| 40001 | 指标名称不能为空 | metric name cannot be empty |
| 40002 | 指标code已存在 | metric code already exists |
| 401 | 没有登录 | no logged in |
| 403 | 没有权限 | no permission |
| 500 | 系统异常 | system error |

---

## 六、数据库表说明

| 表名  | 说明  |
| --- | --- |
| t_digital_data_asset_table_registry | 数据资产表注册表 |
| t_digital_data_asset_column_info | 数据资产字段信息表 |
| t_digital_metric_info | 指标完整信息表（合并列表+详情） |
| t_digital_operation_domain | 领域信息表 |

---

**文档生成时间**: 2026-03-06

Mysql

```sql
CREATE TABLE `t_digital_metric_info` (
    `metric_code` int NOT NULL AUTO_INCREMENT COMMENT '主键 - 指标 code',
    `metric_name` varchar(255) NOT NULL COMMENT '指标名称',
    `app_type` varchar(50) NULL COMMENT '应用类型',
    `metric_type` varchar(50) NULL COMMENT '指标类型',
    `result_data_api` varchar(1024) NULL COMMENT '结果数据 API',
    `result_data_api_name` varchar(255) NULL COMMENT '结果数据 API 名称',
    `detail_data_api` varchar(1024) NULL COMMENT '明细数据 API',
    `detail_data_api_name` varchar(255) NULL COMMENT '明细数据 API 名称',
    `domain` varchar(1024) NULL COMMENT '领域',
    `dimensions` varchar(1024) NULL COMMENT '维度',
    `status` int NULL DEFAULT 0 COMMENT '状态（0：未启用，1：启用等）',
    `owner` varchar(50) NULL COMMENT '指标责任人',
    `last_modifier` varchar(50) NULL COMMENT '最后修改人',
    `metric_status` varchar(50) NULL COMMENT '指标状态',
    `purpose` varchar(2048) NULL COMMENT '设置目的',
    `definition` varchar(2048) NULL COMMENT '指标定义',
    `calculation_formula` varchar(1024) NULL COMMENT '计算公式',
    `available_dimensions` varchar(1024) NULL COMMENT '可用维度',
    `available_metrics` varchar(255) NULL COMMENT '可用度量',
    `statistical_cycle` varchar(255) NULL COMMENT '统计周期',
    `refresh_frequency` varchar(255) NULL COMMENT '刷新频率',
    `scope_and_definition` text NULL COMMENT '统计范围及口径',
    `create_time` datetime NULL COMMENT '创建时间',
    `update_time` datetime NULL COMMENT '更新时间',
    `is_deleted` int NULL DEFAULT 0 COMMENT '是否删除',
    PRIMARY KEY (`metric_code`)
) ENGINE=InnoDB AUTO_INCREMENT=10001 DEFAULT CHARSET=utf8mb4 COMMENT='指标完整信息表（合并列表+详情）';
```

```sql
CREATE TABLE `t_digital_data_asset_table_registry` (
    `table_registry_id` varchar(255) NOT NULL COMMENT '表注册 ID(应用层生成唯一主键)',
    `physical_table_name` varchar(255) NOT NULL COMMENT '物理表名 (数据库中实际表名)',
    `business_topic` varchar(255) NULL COMMENT '所属业务主题 (如用户域/交易域/商品域)',
    `data_layer` varchar(255) NULL COMMENT '数据分层 (如 ODS/DWD/DWS/ADS/CDM 等)',
    `table_chinese_name` varchar(255) NULL COMMENT '表中文名/业务名称)',
    `data_classification` varchar(50) NULL COMMENT '数据密级/分类 (如普通/内部/机密/绝密)',
    `data_owner` varchar(255) NULL COMMENT '数据管家/数据负责人',
    `last_updated_by` varchar(255) NULL COMMENT '最后更新人',
    `last_updated_date` datetime NULL COMMENT '最后更新日期',
    `status` int NULL DEFAULT 1 COMMENT '激活状态 1为上线 0为下线',
    `is_deleted` int NULL DEFAULT 0 COMMENT '是否删除',
    PRIMARY KEY (`table_registry_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据资产表注册表';
```

```sql
CREATE TABLE `t_digital_data_asset_column_info` (
    `column_info_id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `table_name` varchar(255) NOT NULL COMMENT '表名',
    `column_name` varchar(255) NOT NULL COMMENT '字段名',
    `column_type` varchar(255) DEFAULT NULL COMMENT '字段类型',
    `column_comment` text COMMENT '字段注释',
    `column_chinese_name` varchar(255) DEFAULT '' COMMENT '中文名称',
    `business_definition` varchar(1000) DEFAULT '' COMMENT '业务定义',
    `column_english_name` varchar(255) DEFAULT '' COMMENT '英文名称',
    `data_classification` varchar(50) DEFAULT '' COMMENT '密级',
    `privacy_label` varchar(100) DEFAULT '' COMMENT '隐私标签',
    `last_updated_date` datetime DEFAULT NULL COMMENT '修改时间',
    PRIMARY KEY (`column_info_id`),
    UNIQUE KEY `uk_table_column` (`table_name`, `column_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据资产字段信息表';
```

```sql
CREATE TABLE `t_digital_operation_domain` (
    `domain_id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
    `domain_name_en` varchar(255) NOT NULL COMMENT '领域名称（英文）',
    `domain_name_cn` varchar(255) NOT NULL COMMENT '领域名称（中文）',
    `domain_owner` varchar(50) NULL COMMENT '领域责任人',
    `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（自动更新）',
    `last_updater` varchar(50) NULL COMMENT '最后更新人',
    `domain_status` tinyint NULL DEFAULT 1 COMMENT '领域状态（1：启用，0：禁用）',
    `domain_desc` varchar(1024) NULL COMMENT '领域描述（说明该领域的业务范围）',
    `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='领域信息表';
```

```sql
CREATE TABLE `t_digital_operation_dimension` (
    `dimension_id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
    `dimension_name_en` varchar(255) NOT NULL COMMENT '维度名称（英文）',
    `dimension_name_cn` varchar(255) NOT NULL COMMENT '维度名称（中文）',
    `dimension_owner` varchar(50) NULL COMMENT '维度责任人',
    `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（自动更新）',
    `last_updater` varchar(50) NULL COMMENT '最后更新人',
    `dimension_status` tinyint NULL DEFAULT 1 COMMENT '领域状态（1：启用，0：禁用）',
    `dimension_desc` varchar(1024) NULL COMMENT '维度描述（说明该维度的业务范围）',
    `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`domain_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='维度信息表';
```

