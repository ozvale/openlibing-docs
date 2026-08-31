# 安全设计：manual-version-scan-scheduled-scan

## 1. 认证授权

- 方案：沿用项目现有网关鉴权，`/batchUpdateScheduled` 与 `/save` 同层级（业务后台接口，非匿名）
- 越权防护：本次不引入新的权限模型（不新增 RBAC/ABAC），**但** `batchUpdateScheduled` 为批量写接口，若后续需要对定时标记做操作审计，应在 service 层记录操作人（当前记录 update_time 留痕）
- 凭证：不新增凭证；平台 token 复用 `platformUtil.getPlatformToken` 既有解密链路

## 2. 输入输出

- 边界校验（Controller/Service）：
  - `batchUpdateScheduled`：`ids` 非空 + 集合大小 ≤ 500；`isScheduled` 仅允许 0/1；非法输入返回失败（fail-secure），不落 SQL
  - `save`：`is_scheduled` 可选字段，沿用现有 `@NotNull` 校验体系
- 输出编码：批量接口返回更新记录数（int），无反射型输出风险
- SQL 注入：`WHERE id IN (...)` 使用 MyBatis `<foreach>` 参数化绑定，无字符串拼接

## 3. 数据保护

- 分类分级：`tbl_manual_version_scan` 为内部业务数据（仓库 URL/名称），非个人敏感数据，不做字段级加密
- 传输加密：沿用项目既有 HTTPS + 网关链路；MQ 走内网既有 broker 通道
- 脱敏：日志只记录 repoId/branchId/scanId，不打印完整 repo_url 全量内容（沿用现有日志风格）
- 最小化：查询接口仅透出新增 `isScheduled` 字段，不额外暴露字段

## 4. 依赖供应链

- 无新增第三方依赖（仅复用 Spring @Scheduled / RabbitMQ / MyBatis 既有组件）
- 无需锁文件 / replace 审查

## 5. 部署运行时

- 配置管理：cron 表达式走配置中心（`${job.cron.manual.version.scan:0 0 0 * * ?}`），不入代码
- 审计日志（最小集合）：
  - 定时任务触发/跳过：记录 lockKey、repo 数量（info）
  - 单仓投递成功/失败：记录 repoId/branchId/scanId/error（info/error）
  - 批量修改定时标记：记录更新记录数（info）
- 多实例：分布式锁 `manual_version_scheduled_scan_<env>` 保证单实例执行

## 6. 失败模式

- Fail Secure：
  - `batchUpdateScheduled` 输入非法 → 返回失败，不执行任何更新
  - 定时任务异常 → 锁在 finally 释放，任务体 catch 不中断整个任务
  - 单仓投递失败 → 记录 error，跳过该仓，不阻塞其他仓库
  - 消费端扫描异常 → 状态回写 SCAN_FAILED + basicReject，不无限重试
- 应急响应：定时扫描异常不影响手动扫描（独立队列隔离）；broker 未声明队列时 `@QueueBinding` 随启动自动声明

## 7. 验证计划

- 单元测试：
  - `batchUpdateScheduled`：空 ids / 非法 isScheduled / 超限 ids → 返回 0 不落 SQL
  - `startScheduledScan`：SCANNING 跳过、repoInfo 缺失跳过、单仓异常不中断
  - `startVersionScan(po, true, true)`：scheduled 队列直发分支
- 集成测试：不适用（无跨服务新契约）
- 事后审查：安全约束交由 `gitcode-security-check` 验证实现（用户触发时执行）
