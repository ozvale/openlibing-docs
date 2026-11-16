# Proposal: 工具软件包病毒扫描对接发布服务

- 仓：openlibing-framework
- 分支：ZZT_202611_iter1_safe
- 模式：Full
- 日期：2026-11-04
- 状态：待实现

## 1. 需求背景

`ToolApplyController.saveToolSoftwarePack`（整片/分片上传软件包）完成文件格式、大小、压缩炸弹校验后，需通过 Feign 调用发布服务（openlibing-platform-release）的外部病毒扫描接口，对 OBS 桶内软件包执行 ClamAV 病毒扫描；扫描结果落库 `tool_apply`，并按结果驱动审核邮件与状态流转。

现状：上传接口返回的 `scanResult` 为硬编码 `"success"`，病毒扫描从未真正执行；`tool_apply` 表已预留 `virus_scan_result`/`last_scan_time` 字段。

## 2. 接口契约（来源：外部病毒扫描接口对接报告 v1.0）

### 2.1 提交扫描任务

- `POST /publish/externalInterface/virusScan/submit`
- 入参 body：`projectId`(String)、`bucketName`(String)、`objectKey`(String)、`ak`(可选,AES密文)、`sk`(可选,AES密文)、`endPoint`(可选)
- 出参：`{code, message, result: {taskId, status}}`，code=200 成功；400 校验失败（含同对象任务执行中防重复）；500 服务异常
- Feign 直连服务时路径不含 `/openlibing-platform-release` 网关前缀

### 2.2 查询扫描结果

- `GET /publish/externalInterface/virusScan/result?taskId={taskId}`
- 出参 `result`：`taskId`、`status`（0待执行/1执行中/2成功/3失败）、`scanResult`（success未检出/failed检出或失败）、`scanDetails`（清洗后详情，≤500字节）、`fileName`、`createTime`、`completeTime`
- 轮询间隔 ≥5s；大文件可达分钟级；终态(2/3)后停止轮询
- code：200 正常；404 任务不存在；500 异常

## 3. 核心设计决策（用户已确认）

| 决策     | 结论                                                                                                                                                                                                                             |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 扫描模型 | **异步闭环**：上传接口提交任务即返回 taskId；申请提交时落库并启动后台轮询；终态后回填 tool_apply 并驱动邮件/状态流转                                                                                                             |
| OBS 凭证 | **传三件套**（framework 自有 obs.access-key-id/secret-access-key/endpoint，指向 tool-bucket），不依赖发布服务 hw_project 表；ak/sk 为 AES 密文 Environment 配置，请求体透传密文，全链路零日志（详见 design.md 2.7 安全自检映射） |
| 开发分支 | ZZT_202611_iter1_safe（与安全整改同分支）                                                                                                                                                                                        |
| 流程模式 | Full                                                                                                                                                                                                                             |

### 3.1 异步闭环时序

```
saveToolSoftwarePack(整片/最后一片)
  → 现有校验(格式/大小/压缩炸弹)
  → Feign submit {projectId, bucketName=tool-bucket, objectKey=obsPath, ak, sk, endPoint}
  → 返回 VO: {obsPath, scanTaskId, scanResult="scanning", scanTime, uploadId}

saveToolApply(前端传 virusScanTaskId)
  → 落库 tool_apply: virus_scan_task_id + virus_scan_status(1)
  → 启动后台轮询(5s间隔, 超时上限30分钟)
      ├─ 终态 success: 回填 result/status/details/fileName/last_scan_time=completeTime
      │    → 发审核人邮件(applyToolContent)
      └─ 终态 failed: 回填 + status=2审核不通过 + reviewRemark"病毒扫描未通过，自动拒绝" + reviewTime
           → 发申请人邮件 → deleteObject(tool-bucket, softwarePackageObsPath)
```

兼容：DTO.virusScanTaskId 为空时回退现有行为（前端传 virusScanResult），保证灰度期可用。

## 4. 验收标准

1. 整片/分片上传校验通过后均发起 Feign 扫描提交，taskId 返回前端；提交失败时上传接口返回明确失败信息且不残留无效 OBS 对象（沿用现有失败清理）
2. `saveToolApply` 带 taskId 时：taskId 与扫描状态落库 tool_apply；终态 success 后审核人收到审核提示邮件
3. 终态 failed 后：申请人收到扫描失败邮件；该申请 status=2 审核不通过 + reviewRemark；OBS 桶内软件包对象被删除
4. 轮询有超时上限与异常终止保护，不泄漏线程/任务
5. Liquibase changeSet 适配 beta 现有索引/字段，不重复建列；⚠️ 生产暂禁新 DDL，生产部署节奏需用户单独把控
6. spotless/Checkstyle/SpotBugs/PMD 通过；相关单测全绿（上传提交、申请落库、轮询三终态分支、OBS 清理）

## 5. 已知风险与开放项

- ak/sk AES 密文格式与发布服务解密体系一致性需联调验证（同 openlibing 体系，预期一致）
- 前端需同步改造：上传后保存 taskId → 申请时传 virusScanTaskId（不再依赖硬编码 scanResult）
- 上传与申请之间的窗口期扫描任务无人查询属预期行为（发布服务侧已终态，申请后首次轮询即得结果）
- 嵌套 zip 炸弹等深层风险仍由解压侧控制兜底（见 software-pack-zip-deep-check proposal）
