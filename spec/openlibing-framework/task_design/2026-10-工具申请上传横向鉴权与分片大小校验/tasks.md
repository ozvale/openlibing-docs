# 实现任务：工具申请上传横向鉴权与分片大小校验

## 进度: 9/9 complete

- [x] Task 1: `ToolApplyController.saveToolIcon` 增加 `projectId` 参数（`@NotNull`+`@Min(0)`）并透传
- [x] Task 2: `ToolApplyController.saveToolSoftwarePack` 增加 `userId`、`projectId` 参数并透传
- [x] Task 3: `ToolApplyService` 接口同步两个方法签名
- [x] Task 4: `ToolApplyServiceImpl.saveToolIcon` 入口新增 `verifyPermissions(userId, null, projectId, null, SAVE_TOOL_APPLY)`
- [x] Task 5: `ToolApplyServiceImpl.saveToolSoftwarePack` 入口新增 `verifyPermissions(...)`（解析 toolInfo 之前）
- [x] Task 6: 分片上传大小校验：新增 `MAX_SOFTWARE_PACK_SIZE`/`CHUNK_SIZE_PREFIX` 常量与 `validateChunkSize`，`chunkUpload` 调用并在失败时中止+清理；`cleanupChunkSession` 增加删除累计大小键；`validateSoftwarePackFile` 复用常量
- [x] Task 6b: 分片上传类型校验：新增 zip 魔数常量与 `validateChunkFileType`/`isZipHeader`，`chunkUpload` 在 `chunkIndex == 1` 时校验首片，失败时中止+清理
- [x] Task 7: 更新/补充 `ToolApplyControllerTest`、`ToolApplyServiceImplTest`
- [x] Task 8: 运行质量门禁与安全审查，提交 commit
