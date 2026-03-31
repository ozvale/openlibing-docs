# 通用运营数据接入接口设计说明书（V1.0）

## 1. 文档目的

本文档用于指导开发实现“通用运营数据接入接口”。  
文档面向开发人员和 AI 编码工具，要求内容具备明确的边界、数据模型、接口契约、校验规则和实现约束，避免开发过程中出现理解偏差。

## 2.核心概念

### 2.1 appCode

应用唯一标识，用于区分不同调用方，例如：

- `browser_assistant`
- `idea_plugin_x`
- `desktop_tool_a`

### 2.2 modelCode

数据模型编码，用于标识某类业务数据，例如：

- `user_event`
- `error_log`
- `install_record`

`modelCode` 在同一个 `appCode` 下必须唯一。

### 2.3 tableName

平台内部真实物理表名，仅服务端使用，不对外暴露，不允许客户端传入。

### 2.4 schemaVersion

模型结构版本号，用于后续兼容字段新增、停用和模型升级。  
本期可默认从 `1` 开始，先保留字段，不强制在请求中传递。

---

## 3. 系统架构

建议按以下层次实现，且结构必须参照当前项目进行开发

1. Controller 层  
   负责接收请求、基础参数校验、返回统一响应

2. Application/Service 层  
   负责鉴权、元数据加载、字段校验、落库编排、日志记录

3. Domain/Metadata 层  
   负责数据模型、字段规则、权限信息管理

4. Repository / Mapper 层  
   负责元数据查询、动态插入、日志持久化 可适当使用mybatisPlus

5. DB 层  
   包含元数据表、调用日志表、业务数据表 可适当使用mybatisPlus


---

## 4. 元数据与表设计

### 4.1 数据模型主表 `tbl_third_api_data_model`

用于维护模型和真实表的映射关系。

建议字段：

| 字段  | 类型  | 说明  |
| --- | --- | --- |
| id  | bigint | 主键  |
| app_code | varchar(64) | 所属应用 |
| model_code | varchar(64) | 模型编码 |
| model_name | varchar(128) | 模型名称 |
| table_name | varchar(128) | 真实表名 |
| schema_version | int | 结构版本 |
| status | tinyint | 状态：0-停用，1-启用 |
| description | varchar(512) | 描述  |
| created_time | datetime | 创建时间 |
| updated_time | datetime | 更新时间 |

约束建议：

- `uk_app_model(app_code, model_code)`
- `uk_table_name(table_name)`

### 4.2 业务数据表（人工创建）

---

## 5. 接口设计

### 5.1 接口地址

`POST /api/data/ingest`

说明：

- URL 使用统一语义，不直接暴露 `insert`
- 接口语义是“数据接入”，而不是简单“数据库插入”

### 5.2 请求体示例

```json
{
  "appCode": "xxxx",
  "modelCode": "user_event",
  "requestId": "b7d7ec72d2e84b67a5b2a3b660001001",
  "data": {
    "userId": "123",
    "event": "click_button",
    "page": "home",
    "eventTime": "2026-03-19 10:20:00"
  }
}
```

### 5.3 请求字段说明

| 字段  | 类型  | 是否必填 | 说明  |
| --- | --- | --- | --- |
| appCode | string | 是   | 应用编码 |
| modelCode | string | 是   | 模型编码 |
| requestId | string | 否   | 请求唯一标识，建议传入，用于排查和幂等扩展 |
| data | object | 是   | 实际业务数据 |

说明：

- `data` 中只允许出现当前模型已配置的字段
- 本期接口先支持单条写入，批量写入作为后续扩展

### 5.4 响应体

```json
{
  "code": "0",
  "message": "success",
  "requestId": "b7d7ec72d2e84b67a5b2a3b660001001",
  "success": true
}
```

### 5.5 响应字段说明

| 字段  | 类型  | 说明  |
| --- | --- | --- |
| code | string | 返回码，`0` 表示成功 |
| message | string | 响应描述 |
| requestId | string | 请求流水号 |
| success | boolean | 是否成功 |

---

## 6. 接口处理流程

### 6.1 主流程---《非常重要》

1. 接收请求
2. 校验请求体基础参数
3. 校验应用是否存在且状态可用
4. 根据 `app_code + model_code`去 openlibing_ops.tbl_third_api_data_model表查询模型配置-----MySQL库，需要新建一个service单独去做这件事。
5. 校验模型状态是否启用
6. 根据拿到table_name查询openlibing_ops.t_digital_data_asset_column_info表，请复用DataAssetColumnInfoMapper即可--MySQL库
7. 需要校验传入的参数是否在表字段中，在的才能进行写入
8. 生成安全的插入语句并写入目标表---目标表是在Doris库，可以通过@DataResource使用，需要新建一个service以及对应的mapper xml去做这件事
9. 记录接口调用日志（忽略）
10. 返回结果，复用Result类

### 6.2 字段校验规则

- 请求中的字段必须全部存在于字段配置表中
- 配置为必填的字段不能为空
- 字符串字段需校验长度
- 数值字段需校验格式
- 时间字段需校验格式或可解析性

---

## 7. 安全设计

动态 SQL  
核心原则是：动态的是“已验证过的白名单元数据”，不是“客户端原始输入”。

### 7.1 动态表名和字段名必须走白名单

- `tableName` 必须来自平台维护的元数据
- `columnName` 必须来自平台维护的字段配置
- 绝不能直接信任客户端传入的字段名去拼接 SQL

### 7.2参数值必须使用预编译绑定

- SQL 中的字段值必须使用参数绑定
- 例如 MyBatis 中值部分必须使用 `#{}`，不能使用 `${}`

实际实现时请固定编码、字段顺序和空值处理规则。

## 8. 动态 SQL 实现要求

### 8.1 可用实现方式

1. MyBatis 动态 SQL

建议：

- 但必须先在 Java 代码中完成表名和列名白名单过滤

### 8.2 严格约束

以下逻辑必须在进入 Mapper 前完成：

1. `tableName` 已从元数据获取，不能来自客户端
2. `columns` 已按字段配置过滤
3. `values` 与 `columns` 顺序一一对应
4. 所有非法字段在 Service 层直接拦截

### 8.3 风险说明

虽然 MyBatis 中 `${tableName}`、`${col}` 常见于动态表插入，但它们本质仍是字符串拼接。  
因此只有在“表名和字段名均已通过服务端白名单验证”的前提下才允许使用。

开发时禁止出现以下情况：

- 直接使用客户端传入的表名拼接 SQL
- 未校验字段名即直接拼接 `${col}`
- 将字段值拼接成 SQL 字符串

---

## 9. 错误码设计

建议定义统一错误码

---