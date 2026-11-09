# 静态代码分析 GitHub 接入方案与文档 · bandit — 设计文档

## 1. 方案设计

### 1.1 需求背景与目标态

openLiBing 的代码检查链路当前主要面向 GitCode Actions：各静态分析工具产出 SARIF，经 `upload-sarif-action` 上传 OBS 并回调 openLiBing，最终在「开发管理 - 代码检查」页面展示。

「静态代码分析 GitHub 接入」FE 已由 clang-tidy 完成首个落地，并沉淀了可复用的 GitHub 接入范式：平台来源枚举（`GITHUB_ACTION`）、前端平台筛选与来源标签、`upload-sarif-action` / `pre-commit-action` 双插件的平台识别与 OIDC 免密换证改造均已交付。gosec、clippy 已先后验证该范式可复制。本 US 将该范式复制到 Python 语言安全扫描工具 **bandit**（基于 AST 检测硬编码密码、命令注入、不安全反序列化、弱哈希等风险），进一步覆盖 Python 技术栈。

**目标态**：

1. 在 GitHub 平台 `openlibing-test` 组织下准备可运行的 bandit 流水线（`bandit-full-scan-demo`），覆盖 workflow 全量扫描与 pre-commit 集成两种入口；
2. 扫描结果能够生成合法 SARIF（bandit 原生 `-f sarif` 直出），上传 OBS 并回调 openLiBing；
3. 「代码检查」页面筛选 GitHub 平台后能看到问题列表与详情（前端零改动，复用 clang-tidy 已交付能力），高危问题严重度标记准确；
4. 同步沉淀 bandit 接入的 GitHub 侧差异经验（插件参数兼容性、配置格式约束）；
5. 本设计文档归档到 `openlibing-docs` 仓。

前端原型复用「静态代码分析 GitHub 接入」FE 已归档的 prototype.html（平台筛选、GitHub Action 来源标签），本 US 无前端改动、不单独出原型。

### 1.2 总体方案

沿用**单份代码、运行时识别平台**的方案，不为 GitHub 维护独立分支：

- 业务配置（`.bandit.yml` 规则、扫描命令、pre-commit 钩子）在 GitCode 与 GitHub 完全复用，差异集中在 workflow 写法与插件引用；
- 两个 action 按 `GITHUB_ACTIONS` 识别运行平台，只读取对应平台的上下文变量（clang-tidy US 已交付，本 US 直接复用）；
- GitHub 侧使用 `GitHubActions` OIDC 身份提供商免密换证，OBS 桶按平台隔离（`openlibing-github-action`）；
- 产品侧零改动：来源枚举与前端标签沿用 clang-tidy 已上线能力；
- 演示仓 `bandit-full-scan-demo` 与 GitCode 侧 `test-bandit-scan` 同源：被扫样例代码与规则口径一致，GitCode 侧流水线语法移植为 GitHub Actions 语法。

### 1.3 关键选型与理由

| 决策点                | 选择                                                                 | 理由                                                                                                                 |
| --------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 认证方式              | OIDC 免密换证（`GitHubActions` 身份提供商）                          | 复用 clang-tidy 已打通的链路，不落任何长期 AK/SK                                                                     |
| OBS 桶                | GitHub 使用 `openlibing-github-action`                               | 与 GitCode 桶隔离，便于权限与成本归集（复用既有桶，无新增）                                                          |
| SARIF 转换            | bandit 原生 `-f sarif` 直出（依赖 `sarif-om` + `jschema-to-python`） | **零转换器、零预置二进制**，与 gosec 同级简化；`bandit[sarif]` extra 随 pip 安装                                     |
| 规则配置格式          | `.bandit.yml`（YAML）                                                | bandit 1.9.x 的 `-c` 不再解析裸 `.bandit` INI 文件（实测报 `expected '<document start>'`），YAML 为官方现行格式      |
| 规则单一事实源        | 扫描工作流与 pre-commit hook 共用 `.bandit.yml`                      | 两端口径一致，避免规则漂移；版本锁定 `bandit==1.9.4`（与 GitCode 侧一致）                                            |
| pre-commit SARIF 产出 | manual 阶段专用 hook 直出原生 SARIF，不走日志解析                    | pre-commit-action 日志解析存在行号进 uri、startLine 存列号、无 snippet 缺陷（GitCode 侧实证），原生 SARIF 元数据齐全 |
| 入口形态              | pre-commit 集成 + workflow 全量扫描并存                              | 分别覆盖提交前拦截与全量归档场景，共用同一份规则配置                                                                 |
| 产品侧改动范围        | 无                                                                   | 来源枚举与前端标签已由 clang-tidy US 交付，本 US 仅验证复用                                                          |

### 1.4 涉及文件与跨仓影响

| 仓库 / 模块                                              | 涉及内容                                                                                                                                               |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `bandit-full-scan-demo`（GitHub `openlibing-test` 组织） | `.github/workflows/` 两套 GitHub 工作流、`.bandit.yml`、`.pre-commit-config.yaml`、`requirements.txt`、`demo/` 被扫样例（含 3 个 HIGH 严重度高危样例） |
| `openlibing-docs`                                        | 本设计文档归档                                                                                                                                         |
| `docs`（后续 US）                                        | bandit README 增加 GitCode / GitHub 差异速查表，demos 拆分 `gitcode/` 与 `github/` 目录（本 US 未含）                                                  |

`upload-sarif-action`、`pre-commit-action`、`openlibing-codecheck` 后端、`openlibing-web` 前端均无改动（复用 clang-tidy US 已交付成果）。

## 2. 实现逻辑设计

### 2.1 主流程

场景二（workflow 全量扫描，`bandit-scan.yml`）：

```text
GitHub 代码仓触发 workflow（手动 / push main / 定时）
  → checkout → setup-python 3.12
  → pip install "bandit[sarif]==1.9.4"
  → bandit -c .bandit.yml -r demo -f sarif -o <临时目录>/bandit.sarif（非门禁，检出即继续）
  → upload-sarif-action@source-platform-detection（OIDC 换证 → OBS 上传 → 回调 openLiBing，category=business）
```

场景一（pre-commit 集成，`bandit-precommit.yml`）：

```text
GitHub 代码仓触发 workflow（手动 / push main / PR）
  → checkout → setup-python 3.12 → pip install pre-commit → mkdir 报告目录
  → pre-commit-action@main（--all-files --hook-stage=manual 收集原生 SARIF）
  → upload-sarif-action@source-platform-detection（category=pre-commit-report）
  PR 事件：纯门禁（钩子命中即失败拦截），跳过上传归档
```

触发限制：上传类工作流不含 `pull_request` 触发——华为云 IAM `GitHubActions` 信任策略仅放行 push 形 sub（`repo:<org>/<repo>:ref:refs/heads/<branch>`），`pull_request` 形 sub 换证会被拒绝（沿承 clang-tidy/clippy 结论）。

### 2.2 平台识别与上下文映射

由 `upload-sarif-action` 在运行时完成（clang-tidy US 已交付，本 US 验证复用）：`GITHUB_ACTIONS=true` 识别平台，上报来源标记 `GITHUB_ACTION`，上下文映射 `pipelineId=GITHUB_JOB`、`pipelineRunId=GITHUB_RUN_ID`、`pipelineName=GITHUB_WORKFLOW`、`commitId=GITHUB_SHA`。

### 2.3 认证与上传逻辑

workflow 声明 `permissions: id-token: write`，`upload-sarif-action` 通过 GitHub Actions OIDC 接口申请 ID Token，向华为云 IAM `GitHubActions` 身份提供商换 STS 临时凭证，上传 OBS 桶 `openlibing-github-action`（key 结构与 GitCode 桶一致：`bandit-results/{owner}/{repo}/{yyyyMMdd.HH}/{runId}/bandit.sarif`），随后回调 openLiBing `/codescan/v1/result/receive`。全链路无静态 AK/SK。

### 2.4 前端展示逻辑

前端零改动。「开发管理 - 代码检查」页面按 GitHub 平台筛选，来源标签展示 GitHub Action；bandit 问题展示工具名 Bandit、真实行号、源码片段与 issue_severity 严重度标记（依赖原生 SARIF 元数据齐全）。

### 2.5 边界与异常处理

- **bandit 1.9.x 配置格式**：`-c` 仅支持 YAML/TOML，裸 `.bandit` INI 报错；规则配置命名 `.bandit.yml`；
- **GitHub 版 pre-commit-action 的 extra_args 校验**：按空格拆分 token 且要求以 `--` 开头，`--hook-stage manual` 中 `manual` 被拒（`Invalid extra_args`），必须使用等号形式 `--hook-stage=manual`（argparse 兼容）；
- **GitHub 版 pre-commit-action 不预创建 report 目录**：目录缺失时 bandit `-o` 写文件直接失败（exit 2），插件退化为日志解析兜底 SARIF（元数据受损）；workflow 必须先 `mkdir -p` 报告目录。GitCode 版会预创建，两侧行为不一致，接入文档需显式说明；
- **pre-commit 4.x stages 语义**：未声明 `stages` 的 hook 在 `--hook-stage manual` 下同样执行（默认含全部阶段），本地拦截 hook 与 manual 专用 SARIF hook 共存无冲突；
- **扫描非门禁**：bandit 检出问题退出码 1，扫描工作流捕获退出码后继续上传（`exit 0`），报告完整性优先；pre-commit 场景保持门禁语义（失败即拦截）；
- **SARIF 产出校验**：扫描后 `test -s` 校验报告非空，失败立即报错，避免被上传步骤的"路径不存在"误导。

### 2.6 验证情况

演示仓 `https://github.com/openlibing-test/bandit-full-scan-demo`（私仓，与插件仓可见性一致），三条 commit 迭代验证：

| 验证项          | 结果                                                                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Actions 运行    | `bandit-scan` / `bandit-precommit` 两条工作流均 success                                                                                                                                                 |
| 来源标记        | 日志 `[INFO] 来源标记: GITHUB_ACTION`                                                                                                                                                                   |
| OIDC 换证       | 提供商 `GitHubActions`、委托 `github-actions`，STS 换证成功                                                                                                                                             |
| OBS 上传        | 桶 `openlibing-github-action`，key 含 owner/repo/runId                                                                                                                                                  |
| 回调            | `/codescan/v1/result/receive` 返回 `{"code":200,"msg":"success"}`                                                                                                                                       |
| 结果集          | 全量扫描 14 条问题、10 类规则（B101/B104/B105/B110/B311/B324/B404/B501/B506/B602 等）；高危样例文件恰好 3 条 HIGH/HIGH（B605 os.system 命令注入、B701 jinja2 关闭自动转义、B501 requests 关闭证书校验） |
| 原生 SARIF 链路 | precommit 收集日志确认"bandit 已提供 sarif 文件，直接使用"，无兜底解析                                                                                                                                  |
| 严重度标定      | B301（pickle）、B506（yaml.load）在 bandit 1.9.4 已降为 MEDIUM，高危样例选型经本地实测校准                                                                                                              |

## 3. 类设计

本 US 无产品代码改动，不涉及类设计。演示仓关键构件：

| 构件                                     | 职责                                                                                                                                            |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `.bandit.yml`                            | 规则单一事实源（排除目录、全量规则口径，不做严重度过滤）                                                                                        |
| `.pre-commit-config.yaml`                | 默认 stage bandit hook（本地拦截）+ manual stage bandit-sarif hook（直出 SARIF，`additional_dependencies` 补齐 `sarif-om`/`jschema-to-python`） |
| `.github/workflows/bandit-scan.yml`      | 全量扫描入口（手动/push/定时）                                                                                                                  |
| `.github/workflows/bandit-precommit.yml` | pre-commit 集成入口（手动/push/PR 门禁）                                                                                                        |
| `demo/`                                  | 被扫样例：常规风险（B101/B104/B105/B311/B324/B506/B602/B110）+ 安全对照 + 高危样例（B605/B701/B501）                                            |

## 4. 数据模型设计

无新增数据模型。复用现有 `static_alarm_scan_run` 与问题明细存储：`category=business` / `pre-commit-report`、`source=GITHUB_ACTION`、`tool=Bandit`，与 clang-tidy/gosec/clippy 完全一致。

## 5. 性能设计

bandit 基于 AST 静态解析 Python 源码，无需编译数据库与构建产物，单仓扫描秒级至分钟级；workflow 使用 `actions/setup-python` 缓存 pip 依赖，pre-commit hook 环境首次构建后由 pre-commit 缓存复用。对 runner 资源无特殊要求（ubuntu-latest 托管池）。

## 6. API接口设计

无新增接口。复用两个既有 action 的输入契约：`upload-sarif-action`（`sarif_file`/`source_path`/`category`/`env_type`）与 `pre-commit-action`（`extra_args`/`report-dir`），以及 openLiBing 回调接口 `/codescan/v1/result/receive`。

## 7. 安全设计

- 认证链路全程 OIDC 免密换证，无静态 AK/SK；IAM 信任策略限定 `iss`/`aud`/`sub`，`pull_request` 形 sub 天然被拒；
- OBS 桶按平台隔离（`openlibing-github-action`），后端允许集合已含 GitHub 桶；
- 演示仓为私仓，恶意样例代码仅用于工具能力验证，README 显式声明请勿在生产代码参考；
- pre-commit 基础钩子含 `detect-private-key`，防止敏感信息随 demo 代码入库。
