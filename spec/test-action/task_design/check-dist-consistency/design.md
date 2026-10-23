# test-action 插件 dist 一致性校验流水线 — 技术设计

> 来源：`openlibing/test-action` commit `3307ebfdc45402dd99979e04b6157250a55a0fe7`
> （`ci(check-dist): 新增插件 dist 与源码重建一致性校验流水线`）。
> 源文件：[.gitcode/workflows/check-dist.yml](https://gitcode.com/openlibing/test-action/blob/3307ebfdc45402dd99979e04b6157250a55a0fe7/.gitcode/workflows/check-dist.yml)。
> 本文档为该 GitCode Actions 工作流的设计归档，覆盖方案设计、架构决策、实现逻辑、配置与数据契约、一致性算法、性能、安全七个维度。

## 方案概述

`test-action` 仓是一个多插件仓，收录 5 个 GitCode Actions 插件（`metadata-collect`、`precision-test`、`pytest-orch`、`test-result-display`、`upload-reports`）。每个插件均以 `@vercel/ncc` 将源码打包成单文件 `dist/index.js` 并**随仓提交**，供消费方 workflow 以 `uses: ./<plugin>` 直接引用。这意味着 `dist/` 是「提交产物 = 运行产物」的契约，一旦源码改动后忘记重建并提交 `dist/`，运行时执行的就是过期代码。

本工作流 `check-dist.yml` 是一条**只读校验流水线**，在每次源码或 `dist/` 变更时触发，对每个插件从源码重建 `dist/`，并与仓库中已提交的 `dist/` 做字节级比对：

1. 检出代码（PR 事件检出预合并 commit，push 事件默认检出）。
2. 安装 Node 16 并启用 npm 依赖缓存。
3. 逐个插件执行 `npm ci && npm run build` 重建 `dist/`。
4. 用 `git add` 暂存重建结果，再用 `git diff --cached` 与 HEAD 比对，差异即「提交的 dist 与源码不一致」。
5. 收集全部失败插件，末尾统一 `exit 1`，任一插件不一致即流水线失败。

目标是把「忘记重建 dist」「手改 dist」「本地环境漂移导致 dist 不一致」这三类问题挡在合入前。

## 架构决策

| 决策        | 选择                                                 | 原因                                                                                         |
| ----------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 触发事件    | `push` + `pull_request_target` + `workflow_dispatch` | push 守主干；PR 守贡献者分支合入；dispatch 支持手动复跑与环境变更后回归                      |
| PR 事件类型 | `pull_request_target`（非 `pull_request`）           | 工作流文件本身始终读默认分支（master）最新版本，PR 无法通过改 yml 来弱化或绕过校验           |
| PR 检出对象 | `merge_commit_sha` → `head.sha` → `''` 三级回退      | 优先校验「PR 与目标分支合并后的最终代码」，冲突无法预合并时回退 head，push 事件回退默认检出  |
| 路径过滤    | 5 个插件目录 `/**` + 本 yml                          | 仅在相关产物变更时触发，避免无关改动浪费执行机资源                                           |
| 比对方式    | `git add dist/` → `git diff --cached`                | 重建覆写工作区后暂存到 index，与 HEAD（已提交）比对，借用 git 自身 diff 引擎免写专用比对脚本 |
| 差异容忍    | `--ignore-space-at-eol`                              | 规避行尾空白（CRLF/LF 跨平台）造成的假阳性，关注实质字节差异                                 |
| 失败策略    | `set +e` + `FAILED` 累积 + 末尾统一失败              | 「报告全部」而非「快速失败」，一次跑完所有插件，贡献者一轮看到所有需重建的插件               |
| 权限        | `repository: read`                                   | 校验只需读源码 + 本地重建，不回写仓库、不碰密钥，最小权限                                    |
| 运行机      | `runs-on: [default]`                                 | 复用 GitCode 默认执行机池，无需自建                                                          |
| 日志注解    | `::group::` / `::error::` / `::notice::`             | 在 PR 检查 UI 折叠日志、高亮失败插件、给出一致项 notice，降低人工排查成本                    |

## 涉及文件

| 文件                                | 操作 | 说明                                                                       |
| ----------------------------------- | ---- | -------------------------------------------------------------------------- |
| `.gitcode/workflows/check-dist.yml` | 新增 | 唯一变更文件，单 job `check-dist`，含 checkout / setup-node / 重建比对三步 |

工作流为纯新增，不修改任何插件源码或 `dist/`。被校验的 5 个插件及其构建工具链如下（构建命令取自各自 `package.json#scripts.build`）：

| 插件                  | 入口                    | build 命令                                                   | 产物                                  |
| --------------------- | ----------------------- | ------------------------------------------------------------ | ------------------------------------- |
| `metadata-collect`    | TypeScript `src/`       | `tsc && ncc build dist/index.js --license licenses.txt`      | `dist/index.js` + `dist/licenses.txt` |
| `precision-test`      | `index.js` + `src/*.py` | `ncc build index.js ...` + `cp src/*.py dist/test_selector/` | `dist/index.js` + 内嵌 python 资源    |
| `pytest-orch`         | `index.js`              | `ncc build index.js --license licenses.txt --asset-builds`   | `dist/index.js` + licenses            |
| `test-result-display` | `index.js`              | `ncc build index.js --license licenses.txt`                  | `dist/index.js` + licenses            |
| `upload-reports`      | `index.js`              | `npm ci && ncc build index.js --license licenses.txt`        | `dist/index.js` + licenses            |

五者均以 `@vercel/ncc` 打包为单文件，`dist/` 目录即提交产物。

## 实现逻辑设计

### Job 结构

```text
job: check-dist  (runs-on: [default], permissions: repository: read)
  ├ Step 1  Checkout      ref = merge_commit_sha || head.sha || ''
  ├ Step 2  Setup Node    node-version: 16, cache: true
  └ Step 3  Rebuild & verify   单 run 脚本，循环 5 个插件
```

### Step 3 校验循环（核心算法）

```text
set +e                                  # 关闭 errexit，允许单插件失败继续
PLUGINS="metadata-collect precision-test pytest-orch test-result-display upload-reports"
FAILED=""
for plugin in $PLUGINS; do
  ::group:: Rebuild dist: $plugin
  ├ (cd "$plugin" && npm ci && npm run build)   # 重建：工作区 dist/ 被覆写
  │   └ 失败 → 记 $plugin 到 FAILED，continue（跳过比对）
  ├ git add -- "$plugin/dist/"                  # 把重建结果暂存进 index
  ├ git diff --cached --ignore-space-at-eol --quiet -- "$plugin/dist/"
  │   ├ exit 0 → ::notice:: 一致
  │   └ exit 1 → ::error:: 不一致；打印 diff --stat + diff 前 200 行；记 $plugin
  ::endgroup::
done
[ -n "$FAILED" ] → ::error:: 汇总 + exit 1
否则 → ::notice:: 全部一致
```

### 一致性比对原理

`git diff --cached` 比较的是 **index（暂存区）与 HEAD**：

1. `npm run build` 把重建产物写入工作区 `dist/`，此时 index 仍等于 HEAD（即已提交的 dist）。
2. `git add -- "$plugin/dist/"` 把工作区新产物读入 index，index 与 HEAD 出现差异。
3. `git diff --cached --quiet -- "$plugin/dist/"` 比对 index vs HEAD：
   - 完全相同 → exit 0 → 提交的 dist 与源码重建一致。
   - 有差异 → exit 1 → 提交的 dist 已过期/被手改。

`--ignore-space-at-eol` 屏蔽行尾空白差异；`--quiet` 抑制输出并以退出码判定；限定 path 为 `$plugin/dist/` 避免跨插件污染。

### 失败语义

- **构建失败**（`npm ci` 或 `npm run build` 出错）：记入 `FAILED`，跳过该插件比对，继续下一插件，末尾 `exit 1`。
- **比对失败**（dist 漂移）：记入 `FAILED`，打印 `diff --stat` 与前 200 行 diff 供定位，继续下一插件，末尾 `exit 1`。
- **全部一致**：仅发 `::notice::`，退出码 0。

`::group::` / `::endgroup::` 把每个插件的日志折叠为一个可展开块，`::error::` 在 PR 检查页直接标红失败插件名。

## 配置与数据契约

### 触发契约

```yaml
on:
  push:
    branches: [main, master]
    paths: ["<plugin>/**" ×5, ".gitcode/workflows/check-dist.yml"]
  pull_request_target:
    branches: ["*"]
    paths: ["<plugin>/**" ×5, ".gitcode/workflows/check-dist.yml"]
  workflow_dispatch:
```

- `push` 仅在 `main`/`master`；`pull_request_target` 目标分支为任意（`"*"`）。
- 路径过滤覆盖 5 个插件目录全量 `/**`（源码 + dist + 配置）与 yml 自身；任何插件相关变更均触发。

### 检出 ref 表达式

```yaml
ref: ${{ atomgit.event.pull_request.merge_commit_sha
  || atomgit.event.pull_request.head.sha || '' }}
```

| 事件                 | 取值               | 语义                                               |
| -------------------- | ------------------ | -------------------------------------------------- |
| PR（可预合并）       | `merge_commit_sha` | 预合并后的 commit，校验「合入后的最终代码」        |
| PR（冲突无法预合并） | `head.sha`         | 回退到 PR head，仍能捕获 dist 漂移，但不反映合并态 |
| push                 | `''`（空）         | checkout 默认检出当前分支                          |

上下文变量用 `atomgit.event.*`（GitCode Actions 等价于 GitHub 的 `github.event.*`）。

### 动作引用

`uses: checkout` / `uses: setup-node` 为 GitCode Actions 平台内置动作引用（非 `actions/checkout`），由平台解析。

### 插件清单契约

`PLUGINS` 变量为**硬编码空格分隔列表**，与仓库实际插件目录强耦合：新增/移除插件必须同步改 yml，否则新插件不被校验、已移除插件导致 `cd` 失败。该清单未做存在性校验。

## 性能设计

- **串行重建**：5 个插件顺序 `npm ci && npm run build`，无并发；单插件失败不阻断后续，保证一次跑完全部以汇总所有问题。
- **依赖缓存**：`setup-node` 的 `cache: true` 启用 npm 缓存。**注意**：缓存键默认由**根目录** `package-lock.json` 派生，而实际 `npm ci` 发生在各插件子目录（各自有独立 `package-lock.json`），子目录依赖命中缓存的概率有限（见遗留项）。
- **重复安装**：`upload-reports` 的 `build` 脚本本身是 `npm ci && ncc build`，工作流外层再 `npm ci` 一次，对该插件 `npm ci` 执行两遍（幂等、无副作用，仅多耗一次安装时间）。
- **diff 输出截断**：漂移时仅打印前 200 行 diff（`| head -n 200`），避免超大产物差异刷爆日志。
- **可重建性依赖锁文件**：`npm ci` 严格按 `package-lock.json` 安装，ncc/tsc 版本被锁定，是跨环境重建结果可复现的前提；锁文件未提交或被改会导致重建漂移。

## 安全设计

### FIND-01 `pull_request_target` + 检出 PR 代码 + 执行构建的高危组合

`pull_request_target` 会用**默认分支（master）的工作流文件 + 默认分支的权限/密钥上下文**运行，而本工作流又显式 `ref` 检出** PR 的预合并代码**并执行 `npm ci && npm run build`。这正是社区反复警告的「pull_request_target 跑不受信代码」模式：

- `npm ci` 默认执行 `package.json` 的 `preinstall`/`postinstall` 等生命周期脚本（未加 `--ignore-scripts`）。
- `npm run build` 执行各插件 `build` 脚本（ncc/tsc/cp），脚本内容可被 PR 任意修改。
- 即贡献者可通过修改 `package.json` 在受信上下文里执行任意代码。

**现有缓解（已落地）**：

- `permissions: repository: read`，仅只读仓库，不写回、不引用任何 `secrets.*`，无密钥泄漏面。
- 工作流不产出任何 artifact、不回写仓库。

**残留风险**：

- 执行机为共享池 `runs-on: [default]`，不受信 install/build 脚本可污染共享 npm 缓存（`cache: true`）或工作区，影响后续 Job。
- 无网络隔离，恶意脚本可外联（虽无可窃取的密钥，但可探测内网或污染缓存）。

**建议缓解**：`npm ci` 改为 `npm ci --ignore-scripts` 以阻断 install 阶段生命周期脚本（build 脚本仍需执行，这是校验本质决定的，不可避）；或为该 Job 分配独立/沙箱执行机；或在 yml 注释中显式声明此风险已评估接受。

### FIND-02 权限最小化

`repository: read` 与「不引用任何 secret」共同把 blast radius 压到最低；即便不受信代码执行，也只能读 PR 作者本就可见的仓库内容。建议后续维持此约束：禁止给本 Job 加 `repository: write` 或注入密钥。

### FIND-03 缓存污染

`setup-node` 的 `cache: true` 在共享池上为跨 Job 共享缓存。若 FIND-01 的不受信脚本写入缓存，可影响同池后续 Job 的依赖完整性。缓解同 FIND-01（`--ignore-scripts` / 沙箱机）。

## 风险 & 缓解

| 风险                         | 缓解                                                                |
| ---------------------------- | ------------------------------------------------------------------- |
| PR 改 yml 弱化校验           | 用 `pull_request_target` 读 master 版 yml，PR 无法影响校验逻辑      |
| 忘记重建 dist                | 源码或 dist 变更即触发，重建后比对，漂移即失败                      |
| 手改 dist 偷跑               | 重建覆盖工作区 dist，与 HEAD 比对即暴露手改                         |
| 跨平台行尾差异假阳           | `--ignore-space-at-eol` 屏蔽行尾空白                                |
| 单插件失败掩盖后续问题       | `set +e` + 累积 `FAILED`，一次报告全部失败插件                      |
| 新增插件未被校验             | `PLUGINS` 硬编码，需手动同步（见遗留项）                            |
| 共享执行机被不受信脚本污染   | 读权限 + 无密钥限制爆炸半径；建议 `--ignore-scripts`/沙箱（见安全） |
| ncc/tsc 版本漂移致重建不一致 | `npm ci` 严格按锁文件安装，锁文件未提交即漂移                       |

## 跨仓影响

- 仅作用于 `openlibing/test-action` 仓内部，不修改任何插件源码或 dist。
- 不涉及其他仓；本流水线为该仓自管的 CI 门禁，消费方 workflow 不感知。
- 若未来插件清单变更（新增/移除插件），需同步修改本 yml 的 `PLUGINS` 与 `paths` 过滤。

## 遗留项 / 后续跟进

以下问题在本次 commit 中**未处理**，建议单独提 issue 跟进：

1. **`PLUGINS` 硬编码**：插件清单写死在 yml，与实际目录强耦合且无存在性校验。建议改为动态枚举（遍历含 `action.yml` 的目录）或加目录存在性校验，避免新增插件漏检或移除插件后 `cd` 失败。
2. **Node 16 已 EOL**：`setup-node` 固定 `node-version: 16`，Node 16 早已停止维护；各插件 `engines` 亦标 `>=16.0.0`。建议评估升级到受支持 LTS（如 20）并回归 ncc 重建产物一致性。
3. **依赖缓存未命中子目录**：`cache: true` 默认按根 `package-lock.json` 派生缓存键，而安装发生在各插件子目录，子目录依赖缓存命中率有限。可改为对每个插件显式指定 `cache-dependency-path` 以提升命中率。
4. **`upload-reports` 重复 `npm ci`**：其 `build` 脚本自带 `npm ci`，工作流外层再 `npm ci` 一次。建议统一：要么工作流不跑 `npm ci` 改由 build 脚本自管（但破坏其他插件契约），要么把 `upload-reports` 的 build 脚本改为只 `ncc build`。
5. **`npm ci` 未加 `--ignore-scripts`**：install 阶段生命周期脚本在 `pull_request_target` 受信上下文执行（见 FIND-01），建议加 `--ignore-scripts` 收窄攻击面。
6. **缺单元/集成测试**：本流水线本身无回归测试，校验算法（git add + git diff --cached）的正确性依赖人工验证；可考虑补一个最小仓 fixture 做端到端断言。
7. **冲突 PR 回退 head.sha**：无法预合并时回退 head，校验的是 PR 孤立态而非合并态，可能漏掉合并引入的 dist 漂移；可在日志显式标注当前处于「回退态」以便排查。
