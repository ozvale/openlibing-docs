# oss-version-scan-action — 技术设计

## 方案概述

版本级插件与 PR 级插件复用同一套 trivy 扫描 + 判定核心逻辑。为消除重复代码，
抽取 `shared/index.js` 作为共享门禁引擎，`oss-pr-scan-action` 与
`oss-version-scan-action` 均为薄封装入口，仅差 action 元数据与 logPrefix。

## 架构决策

| 决策         | 选择                                                     | 原因                                                         |
| ------------ | -------------------------------------------------------- | ------------------------------------------------------------ |
| 共享核心     | `shared/index.js`（扫描/解析/判定/summary）              | PR/version 逻辑一致，单一维护点，杜绝重复代码                |
| 插件入口     | 薄封装 `index.js`：`scan({logPrefix})`                   | 两插件仅差标识，入口最小化                                   |
| 代码获取     | workflow 层 `checkout` 插件                              | 版本级扫全量分支，checkout `ref` 指定分支；插件不做 git 操作 |
| token        | 不接收 token 输入                                        | checkout 已用 `secrets.ROBOT_TOKEN`，插件无需再传            |
| 漏洞库       | 复用 runner 预置 /opt cache-dir，不传 `--skip-db-update` | 与 PR 级一致，trivy 自动更新                                 |
| create-issue | **不实现**                                               | 建 issue 与扫描门禁解耦，按需独立设计                        |
| 触发         | 自测：`workflow_dispatch`；正式：`schedule`              | 开发期手动验证，正式接入定时                                 |
| runs-on      | `["self-hosted","region=overseas","oss=version"]`        | 版本级执行机标签                                             |

## 涉及文件

| 文件                                      | 操作                         | 说明                                        |
| ----------------------------------------- | ---------------------------- | ------------------------------------------- |
| `shared/index.js`                         | 新增                         | 共享门禁引擎（从 oss-pr-scan-action 抽离）  |
| `oss-pr-scan-action/index.js`             | 重构（改薄入口 + 引 shared） | 行为不变，单测回归                          |
| `oss-version-scan-action/action.yml`      | 新增                         | 插件元数据（inputs = PR 级同款）            |
| `oss-version-scan-action/index.js`        | 新增                         | `scan({logPrefix:'oss-version-scan'})`      |
| `oss-version-scan-action/package.json`    | 新增                         | `@actions/core` + `@vercel/ncc`             |
| `oss-version-scan-action/test/*.test.js`  | 新增                         | 复用 shared 纯函数单测                      |
| `oss-version-scan-action/README.md`       | 新增                         | 使用文档                                    |
| `.gitcode/workflows/oss-version-scan.yml` | 新增                         | workflow_dispatch（自测）/ schedule（预留） |

## shared 导出接口

```js
// shared/index.js
module.exports = {
  scan, // async run(meta) 主流程；meta.logPrefix 标识插件
  extractRiskCounts, // 解析 trivy JSON -> {vulnCount, licenseCount, vulnItems, licenseItems}
  judge, // 四级别门禁判定 -> {pass, block, warnExceeded}
  itemsToMarkdown, // 数组 -> Markdown 表格
  resolveConfig, // scan-target/cache-dir/trivy-config 解析与存在性校验
  buildTrivyArgs, // 组装 trivy fs 参数（对齐 scan_vuls.sh）
  runTrivyScan, // 执行扫描并重试
  findMavenProjectDir, // 查找含 pom.xml 的工程根目录（方案 A）
  runMavenResolve, // mvn 预解析传递依赖，先离线后在线，失败降级（方案 A）
  getTimestamp,
  sleepSync,
  trimInput,
  intInput,
  appendSummary, // 工具
};
```

## 核心流程（shared.scan）

```
1. 读 inputs（scan-target/trivy-config/cache-dir/8 个 *-limit 门禁参数/debug）+ meta.logPrefix
2. resolveConfig：解析路径 + 存在性校验
3. checkTrivy（trivy --version 探测）
4. runMavenResolve（方案 A）：含 pom.xml 时 mvn dependency:resolve 填充 ~/.m2
   （先离线后在线，超时 600s，失败降级）
5. runTrivyScan：trivy fs（vuln,license，不传 --skip-db-update，重试10次）
6. extractRiskCounts：四级别（CRITICAL/HIGH/MEDIUM/LOW）漏洞与 license 计数，UNKNOWN 不统计
7. judge：CRITICAL/HIGH 超门禁 -> no pass；MEDIUM/LOW 超门禁 -> warnExceeded 仅提示
8. appendSummary：扫描信息表 + 四级别计数表 + 明细表 + 结论（MEDIUM/LOW 超时加提示行）
9. no pass -> core.setFailed
```

## 版本级与 PR 级差异（仅这些）

| 维度          | oss-pr-scan                | oss-version-scan                              |
| ------------- | -------------------------- | --------------------------------------------- |
| 触发          | pull_request/push/dispatch | workflow_dispatch（自测）/schrequency（正式） |
| checkout 对象 | 预合并分支                 | 全量分支（workflow 指定 ref）                 |
| runs-on 标签  | `oss=pr`                   | `oss=version`                                 |
| logPrefix     | `oss-pr-scan`              | `oss-version-scan`                            |

## 风险 & 缓解

| 风险                 | 缓解                                                                                           |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| 重构 PR 级引入回归   | 抽取后跑 PR 级既有单测回归；行为不变                                                           |
| 版本级扫大仓耗时     | 与 PR 级相同重试/超时机制；workflow timeout 兜底                                               |
| schedule 触发权限    | 自测仅 workflow_dispatch；正式 schedule 需注意默认分支与定时配置                               |
| pom 传递依赖解析漏检 | 与 PR 级一致：扫描前 `mvn dependency:resolve` 预填充 `~/.m2`（方案 A，先离线后在线，失败降级） |
| 执行机缺 Maven 环境  | 版本级机 a959 已装 JDK17+Maven3.9.9+ArtGalaxy 私仓配置并填充 `~/.m2`；PR 级机 7dbc 需同步部署  |

## 跨仓影响

- 不涉及其他仓；仅供目标仓 `.gitcode/workflows/` 接入。
- 生产接入待测试组织验证完成后另行 PR。
