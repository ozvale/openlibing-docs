# 蓝区性能数据上传归档 — 实现任务

## Task 1: 接口层改造 — Controller 新增 label + archivePath 参数

**文件：**
- 修改：`openlibing-sync-service/src/main/java/com/openlibing/sync/api/controller/TestCaseDataController.java`

- [x] **Step 1: 新增 label 和 archivePath 参数**
  在 `uploadTestcaseMetadata` 方法中新增 `@RequestParam(value = "label", required = false, defaultValue = "") String label` 和 `@RequestParam(value = "archivePath", required = false, defaultValue = "") String archivePath` 参数

- [x] **Step 2: 流水线参数改为可选**
  将 `pipelineId`、`pipelineRunId`、`jobId` 的 `@RequestParam` 注解改为 `required = false`，`defaultValue = ""`

- [x] **Step 3: 调整校验逻辑**
  - files 为空时返回 BAD_REQUEST，data 字段携带 `files must not be empty`
  - archivePath 非空但 label 为空时返回 BAD_REQUEST，data 字段携带 `archivePath requires label`
  - label 和流水线参数均为空时返回 BAD_REQUEST，data 字段携带 `must provide either label or pipelineId/pipelineRunId/jobId`
  - 文件数量超限校验保持不变

- [x] **Step 4: 传递 label 和 archivePath 到 Service 层**
  调用 `testCaseDataService.uploadTestcaseMetadata` 时传入 label 和 archivePath 参数

## Task 2: 服务层改造 — label + archivePath 路由逻辑

**文件：**
- 修改：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/service/testcase/TestCaseDataService.java`
- 修改：`openlibing-sync-service/src/main/java/com/openlibing/sync/domain/service/testcase/impl/TestCaseDataServiceImpl.java`

- [x] **Step 1: 修改接口签名**
  `TestCaseDataService.uploadTestcaseMetadata` 方法新增 `String label` 和 `String archivePath` 参数

- [x] **Step 2: 实现 OBS 路径路由方法**
  新增 `buildObjectKey` 私有方法，根据参数组合构建不同的 OBS 路径：
  - label + archivePath：`/{label}/{archivePath}/{filename}`
  - 仅 label：`/{label}/{filename}`
  - 无 label：`testcase-metadata/{pipelineId}/{pipelineRunId}/{jobId}/{filename}`

- [x] **Step 3: 去除两侧斜杠**
  使用 `StringUtils.strip(value, "/")` 去除 label 和 archivePath 两侧的斜杠，避免路径异常

- [x] **Step 4: 移除 performance/precision 特殊分支**
  删除 `LABEL_PERFORMANCE`、`LABEL_PRECISION` 常量，删除 `getFileExtension` 方法，删除时间戳重命名逻辑，统一走 label + archivePath 路由

- [x] **Step 5: 修改 uploadTestcaseMetadata 实现**
  在文件遍历循环中，使用 `buildObjectKey` 替代原有的固定路径拼接，移除 timestamp 和 fileIndex 变量

## Task 3: 上传脚本改造

**文件：**
- 修改：`openlibing-pytest-executor/script/upload_to_openlibing.py`

- [x] **Step 1: 重命名 auth_secret 为 openlibing_secret**
  参数名 `--auth-secret` 改为 `--openlibing-secret`，函数参数 `auth_secret` 改为 `openlibing_secret`

- [x] **Step 2: 支持环境变量读取 secret**
  若未传入 `--openlibing-secret`，从环境变量 `OPENLIBING_SECRET` 读取；两者均未提供时报错退出

- [x] **Step 3: 新增 --archive-path 参数**
  新增 `--archive-path` 可选参数，需与 `--label` 同时传入

- [x] **Step 4: 调整参数校验逻辑**
  - `--archive-path` 不能脱离 `--label` 单独传入
  - 至少需要 `--label` 或流水线参数之一

- [x] **Step 5: 修复简化 JSON 多 key 解析缺陷**
  将链式 replace 改为拆分-重组方式，正确处理 `{key: value, key: value}` 格式

## Task 4: 验证与测试

- [x] **Step 1: 无 label 场景回归测试**
  验证不带 label 参数调用接口，行为与变更前完全一致

- [x] **Step 2: 仅 label 场景测试**
  验证上传文件归档到 `/{label}/{filename}`

- [x] **Step 3: label + archivePath 场景测试**
  验证上传文件归档到 `/{label}/{archivePath}/{filename}`

- [x] **Step 4: archivePath 优先级测试**
  验证 label + archivePath 与流水线参数同时传入时，以 archivePath 为最终归档路径

- [x] **Step 5: 斜杠边界测试**
  验证 label/archivePath 含前后斜杠时被正确去除

- [x] **Step 6: 参数校验测试**
  验证 archivePath 无 label、无 label 无流水线参数等非法场景返回具体错误信息

- [x] **Step 7: 上传脚本单元测试**
  覆盖 _process_json_param、upload_data_to_openlibing（mock HTTP）、CLI 参数校验等场景
