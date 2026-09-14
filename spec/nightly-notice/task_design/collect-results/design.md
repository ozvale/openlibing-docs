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
  → 生成 archive/YYYY/MM/DD/<时间戳>.json + .md
  → git add -f archive/ + commit + push（回到本仓 master）
```

## AI 汇总流程

```
Windows 计划任务（每日 07:30）
  → scripts/generate_daily_summary.sh --repo-root <仓库根>
      → opencode run "<prompt>" -f skills/record-summary/SKILL.md
        → 读 archive/ 最新 json → 逐仓逐 job 总结（成败/问题数/链接）
        → 产出 records/YYYY/MM/DD.md（模板 {OWNER} 占位，行尾硬换行）
      → git commit + push master（遵循仓库 commit 规范）
```

注册定时任务：`scripts/register_daily_summary.bat`（schtasks，默认 07:30）。

## API 数据模型（来自 gitcode CLI 源码 `api/queries_actions.go`）

- `WorkflowRun`: `workflow_run_id / workflow_id / workflow_name / status / event / run_number / head_branch / head_sha / start_time / end_time`
- `WorkflowRunStage`: `id / name / status / sequence / start_time / end_time / jobs[]`
- `WorkflowRunJob`: `id / name / identifier / status / sequence / job_type / start_time / end_time / execute_cost_time / exec_id / message / steps[]`
- `WorkflowRunStep`: `id / name / task / status / sequence / start_time / end_time / log`

## 涉及文件（现状）

| 文件                                     | 操作    | 说明                                              |
| ---------------------------------------- | ------- | ------------------------------------------------- |
| `config/collect.yaml`                    | ✅ 已有 | 采集目标配置（8 仓）                              |
| `collector/fetch_nightly_results.py`     | ✅ 已有 | 采集 + 提取 + 归档主脚本                          |
| `collector/gitcode_api.py`               | ✅ 已有 | Actions v8 API 封装（urllib 降级 + download_log） |
| `collector/archive_writer.py`            | ✅ 已有 | 归档生成（json+md，东八区时间戳）                 |
| `collector/archive_state.py`             | ✅ 已有 | run_id 去重                                       |
| `.gitcode/workflows/collect-archive.yml` | ✅ 已有 | schedule cron + push 触发 + paths-ignore 防自触发 |
| `skills/record-summary/SKILL.md`         | ✅ 已有 | AI 日报规则：模板/{OWNER} 占位/硬换行/不臆造      |
| `scripts/generate_daily_summary.sh`      | ✅ 已有 | 每日总结入口（`--repo-root` 任意位置执行）        |
| `scripts/register_daily_summary.bat`     | ✅ 已有 | 注册 Windows 计划任务                             |
| `requirements.txt`                       | ✅ 已有 | requests + PyYAML                                 |
| `archive/Y*`                             | 生成    | 采集归档                                          |
| `records/Y*`                             | 生成    | AI 日报                                           |

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
      → 合并为一条消息
      → 调 send_welink.py 发到 owner 群组
```

### 关键决策

| 决策点     | 选择                                                                              | 原因                                          |
| ---------- | --------------------------------------------------------------------------------- | --------------------------------------------- |
| 读取方式   | GitCode API `GET /api/v5/repos/{owner}/{repo}/contents/records/...`（urllib+PAT） | 只取当日文件，不 clone 全仓，依赖最少         |
| 负责人映射 | 内网本地 owner 配置文件（不入库）                                                 | 负责人由内网维护，符合既有 `{OWNER}` 占位设计 |
| GitCode 认证 | 内网本地 `pat.json`（api_base + token）                                             | 独立于 workflow secret；仅用于读远端 records    |
| WeLink 认证 | 小鲁班专属 token（`tools/welink/config/token.txt`，`send_welink.py --setup` 注入） | 与 GitCode PAT 独立，发送专用                   |
| 发送       | 复用 `send_welink.py`（WeLinkSender.send_card）                                   | 已实测可用的发送实现，迁出 skill 复用         |
| 消息形式   | 合并成一条群消息发到 owner 群组（`owners.yaml` 的 `receivers.default`）             | 用户指定                                      |
| 触发       | 内网本地定时（默认 09:30）                                                        | 与 AI 总结 07:30 错开，留时间差               |
| 依赖       | Python 标准库（urllib）+ requests + PyYAML                                        | 尽量少                                        |

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

| 风险                                      | 缓解                                              |
| ----------------------------------------- | ------------------------------------------------- |
| 当日 records 未生成（AI 总结 07:30 失败） | 脚本检查远端文件存在，缺失时明确报错并跳过        |
| owner 配置缺失某仓                        | 未配置的仓按 `{OWNER}` 原文保留或跳过发送，可配置 |
| PAT 过期                                  | 读取失败/401 时明确提示重新配置                   |
| 群消息过长                                | 合并时对超长内容截断/分仓简述                     |
