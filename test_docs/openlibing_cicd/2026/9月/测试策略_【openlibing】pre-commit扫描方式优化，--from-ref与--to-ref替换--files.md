# 【openlibing】pre-commit扫描方式优化，--from-ref/--to-ref替换--files 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/pre-commit-action/issues/1
* **需求编号**: US20260901450773
* **需求名称**: 【openlibing】pre-commit扫描方式优化，--from-ref/--to-ref替换--files
* **核心目标**:
  验证 openlibing-pre-commit-action 插件（dev 分支 v1.0.33）将 PR 事件下扫描文件的获取方式由 `git diff` 显式文件列表（`pre-commit run --files`）切换为 pre-commit 原生区间参数（`pre-commit run --from-ref FETCH_HEAD --to-ref HEAD`）后：增量检查文件范围的正确性、各事件触发链路（pull_request / pull_request_comment / 非 PR 事件 / extra_args）的兼容性、边界场景（空变更 PR、目标分支演进、大量变更文件、浅克隆 merge-base）的稳定性，以及扫描效率的提升效果。
* **开发责任人**: 马菲飞
* **测试责任人**: 刘东方

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在"第 3 节"提供对应的测试用例或方案。

* [x] **功能自检测试**

> * **测试重点：** `--from-ref FETCH_HEAD --to-ref HEAD` 增量检查主路径、违规文件拦截与修复闭环、空变更 PR（skip 逻辑删除后的行为）、目标分支演进下 diff 语义变化、非 PR 事件全量检查回归、extra_args 自定义参数与白名单校验回归。
>* **目的：** 确保扫描方式切换后增量检查范围准确、既有触发链路行为不回退。
>* **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

* [ ] **体验测试**

> * **测试重点：** 站在用户角度进行体验使用，验证产品是否符合用户习惯。
>* **目的：** 满足用户需求，超出用户期望；判定产品是否能让用户快速的接受和使用。
>* **触发条件：** 需求标签含 `need_experience`

* [ ] **集成测试**

> * **测试重点：** 跨服务调用链路验证、上下游数据最终一致性、数据库/中间件版本兼容性。
>* **目的：** 消除组件间级联影响风险。
>* **触发条件：** 需求标签含 `need_itest`

* [ ] **安全与隐私测试**：

> * **测试重点：** 鉴权绕过测试、SQL/命令注入、敏感数据（PII）日志脱敏校验、SBOM 依赖漏洞扫描。
>* **目的：** 验证"纵深防御"机制是否生效，确保无隐私泄露。
>* **触发条件：** 需求标签含 `need_security`

* [ ] **可靠性与韧性测试**

> * **测试重点：** 故障注入（Chaos）。模拟网络丢包/延迟、进程意外溢出、磁盘 IO 满载后等异常情况下的系统自愈行为。
>* **目的：** 验证架构设计中的"面向失败设计"等能力。
>* **触发条件：** 涉及核心Core服务变更,且架构设计含可靠性与韧性设计。

* [ ] **可服务性与可观测性测试**

> * **测试重点：** 告警有效性验证、指标准确性抽检、排障手册实操演练、优雅停机验证。
>* **目的：** 确保系统"可感知、可定位、可维护"。
>* **触发条件：**  涉及核心Core服务变更,且架构设计含可服务性与可观测性设计。

* [x] **性能与伸缩性测试**

> * **测试重点：** 大量变更文件（500+）场景下新旧版本扫描耗时对比（`@master` v1.0.32 vs `@dev` v1.0.33），验证效率提升目标达成且无命令行参数长度（ARG_MAX）风险。
>* **目的：** 验证本次优化的核心收益——扫描效率提升。
>* **触发条件：** 需求目标为效率优化，需提供量化对比数据。

---

## 3. 专项验证设计和执行详情

> 测试自检
>* [ ] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果？
>* [ ] **证据留存**: 关键测试（如性能、安全扫描）是否附带了截图或报告链接？

### 3.0 测试环境说明

* 选一个 GitCode 测试仓库，包含与插件仓库 dev 分支同款的 `.pre-commit-config.yaml`（trailing-whitespace / end-of-file-fixer / check-yaml / check-json / gitleaks / prettier）。
* 测试仓库 workflow 使用 `uses: openlibing/openlibing-pre-commit-action@dev`，触发事件覆盖 `pull_request`、`pull_request_comment`（评论 `pre-commit`）、push（非 PR 事件）。
* 在测试仓库 `.pre-commit-config.yaml` 中追加"文件回显"调试钩子，使被检查的文件范围在流水线日志中直接可见：
  ```yaml
  - repo: local
    hooks:
      - id: debug-files
        name: debug checked files
        entry: xargs -n1 echo "[CHECKED-FILE]"
        language: system
  ```
* 测试前冒烟：确认 dev 分支 `dist/index.js` 已重新构建且与 `index.js` 逻辑一致。

### 3.1 功能测试专项

> 参考测试设计方向
> * 增量主路径：`--from-ref FETCH_HEAD --to-ref HEAD` 下被检查文件集合与 PR 变更文件集合一致。
> * 违规拦截与闭环：违规文件被准确拦截，修复后流水线重跑通过。
> * 边界回归：空变更 PR、目标分支演进（merge-base 三点 diff 语义）、非 PR 全量、extra_args 白名单。

**1.PR增量检查_正常通过（主路径）**:

* **步骤一**：从 master 拉取 `feature/tc1` 分支，合规修改 1~2 个文件（如新增格式正确的 `.md`、修改合法 yaml），提 PR 触发流水线
* **预期结果**: 日志出现 `[INFO] 使用 --from-ref FETCH_HEAD --to-ref HEAD 增量检查`，执行命令为 `python -m pre_commit run --from-ref FETCH_HEAD --to-ref HEAD`，流水线成功并输出 `[OK] pre-commit 检查通过`
* **步骤二**：通过调试钩子回显查看被检查的文件列表
* **预期结果**: 仅 PR 变更文件被检查，未变更文件不在检查范围内

**2.PR存在违规文件_拦截与修复闭环**:

* **步骤一**：`feature/tc2` 分支新增带尾随空格、缺文件末尾换行的文件，并放置模拟私钥片段（触发 gitleaks），提 PR
* **预期结果**: 流水线失败，退出码 1，失败提示中显示 `pre-commit run --all-files` 修复指引
* **步骤二**：推送修复 commit（消除违规）后观察流水线自动重跑
* **预期结果**: 重跑通过，完整闭环正常

**3.PR空变更_跳过路径删除后的行为回归**:

* **步骤一**：`feature/tc3` 分支提交一个 commit 后再 revert 同一变更，使 merge_commit_sha 与目标分支内容一致（diff 为空），提 PR
* **预期结果**: 流水线成功。旧版日志为"PR 无变更文件，跳过增量检查"；新版应真实执行 pre-commit 且各钩子 0 文件通过，无异常报错

**4.目标分支演进_diff语义验证**:

* **步骤一**：基于 master@A 创建 `feature/tc4`，合规修改文件 X，提 PR 并保持打开
* **步骤二**：向 master 推送新 commit B：修改文件 Y（故意保留尾随空格等违规）
* **预期结果**: 文件 Y 不在本次 PR 检查范围内
* **步骤三**：在 PR 中评论 `pre-commit` 重新触发流水线
* **预期结果**: 仅检查文件 X，不检查文件 Y，流水线成功（同时回归 note 评论触发链路）；若检查了 Y，记录实际行为并评估三点/两点 diff 语义差异是否可接受

**5.非PR事件_全量检查回归**:

* **步骤一**：测试仓库 workflow 增加 push 触发，直接 push 到 master
* **预期结果**: 日志输出 `[INFO] 非 PR 事件，使用 --all-files 检查全量文件`，全量检查行为与旧版一致（该路径未被本次修改改动）

**6.extra_args自定义参数_优先级与白名单回归**:

* **步骤一**：测试 workflow 配置 `extra_args: --all-files`，提一个含违规文件的 PR
* **预期结果**: 自定义参数优先生效，按全量检查执行
* **步骤二**：配置非法参数 `extra_args: xx`（非白名单非 `--` 参数）
* **预期结果**: 白名单校验生效，输出 `[ERROR] Invalid extra_args` 并退出（校验逻辑未被改动，防回归）

**7.浅克隆_merge-base可用性探测**:

* **步骤一**：在测试 workflow 的 checkout 与 run pre-commit 步骤之间插入调试步骤：`git rev-parse --is-shallow-repository` 与 `git merge-base FETCH_HEAD HEAD`
* **预期结果**: merge-base 可正常解析。若输出 `NO_MERGE_BASE`，说明浅克隆环境下 `FETCH_HEAD...HEAD` 三点 diff 会失败，属于阻塞问题（修复方向：fetch 时 `--unshallow` 或显式 diff 文件列表）

### 3.2 性能与伸缩性测试专项

**1.大量变更文件_效率对比与稳定性**:

* **步骤一**：脚本生成 500+ 合规变更文件的 PR（覆盖深层目录、重命名文件、含空格/中文的文件名）
* **预期结果**: 流水线成功；重命名文件仅新路径被检查；无命令行参数长度（ARG_MAX）问题（旧 `--files` 方式在该规模下存在风险）
* **步骤二**：同一 PR 分别使用 `@master`（v1.0.32）与 `@dev`（v1.0.33）各执行一次，记录 run pre-commit 步骤耗时
* **预期结果**: v1.0.33 耗时不高于 v1.0.32，输出量化效率对比数据作为需求收益证明

---
