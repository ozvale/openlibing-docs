# 病毒扫描外部接口（virus-scan-api） — 技术设计

关联业务 Issue: https://gitcode.com/openlibing/openlibing-platform-release/issues/125

## 方案概述

新增与发布评审单解耦的独立病毒扫描任务模型：外部系统 `POST /publish/externalInterface/virusScan/submit` 提交 `bucketName + objectKey`，服务端校验后创建任务记录并异步执行「OBS 单例客户端下载 → clamscan 扫描 → 结果落库 → 临时文件清理」，调用方通过 `GET /publish/externalInterface/virusScan/result?taskId=` 轮询结果。

## 架构决策

### D1：异步任务模型（submit + 轮询）

沿用仓库成熟模式（`SafeScanServiceImpl.batchVirusScan` 同款）：`CompletableFuture.runAsync` + DB 状态机 + 轮询查询。不引入 MQ。状态复用 `ExecuteStatusEnum`（WAIT/EXECUTING/SUCCESS/FAIL）。

### D2：凭证与 endpoint — 调用方三件套优先，projectId 兜底

下载凭证规则（20261103 需求调整）：

- 入参为 `projectId + bucketName + objectKey`，可选 `ak / sk / endPoint` 三件套
- **三件套齐备**：优先使用调用方凭证。**入参 ak/sk 为 AES 密文（与 `hw_project_info` 表存储格式一致，对齐发布链路 `SoftwareObsDownloadServiceImpl` 的解密方式）**，原样入库（`obs_ak`/`obs_sk` 列，不落明文），执行时 `SecurityUtil.decrypt(data, part1)` 解密后使用。endpoint 原样入库（`obs_endpoint`，执行时补 https 前缀）。此时不再查 hw_project_info
- **任一缺失**：整组作废，按 `projectId` 查 `hw_project_info` 表（经 `ReleaseReviewDao.queryHwProjectInfoVo`），AK/SK 解密使用，endpoint 由服务端按项目 region 构造（与 `ReleaseBaseServiceImpl` 建评审单时的构造方式一致）。提交时即查询并快速失败
- 三件套部分传入（只传一两个）视同缺失，整组走兜底，不拼接混用
- 下载统一使用 `try (ObsClient obsClient = new ObsClient(ak, sk, endpoint))` 临时客户端（与现有评审单下载链路同款）
- AK/SK 不经日志输出；scan_details / error_msg 中不含凭证

### D3：扫描引擎复用方式

`SafeScanServiceImpl.executeVirusScan` 与制品/评审单上下文耦合深（downloadType 工厂、SHA256 完整性校验、virus scan 表按 review 关联），**不做整体复用**。复用原子能力：

- `validatePathDir`（路径穿越校验，静态方法可直接调用）
- `LinuxCommandInjectCheck.checkCommand`（命令注入校验）
- `ExecCmdUtil.executeCmdArray("clamscan", "-r", path)`（数组传参防注入）
- 输出清洗逻辑 `cleanClamscanDetails`：从 `SafeScanServiceImpl` 提取为独立工具类 `ClamScanResultParser`（`business/utils`），原方法改为委托调用，**行为不变**

### D4：防重与并发控制

- 提交时按 `bucketName + objectKey` 查询是否存在 EXECUTING 状态任务，存在则拒绝（返回提示），配合 `DistributedLockService` 分布式锁防并发重复提交
- 扫描执行使用现有 `taskExecutor`（ThreadPoolConfig），不新建线程池

### D5：接口风格跟随 externalInterface 现状

Controller 放 `business/controller`（实现阶段从 openeuler 包迁移至 business 包，并精简掉 delegate 层，Controller 直接调用 Service），返回 `MultiResponse`，鉴权跟随现状（网关/内网隔离）。入参校验用 jakarta.validation。

## 接口契约

### 提交任务

```
POST /publish/externalInterface/virusScan/submit
Content-Type: application/json

{
  "projectId": "xxx",
  "bucketName": "xxx",
  "objectKey": "path/to/file.zip",
  "ak": "可选，与sk/endPoint三件套齐备时优先使用",
  "sk": "可选",
  "endPoint": "可选，如 https://obs.cn-north-4.myhuaweicloud.com"
}

成功响应:
{ "code": "200", "message": "success", "result": { "taskId": "uuid", "status": 1 } }

失败响应（参数非法/项目未登记且未传齐三件套/重复提交）:
{ "code": "400", "message": "<原因>", "result": null }
```

### 查询结果

```
GET /publish/externalInterface/virusScan/result?taskId=<uuid>

响应:
{ "code": "200", "message": "success", "result": {
    "taskId": "uuid", "status": 2, "scanResult": "success",
    "scanDetails": "...", "fileName": "file.zip",
    "createTime": "...", "completeTime": "..." } }
```

`scanResult` 语义与现有链路一致：`success`（clamscan 输出含 `: OK`）/ `failed`（检出或扫描异常）。status 使用 `ExecuteStatusEnum` 编码。

## 表结构（Liquibase）

新表 `virus_scan_task`（仿 `release_review_virus_scan.xml` 样式，含 preConditions 幂等保护与 rollback）：

| 字段                                      | 类型                     | 说明                                           |
| ----------------------------------------- | ------------------------ | ---------------------------------------------- |
| id                                        | BIGINT PK AUTO_INCREMENT | 主键                                           |
| task_id                                   | VARCHAR(64) UNIQUE       | 对外任务 ID（UUID）                            |
| project_id                                | VARCHAR(64)              | 项目 ID（hw_project 表关联，凭证来源）         |
| bucket_name                               | VARCHAR(128)             | OBS 桶名                                       |
| object_key                                | VARCHAR(512)             | 对象路径                                       |
| file_name                                 | VARCHAR(256)             | 文件名（从 objectKey 截取）                    |
| status                                    | TINYINT                  | ExecuteStatusEnum 编码，提交即 EXECUTING       |
| scan_result                               | VARCHAR(16)              | success / failed / NULL(未完成)                |
| scan_details                              | VARCHAR(512)             | 清洗后 clamscan 输出（UTF-8 按字节截断）       |
| error_msg                                 | VARCHAR(512)             | 失败原因                                       |
| create_time / update_time / complete_time | DATETIME                 | 时间戳                                         |
| obs_ak                                    | VARCHAR(256)             | 调用方 AK（AES 加密存储；NULL 表示走项目兜底） |
| obs_sk                                    | VARCHAR(256)             | 调用方 SK（AES 加密存储）                      |
| obs_endpoint                              | VARCHAR(128)             | 调用方 endpoint（NULL 表示按项目 region 构造） |

## 涉及文件（最终落地状态）

| 文件                                                                                                 | 操作 | 说明                                                                                               |
| ---------------------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------- |
| `business/controller/VirusScanExternalController.java`                                               | 新增 | submit / result 两个端点（`/publish/externalInterface/virusScan/*`，实现阶段从 openeuler 包迁移）  |
| `business/service/VirusScanTaskService.java` + `business/service/impl/VirusScanTaskServiceImpl.java` | 新增 | 异步执行：下载 + clamscan + 落库 + 清理（实现阶段精简掉 delegate 层，Controller 直接调用 Service） |
| `business/dto/virusscan/VirusScanSubmitModel.java`、`VirusScanTaskResultVo.java`                     | 新增 | 入参 Model / 出参 Vo                                                                               |
| `business/entity/base/VirusScanTaskEntity.java`                                                      | 新增 | MyBatis-Plus 实体                                                                                  |
| `business/mapper/base/VirusScanTaskDao.java`                                                         | 新增 | BaseMapper                                                                                         |
| `business/utils/ClamScanResultParser.java`                                                           | 新增 | 提取 cleanClamscanDetails 逻辑                                                                     |
| `common/aop/log/VirusScanExternalHandler.java`                                                       | 新增 | 外部病毒扫描操作日志补数 Handler（实现阶段补充）                                                   |
| `business/service/impl/SafeScanServiceImpl.java`                                                     | 修改 | cleanClamscanDetails 改为委托 ClamScanResultParser，行为不变                                       |
| `resources/db/changelog/v1.0.0/virus_scan_task.xml`                                                  | 新增 | 建表 changelog                                                                                     |
| `resources/db/changelog/db.changelog.xml`                                                            | 修改 | 注册新 changelog                                                                                   |

对应测试：`VirusScanTaskServiceImplTest` / `VirusScanExternalControllerTest` / `VirusScanVoAndEntityTest` / `VirusScanExternalHandlerTest`。

## 安全设计（生成前约束）

- [ ] 入参 projectId/bucketName/objectKey 必填，ak/sk/endPoint 可选三件套（D2）
- [ ] 三件套齐备时 AK/SK 经 `SecurityUtil.encrypt` 加密入库，不落明文、不落日志
- [ ] 三件套任一缺失时整组作废，按 projectId 查 hw_project_info 兜底，endpoint 由服务端按 region 构造
- [ ] objectKey/bucketName/projectId 过 `LinuxCommandInjectCheck.checkCommand` + 路径合法性校验（拒绝 `..`、绝对路径逃逸、空白控制字符）
- [ ] clamscan 数组传参（`executeCmdArray`），不拼接命令字符串
- [ ] 下载到 `GlobalConstant.LOCAL_FOLDER` 下任务专属子目录，`validatePathDir` 校验后使用，finally 强制删除
- [ ] 下载大小上限（复用/对齐现有下载实现的限制策略），防止压缩炸弹类资源耗尽
- [ ] scan_details 入库前按字节截断（沿用 `StringUtil.truncateByBytesOfUTF8`，500 字节）
- [ ] 不做无关重构，不修改既有评审单扫描链路行为

## 风险 & 缓解

| 风险                                   | 缓解                                                                          |
| -------------------------------------- | ----------------------------------------------------------------------------- |
| 大文件扫描占用线程池，拖慢其他异步任务 | 复用 taskExecutor + CallerRunsPolicy 现状，任务粒度单文件；后续量大再拆专用池 |
| 调用方传入不可访问桶导致凭证失败风暴   | getObject 失败快速落 FAIL，error_msg 记录原因，不重试                         |
| clamscan 宿主机依赖缺失                | 沿用现有部署假设（Dockerfile 已装 ClamAV），FAIL 时 error_msg 可见            |
| 任务表被恶意刷量                       | 网关侧限流 + EXECUTING 状态防重；不引入额外机制（跟随现状）                   |

## 跨仓影响

无。`malicious-code-scan-action` 与本服务无代码耦合；不修改 openlibing-common SDK。
