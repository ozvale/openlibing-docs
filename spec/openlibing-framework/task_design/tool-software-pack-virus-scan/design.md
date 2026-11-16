# Design: 工具软件包病毒扫描对接发布服务

## 1. 改动清单

| 文件                                                                  | 动作           | 说明                                                                                                          |
| --------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------- |
| `business/client/VirusScanClient.java`                                | 新增           | Feign 客户端（submit + result 两接口）                                                                        |
| `business/client/VirusScanFeignConfiguration.java`                    | 新增           | Feign 配置（参照 InterfaceManagementFeignConfiguration）                                                      |
| `business/dto/virusscan/VirusScanSubmitRequest.java`                  | 新增           | 提交入参：projectId/bucketName/objectKey/ak/sk/endPoint                                                       |
| `business/dto/virusscan/VirusScanSubmitResult.java`                   | 新增           | 提交出参 result：taskId/status                                                                                |
| `business/dto/virusscan/VirusScanTaskResultVo.java`                   | 新增           | 查询出参 result：taskId/status/scanResult/scanDetails/fileName/createTime/completeTime                        |
| `business/dto/virusscan/VirusScanResponse.java`                       | 新增           | 通用响应壳：code/message/result                                                                               |
| `business/vo/tool/SoftwarePackScanVO.java`                            | 修改           | 增加 scanTaskId 字段                                                                                          |
| `business/dto/tool/ToolApplyDTO.java`                                 | 修改           | 增加 virusScanTaskId 字段                                                                                     |
| `business/entity/tool/ToolApplyEntity.java`                           | 修改           | 增加 virusScanTaskId/virusScanStatus/virusScanDetails/virusScanFileName/virusScanCreateTime                   |
| `business/mapper/ToolApplyMapper.java` + `mapper/ToolApplyMapper.xml` | 修改           | insert 列映射 + 新增 updateVirusScanResultById 语句                                                           |
| `business/service/impl/ToolApplyServiceImpl.java`                     | 修改           | 上传两路径接扫描提交；申请落库+启动轮询；轮询终态处理                                                         |
| Liquibase changelog                                                   | 新增 changeSet | `20261116_add_virus_scan_columns_tool_apply`：tool_apply 加 5 列（尚未在任何环境执行，单 changeSet 一次到位） |
| `ToolApplyServiceImplTest.java`                                       | 修改           | 新增各分支测试                                                                                                |
| application 配置                                                      | 文档说明       | `platform-release.service.direct-url`（本地直连，缺省走 Nacos 发现）；不新增必填配置                          |

## 2. 关键设计

### 2.1 Feign 客户端

```java
@FeignClient(name = "openlibing-platform-release", contextId = "virusScanClient",
    url = "${platform-release.service.direct-url:}", configuration = VirusScanFeignConfiguration.class)
public interface VirusScanClient {
  @PostMapping("/publish/externalInterface/virusScan/submit")
  VirusScanResponse<VirusScanSubmitResult> submitScan(@RequestBody VirusScanSubmitRequest request);

  @GetMapping("/publish/externalInterface/virusScan/result")
  VirusScanResponse<VirusScanTaskResultVo> queryResult(@RequestParam("taskId") String taskId);
}
```

- 判定逻辑：code==200 且 result!=null 为成功；400 透出 message；500 记日志返回失败
- 入参 projectId：framework 的 Integer projectId 转 String 传入

### 2.2 上传路径接入（ToolApplyServiceImpl）

- `fullUpload` / `completeChunkUpload` 在现有校验与 OBS 上传成功后调用 `submitVirusScan(obsPath, projectId)`
- 提交成功：VO.setScanTaskId(taskId)、setScanResult("scanning")
- 提交失败（Feign 异常/400/500）：返回失败 DataResult；分片路径沿用现有清理链（deleteObject + cleanupChunkSession）；整片路径补 deleteObject 清理
- 不阻塞等待扫描（异步语义）

### 2.3 申请落库与轮询（saveToolApply 改造）

- DTO 带 virusScanTaskId 时：tool_apply 落库 taskId + virusScanStatus="1"，status 保持"0"待审核（扫描成功后审核人邮件由轮询终态触发，与需求 3 一致）
- taskId 为空：直接返回"病毒扫描任务提交失败，请重试"不落库——**无前端回退**（ToolApplyDTO 不含 virusScanResult/virusScanTaskId 字段，扫描字段由后端硬编码 scanning/"1"，前端传值不落库），杜绝旧链路"前端传扫描结果"的绕过面
- 落库成功后启动后台轮询 `startVirusScanPolling(toolApplyId, taskId)`

### 2.4 轮询器（ToolApplyServiceImpl 内部）

- 专用 `ScheduledExecutorService`（2 线程，守护线程，命名 virus-scan-poller，工厂内 setUncaughtExceptionHandler，符合 G.CON.08）；全局单例复用，线程数不随并发扫描数增长。已知局限：每个在途扫描注册一个 5s 周期任务而工作线程仅 2 个，并发扫描数≥2 时查询会被排队拉长实际间隔（scheduleAtFixedRate 同一任务不重叠执行，实际间隔≈max(5s, 排队时长)），属可接受降级；大规模并发时可评估调大线程数
- `scheduleAtFixedRate` 首延迟 5s、间隔 5s；总时长超 30 分钟 cancel + ERROR 日志
- 单次查询异常（Feign 网络抖动）容忍，连续 5 次异常 cancel + ERROR 日志；404（任务不存在，见 proposal 接口契约）无专属分支，与普通异常同样计入连续失败计数——连续 5 次后 cancel 且不写终态，申请滞留"扫描中"，由 2.4.1 手动同步接口自愈
- 终态处理失败（如瞬时 DB 异常）：计入同一连续失败计数并于下个 5s 周期重试（处理成功才 cancel 轮询），连续 5 次处理失败 cancel + ERROR 日志——避免先取消后处理抛异常导致申请静默停留在扫描中；计数仅在非终态推进时清零
- 终态处理抽为可测方法 `handleVirusScanTerminalState(toolApplyId, result)`：
  - success：`updateVirusScanResultById`（result=success,status=2,details,fileName,virus_scan_create_time=createTime,last_scan_time=completeTime）→ 发审核人邮件（applyToolContent + sendEmail(reviewBy)）
  - failed：回填（result=failed,status=3,...）+ 申请 status="2" + reviewRemark + reviewTime → 发申请人邮件（新模板 virusScanFailContent）→ `deleteObject(toolBucket, softwarePackageObsPath)`，删除失败 ERROR 日志（manual cleanup required）
- 轮询按 toolApplyId 查最新 tool_apply 记录，防止申请被撤销（undoApplyInfo）后仍流转：查询记录不存在或 status 已非"0"时 cancel
- 邮件发送异步（CompletableFuture.runAsync，与现有 saveToolApply 邮件一致）

### 2.4.1 手动同步接口（自愈入口）

轮询为内存态，服务重启/超时/连续失败终止后扫描状态可能滞留"执行中"，提供手动自愈接口：

- `POST /tool-apply/sync-virus-scan-result`（userId + id），权限同 getToolApplyInfoById（申请人或审核人）。已知局限：无 @MultiRateLimit 限流；终态复用 handleVirusScanTerminalState，未通过场景会触发邮件+删 OBS——频繁调用可造成重复邮件与 OBS 删除请求放大，后续可增加限流注解
- 逻辑：库内 virus_scan_status 已终态 → 直接返回库内结果（不调远端，防重发邮件/重复删OBS）；否则查询一次远端，终态复用 handleVirusScanTerminalState 后返回最新库内状态；非终态仅返回当前状态
- 并发幂等（如实）：updateVirusScanResultById WHERE 仅 `id = ? and status = '0'`，**无** virus_scan_status 守卫——failed 场景首次更新同时置申请 status='2'，并发另一方 updateCount=0 被拦，仅一方生效；success 场景申请 status 保持 '0'，轮询与手动同步并发存在双写/双发邮件窗口（窗口极小，重复副作用仅为重复邮件与重复删 OBS，无数据损坏），后续可增加 `virus_scan_status = '1'` 条件守卫彻底消除
- 终态处理异常捕获转为失败信息，不向调用方抛500

### 2.4.2 审核拦截（reviewToolInfo）

软件包类型申请必须病毒扫描通过才能人工审核（用户追加需求，含绕过修复）：

- 拦截条件：toolType=0 且 virusScanResult != success。覆盖三类值——scanning（未完成，结果未知）、failed（未通过，兜底防终态流转与人工审核并发竞态）、**null（旧链路绕过修复：旧链路 virusScanResult 由前端传入且不校验，构造不传 taskId/scanResult 的软件包申请可落库 null 绕过原 scanning/failed 判断，导致未扫描软件包直接过审）**
- 扫描结论仅信任服务端终态回填（异步轮询回填），不信任前端传入值——审核读取 DB 回填值（queryById）而非请求参数；配合 2.3 节"taskId 为空不落库、DTO 无前端扫描字段"，前端无法注入扫描结论
- 非软件包类型（web/网站集成）不涉及软件包扫描，null 正常放行，不影响存量 web 工具审核
- 存量影响：加列前落库的 virusScanResult=null 待审核软件包申请将被拦截，需重新提交走扫描闭环

### 2.5 表结构变更（Liquibase）

tool_apply 新增列（changeSet，preConditions 判断列不存在才加）：

| 列                     | 类型         | 说明                                                                    |
| ---------------------- | ------------ | ----------------------------------------------------------------------- |
| virus_scan_task_id     | varchar(64)  | 扫描任务 ID                                                             |
| virus_scan_status      | varchar(1)   | 0待执行/1执行中/2成功/3失败                                             |
| virus_scan_details     | varchar(500) | 清洗后扫描详情（对齐服务端 500 字节截断）                               |
| virus_scan_file_name   | varchar(256) | 扫描文件名                                                              |
| virus_scan_create_time | varchar(20)  | 扫描任务创建时间：申请落库记提交时刻，终态回填优先取发布服务 createTime |

- createTime 入库 virus_scan_create_time（用户要求：扫描开始/完成时间均落库）；completeTime 映射到已有 last_scan_time（远端缺失时兜底本地当前时间）
- ⚠️ 生产暂禁新 DDL（memory 约束）：changeSet 随代码合入，生产部署节奏由用户把控

### 2.6 Mapper

- insert/resultMap 补 5 新列（含 virus_scan_create_time）
- 新增 `updateVirusScanResultById`：回填扫描结果列；failed 场景同语句一并更新 status/reviewRemark/reviewTime（单 SQL，避免多语句竞态）

### 2.7 安全自检映射

- ak/sk 走 Environment 配置注入（AES 密文），日志打印全链路禁打印明文/密文（LogSanitizer 体系）
- scanDetails 来自外部服务清洗后输出（≤500 字节），入库 varchar(500)；邮件内容包含工具名/版本等低敏字段
- objectKey 沿用 framework 生成的 obsPath（已过 OBS key 注入校验），无用户可控注入面
- 轮询任务异常不中断主流程；所有外部调用失败均 fail-closed（申请不流转 + 日志可追）

## 3. 测试策略

1. 上传两路径：Feign submit 成功 → VO 含 taskId；submit 失败 → 接口失败 + OBS 清理调用断言
2. saveToolApply 带 taskId → 落库断言 + 轮询启动（轮询器可注入/绕过）
3. `handleVirusScanTerminalState` 直接单测三分支：success（回填+审核人邮件）、failed（回填+status=2+申请人邮件+deleteObject）、记录已撤销（无副作用）
4. 轮询器超时/连续异常 cancel 逻辑单测（注入 mock ScheduledExecutor 场景由集成逻辑保证，单测聚焦终态方法）
5. 存量测试回归：ToolApplyServiceImplTest 全量 + ZipSecurityCheckUtilTest
