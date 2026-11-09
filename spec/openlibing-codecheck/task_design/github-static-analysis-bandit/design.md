# 静态代码分析 GitHub 接入 · bandit — 设计文档

| 项           | 内容                                                        |
| ------------ | ----------------------------------------------------------- |
| 工具         | bandit（Python 安全静态扫描，基于 AST）                     |
| 平台         | GitHub Actions（openlibing-test 组织）                      |
| 演示仓       | `bandit-full-scan-demo`（openlibing-test 组织，私仓）       |
| 关联 FE 需求 | 静态代码分析 GitHub 接入方案与文档（clang-tidy 已落地范式） |
| 文档日期     | 2026-11-09                                                  |

---

## 1. 方案设计

### 1.1 需求背景

openLiBing 代码检查链路原以 GitCode Actions 为主：静态分析工具产出 SARIF → `upload-sarif-action` 上传 OBS → 回调平台 → 「开发管理 - 代码检查」页展示。FE 需求「静态代码分析 GitHub 接入」已由 clang-tidy 完成首个落地，沉淀了可复用范式：`GITHUB_ACTION` 来源枚举、前端平台筛选与来源标签、双插件（`upload-sarif-action` / `pre-commit-action`）的平台识别与 OIDC 免密换证。gosec、clippy、eslint 已先后复制该范式。

本方案将该范式复制到 **bandit**，补齐 Python 技术栈的安全静态扫描能力（硬编码密码、命令注入、不安全反序列化、弱哈希、关闭证书校验等风险检测）。

### 1.2 需求目标与验收标准

1. GitHub 平台可运行的 bandit 流水线，覆盖 **workflow 全量扫描** 与 **pre-commit 集成** 两种入口；
2. bandit 原生 SARIF 直出（零转换器、零预置二进制），上传 OBS 并回调 openLiBing，回调返回 200；
3. beta「代码检查」页按 GitHub 平台可筛选查看 bandit 问题列表、真实行号、源码片段与严重度标记（前端零改动）；
4. 沉淀 bandit 特有的 GitHub 侧差异经验（配置格式、插件参数兼容性）；
5. 设计文档归档 openlibing-docs 仓（本设计评审通过后执行）。

### 1.3 前置依赖（已就绪资产，全部复用）

| 依赖                                                                                  | 状态                        |
| ------------------------------------------------------------------------------------- | --------------------------- |
| 华为云 IAM `GitHubActions` 身份提供商 + `github-actions` 信任委托（限定 iss/aud/sub） | 已就绪（clang-tidy 时配置） |
| OBS 桶 `openlibing-github-action` + 后端桶白名单                                      | 已就绪                      |
| `upload-sarif-action`（GitHub 版，`source-platform-detection` 分支）                  | 已就绪，直接引用            |
| `pre-commit-action`（GitHub 版，main 分支）                                           | 已就绪，直接引用            |
| GitCode 侧 bandit 参照实现（`test-bandit-scan` 仓，bandit 1.9.4 直出 SARIF 链路）     | 已就绪，本方案同源移植      |

### 1.4 总体改造思路与职责划分

沿用「单份代码、运行时识别平台」原则，不为 GitHub 维护独立分支：

| 层                                              | 职责                                             | 改动                           |
| ----------------------------------------------- | ------------------------------------------------ | ------------------------------ |
| 演示仓 `bandit-full-scan-demo`                  | 被扫样例 + 规则单一事实源 + 两条 GitHub workflow | **新建**（本方案核心交付）     |
| `upload-sarif-action` / `pre-commit-action`     | 平台识别、OIDC 换证、OBS 上传、回调              | 零改动（引用既有分支）         |
| openlibing-codecheck 后端 / openlibing-web 前端 | 来源枚举、平台筛选、结果展示                     | 零改动（clang-tidy US 已交付） |
| openlibing-docs                                 | 本设计文档归档                                   | 后续 US                        |

业务配置（`.bandit.yml` 规则、扫描命令、pre-commit 钩子）在 GitCode 与 GitHub 完全复用，差异集中在 workflow 写法与插件引用。

### 1.5 关键选型与理由

| 决策点           | 选择                                            | 理由                                                                                            |
| ---------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 认证方式         | OIDC 免密换证（`GitHubActions` 提供商）         | 复用已打通链路，不落任何长期 AK/SK                                                              |
| OBS 桶           | GitHub 用 `openlibing-github-action`            | 与 GitCode 桶隔离，便于权限与成本归集（复用既有桶，无新增）                                     |
| SARIF 产出       | bandit 原生 `-f sarif` 直出                     | 零转换器、零预置二进制；依赖 `sarif-om` + `jschema-to-python` 随 `[sarif]` extra 安装           |
| 规则配置格式     | `.bandit.yml`（YAML）                           | bandit 1.9.x 的 `-c` 不再解析裸 `.bandit` INI 文件（实测报 YAML 解析错误），YAML 为官方现行格式 |
| 规则单一事实源   | 扫描工作流与 pre-commit hook 共用 `.bandit.yml` | 两端口径一致防规则漂移；版本锁定 1.9.4 与 GitCode 侧一致                                        |
| pre-commit SARIF | manual 阶段专用 hook 直出原生 SARIF             | 绕开 pre-commit-action 日志解析缺陷（行号进 uri、startLine 存列号、无 snippet）                 |
| 入口形态         | pre-commit 集成 + workflow 全量扫描并存         | 分别覆盖提交前拦截与全量归档场景                                                                |

### 1.6 涉及文件清单（演示仓）

| 文件                                     | 职责                                                                                                                                                                                                                   |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.bandit.yml`                            | 规则单一事实源：排除目录 + 全量规则口径（暂不做严重度过滤，正式启用建议两端同时收紧 `-ll -ii`）                                                                                                                        |
| `.pre-commit-config.yaml`                | 默认 stage bandit hook（本地拦截）+ manual stage `bandit-sarif` hook（直出 SARIF，`additional_dependencies` 补 `sarif-om`/`jschema-to-python`；不能写 `bandit[sarif]`——git 仓安装版本回落 0.0.0 会与 PyPI 同名包冲突） |
| `.github/workflows/bandit-scan.yml`      | 全量扫描：手动 / push main / schedule（5 位 POSIX cron）                                                                                                                                                               |
| `.github/workflows/bandit-precommit.yml` | pre-commit 集成：手动 / push main / PR 门禁                                                                                                                                                                            |
| `requirements.txt`                       | `bandit[sarif]==1.9.4`                                                                                                                                                                                                 |
| `demo/insecure_demo.py`                  | 常规风险样例（B101/B104/B105/B311/B324/B404/B506/B602/B110）                                                                                                                                                           |
| `demo/safe_demo.py`                      | 安全对照写法（预期通过）                                                                                                                                                                                               |
| `demo/high_risk_demo.py`                 | 高危样例：恰好 3 条 HIGH/HIGH——B605 os.system 命令注入、B701 jinja2 关闭自动转义、B501 requests 关闭证书校验                                                                                                           |

私有仓（与插件仓可见性一致）；样例代码仅用于工具能力验证，README 声明请勿在生产代码参考。

### 1.7 平台约束（沿承 clang-tidy/clippy 结论）

- 上传类工作流**不含 `pull_request` 触发**：IAM 信任策略仅放行 push 形 sub（`repo:<org>/<repo>:ref:refs/heads/<branch>`），`pull_request` 形 sub 换证被拒；
- precommit 工作流 PR 事件语义：纯门禁（钩子命中即失败拦截），跳过上传归档；push/手动为门禁 + 归档。

## 2. 实现逻辑设计

### 2.1 场景二主流程（workflow 全量扫描，非门禁）

```text
GitHub 代码仓触发 workflow（手动 / push main / 定时）
  → checkout → setup-python 3.12
  → pip install "bandit[sarif]==1.9.4"（回显 --version，安装失败立即暴露）
  → bandit -c .bandit.yml -r demo -f sarif -o <临时目录>/bandit.sarif
      捕获退出码；test -s 校验 SARIF 非空；检出问题仅日志提示，exit 0 继续
  → upload-sarif-action@source-platform-detection（category=business）
```

### 2.2 场景一主流程（pre-commit 集成，PR 纯门禁）

```text
GitHub 代码仓触发 workflow（手动 / push main / PR）
  → checkout → setup-python 3.12 → pip install pre-commit
  → mkdir -p 报告目录（GitHub 版插件不预创建，见 2.5）
  → pre-commit-action@main（--all-files --hook-stage=manual 收集原生 SARIF）
  → upload-sarif-action@source-platform-detection（category=pre-commit-report）
  PR 事件：纯门禁，跳过上传归档（无 OIDC 换证）
```

### 2.3 平台识别与上下文映射

由 `upload-sarif-action` 在运行时完成（clang-tidy US 已交付，本方案验证复用）：`GITHUB_ACTIONS=true` 识别平台，上报来源标记 `GITHUB_ACTION`，上下文映射 `pipelineId=GITHUB_JOB`、`pipelineRunId=GITHUB_RUN_ID`、`pipelineName=GITHUB_WORKFLOW`、`commitId=GITHUB_SHA`。

### 2.4 认证与上传链路

workflow 声明 `permissions: id-token: write` → GitHub Actions OIDC 接口申请 ID Token → 华为云 IAM `GitHubActions` 提供商 / `github-actions` 委托换 STS 临时凭证 → 上传 OBS 桶 `openlibing-github-action`（key 结构与 GitCode 桶一致：`bandit-results/{owner}/{repo}/{yyyyMMdd.HH}/{runId}/bandit.sarif`）→ 回调 openLiBing `/codescan/v1/result/receive`。全链路无静态 AK/SK。

### 2.5 异常与边界处理（实施实证）

| 边界                                             | 处理                                                                                                                                                                                |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub 版 pre-commit-action 的 `extra_args` 校验 | 按空格拆 token 且要求以 `--` 开头，`--hook-stage manual` 中 `manual` 被拒（`Invalid extra_args`）；必须用等号形式 `--hook-stage=manual`（argparse 兼容，单 token）                  |
| GitHub 版 pre-commit-action 不预创建 report 目录 | 目录缺失时 bandit `-o` 写文件直接失败（exit 2），插件静默退化为日志解析兜底 SARIF（问题数正确但元数据受损，难察觉）；workflow 必须先 `mkdir -p`。GitCode 版会预创建，两侧行为不一致 |
| bandit 1.9.x 配置格式                            | `-c` 仅支持 YAML/TOML，裸 `.bandit` INI 报 `expected '<document start>'`；配置命名 `.bandit.yml`                                                                                    |
| pre-commit 4.x stages 语义                       | 未声明 `stages` 的 hook 在 manual 阶段同样执行（默认含全部阶段），本地拦截 hook 与 manual 专用 SARIF hook 共存无冲突                                                                |
| 扫描非门禁                                       | bandit 检出问题退出码 1，扫描工作流捕获后继续上传（报告完整性优先）；pre-commit 场景保持门禁语义（失败即拦截）                                                                      |
| SARIF 产出校验                                   | 扫描后 `test -s` 校验报告非空，失败立即报错，避免被上传步骤的"路径不存在"误导                                                                                                       |
| 严重度标定                                       | B301（pickle）、B506（yaml.load）在 bandit 1.9.4 已降为 MEDIUM，高危样例选型经本地实测校准                                                                                          |

### 2.6 验证情况

演示仓四个 commit 迭代（初始 → 修复 extra_args → 修复 report 目录 → 追加高危样例），全链路核对结果：

| 检查点          | 结果                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| Actions 运行    | `bandit-scan` / `bandit-precommit` 均 success                          |
| 来源标记        | 日志 `[INFO] 来源标记: GITHUB_ACTION`                                  |
| OIDC 换证       | 提供商 `GitHubActions`、委托 `github-actions`，STS 换证成功            |
| OBS 上传        | 桶 `openlibing-github-action`，key 含 owner/repo/runId                 |
| 回调            | `/codescan/v1/result/receive` 返回 `{"code":200,"msg":"success"}`      |
| 原生 SARIF 链路 | precommit 收集日志确认"bandit 已提供 sarif 文件，直接使用"，无兜底解析 |
| 结果集          | 全量 14 条问题、10 类规则；高危样例恰好 3 条 HIGH/HIGH                 |

## 3. 类设计

本方案无产品代码改动，不涉及类设计（原因：全部改动为演示仓的 workflow/配置/样例代码，平台侧能力复用 clang-tidy US 交付成果）。演示仓关键构件及职责见 1.6 文件清单。

## 4. 数据模型设计

不涉及。无新增数据模型，复用现有 `static_alarm_scan_run` 与问题明细存储：`category=business` / `pre-commit-report`、`source=GITHUB_ACTION`、`tool=Bandit`，与 clang-tidy/gosec/clippy 完全一致。

## 5. 性能设计

bandit 基于 AST 静态解析 Python 源码，无需编译数据库与构建产物，单仓扫描秒级至分钟级，对 runner 资源无特殊要求（ubuntu-latest 托管池）。CI 侧依赖安装走 `actions/setup-python` + pip 直连 PyPI；pre-commit hook 环境首次构建后由 pre-commit 本地缓存复用，后续运行开销为秒级。

## 6. API 接口设计

无新增接口。复用两个既有 action 的输入契约：`upload-sarif-action`（`sarif_file`/`source_path`/`category`/`env_type`）与 `pre-commit-action`（`extra_args`/`report-dir`），以及 openLiBing 既有回调接口 `/codescan/v1/result/receive`（入参含 SARIF 对象 key、来源标记 `GITHUB_ACTION`、上下文映射字段，契约未变化）。

## 7. 安全设计

- **认证链路**：全程 OIDC 免密换证，无静态 AK/SK；IAM 信任策略限定 `iss`/`aud`/`sub`，`pull_request` 形 sub 天然被拒；
- **存储隔离**：OBS 桶按平台隔离（`openlibing-github-action`），后端允许集合已含 GitHub 桶；
- **演示代码风险**：恶意样例仅存于私仓 demo 目录，README 显式声明请勿在生产代码参考；
- **敏感信息防泄露**：pre-commit 基础钩子含 `detect-private-key`，防止私钥/凭证随样例代码入库；workflow 无残留 `OBS_AK`/`OBS_SK` 输入。
