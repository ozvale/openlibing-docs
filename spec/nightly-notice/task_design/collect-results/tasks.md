# nightly-notice 定时采集归档 + AI 汇总日报 — 实现任务

## 进度: 18/18 complete

### 采集层（Phase 3，已完成）

- [x] Task 1: 初始化 `nightly-notice` 仓结构（master 分支，README + .gitignore）
- [x] Task 2: 编写 `config/collect.yaml` 配置 schema（多仓 + workflow 声明，现 8 仓）
- [x] Task 3: 实现 `collector/gitcode_api.py`（Actions v8 API 封装，urllib 降级 + download_log）
- [x] Task 4: 实现 `collector/fetch_nightly_results.py`（采集 + run_id 去重 + 提取主流程）
- [x] Task 5: 实现 `collector/archive_writer.py`（archive/YYYY/MM/DD/ 归档 JSON+MD，东八区时间戳）
- [x] Task 6: 编写 `.gitcode/workflows/collect-archive.yml`（schedule cron + push 触发 + paths-ignore 防自触发）
- [x] Task 7: 本地 dry-run 验证采集 openlibing 组织 nightly 结果（8 仓全通）
- [x] Task 8: 提交 commit（master 直接开发，多轮迭代）

### AI 汇总层（新增，已完成）

- [x] Task 9: 编写 `skills/record-summary/SKILL.md`（日报模板、问题数提取、{OWNER} 占位、硬换行）
- [x] Task 10: 安装 opencode CLI（`npm i -g opencode-ai`，复用现有 Bailian 模型配置）
- [x] Task 11: 验证 `opencode run -f SKILL.md` 生成 records 日报并 push
- [x] Task 12: 编写 `scripts/generate_daily_summary.sh`（支持 `--repo-root` 任意位置执行）
- [x] Task 13: 编写 `scripts/register_daily_summary.bat`（注册 Windows 计划任务，默认 07:30）
- [x] Task 14: 删除 `config/owners.yaml`，报告使用 `{OWNER}` 占位符（负责人移交内网）
- [x] Task 15: 更新 README 反映全链路
- [x] Task 16: 更新本 spec（proposal/design/tasks 反映实际实现）

### 验证（已完成）

- [x] Task 17: 采集 8 仓 dry-run 全通过（4 仓有 nightly run，framework 已归档去重）
- [x] Task 18: AI 总结生成 records/2026/09/13.md（8 仓，{OWNER} 占位，无数据写"暂无日志"）