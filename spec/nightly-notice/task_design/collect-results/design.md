# nightly-notice 定时采集归档 + AI 汇总日报 — 技术设计

## 方案概述

两段式：**采集层**由 `nightly-notice` 仓内 `schedule` cron 定时运行 Python 采集脚本，直接调用 GitCode Actions v8 REST API 拉取目标仓 workflow 的 run/job/step 全量结果（含 step 日志），归档到本仓 `archive/`；**AI 汇总层**在本机（外网）用 opencode CLI 定时读取 archive，生成每日日报 `records/YYYY/MM/DD.md`，供内网侧替换 `{OWNER}` 后发送 WeLink。

## 架构决策

| 决策点              | 选择                                                        | 原因                                                                                    |
| ------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 采集运行载体        | GitCode Action `schedule` cron                              | 平台原生托管、secret 进平台，与现有 `nightly-schedule-scan` 同模式                      |
| 采集实现            | Python 3 + requests（urllib 降级）                          | 团队既有 Python 范式，job+step 全量解析灵活                                             |
| 采集 API 层         | 直接调 Actions v8 REST                                      | run detail 已含 stages/jobs/steps 全量                                                  |
| 日志采集            | `GET .../jobs/{job_id}/download_log`（ZIP，按 step 分文件） | 一次返回全部 step 日志，命名 `{序号}_{step名}.log`                                      |
| 采集凭证            | workflow 注入 `secrets.ROBOT_TOKEN`（= PAT，私有仓 read）   | 已实证可读各仓 actions runs                                                             |
| 归档布局            | `archive/YYYY/MM/DD/<东八区时间戳>.json(.md)`               | 按日归档、时间戳命名                                                                    |
| 采集粒度            | 每次取每个目标 workflow 的**最新一次 run**                  | 用户确认：不要最近 N 轮                                                                 |
| 采集范围            | config 文件声明，当前 8 个 openlibing 仓                    | 用户要求"范围走配置文件"                                                                |
| 回填                | 不回填，只采未来                                            | 用户确认                                                                                |
| **AI 汇总运行位置** | **本机（外网）定时执行 opencode CLI**，不进 workflow        | 用户决策：workflow 内跑 AI 增加凭证/网络复杂度；本机复用现成 opencode + 模型            |
| **AI 客户端**       | opencode CLI（`npm i -g opencode-ai`）                      | 复用现有工作区 opencode 配置（Bailian / deepseek-v4-flash-0731），`run --auto` 可脚本化 |
| **负责人处理**      | 远端报告用 `{OWNER}` 占位符，不填具体责任人                 | 用户决策：远端报告永不含责任人，内网发送时替换                                          |
| 定时方式            | 采集 = GitCode cron；总结 = Windows 计划任务                | 采集托管平台，总结本机计划任务                                                          |

## 采集流程

```
cron 触发
  → 读 config/collect.yaml
  → 对每个 target:
      GET /api/v8/repos/{owner}/{repo}/actions/runs
          filters: workflow_name / branch / per_page=1（最新一次 run）
      → 若最新 run_id 已在归档状态中 → 跳过（不重复写）
      → 取该 run 详情（stages/jobs/steps 全量）→ download_log 拉 step 日志
      → 提取关键字段（status/耗时/message/链接），JSON 瘦身
  → 启动时按 config 收敛 archive_state（retain：删除已移除仓的过期记录）
  → 生成 archive/YYYY/MM/DD/<时间戳>.json + .md
  → git add -f archive/ + commit + push（回到本仓 master）
```

**归档 md 日志渲染收敛（省 token/省空间）**：md 中 step 以 `- **<step>** · <STATUS>` 标记，
完整日志仅在 json 保留（md 只展示 AI 所需）：

| step 状态                                        | md 渲染                                                      |
| ------------------------------------------------ | ------------------------------------------------------------ |
| 整个 job 成功（COMPLETED）                       | step 段整体省略，一行 `#### <job>（任务成功，无 step 日志）` |
| job 内成功 step（COMPLETED）                     | 只保留 `- **name** · COMPLETED`，不带日志块                  |
| 失败/未执行 step（FAILED/INIT/IGNORED/CANCELED） | 标题 + 日志块（原处理）                                      |

skill 侧与之配套：job 全成功不读任何 step 日志；job 失败只读失败 step 日志块、成功 step 不读。

## AI 汇总流程

```
Windows 计划任务（每日 07:30）
  → scripts/generate_daily_summary.sh --repo-root <仓库根>
      → （执行前自动）git fetch 双远端 + fast-forward master，同步远端采集归档
      → opencode run "<prompt>" -f skills/record-summary/SKILL.md
        → 读 archive/<当日>/ 的 md（按需读 step 日志）→ 逐仓逐 job 总结（成败/问题数/链接）
        → 产出 records/YYYY/MM/DD.md（模板 {OWNER} 占位，行尾硬换行）
      → git commit + push master；脚本末尾对 origin + openlibing-test 双远端做兜底 push
```

注册定时任务：`scripts/register_daily_summary.bat`（schtasks，默认 07:30）。

> **同步远端归档（重要）**：采集由远端 workflow（06:30）push 到远端 master；本机 07:30 任务若不拉取则本地 `archive/<当日>` 缺失、总结失败。脚本执行前自动 `git fetch` origin + openlibing-test，再对任一可用远端 `master` 做 fast-forward；本地领先/冲突时警告后继续（宁可用本地旧数据报错，也不盲改本地）。
>
> **双远端推送保证**：AI 裸 `git push` 只推 upstream（openlibing-test）会漏推 origin，历史出现过双端不同步。现三层保障——① opencode 指令要求显式 `git push origin master` 与 `git push openlibing-test master`；② 脚本在 opencode 后对双远端兜底 push；③ AGENTS.md 行为约束写明"禁止裸 git push"。
>
> **改进方向（待定）**：当前方案是"先 fetch+ff 到本地再读"，依赖本地仓库副本与偏快进前进；更彻底方案为直接从远端读取归档（如 `git show origin/master:archive/...` 或 GitCode API），不依赖本地工作区状态、无快进冲突，成本更高，留待需要时评估。

## API 数据模型（来自 gitcode CLI 源码 `api/queries_actions.go`）

- `WorkflowRun`: `workflow_run_id / workflow_id / workflow_name / status / event / run_number / head_branch / head_sha / start_time / end_time`
- `WorkflowRunStage`: `id / name / status / sequence / start_time / end_time / jobs[]`
- `WorkflowRunJob`: `id / name / identifier / status / sequence / job_type / start_time / end_time / execute_cost_time / exec_id / message / steps[]`
- `WorkflowRunStep`: `id / name / task / status / sequence / start_time / end_time / log`

## 涉及文件（现状）

| 文件                                     | 操作    | 说明                                                                    |
| ---------------------------------------- | ------- | ----------------------------------------------------------------------- |
| `config/collect.yaml`                    | ✅ 已有 | 采集目标配置（8 仓）                                                    |
| `collector/fetch_nightly_results.py`     | ✅ 已有 | 采集 + 提取 + 归档主脚本                                                |
| `collector/gitcode_api.py`               | ✅ 已有 | Actions v8 API 封装（urllib 降级 + download_log）                       |
| `collector/archive_writer.py`            | ✅ 已有 | 归档生成（json+md，东八区时间戳）                                       |
| `collector/archive_state.py`             | ✅ 已有 | run_id 去重                                                             |
| `.gitcode/workflows/collect-archive.yml` | ✅ 已有 | schedule cron + push 触发 + paths-ignore 防自触发                       |
| `skills/record-summary/SKILL.md`         | ✅ 已有 | AI 日报规则：模板/{OWNER} 占位/硬换行/不臆造 + step 日志按需读取        |
| `scripts/generate_daily_summary.sh`      | ✅ 已有 | 每日总结入口（fetch+ff 同步、opencode 执行、双远端兜底 push）           |
| `scripts/register_daily_summary.bat`     | ✅ 已有 | 注册 Windows 计划任务                                                   |
| `AGENTS.md`                              | ✅ 已有 | 本仓项目级约束：AI 总结只读 archive、不改脚本、双远端 push、Commit 规范 |
| `requirements.txt`                       | ✅ 已有 | requests + PyYAML                                                       |
| `archive/Y*`                             | 生成    | 采集归档                                                                |
| `records/Y*`                             | 生成    | AI 日报                                                                 |

## 凭证与权限

- 采集：`secrets.ROBOT_TOKEN`（PAT，8 仓 read）+ 本仓 push；`ATOMGIT_TOKEN` 只对当前仓有效
- 总结：本机 opencode 配置（Bailian API Key）+ 本机 Git `credential.helper store` 推送，无 workflow secret 依赖
- 负责人：`{OWNER}` 占位符，远端不存负责人；内网侧维护并替换

## 环境处理（自建 runner）

- workflow 用 `['self-hosted', 'region=cn']`；runner 自带 Python 3.8.10（glibc 2.31，setup-python 的 3.12 不兼容），直接 `python3 -m pip install --user`
- AI 总结在本机跑，无关 runner

## 风险 & 缓解

| 风险                             | 缓解                                                                 |
| -------------------------------- | -------------------------------------------------------------------- |
| 私有仓无权限读出 403             | 提前验证 PAT scope；文档标注所需权限                                 |
| cron 触发时上一轮 nightly 未跑完 | 采集 cron 定在 nightly 之后（06:30）                                 |
| 重复归档                         | run_id 去重状态文件                                                  |
| AI 总结臆造问题数                | SKILL.md 强制"无数据写暂无日志，绝不臆造"                            |
| 负责人占位符被 AI 填充           | SKILL.md/脚本强制 `{OWNER}` 不动                                     |
| AI 提交不符合规范                | SKILL.md 固化 commit 规范（Co-authored-by + Generated-by，不 amend） |
| token 泄露                       | 只放 secret/本地配置，不硬编码                                       |

## 跨仓影响

- openlibing 组织 8 个仓：只读 Actions API，无代码改动
- `openlibing-docs`：spec 归档（本需求），Phase 5 走 PR
- 迁移后目标仓改为 `openlibing/nightly-notice`，届时建 Issue + 补全流程

## 内网通知层设计（本次新增）

### 定位

- **纯工程工具**：不使用 AI、不依赖 opencode/任何模型，Python 标准库为主
- 与项目耦合尽量低：`send_welink.py` 迁出 skill，作为独立工具复用

### 架构

```
内网定时任务(09:30)
  → 内网脚本 notify_daily.py
      → 读远端仓 records/<YYYY>/<MM>/<DD>.md（A 方案：GitCode API + urllib + PAT 读 raw，不 clone）
      → 读 owner 本地配置(仓库→负责人/群组) 替换 {OWNER}
      → 合并消息并自动分块（每片 ≤8500 字符，适配小鲁班 10000 上限）
      → 调 send_welink.py 逐片发到 owner 群组（多片带 (1/N) 序号标题）
```

### 关键决策

| 决策点       | 选择                                                                               | 原因                                                                |
| ------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 读取方式     | GitCode API `GET /api/v5/repos/{owner}/{repo}/contents/records/...`（urllib+PAT）  | 只取当日文件，不 clone 全仓，依赖最少                               |
| 负责人映射   | 内网本地 owner 配置文件（不入库）                                                  | 负责人由内网维护，符合既有 `{OWNER}` 占位设计                       |
| GitCode 认证 | 内网本地 `pat.json`（api_base + token）                                            | 独立于 workflow secret；仅用于读远端 records                        |
| WeLink 认证  | 小鲁班专属 token（`tools/welink/config/token.txt`，`send_welink.py --setup` 注入） | 与 GitCode PAT 独立，发送专用                                       |
| 发送         | 复用 `send_welink.py`（WeLinkSender.send_card）                                    | 已实测可用的发送实现，迁出 skill 复用                               |
| 消息形式     | 合并为一条群消息发到 owner 群组（`owners.yaml` 的 `receivers.default`）            | 用户指定                                                            |
| 超长分块     | 发送端按仓块自动分片，每片 ≤8500 字符（上限 10000），多片标题带序号（1/N）         | 26 仓日报约 1.07 万字符超限（422），发送端兜底分块，AI 总结无需压缩 |
| 触发         | 内网本地定时（默认 09:30）                                                         | 与 AI 总结 07:30 错开，留时间差                                     |
| 依赖         | Python 标准库（urllib）+ requests + PyYAML                                         | 尽量少                                                              |

### 涉及新增文件（nightly-notice 仓）

| 文件                               | 说明                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------ |
| `tools/welink/send_welink.py`      | 从 `skills/send-welink-card/scripts/send_welink.py` 迁出（复用发送实现） |
| `tools/notify/notify_daily.py`     | 内网通知主脚本：读远端 records → 替换 {OWNER} → 合并 → 发送              |
| `tools/notify/owners.example.yaml` | owner 配置示例（本地维护，不入库）                                       |
| `tools/notify/pat.example.json`    | GitCode PAT 配置示例（api_base + token，本地维护）                       |
| `tools/notify/register_notify.bat` | 内网定时任务注册（09:30）                                                |
| `skills/send-welink-card/`         | 删除（skill 机制不再使用）                                               |

### 风险 & 缓解

| 风险                                      | 缓解                                               |
| ----------------------------------------- | -------------------------------------------------- |
| 当日 records 未生成（AI 总结 07:30 失败） | 脚本检查远端文件存在，缺失时明确报错并跳过         |
| owner 配置缺失某仓                        | 未配置的仓按 `{OWNER}` 原文保留或跳过发送，可配置  |
| PAT 过期                                  | 读取失败/401 时明确提示重新配置                    |
| 群消息过长（小鲁班 text 上限 10000）      | 发送端自动分块：每片 ≤8500，逐片发送，多片序号标题 |
