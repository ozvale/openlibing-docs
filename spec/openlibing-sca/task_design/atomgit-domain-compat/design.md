# atomgit-domain-compat — 技术设计

## 方案概述

把"gitcode 平台的域名"从单一 `gitcode.url` 前缀扩展为**域名前缀列表**（配置项 `gitcode.domains`，
默认 `https://gitcode.com,https://atomgit.com`），并新增 `GitcodeUrlUtil` 提供集中判定与路径剥离能力；
删除 `replaceAtomgitDomain` 紧急改写，所有平台判定点改走工具类。

## 架构决策

1. **域名列表而非新增平台类型**：两平台 API 完全兼容，等同同一平台的域名别名。
   平台标识仍为 `"gitcode"`，token / API / 文件下载 URL 全部沿用现有 gitcode 体系，
   避免 `IntegrationApiServiceImpl` 内 30+ 处平台分派逻辑翻倍。
2. **URL 原样入库，不再改写**：移除 `replaceAtomgitDomain`，atomgit URL 保持原样存储与返回，
   下游展示真实来源域名；平台判定由工具类兼容双域名。
3. **配置默认值内置**：`@Value("${gitcode.domains:https://gitcode.com,https://atomgit.com}")`，
   Apollo 未配置时开箱即用；正式切换域名时仅需在 Apollo 调整 `gitcode.url`（构造类 URL 的主域），
   `gitcode.domains` 保留双域名即可完成过渡。
4. **工具类集中判定**：`isGitcodeUrl`（任一前缀命中）与 `stripDomain`（剥离命中前缀返回剩余路径，
   替代 `substring(gitcodeUrl.length())`），避免域名列表语义散落在多个 `@Value` 字段中。

## 涉及文件

| 文件                                              | 操作 | 说明                                                                                                                                                         |
| ------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `common/utils/GitcodeUrlUtil.java`                | 新增 | `@Component`，注入 `gitcode.domains`，提供 `isGitcodeUrl` / `stripDomain`                                                                                    |
| `dm/service/impl/IntegrationApiServiceImpl.java`  | 修改 | 删除 `ATOMGIT_URL` / `replaceAtomgitDomain` 及调用点；`startsWith(gitcodeUrl)` 等判定改用工具类；`getCodeHostingPlatformFlag` 增加 `atomgit.com → "gitcode"` |
| `analysis/utils/security/DownLoadFilesUtils.java` | 修改 | `deleteRepoFromGitcode` 1 处判定改用工具类                                                                                                                   |
| `test/.../GitcodeUrlUtilTest.java`                | 新增 | 双域名命中 / 未命中 / stripDomain / 配置化用例                                                                                                               |
| `test/.../IntegrationApiServiceImplTest.java`     | 修改 | 删除 `replaceAtomgitDomain` 用例；补 atomgit URL 的 `checkUrl` / `buildRepoUrl` / `generatePrUrl` 用例                                                       |

### 不改动文件及理由

- `ScanCommonServiceImpl`：按上下文中的平台字符串 `"gitee"/"gitcode"` 分派 API URL 与 token，
  平台判定发生在上游，双域名兼容后上游仍产出 `"gitcode"`，无需修改。
- `CGitPackageUrlResolver`：白名单已同时含 `gitcode.com` / `atomgit.com`。
- `PlatformUtil`：token/login 按 `PLATFORM_GITCODE` 常量取用，atomgit 复用 gitcode 账号体系。
- `DashboardReportSchedule`：硬编码的是 openlibing-sca 自身仓库地址，与平台兼容无关。

## 关键判定点清单（IntegrationApiServiceImpl）

- `checkUrl`（L905）：双域名 + path 段校验（`stripDomain` 后 split 校验 2/4 段）。
- `buildRepoUrl`（L376）：`startsWith(gitcodeUrlPrefix)` → `isGitCodeUrl`。
- `generatePrUrl`（L780）→ `urlGitCodeAdd`：gitcode 分支判定改工具类；URL 构造仍用 `gitcodePrefixUrl` 主域。
- 个人/版本扫描入口、结果 URL 判定等 17 处 `startsWith(gitcodeUrl)` 全部替换。
- `getCodeHostingPlatformFlag`（L968）：`contains("atomgit.com")` → `"gitcode"`。

## 风险 & 缓解

| 风险                                                              | 缓解                                                           |
| ----------------------------------------------------------------- | -------------------------------------------------------------- |
| atomgit URL 原样入库后，与历史（曾被改写为 gitcode 域名）记录重复 | 上游统一发某一域名；如需合并属数据治理，不在本次范围           |
| `gitcode.domains` 与 `gitcode.url` 配置不一致（列表缺主域）       | 工具类启动时校验：列表未包含 `gitcode.url` 时告警日志提示      |
| URL host 大小写差异                                               | 判定保持 `startsWith` 精确匹配，与既有行为一致，不引入宽松匹配 |

## 跨仓影响

无。仅 `openlibing-sca` 单仓改动；上游（openlibing-framework 等）无需感知。
