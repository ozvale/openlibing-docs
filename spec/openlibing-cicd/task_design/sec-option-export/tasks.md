# 构建产物安全编译选项导出功能 — 实现任务

> 跨仓 Full 模式实现任务清单。业务仓 Issue / PR 标题与 FE 需求名称「构建产物安全编译选项导出功能」逐字一致。

## 进度: 0/12 complete

### 后端（openlibing-cicd-fork，分支 `sec-option-scan-optimization`）

- [ ] **Task 1**: 在 `FileTypeEnums` 新增 `SEC_OPTION("安全编译选项", "_secoption")` 枚举值
  - 文件：`src/main/java/com/openlibing/cicd/common/enums/FileTypeEnums.java`
  - 注意：与既有 `BUILD_LOG`、`TEST_RESULT_PIPELINE` 等枚举值并列，不影响现有逻辑

- [ ] **Task 2**: 新增 `SecOptionExportReqDTO` 入参 DTO
  - 文件：`src/main/java/com/openlibing/cicd/business/dto/secoption/SecOptionExportReqDTO.java`
  - 字段：`projectId`（必填，String）、`recordId`（必填，Long）、`optionKeys`（可选，`List<String>`）
  - 校验注解：`@NotBlank` / `@NotNull` / `@Size(max=14)` 等，遵循 cicd-fork 既有 DTO 校验范式

- [ ] **Task 3**: 新增 `SecOptionExportVO` 出参 VO
  - 文件：`src/main/java/com/openlibing/cicd/business/vo/secoption/SecOptionExportVO.java`
  - 字段：`exportTaskId`（String）、`message`（String）
  - 仿 `TestCaseExportVO` 结构与命名风格

- [ ] **Task 4**: 在 `SecOptionScanFileDetailMapper` 新增 `selectByRecordIdForExport` 方法
  - 文件：`src/main/java/com/openlibing/cicd/business/mapper/SecOptionScanFileDetailMapper.java` + `src/main/resources/mapper/SecOptionScanFileDetailMapper.xml`
  - 入参：`projectId`、`recordId`
  - 返回：`List<SecOptionScanFileDetailEntity>`（含 `filePath`、`rawOptions`、`options`、`filedOptions` Map）
  - SQL：复用既有 `selectFileDetailPage` 的 LEFT JOIN `sec_option_filing` 逻辑，去掉分页、按 `file_path` 升序、字段精简
  - **注意**：删除检查——本任务是新增方法，不删除既有方法；既有 `selectFileDetailPage` 仍被 file-detail 接口使用，不能动

- [ ] **Task 5**: 在 `SecOptionScanService` 接口新增 `submitSecOptionExportTask` 方法签名
  - 文件：`src/main/java/com/openlibing/cicd/business/service/SecOptionScanService.java`
  - 签名：`DataResult<SecOptionExportVO> submitSecOptionExportTask(String userId, SecOptionExportReqDTO request)`

- [ ] **Task 6**: 在 `SecOptionScanServiceImpl` 实现三段式导出
  - 文件：`src/main/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImpl.java`
  - 新增方法：
    - `submitSecOptionExportTask`（同步入口，仿 `submitTestCaseExportTask`）
    - `doSecOptionExport`（异步线程，仿 `doAsyncExport`）
    - `performSecOptionExcelExport`（EasyExcel 多 sheet 写）
    - `tryReuseSecOptionExport`（缓存复用，仿 `tryReuseTestResultExport`）
    - `executeSecOptionExportAndUpload`（查 DB + 生成 Excel + 上传 OBS）
    - `generateSecOptionReadableFileName`（拼文件名 `安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`）
    - `buildSummaryHead` / `buildSummaryData`（Summary sheet 表头 + 数据）
    - `buildDetailHead` / `buildDetailData`（Detail sheet 表头 + 数据）
  - 注入：`FrameworkProjectClient`、`ObsBucketService`、`AsyncTaskExecutor`（既有 Bean，复用）
  - 复用：`ExportStatus` 枚举、`updateExportLogStatus` 私有方法（如果既有方法签名通用则直接调用，否则新增重载）

- [ ] **Task 7**: 在 `BuildArtifactController` 新增 `exportSecOption` 端点
  - 文件：`src/main/java/com/openlibing/cicd/business/controller/BuildArtifactController.java`
  - 路径：`POST /build-artifact/sec-option/export`
  - 签名：`exportSecOption(@RequestParam String userId, @Valid @RequestBody SecOptionExportReqDTO request)` → `DataResult<SecOptionExportVO>`
  - 复用既有 `userId` 解析逻辑（与 `/overview`、`/file-detail` 一致）

### 前端（openlibing-cicd-web，分支 `develop_202608_iter2`）

- [ ] **Task 8**: 切换到 `develop_202608_iter2` 分支，调研产物包详情页实际 Vue 组件路径
  - 命令：`git -C /d/Develop/Java/openlibing-cicd-web checkout develop_202608_iter2`
  - 调研：找到 `sec-option-detail` 路由对应的 Vue 组件绝对路径（预计在 `src/views/pipeline/` 或 `src/views/secOption/` 下）
  - 调研：找到既有 API 文件路径（预计在 `src/api/secOption/` 或 `src/api/pipeline/` 下）
  - 调研：确认 `ExportSource` 类型定义位置（在 `src/stores/exportTask.ts`）

- [ ] **Task 9**: 在 `src/api/secOption/url.ts`（或 `src/api/pipeline/url.ts`）新增 `SEC_OPTION_EXPORT` 常量
  - 值：`/build-artifact/sec-option/export`

- [ ] **Task 10**: 在 `src/api/secOption/api.ts`（或 `src/api/pipeline/api.ts`）新增 `exportSecOption` 函数
  - 签名：`export const exportSecOption: RequestFunc = (a, s) => apiClient.post(urls.SEC_OPTION_EXPORT, a, s)`
  - 遵循 cicd-web 既有 API 函数范式

- [ ] **Task 11**: 在 `src/stores/exportTask.ts` 的 `ExportSource` 类型加 `'sec-option'` 值
  - 与既有 `'pipeline-log'`、`'test-report'` 等并列，不删除既有值
  - 其他逻辑无改动（既有轮询、自动下载、sessionStorage 持久化逻辑通用）

- [ ] **Task 12**: 在产物包详情页 Vue 组件顶部按钮区新增"导出"按钮
  - 文件：Task 8 调研到的实际 Vue 组件路径
  - 新增：`<el-button type="primary" size="small" :icon="Download" :loading="isExporting" @click="handleExport">导出</el-button>`
  - 新增：`isExporting` ref、`handleExport` async 方法
  - 复用：`useExportTaskStore`、`extractExportId`、`ElMessage`
  - 位置：放在"待备案项列表"按钮右侧，与既有按钮同 `header-actions` 区

### 验证

- [ ] **Task V1**: 后端单元测试
  - 测试 `submitSecOptionExportTask` 入参校验（projectId/recordId 必填、optionKeys 枚举白名单）
  - 测试 `generateSecOptionReadableFileName`（packageName 含特殊字符 sanitize）
  - 测试 `buildSummaryHead/Data`（14 项固定顺序、未扫描项不输出）
  - 测试 `buildDetailHead/Data`（每扫描项两列、未备案留空字符串）
  - 测试 `tryReuseSecOptionExport`（命中/未命中分支）
  - Mock framework Feign 调用与 OBS 上传

- [ ] **Task V2**: 端到端验证
  - 切到 develop_202608_iter2 分支启动前端，进入产物包详情页，点击"导出"按钮
  - 验证浮窗出现"生成中"状态，3 秒轮询
  - 验证 Excel 生成完毕后自动下载
  - 验证 Excel Sheet1 "Summary" 列与详情页汇总表逐字一致
  - 验证 Excel Sheet2 "Detail" 每扫描项两列、未备案文件备案值列空
  - 验证文件名格式 `安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`
  - 验证同一 recordId 重复点导出秒级返回（缓存命中）

### 文档归档（openlibing-docs 仓，Phase 5 由用户触发）

- [ ] **Task D1**: 本设计文档（`proposal.md` / `design.md` / `tasks.md` / `export-demo.html`）通过 docs PR 提交到主干
- [ ] **Task D2**: 归档时生成 `archive.md`，沉淀可复用经验到 `ai_memory.md`

## 任务依赖关系

```
Task 1 (FileTypeEnums) ─┐
Task 2 (ReqDTO)        ─┤
Task 3 (VO)            ─┼─→ Task 5 (Service 接口) ─→ Task 6 (Service 实现) ─→ Task 7 (Controller)
Task 4 (Mapper)        ─┘                                                    │
                                                                              ▼
Task 8 (调研前端结构) ─→ Task 9 (URL) ─→ Task 10 (API) ─→ Task 12 (Vue 组件)
                       Task 11 (store 类型) ─┘
                                                                              │
                                                                              ▼
                                                                       Task V2 (端到端)
```

- Task 1-4 可并行（独立新增类与方法签名）
- Task 5-6 串行（接口先于实现）
- Task 7 依赖 Task 6
- Task 8 是前端调研前置
- Task 9-12 串行（URL → API → store → Vue 组件）
- Task V1 可在 Task 6 完成后开始
- Task V2 需后端 Task 7 + 前端 Task 12 都完成
