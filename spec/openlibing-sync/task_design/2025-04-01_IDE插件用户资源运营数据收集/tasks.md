# 工程能力看板 — 数据接入与测试用例解析插件 — 实现任务

## 进度: 2/2 complete（此项目已通过 git commits 完成实现）

### Task 1: 通用数据接入服务（Data Ingest）

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
- 新增：`openlibing-sync-service/src/main/resources/mapper/DynamicDorisMapper.xml`
- 新增：`openlibing-sync-service/src/main/resources/mapper/ThirdApiDataModelMapper.xml`
- 修改：`openlibing-sync-service/src/main/java/com/openlibing/sync/infrastructure/response/ResponseCodeEnum.java`

- [x] **Step 1: 创建数据模型和 Mapper 层**
  创建 ThirdApiDataModel 实体、Mapper 接口及 XML，映射 `openlibing_ops.tbl_third_api_data_model` 表

- [x] **Step 2: 创建动态 Doris 操作层**
  创建 DynamicDorisMapper、DynamicDorisService 及实现，支持根据表名和列名列表动态构建 INSERT 语句

- [x] **Step 3: 创建数据接入业务层**
  实现 DataIngestService：请求校验 → 查询模型 → 校验必填字段 → 调用动态 Doris 写入

- [x] **Step 4: 创建 Controller 入口**
  实现 `POST /api/data/ingest` 接口，接收 JSON 请求体

- [x] **Step 5: 扩展错误码**
  在 ResponseCodeEnum 中新增 MODEL_NOT_FOUND、TABLE_NOT_FOUND、TABLE_COLUMN_NOT_FOUND、INVALID_FIELD

- [x] **Step 6: 问题修复与 codecheck**
  移除 DataIngestController 中冗余的 log 导入，修复 DataIngestServiceImpl 和 ThirdApiDataModelServiceImpl 中的 codecheck 告警

### Task 2: 测试用例元数据解析插件（TestCase Parser）

**文件：**
- 新增：`openlibing-sync-plugins/src/main/java/com/openlibing/sync/model/TestCaseMeasureData.java`
- 新增：`openlibing-sync-plugins/src/main/java/com/openlibing/sync/model/TestCaseMetadata.java`
- 新增：`openlibing-sync-plugins/src/main/java/com/openlibing/sync/model/TestCaseResult.java`
- 新增：`openlibing-sync-plugins/src/main/java/com/openlibing/sync/plugins/TestCaseMetadataParser.java`

- [x] **Step 1: 修正包路径命名**
  将 `opelibing` 统一修正为 `openlibing`，确保包名与项目名称一致

- [x] **Step 2: 创建三个数据模型**
  - TestCaseMeasureData：聚合 metadataList 和 resultList
  - TestCaseMetadata：用例元数据（caseNumber、className、caseFilePath、repoUrl、repoBranch 等）
  - TestCaseResult：用例执行结果（result、time、failureMessage、failureType 等）

- [x] **Step 3: 实现核心解析器 TestCaseMetadataParser**
  - 实现 OBS 对象列举和 XML 拉取
  - 实现双文件分类解析（metadata 前缀 vs result 文件）
  - 实现 DOM 解析 XML，提取结构化字段

- [x] **Step 4: 修复文件路径斜杠分隔索引越界**
  在 extractFileName 方法中处理斜杠分隔符，确保索引不越界

- [x] **Step 5: 新增 level 字段并优化 isFlaky 判断条件**
  - TestCaseResult 新增 level 字段
  - 优化 isFlaky 的判定逻辑（基于多轮结果的一致性判断）

- [x] **Step 6: 新增文件路径、文件名、所属类信息**
  - TestCaseResult 新增 caseFilePath、caseFileName、className 字段
  - TestCaseMetadataParser 在解析时填充这些字段

- [x] **Step 7: 未执行用例加入 resultsList**
  修改解析逻辑，确保 No Execute 状态的用例也计入结果列表

- [x] **Step 8: 新增 type 和 frameType 字段**
  - TestCaseResult 新增 type（用例类型）和 frameType（框架类型，如 pytest/uniautos/kptest）
  - TestCaseMetadataParser 解析时提取对应 XML 属性

- [x] **Step 9: codecheck 修复**
  修复代码静态检查问题，确保通过质量门禁

### Task 3: 分支合并

- [x] **Step 1: 同步 master 变更到 dev_ljp_0310 分支**
- [x] **Step 2: 同步 release_20260331_iter2 变更到 dev_ljp_0310 分支**