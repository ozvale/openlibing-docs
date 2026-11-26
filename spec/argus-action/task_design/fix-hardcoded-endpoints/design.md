# argus-action 硬编码公网端点收敛 — 技术设计

## 方案概述

沿用组织先例（code-metrics-action #22 / upload-ut-action #2）的“部分成立·小整改 + 白名单”模式：
保留公开 SaaS 默认值，在同文件收敛常量，补 `gitleaks:allow`、测试和产物重建。

## 关键决策

1. **同文件常量，不新建 config 文件**
   - 仅 2 个端点、1 个实现文件（`argus-action/dist/argus-scan.js`，293 行）；
   - argus 没有 `src/` 层，源码本身位于 `dist/`，新增 `config/endpoints.js` 会引入
     require 路径、ncc 解析和 zip/CLI 分发约束，收益不足；
   - 先例中拆 `src/config/endpoints.js` 的场景均为 5~8 个端点、跨多个模块。

2. **不新增环境变量**
   - `codecheck-ip` / `openlibing-url` 已是 action input，CLI 也支持同名 `--` 参数；
   - 新增 env 只会扩大行为面，不增加实际覆盖能力。

3. **默认值对齐**
   - `codecheck-ip` 统一为 `https://apig.openlibing.com`（原代码 `:443` 与之等价，去冗余）；
   - `openlibing-url` 统一为 `https://www.openlibing.com/apps/argus`（与 action.yml 一致）；
     仅 CLI / 空 input 场景的链接从站点根变为 Argus 页面，属有意修正，写入交付说明。

4. **构建链修复**
   - 现状：`npm run package` 输出到 `build/argus-action/dist/index.js`，`zip.js` 从该目录打包，
     但 action 的 `main` 是 `argus-action/dist/index.js`，该文件不会被更新；
   - 方案：`zip.js` 打包前把 `build/argus-action/dist/index.js` 复制到
     `argus-action/dist/index.js`，保证 Action 实际入口与 zip 同源；
   - 不改变 ncc 输出目录，避免 ncc 清理源码目录的风险。

5. **gitleaks 白名单**
   - ncc 产物 `argus-action/dist/index.js` 内含第三方依赖的作者邮箱与变量名
     （如 SDK 中的 `secretAccessKey` 变量名、第三方依赖作者邮箱），属打包固有误报，非本次引入；
   - 在 `.gitleaks.toml` 全局 allowlist 增加 `^argus-action/dist/index\.js$`，
     与 `node_modules` / `vendor` / `.min.js` 同为“不重复扫描的产物路径”；
   - 源码 `argus-scan.js` 与 `action.yml` 仍正常扫描，默认端点行用 `gitleaks:allow` 说明。

## 涉及文件

| 文件                              | 操作 | 说明                                                                                                            |
| --------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------- |
| `argus-action/dist/argus-scan.js` | 修改 | 顶部两个默认端点常量；`getConfig()` / `parseArgs()` 复用；`gitleaks:allow` 理由；Summary 改为「漏洞详情」超链接 |
| `argus-action/action.yml`         | 注释 | 两个 default 上方注明公开 SaaS 端点、可被 input 覆盖、`gitleaks:allow`                                          |
| `argus-action/README.md`          | 修改 | 移除 AK/SK、`signer.js`；补 OIDC `id-token: write`；修正默认值与覆盖说明                                        |
| `test/mock-sdk.js`                | 修改 | 记录 `callApig` 收到的 URL                                                                                      |
| `test/argus.test.js`              | 修改 | 默认端点、`--codecheck-ip` 覆盖、Summary 链接用例                                                               |
| `zip.js`                          | 修改 | 打包前同步 bundle 到 `argus-action/dist/index.js`                                                               |
| `.gitleaks.toml`                  | 修改 | 打包产物路径白名单，消除第三方依赖误报                                                                          |
| `argus-action/dist/index.js`      | 重建 | ncc 产物                                                                                                        |
| `argus-action.zip`                | 重建 | 发布包                                                                                                          |

## 风险 & 缓解

| 风险                                 | 缓解                                                                   |
| ------------------------------------ | ---------------------------------------------------------------------- |
| ncc 重建导致 `dist/index.js` 大 diff | review 以源码 / action.yml / README 为准；用 grep + unzip 校验产物     |
| CLI 默认链接变化                     | 仅影响 CLI / 空 input；Action 行为不变；新增用例覆盖                   |
| 扫描器下一轮仍命中 dist              | 在 issue #2 评论中预置“ncc 固有行为”说明，按 upload-sarif #10 先例归档 |
| gitleaks 命中打包产物第三方误报      | 产物路径加入 `.gitleaks.toml` allowlist；源码仍正常扫描                |
| 构建链改动影响 CI                    | `build.yml` 只执行 `npm run build`，不依赖 `build/` 路径；改后命令不变 |

## 跨仓影响

无。仅 `argus-action` 单仓；`openlibing-docs` 仅新增本目录文档。
