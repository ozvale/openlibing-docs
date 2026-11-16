# Tasks: 工具软件包病毒扫描对接发布服务

## Phase 3 实现步骤

- [x] 1. Liquibase：tool_apply 新增 5 列 changeSet `20261116_add_virus_scan_columns_tool_apply`（virus_scan_task_id/virus_scan_status/virus_scan_details/virus_scan_file_name/virus_scan_create_time，preConditions 防重复；尚未执行，单 changeSet 合并）
- [x] 2. DTO：VirusScanResponse/VirusScanSubmitRequest/VirusScanSubmitResult/VirusScanTaskResultVo；SoftwarePackScanVO+scanTaskId；ToolApplyDTO+virusScanTaskId
- [x] 3. Entity + Mapper：ToolApplyEntity 5 新字段；ToolApplyMapper.xml insert/resultMap 列映射 + updateVirusScanResultById 语句
- [x] 4. Feign：VirusScanClient + VirusScanFeignConfiguration（参照 InterfaceManagementClient 写法）
- [x] 5. ToolApplyServiceImpl 上传接入：fullUpload/completeChunkUpload 调 submitVirusScan；成功 VO 带 taskId + scanResult="scanning"；失败 fail-closed + OBS 清理
- [x] 6. ToolApplyServiceImpl 申请接入：saveToolApply 带 taskId 落库（task_id+status=1）+ 启动轮询；taskId 空直接失败不落库（无前端回退，DTO 无前端扫描字段）
- [x] 7. ToolApplyServiceImpl 轮询器：ScheduledExecutorService(2线程,守护,UncaughtExceptionHandler)、5s间隔、30min超时、连续5次异常终止、撤销保护
- [x] 8. 终态处理 handleVirusScanTerminalState：success→回填+审核人邮件；failed→回填+status=2+申请人邮件+deleteObject(删失败ERROR)；单元可测
- [x] 9. 邮件模板：申请人扫描失败通知内容（virusScanFailContent）
- [x] 10. 测试：上传两路径提交断言、申请落库断言、终态三分支、清理断言；回归存量测试（新增14个测试，ToolApplyServiceImplTest 共68个全绿）
- [x] 11. 验证：spotless:apply + 全量 ToolApplyServiceImplTest + ZipSecurityCheckUtilTest + 编译（定向 74/74 通过；全量回归 clean test BUILD SUCCESS，2284/2284 通过，0 失败 0 错误）
- [x] 12. 交付：用户确认后按 ≤1000 行拆分提交——91dedb7a2（feat，747行：基础设施+业务逻辑）、a402865f4（test，615行：14个单测），两 commit pre-commit 全绿（含 gitleaks + Spotless/CheckStyle/SpotBugs/PMD）
- [x] 13. 手动同步接口（用户追加）：POST /tool-apply/sync-virus-scan-result，库内终态直返防重、远端终态复用幂等终态处理、权限同查看接口；新增6个单测（syncVirusScanResult* 系列：ReturnsDbStateDirectlyWhenAlreadyTerminal/HandlesRemoteTerminalState/ReturnsScanningWhenRemoteInProgress/RejectsInvalidRequests/FailsWhenRemoteQueryFails/FailsGracefullyWhenTerminalHandlingThrows）
- [x] 14. 审核拦截（用户追加）：reviewToolInfo 对软件包类型（toolType=0）要求 virusScanResult 必须为 success 才放行（scanning/failed/null 全拦，null 为旧链路构造绕过修复）；非软件包类型不判断；新增4个单测（reviewToolInfoBlockedWhenVirusScanScanning/BlockedWhenVirusScanFailed/BlockedWhenSoftwarePackWithoutScanResult/AllowsNonSoftwarePackWithoutScanResult）
- [x] 15. 手动同步/触发/审核拦截交付验证：commit a0c0033f8（feat(tool-apply): defer virus scan to apply save and add manual trigger；同分支副本 992f16e24/e46727d2c）——含手动同步 6 单测、手动触发 4 单测、审核拦截 4 单测；全量回归 ToolApplyServiceImplTest 82 个测试全绿

## 验证命令

```
python scripts/run-mvn.py spotless:apply test "-Dtest=ToolApplyServiceImplTest,ZipSecurityCheckUtilTest"
```

## 前端/联调依赖（非本仓）

- 前端：上传响应保存 scanTaskId → saveToolApply 传 virusScanTaskId（改造后不再依赖 scanResult="success"）
- 联调：ak/sk AES 密文格式与发布服务解密体系一致性；platform-release 本地直连配置 platform-release.service.direct-url
- 生产 DDL 禁令期间部署节奏由用户把控（changeSet 随代码走）
