# fix-vuln-dependency-tree — 技术设计

## 方案概述

将 `buildVulnDependencyTree` 从"单一 root 正向展开"改为"**漏洞驱动反向引入链**"：对每个漏洞组件，沿 `DependsOn` 反图 BFS/DFS 收集所有到 root/direct 顶层的路径，顶层相同则合并；无引入链的组件孤列。同时新增 Python 依赖文件探测与提示，并在 README 补充许可证语言能力说明。

## 架构决策

### 决策 1：反向引入链 + 同根合并（核心）

原因：pnpm/npm/yarn 是"多根"依赖图（无 `Relationship==='root'`，各 direct 顶层独立成树），原单根展开必然漏漏洞组件。

```js
// 结构（兼容现有 dependencyTreeToText / Summary 消费）
// 返回 [{ root: '<name>:<ver>', nodes: [依赖树节点] }]；无链组件 { root: '<name>:<ver>' }
function buildVulnDependencyTree(resultJson, vulnItems) {
  // 1. 解包 Results
  // 2. 建反图 childID -> [parentID]（利用 Packages[].DependsOn）
  // 3. 定位每个漏洞组件所在包（pkg:installed 匹配 Name:Version）
  // 4. 对每个漏洞组件反向 BFS，终止条件：
  //      - 包 Relationship==='root'（Maven 单根）或
  //      - direct 顶层（Relationship==='direct' 且反图无父）
  // 5. 收集该漏洞全部路径，反转成正向 root->...->vuln
  // 6. 顶层同名的漏洞路径合并成同一棵树（公共前缀合并 + ID 环防护）
  // 7. severity 取该组件最高级别
  // 8. 无任何 DependsOn / 反图无父路径的漏洞组件 -> 孤列 { root }
}
```

### 决策 2：severity 取组件最高级别

原 `highKeyToSeverity` 用"第一个匹配"的 severity，多漏洞组件会标低（run215 amqp-client：有 HIGH 却标 `[LOW]`）。改为遍历组件全部漏洞，取最高级别（CRITICAL>HIGH>MEDIUM>LOW）标注。

### 决策 3：Python 依赖文件探测与提示（纯提示，不修复）

`scan()` 中新增轻量探测（浅层遍历 scanTarget，复用 findMavenProjectDir 思路）：

```js
function findPythonDepFiles(scanTarget) {
  // 检测 requirements*.txt / Pipfile* / pyproject.toml / poetry.lock，返回匹配文件相对名列表
}
```

命中时：

- Summary 概览表后追加提示块（markdown）
- `core.info` 日志输出同文案
- 文案建议执行 `pip freeze > requirements.lock` 或 `pip-compile -o requirements.lock requirements.txt`

要点：这是**数据源限制的显性提示**，不改漏洞检测；探测浅层（默认 maxDepth 4），开销可忽略。

### 决策 4：README 语言能力说明

在两个插件 README「前提：runner 环境」或新增小节说明：

- Node（pnpm/npm/yarn）：组件/漏洞来自 lockfile；**license 需要已安装的 `node_modules`**，插件不执行安装 → license 列可能为空
- Python（pip）：漏洞仅覆盖 requirements 直接依赖；**license 需要已安装 `site-packages`**；引入链无数据源
- 指引"需要完整 license/引入链时使用方自行保障安装或构建期产出 SBOM"

## 涉及文件

| 文件                                     | 操作 | 说明                                                             |
| ---------------------------------------- | ---- | ---------------------------------------------------------------- |
| `shared/index.js`                        | 修改 | 重构 buildVulnDependencyTree；新增 findPythonDepFiles 与提示插入 |
| `shared/index.js`                        | 修改 | dependencyTreeToText 支持孤列节点（root 无 nodes）               |
| `oss-version-scan-action/README.md`      | 修改 | 语言能力说明                                                     |
| `oss-pr-scan-action/README.md`           | 修改 | 同                                                               |
| `oss-version-scan-action/test/*.test.js` | 修改 | 补方案B单测                                                      |
| `oss-pr-scan-action/test/*.test.js`      | 修改 | 补共享函数单测                                                   |
| `oss-scan-action` `dist/`（两插件）      | 修改 | ncc 重建                                                         |

## 风险 & 缓解

| 风险                                     | 缓解                                                      |
| ---------------------------------------- | --------------------------------------------------------- |
| 多根图展开性能                           | 仅沿漏洞反查，不遍历全图；路径去重 + ID 环防护            |
| pnpm 部分包无 DependsOn（817/1801 实测） | 无链漏洞孤列展示，不虚假合成路径                          |
| 反向 BFS 路径爆炸（多父组件）            | 限制每漏洞保留路径数（如上限 20）+ 深测护                 |
| 返回结构变化破坏现有测试                 | 保留 `[{root,nodes}]` 契约，dependencyTreeToText 兼容孤列 |

## 跨仓影响

无接口契约变化；仅 oss-scan-action 内部展示逻辑与提示增强。docs spec 随本分支归档。
