# 病毒扫描外部接口（virus-scan-api）

关联业务 Issue: https://gitcode.com/openlibing/openlibing-platform-release/issues/125

## 需求背景

外部系统需要复用 openlibing-platform-release 的病毒扫描能力：传入 OBS 对象路径（endpoint + bucketName + objectKey），由服务端从 OBS 下载文件并执行 ClamAV 病毒扫描，返回扫描结果。

现有扫描能力（`SafeScanServiceImpl.executeVirusScan`）与发布评审单（reviewId）上下文强绑定，无法独立对外提供，需要解耦出一套独立的扫描任务模型。

## 功能描述

### 做什么

- 新增外部接口（`/publish/externalInterface` 风格路径，鉴权跟随现状：网关/内网隔离）：
  - `POST /publish/externalInterface/virusScan/submit`：提交扫描任务，必填 `projectId` / `bucketName` / `objectKey`，可选 `ak` / `sk` / `endPoint` 三件套，返回 `taskId`
  - `GET /publish/externalInterface/virusScan/result`：按 `taskId` 轮询扫描结果（status / scanResult / scanDetails）
- 下载凭证规则：ak/sk/endPoint 三件套齐备时优先使用调用方凭证（AES 加密入库）；任一缺失则按 `projectId` 查 `hw_project_info` 表兜底（与现有评审单下载链路同源）
- 异步执行模型：提交后立即返回 taskId，后台线程完成「OBS 下载 → clamscan 扫描 → 结果落库 → 临时文件清理」
- 新增 Liquibase 表 `virus_scan_task` 记录任务状态与扫描结果
- 复用现有能力：按项目 AK/SK 建临时 ObsClient 的下载模式、clamscan 调用与输出清洗逻辑、异步状态机模式

### 不做什么

- 不改动现有发布评审单（reviewId）扫描链路
- 不引入新的鉴权机制（API-Key/token 签名）
- 不对接 malicious-code-scan-action
- 不做批量扫描/目录递归扫描（单对象粒度）

## 验收标准

- [ ] 提交接口：合法参数返回 taskId，任务初始状态为 EXECUTING；三件套缺失且 projectId 未登记 hw 账号信息时快速失败
- [ ] 结果接口：能按 taskId 返回 status（WAIT/EXECUTING/SUCCESS/FAIL）、scanResult（success/failed）、scanDetails
- [ ] 入参校验：projectId/bucketName/objectKey 通过路径穿越校验与命令注入检查（LinuxCommandInjectCheck / validatePathDir 同等强度）
- [ ] 凭证安全：三件套齐备时 AK/SK 加密入库不落明文；任一缺失时按 projectId 查 hw_project_info 兜底；AK/SK 不落日志
- [ ] 扫描完成后临时文件强制清理
- [ ] 单元测试覆盖 Controller/Service 层，`mvn test` 通过

## 影响范围

- 业务仓：`openlibing-platform-release`（新增 Controller/Service/Entity/Mapper + Liquibase changelog，不修改既有评审单扫描链路）
- 文档仓：`openlibing-docs`（本 spec 目录）
