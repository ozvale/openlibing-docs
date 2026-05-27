# 通用数据接入能力 — 实现任务

## 进度: 2/2 complete（已通过 git commits 完成）

### Task 1: 数据接入服务初始实现

**文件：**
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/api/controller/DataIngestController.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/api/dto/thirdapi/DataIngestRequest.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/app/service/thirdapi/DataIngestService.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/app/service/thirdapi/impl/DataIngestServiceImpl.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/mapper/thirdapi/DynamicDorisMapper.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/mapper/thirdapi/ThirdApiDataModelMapper.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/model/thirdapi/ThirdApiDataModel.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/service/thirdapi/DynamicDorisService.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/service/thirdapi/ThirdApiDataModelService.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/service/thirdapi/impl/DynamicDorisServiceImpl.java`
- 新增：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/service/thirdapi/impl/ThirdApiDataModelServiceImpl.java`
- 修改：`openlibing-sync-service/src/main/java/com/openlibing/sync/infrastructure/response/ResponseCodeEnum.java`
- 新增：`openlibing-sync-service/src/main/resources/mapper/DynamicDorisMapper.xml`
- 新增：`openlibing-sync-service/src/main/resources/mapper/ThirdApiDataModelMapper.xml`

- [x] **Step 1: 创建 ThirdApiDataModel 实体和 Mapper**
  创建实体类映射 `openlibing_ops.tbl_third_api_data_model` 表，包含 id/appCode/modelCode/modelName/tableName/schemaVersion/status 等字段；创建 Mapper 接口和 XML 实现按 appCode+modelCode 查询

- [x] **Step 2: 创建 ThirdApiDataModelService**
  创建服务接口和实现，封装模型查询（getByAppCodeAndModelCode）和状态检查（isModelEnabled）

- [x] **Step 3: 创建 DynamicDorisMapper 和 DynamicDorisService**
  创建 Mapper 接口定义动态 INSERT 方法，XML 中编写动态 SQL；创建 Service 接口和实现封装 Mapper 调用

- [x] **Step 4: 创建 DataIngestRequest DTO**
  定义请求数据结构：appCode（应用编码）、modelCode（模型编码）、data（Map<String, Object> 业务数据）

- [x] **Step 5: 创建 DataIngestService 接口和实现**
  核心业务逻辑：
  - validateRequest：空值校验
  - 查模型：根据 appCode+modelCode 查询 ThirdApiDataModel
  - 模型状态检查：已停用返回 MODEL_NOT_FOUND
  - 获取表列信息：通过 DataAssetService 查询列元数据
  - 必填字段校验：基于 columnComment 的"必填"关键字
  - 动态插入：调用 DynamicDorisService.dynamicInsert

- [x] **Step 6: 创建 DataIngestController**
  实现 `POST /api/data/ingest`，日志记录请求参数，调用 DataIngestService

- [x] **Step 7: 扩展 ResponseCodeEnum**
  新增 4 个错误码：MODEL_NOT_FOUND(40001)、TABLE_NOT_FOUND(40002)、TABLE_COLUMN_NOT_FOUND(40003)、INVALID_FIELD(40004)

- [x] **Step 8: 问题修复 — 删除 Controller 冗余导入**
  commit `64af99c`：移除 DataIngestController.java 中 2 行冗余的 log 依赖导入

- [x] **Step 9: codecheck 修复**
  commit `ffc7a1f`：
  - DataIngestServiceImpl：修复日志参数格式（+6/-1）
  - ThirdApiDataModelServiceImpl：修复日志参数格式（+5/-1）
  - ResponseCodeEnum：删除 2 行未使用的 import（-2）

### Task 2: 分支同步


- [x] **Step 1: 同步 master 代码到 dev_ljp_0310 分支**
  合入 master 分支的 README.md 更新（+152/-1）