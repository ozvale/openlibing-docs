# 通用数据接入能力

## 需求背景

OpenLibing 同步服务需要为工程能力看板提供第三方数据接入能力，允许外部应用通过标准 HTTP API 将运营数据写入 Doris 数据库。当前缺少统一的数据写入入口，各业务方需各自对接数据存储层，导致重复开发和数据口径不一致。

## 功能描述

- 提供统一 REST API `POST /api/data/ingest` 作为第三方数据写入入口
- 支持按 appCode + modelCode 动态路由到注册的数据模型
- 通过 DataAsset 元数据管理校验必填字段和数据列白名单
- 支持动态 Doris INSERT，根据表结构自动构建写入 SQL
- 提供数据模型注册查询管理（ThirdApiDataModel），映射 `tbl_third_api_data_model` 表

## 验收标准

- [ ] `POST /api/data/ingest` 接口可正确接收 JSON 请求体并返回处理结果
- [ ] 根据 appCode + modelCode 可正确路由到对应数据模型
- [ ] 必填字段缺失时返回 `INVALID_FIELD` 错误
- [ ] 模型不存在或已禁用时返回 `MODEL_NOT_FOUND` 错误
- [ ] 表或列配置不存在时返回对应错误码
- [ ] 响应码枚举类完成扩展，新增4个错误码

## 影响范围

- `openlibing-sync-service`：新增 thirdapi 包（controller / dto / service / mapper / model），修改 ResponseCodeEnum
- 新增 Doris 动态数据源操作路径（DynamicDorisMapper + DynamicDorisService）
- 新增 `tbl_third_api_data_model` 表的 CRUD 操作