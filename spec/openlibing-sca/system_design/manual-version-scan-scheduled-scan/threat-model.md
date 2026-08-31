# 威胁模型：manual-version-scan-scheduled-scan

## 资产清单

| 资产 | 分类 | 责任域 | 备注 |
|------|------|--------|------|
| `tbl_manual_version_scan` 记录 | 内部 | 业务服务 | 含 repo_url / repo_name / 定时标记，无个人敏感数据 |
| 定时扫描消息（ScanRequestVO JSON） | 内部 | RabbitMQ | 含仓库 URL、分支、scanId，无凭证 |
| 定时任务触发权 | 内部 | 业务服务 | cron 配置中心可改，多实例靠分布式锁 |
| 平台访问 token | 机密 | IntegrationApiServiceImpl | 复用既有 `platformUtil.getPlatformToken` 解密链路，本次不新增 token 存取 |

## 信任边界

- 客户端 → `/version/scan/batchUpdateScheduled`：需鉴权（沿用项目现有网关鉴权）；**该接口为水平越权敏感点**（任一登录用户可批量改任意记录的定时标记）
- `/version/scan/save`：既有接口，新增可选字段 `is_scheduled`，沿用既有鉴权
- 业务服务 → RabbitMQ `amq_version_scheduled_direct`：内网，复用既有 broker 链路
- 业务服务 → 数据库：内网，参数化查询

## 数据流

1. 客户端 → 网关 → `/batchUpdateScheduled`：body `{ids, isScheduled}`，HTTPS + 鉴权
2. 业务服务 → DB：`UPDATE tbl_manual_version_scan SET is_scheduled=?, update_time=? WHERE id IN (...)`，参数化
3. [每天凌晨] `ManualVersionScanSchedule` → 分布式锁 → 查 `is_scheduled=1 AND is_version_scan=1`
4. 业务服务 → RabbitMQ：`convertAndSend("amq_version_scheduled_direct", "version_scheduled_rout_key", msg)`，消息为 ScanRequestVO JSON（含仓库 URL/分支/scanId）
5. Listener `concurrency=1` 串行消费 → `doScanV3` → 状态回写

## STRIDE 评估

| 资产/流程 | S | T | R | I | D | E | 缓解措施 |
|------|---|---|---|---|---|---|---------|
| `/batchUpdateScheduled` 接口 | 中 | 高 | 中 | 低 | 高 | 中 | 输入校验（ids 数量上限、isScheduled 值域 0/1）；沿用网关鉴权；审计日志 |
| 定时扫描消息 | 低 | 中 | 中 | 中 | 中 | 低 | 串行消费；失败 basicReject + 状态回写；消息含仓库 URL（非敏感） |
| 定时任务 | 低 | 低 | 低 | 低 | 低 | 低 | 分布式锁防多实例重复投递；SCANNING 跳过防重复入队 |
| `is_scheduled` 批量修改 | 低 | 高 | 中 | 低 | 低 | 中 | isScheduled 值域校验；空 ids 防护；审计 update_time |

## 关键决策

- `/batchUpdateScheduled` 输入校验：ids 非空 + 数量上限（500）+ `isScheduled` 仅允许 0/1，非法直接拒绝（fail-secure）
- 批量修改记录 `update_time` 留痕（审计最小集合）
- 定时投递前 `scan_status=SCANNING` 跳过，防止重复入队导致队列堆积（DoS 缓解）
- 队列串行消费 `concurrency=1`，天然限流（D 威胁缓解）
- 不新增凭证存取，token 沿用既有解密链路（零信任最小化改动）
