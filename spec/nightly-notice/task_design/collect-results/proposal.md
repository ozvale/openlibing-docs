# nightly-notice 定时采集归档 + AI 汇总日报

## 需求背景

openlibing 各业务仓配置了定时流水线（如 `openlibing-framework` 的 `nightly-schedule-scan`，每天 03:00 触发防投毒/SCA/pre-commit 检查）。目前这些检查结果分散在 GitCode Actions 页面，没有统一的历史归档，也无法被后续内网通知工具消费。

需要一个定时自动化能力：定期从 GitCode Actions v8 API 拉取指定仓指定 workflow 的 run/job/step 结果（含各 step 日志），归档到独立代码仓；并由 AI 汇总为每日日报，供内网侧替换负责人占位符后发送 WeLink 提醒。

## 功能描述

### 采集层（已完成）

- 通过配置文件声明采集目标（当前 8 个 openlibing 仓的 `nightly-schedule-scan`）
- 定时（GitCode Action `schedule` cron）触发采集
- 每次执行拉取每个目标 workflow 的**最新一次 run** 的完整结果：run 级 + job 级 + step 级全量 + **各 step 实际日志**（`download_log` ZIP 解包）
- 按 `archive/YYYY/MM/DD/<东八区时间戳>.{json,md}` 归档到本仓
- 成功 job 也要采集归档，不只是失败项；`archive_state.json` 按 run_id 去重

### AI 汇总层（已完成）

- 本机定时（脚本 + Windows 计划任务）用 **opencode CLI**（复用 `skills/record-summary`）读取 archive 最新结果
- 逐仓逐 job 总结：job 成败、问题数量（从 step 日志智能提取，如 argus 的 `pendingConfirm`/`pendingFix`、SCA 的 `unconfirmedFileNum`）
- 无数据不臆造：统一写"暂无日志"（引用 GitCode 平台提示）
- 产出 `records/YYYY/MM/DD.md`，按模板 `{仓库名}代码仓nightly流水线检查结果，请{OWNER}确认`
- **`{OWNER}` 为占位符**：远端报告不含具体责任人；由内网侧维护负责人映射，发送 WeLink 前替换

不做什么：

- 不在 workflow 内跑 AI 总结（AI 在本机外网环境定时执行）
- 远端报告不携带具体负责人（`{OWNER}` 占位）
- 不回填历史 run（只采部署之后的 run）
- 本仓不维护负责人映射（移交内网侧）

## 验收标准

- [x] 通过配置文件可声明采集目标（仓库 / workflow / 分支），脚本无硬编码目标
- [x] 定时 workflow 可正常触发并完成采集 + 归档提交
- [x] 归档数据包含 run/job/step 级全量状态 + step 日志，成功/失败都保留
- [x] 归档文件路径符合 `archive/YYYY/MM/DD/<时间戳>.*`
- [x] 重复运行按 run_id 去重，不产生重复归档
- [x] 自建 runner / 无 pip 环境下可运行（urllib 降级）
- [x] 本地 dry-run 模式可验证采集结果，不污染归档
- [x] AI 汇总能按模板产出 records 日报，`{OWNER}` 占位，问题数不臆造
- [x] 脚本支持任意位置执行（`--repo-root`），并注册 Windows 计划任务

## 影响范围

- 新仓 `LinYP300/nightly-notice`（首版个人仓，后续迁移 openlibing 组织）
- 只读访问 openlibing 组织 8 个私有仓的 Actions API
- 本机 opencode CLI（Bailian 模型 `deepseek-v4-flash-0731`）
- 无任何业务仓代码改动