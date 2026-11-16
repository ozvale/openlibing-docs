# 单 Action 重构 — 技术设计

## 方案概述

将两个薄入口插件合并为根级单 Action：`action.yml` + `index.js` 按必填输入 `scan-type` 分发到 `shared.scan()`，统一根级构建、测试与产物。参照 `malicious-code-scan-action#28` 的结构，但保留 `scan-type` 必填（不做自动判断），SBOM 仅 version 可用。

## 目标目录结构

```text
trivy-action/
├── action.yml                 # 统一 Action 定义（scan-type 必填 + 全部输入）
├── index.js                   # 统一入口：scan-type 分发 pr/version
├── shared/index.js            # 共享门禁引擎（行为不变）
├── test/
│   └── test-oss-scan-action.test.js  # 合并后的单套测试
├── dist/
│   ├── index.js               # 根级 ncc 打包产物
│   └── licenses.txt
├── package.json               # 根级 build/test 脚本
├── package-lock.json
├── README.md                  # 单插件文档 + 迁移说明
└── .gitcode/workflows/        # oss-pr-scan / oss-version-scan / build / ut
```

## 架构决策

| 决策      | 选择                                                                                          | 原因                                                                                     |
| --------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 插件形态  | 根级 `action.yml` + `index.js` + 根 `dist/`                                                   | 单插件模式，消除两套重复产物                                                             |
| scan-type | 必填，仅 `pr` / `version`；非法直接失败                                                       | 避免事件差异导致误判；workflow 显式声明更可读                                            |
| 分发实现  | `resolveScanType()` 读取 `INPUT_SCAN-TYPE`，`run()` 分发                                      | 与 `@actions/core` 输入语义一致，单测可直接覆盖                                          |
| logPrefix | `pr` → `oss-pr-scan`；`version` → `oss-version-scan`                                          | 保留现有日志可辨识度                                                                     |
| SBOM 门控 | `shared.scan` 增加 `meta.scanType`；仅 `version` 读取 SBOM 输入，`pr` 强制 `'null'`/`'table'` | 满足“仅版本级可输出 SBOM”的决策，同时保持 shared 兼容旧调用（`scanType` 未传时行为不变） |
| 旧目录    | 删除                                                                                          | 与参考 PR 一致；旧引用通过 README 迁移说明处理                                           |
| 测试      | 合并为单套根级测试文件                                                                        | 用例大量重复，单套降低维护成本；保留 PR 集成与 version SBOM 用例                         |
| 构建      | 根 `npm run build`（ncc）                                                                     | 单次构建，CI 简化                                                                        |
| 测试脚本  | 根 `node --test`；UT workflow 用 `npx c8@10` 采集覆盖率                                       | 统一测试入口，c8 不进入 devDependency，避免额外锁文件变更                                |

## 接口设计

### action.yml（关键输入）

| 输入                               | 必填 | 默认             | 说明                            |
| ---------------------------------- | ---- | ---------------- | ------------------------------- |
| `scan-type`                        | 是   | —                | `pr` / `version`                |
| `scan-target`                      | 否   | `.`              | 扫描目录                        |
| `trivy-config`                     | 否   | runner 预置      | trivy 配置                      |
| `cache-dir`                        | 否   | runner 预置      | 漏洞库缓存                      |
| `vuln-*-limit` / `license-*-limit` | 否   | 现有默认值       | 门禁阈值                        |
| `show-all-vulnerabilities`         | 否   | `false`          | 展示全量漏洞                    |
| `sbom-output` / `sbom-output-type` | 否   | `null` / `table` | **仅 `scan-type=version` 生效** |
| `debug`                            | 否   | `false`          | 调试日志                        |

`runs.using: node16`，`runs.main: dist/index.js`（保持不变）。

### index.js

```js
function resolveScanType() {
  const type = (process.env["INPUT_SCAN-TYPE"] || "").trim().toLowerCase();
  if (type === "pr" || type === "version") return type;
  throw new Error("scan-type 必填，仅支持 pr / version");
}

async function run(scanFn = scan) {
  const scanType = resolveScanType();
  await scanFn({
    logPrefix: scanType === "pr" ? "oss-pr-scan" : "oss-version-scan",
    scanType,
  });
}
```

错误通过 `::error::` + `process.exitCode = 1` 处理；导出 `run` / `resolveScanType` 供单测；`scanFn` 可注入供测试，生产默认使用 `shared.scan`。

### shared/index.js

`scan(meta)` 中 SBOM 配置改为：

```js
sbomOutput: meta.scanType === 'pr' ? 'null' : trimInput('sbom-output', 'null'),
sbomOutputType: meta.scanType === 'pr' ? 'table' : trimInput('sbom-output-type', 'table'),
```

- `scanType === 'version'` 或未传（单测/旧调用）→ 保持原逻辑；
- `scanType === 'pr'` → 强制关闭 SBOM。

## workflow 迁移

| workflow               | 旧                                                             | 新                                                                    |
| ---------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------- |
| `oss-pr-scan.yml`      | `uses: openlibing/trivy-action/oss-pr-scan-action@master`      | `uses: openlibing/trivy-action@v1.4`（PR 自测）+ `scan-type: pr`      |
| `oss-version-scan.yml` | `uses: openlibing/trivy-action/oss-version-scan-action@master` | `uses: openlibing/trivy-action@v1.4`（PR 自测）+ `scan-type: version` |
| `build.yml`            | 循环两个子目录 `npm ci && npm run build`                       | 根目录单次                                                            |
| `ut.yml`               | 循环两个子目录 + 两文件 `node --test`                          | 根目录 `npm ci` + 单套测试                                            |

## 测试设计

合并 `test-oss-pr-scan-action.test.js` 与 `test-oss-version-scan-action.test.js`：

1. 公共用例去重（解析/判定/转义/日志/Python/前端/临时文件/安全提示）。
2. 保留 PR 侧 `scan()` 集成测试（正常/show-all/阻断/无结果/trivy 缺失/非法 JSON）。
3. 保留 version 侧 SBOM/清单/依赖树用例。
4. 新增：
   - `resolveScanType`：合法 pr/version、缺失/非法抛错；
   - SBOM 门控：`scanType=pr` + `sbom-output=list` 不输出清单；`scanType=version` 输出清单。
5. 测试文件位于根 `test/`，import `../shared/index.js`；继续隔离 `ATOMGIT_STEP_SUMMARY`。

## 风险与缓解

| 风险                 | 缓解                                                                                                |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| 旧引用失效（破坏性） | README 提供迁移对照；已知下游仓在合入后同步更新                                                     |
| 测试合并遗漏用例     | 以用例清单逐项核对两文件；合并后测试数与覆盖率为基线                                                |
| SBOM 门控回归        | 新增 pr/version 门控用例；version 现有 SBOM 用例保留                                                |
| 根级构建影响 node16  | 继续使用 `@vercel/ncc` 打包为自包含 CJS，`runs.using: node16` 不变                                  |
| CI 覆盖率计算变化    | UT 改为根级单次 c8，include `shared/**/*.js` 与根 `index.js`；保持 `fetch-depth: 0` 与 Summary 隔离 |

## 跨仓影响

- 所有引用旧子路径的下游 workflow 必须迁移：`openlibing/trivy-action/oss-pr-scan-action@master` → `openlibing/trivy-action@master` + `scan-type: pr`；version 同理。
- 插件输入除新增必填 `scan-type` 外保持兼容；version 侧 SBOM 输入不变。

## 落地偏差与验证

| 项目         | 计划                    | 实际                                                                                                                   |
| ------------ | ----------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 测试脚本     | 根 `c8 ... node --test` | 根 `node --test`；UT workflow 用 `npx c8@10` 采集，未新增 c8 devDependency                                             |
| 测试可注入性 | 未规划                  | `run(scanFn = scan)` 增加测试注入点，覆盖分发逻辑                                                                      |
| Action 引用  | 根引用 `@master`        | PR 自测引用 `@v1.4`（tag 基于 `fix-oss-scan-security`）；main workflow 使用 `@main`；合入后可切回 `@master` 或正式标签 |
| 测试规模     | 合并两套                | 82 用例；总覆盖率 97.59%，增量覆盖率 98%                                                                               |
| CI           | build/ut 根级           | 同时更新 `nightly-schedule-scan.yml`；oss-pr-scan / ut / pre-commit / build 均通过                                     |
