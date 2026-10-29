# 工具申请上传接口横向鉴权与分片大小校验

关联 Issue：[openlibing/openlibing-framework#116](https://gitcode.com/openlibing/openlibing-framework/issues/116)（第 6 项：工具箱管理功能中，上传图标、上传文件的横向鉴权与分片上传的文件大小校验）

## 需求背景

`ToolApplyController` 中两个文件上传接口存在安全缺陷：

1. `POST /tool-apply/save-tool-icon`（保存工具申请-工具图标）：仅校验 `userId` 非空，**未做横向越权校验**。任意登录用户可传入任意 `userId` 上传/覆盖指定工具名称的图标。
2. `POST /tool-apply/save-tool-software-pack`（保存工具申请-安装包）：
   - **既无 `userId` 也无项目上下文**，完全没有任何身份与横向越权校验，任意调用方可占用 OBS 存储。
   - 分片上传路径（`chunkUpload`）**未做任何文件大小校验**；完整上传路径（`fullUpload`）虽有 zip 格式 + 5GB 限制，但分片模式可通过多片累计绕过。

同类接口 `saveToolApply` 已采用 `commonService.verifyPermissions(userId, productId, projectId, repoId, url)` 做横向鉴权，本需求对齐该既有模式。

## 验收标准

- [ ] `saveToolIcon` 在执行业务逻辑前调用 `commonService.verifyPermissions(userId, null, projectId, null, UrlConstant.SAVE_TOOL_APPLY)`，无权限时拒绝。
- [ ] `saveToolSoftwarePack` 在解析 `toolInfo` 前调用同样的横向鉴权，无权限时拒绝。
- [ ] 两个接口新增请求参数：`saveToolIcon` 增加 `projectId`；`saveToolSoftwarePack` 增加 `userId` 与 `projectId`（均为必填，`projectId >= 0`）。
- [ ] 分片上传对每个分片校验非空且单分片不超过 5GB；对同一 `uploadId` 会话累计已上传分片大小，累计超过 5GB 时中止 OBS 分段上传、清理会话并返回明确错误。
- [ ] 分片上传对**首片**（`chunkIndex == 1`，即文件头部）校验 zip 魔数（`50 4B 03 04` / `50 4B 05 06` / `50 4B 07 08`），非 zip 时中止并清理会话，与完整上传的类型校验对齐。
- [ ] 分片会话清理（`cleanupChunkSession`）同步清理累计大小 Redis 键，避免脏数据。
- [ ] 相关单元测试更新并通过；质量门禁（spotless/checkstyle/spotbugs/pmd）通过。
- [ ] 接口契约变更同步到 API 文档，并通知前端在调用时补充 `userId`/`projectId` 参数。

## 影响范围

- 模块：tool（工具箱管理-工具申请）
- 仓：openlibing-framework（单仓）
- 文件：1 个 Controller、1 个 Service 接口、1 个 Service 实现、2 个测试类
- 兼容性：**接口契约变更（新增必填请求参数）**，需前端同步改造后上线，前后端需协同发布。
