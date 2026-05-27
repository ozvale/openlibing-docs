# 工程能力看板 — 数据接入与测试用例解析插件 — 技术设计

## 方案概述

本设计包含两个独立子系统：通用数据接入服务（Third API Data Ingest）和测试用例元数据解析插件（TestCase Metadata Parser），共同为工程能力看板提供数据采集和加工能力。

## 架构决策

### 数据接入服务
- **统一 API 入口**：通过 `POST /api/data/ingest` 接收 JSON 数据，按 appCode + modelCode 路由到对应数据模型
- **三层架构**：Controller → Service → Mapper，遵循现有 openlibing-sync-service 的分层模式
- **动态 Doris 写入**：使用 DynamicDorisService 根据表名列名动态构建 INSERT 语句，避免硬编码表结构
- **必填字段校验**：通过 DataAssetColumnInfo 的 columnComment 标注"必填"关键字做校验

### 测试用例解析插件
- **OBS 数据源**：从 OBS 对象存储拉取流水线产物中的 XML 报告
- **双文件解析**：区分 metadata 文件（用例元数据）和 result 文件（执行结果），分别解析后合并
- **Flaky 检测**：基于同一用例的多轮执行结果判定，阈值设为 3 次执行
- **增量字段演进**：TestCaseResult 模型逐步加入 level、type、frameType、filePath、className、fileName（通过多次迭代添加）

## 涉及文件

### 数据接入能力

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/controller/DataIngestController.java` | 新增 | 数据接入 REST 入口 |
| `api/dto/thirdapi/DataIngestRequest.java` | 新增 | 接入请求 DTO，含 appCode/modelCode/data |
| `app/service/thirdapi/DataIngestService.java` | 新增 | 数据接入服务接口 |
| `app/service/thirdapi/impl/DataIngestServiceImpl.java` | 新增 | 核心实现：校验 → 查模型 → 校验必填字段 → 动态插入 Doris |
| `domain/mapper/thirdapi/DynamicDorisMapper.java` | 新增 | Doris 动态 SQL Mapper |
| `domain/mapper/thirdapi/ThirdApiDataModelMapper.java` | 新增 | 数据模型 CRUD Mapper |
| `domain/model/thirdapi/ThirdApiDataModel.java` | 新增 | 数据模型实体，映射 tbl_third_api_data_model 表 |
| `domain/service/thirdapi/DynamicDorisService.java` | 新增 | 动态 Doris 操作服务接口 |
| `domain/service/thirdapi/ThirdApiDataModelService.java` | 新增 | 数据模型管理服务接口 |
| `domain/service/thirdapi/impl/DynamicDorisServiceImpl.java` | 新增 | 动态 INSERT 实现 |
| `domain/service/thirdapi/impl/ThirdApiDataModelServiceImpl.java` | 新增 | 模型查询实现 |
| `infrastructure/response/ResponseCodeEnum.java` | 修改 | 新增 MODEL_NOT_FOUND、TABLE_NOT_FOUND、TABLE_COLUMN_NOT_FOUND、INVALID_FIELD |
| `resources/mapper/DynamicDorisMapper.xml` | 新增 | 动态 Doris SQL XML |
| `resources/mapper/ThirdApiDataModelMapper.xml` | 新增 | 模型查询 SQL XML |

### 测试用例解析插件

| 文件 | 操作 | 说明 |
|------|------|------|
| `plugins/TestCaseMetadataParser.java` | 新增 | 核心解析器：OBS 拉取 → XML 解析 → 构建结构化数据 |
| `model/TestCaseMeasureData.java` | 新增 | 度量数据聚合对象 |
| `model/TestCaseMetadata.java` | 新增 | 用例元数据模型 |
| `model/TestCaseResult.java` | 新增 | 用例结果模型（过程迭代增强字段） |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| OBS 依赖导致解析失败 | 异常捕获 + 日志记录，单文件解析失败不影响其他文件 |
| Doris 动态写入 SQL 注入 | 使用白名单列名校验，只允许已注册列名写入 |
| XML 格式多样不兼容 | 增加日志，识别新格式后扩展解析逻辑 |
| 包路径命名错误（opelibing） | commit `05e393b` 统一修正为 openlibing |

## 跨仓影响

无跨仓影响，所有改动集中在 `openlibing-sync` 仓库内部。