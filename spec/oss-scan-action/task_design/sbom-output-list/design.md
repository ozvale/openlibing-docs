# sbom-output-list — 技术设计

## 方案概述

复用 trivy fs 的 JSON 结果（`Results[].Packages[]`），解析出开源软件清单，按 `sbom-output`（list 开关）与 `sbom-output-type`（table/code）参数决定是否/如何输出到 Step Summary 与插件日志。不新增任何 trivy 调用。

## 架构决策

### 决策 1：数据源 = 现有 fs JSON 结果，而非额外 SBOM 命令

- 理由：`Results[].Packages[]` 已含 `Name`/`Version`/`Identifier.PURL`/`Relationship`，实测 272 组件完整可提取；且 `trivy fs --format json` 本就是插件现用输出格式（`runTrivyScan` 的 resultFile）。
- 收益：零新增 trivy 调用，性能开销可忽略（纯内存解析）。

### 决策 2：参数解析语义

```js
// sbom-output：null|list（其余文本等同 null，为 sbom 模式预留）
sbomOutput: trimInput('sbom-output', 'null'),
// sbom-output-type：table|code（仅 sbom-output=list 生效），默认 table
sbomOutputType: trimInput('sbom-output-type', 'table'),
// 判定
const outputList = config.sbomOutput === 'list';
const isTable = config.sbomOutputType === 'code' ? false : true; // 仅 code 非 table
```

### 决策 3：输出位置（不落盘）

| 位置                            | 内容                               |
| ------------------------------- | ---------------------------------- |
| Step Summary（`appendSummary`） | 统计行 + 清单；≥500 行截断并提示   |
| 插件日志（`core.info`）         | 全量清单（GitCode job 日志可回放） |

> 不落盘原因：GitCode 用户无法预览 runner 落盘文件；清单长度可预知（200-300 行量级），Summary + 日志足够承载。

### 决策 4：清单生成函数（shared 新增、可单测）

```js
/** 从 trivy fs JSON 提取全部组件（去重，按 Name 排序）。返回 [{ name, version, relationship, purl }] */
function extractPackageList(resultJson) { ... }

/** 生成为 markdown 表格文本 */
function packageListToTable(pkgs) { ... }

/** 生成为代码块文本（text 围栏内） */
function packageListToCode(pkgs) { ... }
```

- `extractPackageList`：便利每个 `Results[]` 里 `Packages`，收集 `Name`/`Version`/`Relationship`/`Identifier.PURL`；按 `Name` 去重（同一组件名取第一个）+ 按名称排序。
- 输出含头部统计：`组件总数：N（direct X / indirect Y）`。

### 决策 5：插入位置（scan() 主流程）

在扫描统计与明细输出之后、最终 pass/fail 判定之前（约 `shared/index.js:712` 附近）插入：

```js
if (outputList) {
  const pkgs = extractPackageList(parsed);
  const summaryBlock = isTable
    ? packageListToTable(pkgs)
    : packageListToCode(pkgs);
  appendSummary(summaryBlock); // Summary：截断到 500 行
  core.info(tag + " 开源软件清单(全量):\n" + summaryBlock); // 日志：全量
}
```

截断逻辑内置于 `packageListToTable/Code`：行数 `> 500` 时只输出前 500 行 + 提示行。

## 涉及文件

| 文件                                                                | 操作 | 说明                                                      |
| ------------------------------------------------------------------- | ---- | --------------------------------------------------------- |
| `shared/index.js`                                                   | 修改 | 新增 3 个函数 + scan() 中参数解析与输出插入；exports 增加 |
| `oss-pr-scan-action/action.yml`                                     | 修改 | inputs 新增 `sbom-output`、`sbom-output-type`             |
| `oss-version-scan-action/action.yml`                                | 修改 | 同上                                                      |
| `oss-pr-scan-action/test/test-oss-pr-scan-action.test.js`           | 修改 | 新增单测                                                  |
| `oss-version-scan-action/test/test-oss-version-scan-action.test.js` | 修改 | 新增单测                                                  |
| `oss-pr-scan-action/README.md`                                      | 修改 | 参数说明                                                  |
| `oss-version-scan-action/README.md`                                 | 修改 | 参数说明                                                  |
| `dist/`（两插件）                                                   | 修改 | ncc 重建                                                  |

## 风险 & 缓解

| 风险                          | 缓解                                                       |
| ----------------------------- | ---------------------------------------------------------- |
| Package 结构随 trivy 版本变化 | 兼容 `Name`/`Version` 缺失时降级跳过；单测用真实 JSON 样例 |
| Summary 过长                  | 500 行截断内置                                             |
| 重复组件名（不同源）          | 按 `Name` 去重（直接依赖优先）                             |

## 跨仓影响

无接口契约变化；仅 oss-scan-action 内部加能力。docs spec 随本分支归档。
