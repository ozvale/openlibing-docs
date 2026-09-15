# 实现任务清单

## 阶段 1：基础设施

- [ ] 在 `openlibing-sync` 中新增 `CommunityRepoScanJob` 类骨架，继承现有 `BaseScheduledJob`
- [ ] 配置 CRON：`0 2 * * *`（每日凌晨 2 点），可通过环境变量调整
- [ ] 准备 `/tmp/sync/repo-scan/` 工作区根目录，加入 `.gitignore`/`cleaner` 策略
- [ ] 在 Doris 中创建表 `community_repo_whitelist` / `community_repo_scan_record` / `community_testcase_summary`

## 阶段 2：白名单与克隆

- [ ] 实现白名单加载与缓存（每 5 分钟刷新一次）
- [ ] 实现 `RepoCloner` 工具类：clone / pull / 切换分支 / 单仓超时控制
- [ ] 注入 GitCode Token（私有仓支持）
- [ ] 实现单仓失败隔离（try-except 包裹，失败写日志）
- [ ] 单元测试：cloner 在网络异常、超时、磁盘满等情况下的处理

## 阶段 3：扫描引擎

- [ ] 评估并选择方案 A 或 B（参见 design.md §3）
- [ ] 若选 A：在 `openlibing-pytest-executor` 中新增 `POST /api/v1/scan_repository` 端点
- [ ] 若选 B：在 `openlibing-sync` 内实现 pytest 文件扫描（基于 `ast` / `pytest --collect-only`）
- [ ] 输出统一 JSON schema：`{test_file_count, testcase_count, skipped_count, namespaces[]}`
- [ ] 单元测试：扫描引擎对样例仓库（pytest 用例 / 非 pytest / 无用例）的输出

## 阶段 4：数据写入

- [ ] 实现 `ScanResultWriter`：调用 `/api/data/ingest`（复用已有数据接入能力）
- [ ] 失败重试：本地缓冲 + 异步重投（最多 3 次）
- [ ] 端到端测试：从白名单配置 → 扫描 → 入库的全链路

## 阶段 5：监控与告警

- [ ] 添加 Prometheus 指标（参见 design.md）
- [ ] 配置告警规则：连续 3 次扫描失败 / 成功率 < 80% / 单仓超时率 > 20%
- [ ] Grafana 看板：扫描成功率、Top 仓用例数趋势、失败仓清单

## 阶段 6：上线与验证

- [ ] 灰度环境：先添加 2 个仓验证
- [ ] 生产环境：白名单首批 5 个社区仓
- [ ] 运行一周后评审指标，调整 CRON 频率与并发数
- [ ] 文档更新：`openlibing-sync/README.md` 与运营 SOP

## 后续可选增强（不在本期范围）
- 支持 GitLab、Gitee、GitHub 等多平台仓库
- 接入 AI 评审：自动识别可疑用例 / 异常模式
- 与 IDE 插件数据交叉分析，识别"开发者使用 vs 仓库真实测试"的一致性