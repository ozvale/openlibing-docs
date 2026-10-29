# fix-vuln-dependency-tree — 漏洞组件引用关系多根修复与语言能力提示

## 需求背景

oss-version-scan-action / oss-pr-scan-action（openlibing/trivy-action）的「组件引用关系」依赖树展示存在两类缺陷：

1. **多根场景漏展漏洞组件**：`shared/index.js` 的 `buildVulnDependencyTree` 只从 `Relationship==='root'` 或 `packages[0]` 展开**单棵**依赖树。该逻辑为 Maven 单根设计（pom 模式有唯一 root），但
   **pnpm/npm/yarn 是"多根"结构**（150 个 direct 顶层包各自成树，无 root 关系），导致非首个根的漏洞组件（如 run204 的 node-forge、wangeditor）有漏洞明细却无引入链展示。
2. **severity 标注不准**：取"第一个匹配"漏洞级别，可能标低（如 run215 中 amqp-client 多漏洞本应 HIGH 却标 `[LOW]`）。

同时两类数据源限制需要向用户显性提示：

- Python `requirements.txt` 只有直接依赖，**无传递依赖、无依赖图、无 license** → 漏洞/引入链必然不完整；
- Node/pip 的 license 数据来自已安装目录（`node_modules` / `site-packages`），插件不执行依赖安装 → 这些语言 license 列可能为空。

关联业务 Issue：https://gitcode.com/openlibing/trivy-action/issues/2

## 功能描述

1. **方案 B 重构组件引用关系**：改为"漏洞驱动反向引入链"——从每个漏洞组件 BFS/DFS 反向找所有引入路径
   （终止于 root 或 direct 顶层），顶层相同的路径合并到同一棵树；无 DependsOn 的组件（Python）孤列。
2. **severity 标注**：漏洞组件取该组件**最高级别**漏洞（修 `[LOW]` 标成 `[HIGH]` 的 bug）。
3. **Python 依赖提示**：检测到 `requirements*.txt`/`Pipfile*`/`pyproject.toml` 时，在 Summary 概览与日志提示
   可通过 `pip freeze > requirements.lock` 或 `pip-compile` 生成全量 lock 获取更精准结果。
4. **README 语言能力说明**：补充无法直接解析许可证的语言（Node 需 node_modules、Python 需 site-packages），
   说明插件不执行依赖安装。

## 不做的事

- 不改变漏洞/license 门禁判定逻辑与阈值参数。
- 不在插件内执行依赖安装（pnpm install / pip install）。
- 不新增/不改变 action.yml 输入参数。
- 不改动 Python 漏洞检测本身（那是数据源问题，提示而非修复）。

## 验收标准

- [ ] 多根（pnpm/npm/yarn）场景下，每个漏洞组件均能展示引入链；顶层相同的路径合并
- [ ] Maven 单根场景输出与现状一致（root 树 + 各分支）
- [ ] severity 取组件最高级别（不再把 HIGH 标成 LOW）
- [ ] 无 DependsOn 组件（Python）孤列，不报错
- [ ] 检测到 Python 依赖文件时 Summary 与日志出现全量 lock 提示
- [ ] README（version + pr）补充许可证语言能力说明
- [ ] version/pr 两套单测全绿，dist 重建

## 影响范围

| 仓              | 文件                                                                 | 操作                                                                  |
| --------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| oss-scan-action | `shared/index.js`                                                    | 重构 buildVulnDependencyTree + dependencyTreeToText + Python 探测提示 |
| oss-scan-action | `oss-version-scan-action/test/*`                                     | 补单测                                                                |
| oss-scan-action | `oss-pr-scan-action/test/*`                                          | 补单测（共享函数）                                                    |
| oss-scan-action | `oss-version-scan-action/README.md` / `oss-pr-scan-action/README.md` | 语言能力说明                                                          |
| oss-scan-action | `dist/`（两插件）                                                    | ncc 重建                                                              |
| openlibing-docs | `spec/oss-scan-action/task_design/fix-vuln-dependency-tree/`         | 本 spec                                                               |
