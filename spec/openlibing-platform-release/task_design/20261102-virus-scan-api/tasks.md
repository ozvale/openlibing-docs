# 病毒扫描外部接口（virus-scan-api） — 实现任务

关联业务 Issue: https://gitcode.com/openlibing/openlibing-platform-release/issues/125

## 进度: 7/7 complete

已随业务仓 PR（分支 `check_safe_202611` → `release_20261116`）交付。

- [x] Task 1: 提取 `ClamScanResultParser` 工具类（从 `SafeScanServiceImpl.cleanClamscanDetails`），原方法改为委托，行为不变，补对应单测
- [x] Task 2: 新增 Liquibase changelog `virus_scan_task.xml` + 实体 `VirusScanTaskEntity` + `VirusScanTaskDao`，注册到 master changelog
- [x] Task 3: 新增 DTO（`VirusScanSubmitModel` / `VirusScanTaskResultVo`，含 jakarta.validation 注解）
- [x] Task 4: 新增 `VirusScanTaskService(Impl)`：submitTask（校验 + 防重 + 建任务 + 异步执行）/ getTaskResult / 私有 executeScan（下载 → clamscan → 落库 → 清理）
- [x] Task 5: 新增 `VirusScanExternalController`（submit / result 端点，MultiResponse；实现阶段调整：置于 business 包，精简 delegate 层，Controller 直接调用 Service）
- [x] Task 6: 单元测试：Service/Controller/DTO 层 Mockito 单测（参数校验、防重、成功/失败路径、清理逻辑），另补 `VirusScanExternalHandlerTest`
- [x] Task 7: 验证：`mvn compile` + `mvn test`（含 JaCoCo 门禁），AI 自检清单核对
