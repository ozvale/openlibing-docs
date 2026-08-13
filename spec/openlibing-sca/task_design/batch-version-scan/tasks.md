# 版本扫描批量操作 - 实现任务清单

## 实现步骤

### 1. 新增 Result VO

- [x] 新建 `ManualVersionScanStartResultVO.java`
  - 字段: repoId (Integer), branchId (Integer), scanId (String), success (Boolean), errorMsg (String)
  - 手写全参构造函数（非 Lombok @AllArgsConstructor，遵循项目 SpotBugs 规范）

### 2. Controller 层改造

- [x] 修改 `ManualVersionScanController.startScan()`
  - 入参从 `@RequestBody @Valid ManualVersionScanStartPo` 改为 `@RequestBody @Valid List<ManualVersionScanStartPo>`
  - 返回从 `ResponseEntity` (data=String) 改为 `ResponseEntity` (data=List<ManualVersionScanStartResultVO>)
- [x] 新增 `ManualVersionScanController.deleteByIds()`
  - `POST /version/scan/deleteByIds`
  - 入参 `@RequestBody List<String> ids`
  - 返回删除条数 int

### 3. Service 接口改造

- [x] 修改 `ManualVersionScanService.startScan()` 方法签名
  - 入参: `List<ManualVersionScanStartPo> startPoList`
  - 返回: `List<ManualVersionScanStartResultVO>`
  - Javadoc: "批量触发版本扫描，每条扫描的结果集合（单条失败不影响其他条）"
- [x] 新增 `ManualVersionScanService.deleteByIds()` 方法声明
  - 入参: `List<String> ids`
  - 返回: `int` (实际删除记录数)

### 4. ServiceImpl 核心实现

- [x] 改造 `ManualVersionScanServiceImpl.startScan()`
  - 空/null 列表直接返回空 List
  - 遍历 startPoList，逐条 try-catch
  - ScaException: 设置 success=false + errorMsg（拼接 errorMsg + adviceMsg）
  - Exception: 设置 success=false + errorMsg（取 ex.getMessage()）
  - 成功: 设置 success=true + scanId
  - 每条结果加入 results 列表后返回
- [x] 提取 `startSingleScan(ManualVersionScanStartPo)` 私有方法
  - 复用原 startScan 中的单条扫描逻辑
  - 校验 repoId/branchId 非空
  - 查 tbl_manual_version_scan 确认已添加
  - 查 repo_info 获取仓库信息
  - 调 integrationApiService.startVersionScan()
  - 更新 scanStatus 为 SCANNING
  - 仍以抛异常方式处理错误（由调用方 try-catch 转为 ResultVO）
- [x] 新增 `deleteByIds(List<String> ids)`
  - 空/null 跳过 Mapper 调用，返回 0
  - 调用 mapper.deleteByIds(ids)
  - 日志记录请求数与实际删除数

### 5. Mapper 层

- [x] 在 `TblManualVersionScanMapper.java` 新增方法声明
  - `int deleteByIds(@Param("ids") List<String> ids)`
- [x] 在 `TblManualVersionScanMapper.xml` 新增 SQL
  - `<delete id="deleteByIds">` + MyBatis `<foreach>` 动态 IN 子句

### 6. 单元测试 - Controller

- [x] 改造 `ManualVersionScanControllerTest` 原有用例
  - startScan 入参改为单元素 List
  - mock 返回值改为 List<ManualVersionScanStartResultVO>
  - 断言改为逐条检查 ResultVO 字段
- [x] 新增 startScan 批量测试
  - `startScan_batchWithMultipleItems`: 2 条全部成功
  - `startScan_emptyList`: 空列表返回空结果
  - `startScan_scaException`: 单条 ScaException 返回失败结果
  - `startScan_generalException`: 单条 RuntimeException 返回失败结果
- [x] 新增 deleteByIds 测试
  - `deleteByIds_success`: 3 条 ID 删除 2 条
  - `deleteByIds_emptyList`: 空列表返回 0
  - `deleteByIds_scaException`: ScaException 捕获并返回错误响应
  - `deleteByIds_generalException`: RuntimeException 捕获并返回错误响应

### 7. 单元测试 - ServiceImpl

- [x] 改造 `ManualVersionScanServiceImplTest` 原有用例
  - startScan 入参改为单元素 List，返回值改为 List<ResultVO>
  - 校验失败场景从 assertThrows 改为检查 ResultVO.success=false
- [x] 新增 startScan 批量测试
  - `startScan_emptyList_returnsEmptyResult`: 空列表
  - `startScan_nullList_returnsEmptyResult`: null 列表
  - `startScan_batch_partialFailure`: 3 条中 1 成功 2 失败（未添加/参数非法）
- [x] 新增 deleteByIds 测试
  - `deleteByIds_success`: 正常批量删除
  - `deleteByIds_emptyList_skipsMapper`: 空列表不调 Mapper
  - `deleteByIds_nullList_skipsMapper`: null 列表不调 Mapper
  - `deleteByIds_singleId`: 单条删除

## 关键技术点

1. **批量失败隔离**：遍历逐条执行，try-catch 内部化，单条异常转为 ResultVO(false)，不影响后续条目
2. **单条逻辑复用**：提取 `startSingleScan` 私有方法，保持原有异常抛出语义，批量层做异常→Result 转换
3. **空/null 防御**：startScan 和 deleteByIds 入口统一判断空/null，返回安全默认值
4. **接口兼容性**：`startVersionScan` 入参从单对象改为 List 属于破坏性变更，前端需同步适配
