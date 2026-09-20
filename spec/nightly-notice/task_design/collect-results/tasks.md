# nightly-notice 定时采集归档 + AI 汇总日报 + 内网通知 — 实现任务

## 进度: 18/18 complete（采集/汇总）+ 内网层进行中

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
- [x] Task 16b: 修复"本机定时任务读不到当日 archive"缺陷 —— `generate_daily_summary.sh` 执行前自动 `git fetch` 双远端 + fast-forward master；README/spec 补充同步说明与改进方向（直接读远端归档）

### 验证（已完成）

- [x] Task 17: 采集 8 仓 dry-run 全通过（4 仓有 nightly run，framework 已归档去重）
- [x] Task 18: AI 总结生成 records/2026/09/13.md（8 仓，{OWNER} 占位，无数据写"暂无日志"）

### 内网通知层（本次新增，纯工程工具）

- [x] Task 19: 将 `skills/send-welink-card/scripts/send_welink.py` 迁出至独立工具目录（`tools/welink/`）
- [x] Task 20: 删除 `skills/send-welink-card/`（skill 机制不再使用）
- [x] Task 21: 实现 `tools/notify/notify_daily.py`：从 GitCode API 读远端 records 当日 md（A 方案 urllib+PAT）
- [x] Task 22: 实现 `{OWNER}` 替换：读取 owner 本地配置（仓库→负责人/群组），未配置仓可跳过/占位
- [x] Task 23: 合并为一条群消息，调 `send_welink.py` 发到 owner 群组
- [x] Task 24: 支持参数/配置：远端仓库地址（--repo）、owner/PAT 配置文件路径
- [x] Task 25: 编写 owner/PAT 示例配置文件（`owners.example.yaml` / `pat.example.json`）
- [x] Task 26: 编写内网定时任务注册 `register_notify.bat`（默认 09:30）
- [x] Task 27: 本地 dry-run 验证读取+替换+合并（--date 2026-09-13 实测通过）
- [x] Task 28: 凭证澄清：`pat.json` 仅保留 GitCode token/api_base；WeLink 小鲁班 token 走 `tools/welink/config/token.txt` 独立注入

### 优化与缺陷修复（追加）

- [x] Task 29: 修复本机定时任务读不到当日 archive —— `generate_daily_summary.sh` 执行前 fetch 双远端 + fast-forward
- [x] Task 30: 修复 ff 循环只同步第一个远端 —— 遍历所有可用远端依次 ff，避免误 break
- [x] Task 31: archive_state 按 config 收敛 —— 采集启动 `retain()` 删除已移除仓记录；无新 run 也保存清理结果
- [x] Task 32: 归档 md 日志收敛 —— job 成功整段省略、成功 step 无日志、失败/未执行 step 保留日志块；skill 按需读取 step 日志
- [x] Task 33: 双远端推送兜底 —— opencode 指令显式推 origin+openlibing-test；脚本末尾兜底 push；AGENTS.md 约束禁止裸 `git push`
- [x] Task 34: 新增本仓 `AGENTS.md` —— AI 总结只读 archive、不改脚本、Commit 规范、双远端推送约定

### 内网通知增强（追加）

- [x] Task 35: 内网工具超长分块 —— 小鲁班 `send_card` text 上限 10000 字符，26 仓合并日报 10717 超限 422；`notify_daily.py` 发送端按仓块自动分片（每片 ≤8500），多片标题带 (1/N) 序号
