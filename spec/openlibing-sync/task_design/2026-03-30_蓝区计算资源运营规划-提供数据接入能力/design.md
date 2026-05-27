# 通用数据接入能力 — 技术设计

## 方案概述

在 `openlibing-sync-service` 中新增 thirdapi 子包，按 Controller → Service → Mapper 标准三层架构实现通用数据接入服务，通过 `ThirdApiDataModel` 元数据驱动动态 Doris 写入。

## 架构决策

- **统一 API 入口**：`POST /api/data/ingest`，接收 `DataIngestRequest`（appCode + modelCode + data），由 Controller 层负责请求日志记录
- **元数据驱动路由**：根据 appCode + modelCode 查询 `tbl_third_api_data_model` 表，获取目标 tableName 和启用状态，实现动态路由
- **必填字段校验**：复用已有 `DataAssetService.queryColumnInfoByTableName` 获取列元数据，通过 columnComment 是否包含"必填"关键字判断是否为必填字段
- **动态 Doris INSERT**：通过 `DynamicDorisMapper` 接收表名 + 列名白名单 + 数据 Map，构建动态 INSERT SQL，避免硬编码表结构
- **列白名单安全机制**：只允许 `DataAssetColumnInfo` 中已注册的列名写入，防止 SQL 注入和数据污染

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/controller/DataIngestController.java` | 新增 | 数据接入 REST 入口，接收请求并打印日志 |
| `api/dto/thirdapi/DataIngestRequest.java` | 新增 | 请求 DTO：appCode + modelCode + Map data |
| `app/service/thirdapi/DataIngestService.java` | 新增 | 数据接入服务接口 |
| `app/service/thirdapi/impl/DataIngestServiceImpl.java` | 新增 | 核心实现：请求校验 → 查模型 → 查列信息 → 校验必填 → 动态插入 |
| `domain/mapper/thirdapi/DynamicDorisMapper.java` | 新增 | Doris 动态 INSERT Mapper 接口 |
| `domain/mapper/thirdapi/ThirdApiDataModelMapper.java` | 新增 | 数据模型 CRUD Mapper 接口 |
| `domain/model/thirdapi/ThirdApiDataModel.java` | 新增 | 模型实体，映射 `openlibing_ops.tbl_third_api_data_model` |
| `domain/service/thirdapi/DynamicDorisService.java` | 新增 | 动态 Doris 服务接口 |
| `domain/service/thirdapi/ThirdApiDataModelService.java` | 新增 | 数据模型服务接口 |
| `domain/service/thirdapi/impl/DynamicDorisServiceImpl.java` | 新增 | 调用 Mapper 执行动态 INSERT |
| `domain/service/thirdapi/impl/ThirdApiDataModelServiceImpl.java` | 新增 | 按 appCode+modelCode 查询模型 |
| `infrastructure/response/ResponseCodeEnum.java` | 修改 | 新增 MODEL_NOT_FOUND(40001)、TABLE_NOT_FOUND(40002)、TABLE_COLUMN_NOT_FOUND(40003)、INVALID_FIELD(40004) |
| `resources/mapper/DynamicDorisMapper.xml` | 新增 | 动态 Doris INSERT SQL |
| `resources/mapper/ThirdApiDataModelMapper.xml` | 新增 | 模型查询 SQL |

## 数据模型

`tbl_third_api_data_model` 表结构关键字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT (PK, AUTO) | 主键 |
| app_code | VARCHAR | 应用编码，路由键 |
| model_code | VARCHAR | 模型编码，路由键 |
| model_name | VARCHAR | 模型名称 |
| table_name | VARCHAR | 写入的真实 Doris 表名 |
| schema_version | INT | 结构版本 |
| status | INT | 0-停用，1-启用 |
| description | VARCHAR | 描述 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| Doris 动态 SQL 注入风险 | 列名白名单校验 + 只允许已注册列写入 |
| 模型/表不存在未处理 | 4 个专用错误码 + 日志记录 + 明确错误返回 |
| 必填字段遗漏写入 | 基于 columnComment 的必填校验 + 前置拦截 |
| 请求参数不完整 | DataIngestServiceImpl.validateRequest 空值校验 |

## 跨仓影响

无跨仓影响，所有改动集中在 `openlibing-sync-service` 模块内部。