# GitCode 双域名与 Atomgit 文件下载映射 — 技术设计

> 前置 spec：`atomgit-domain-compat/`（双域名兼容设计方案，本 PR 为其落地交付 + 扩展）。同迭代 PR #328 复用本 PR 引入的 `GitcodeUrlUtil` 并扩展至评审/查询链路（含尾斜杠归一化增强），两 PR 为兄弟分支，合入时注意 `GitcodeUrlUtil` 的合并顺序。

## 方案概述

以 `GitcodeUrlUtil` 为唯一域名判定与映射入口，三层能力：

1. **域名判定**：`gitcode.domains` 前缀列表 + `isGitcodeUrl`，替换散落的单域名 `startsWith`。
2. **域名→API 映射**：`gitcode.domain.apis`（`Web域名=v5基址` 逗号分隔）+ `resolveApiBase` / `resolveApiHost`，让别名域名可指向各自的 v5 API。
3. **域名归一化兜底**：`normalizeToPrimaryDomain` 将别名域名 URL 换为主域名，供 DB 查询未命中时兜底重查。

## 关键决策

1. **前缀列表按配置顺序匹配（findFirst）**：`matchDomainBase` 返回第一个命中的前缀，`gitcode.domains` 中主域名排在别名前可保证主域名优先。
2. **映射配置宽松解析**：`gitcode.domain.apis` 条目无 `=`、以 `=` 开头/结尾均跳过并 warn，不阻断启动；key 统一 `removeEnd("/")` 归一化，兼容配置尾斜杠差异。
3. **API host 从 v5 基址反推**：`resolveApiHost` 取映射基址中 `/api/v5` 之前的部分（如 `https://api.atomgit.com/api/v5/repos` → `https://api.atomgit.com`），供 `urlGitCodeAdd` 这类自行拼接 v5 路径的调用方使用，避免两套配置漂移。
4. **下载 URL 替换以"命中前缀"为单位整体替换**：`downLoadGitcodeSence` 用 `mergeUrl.replace(domainBase, apiBase)`，而非仅替换 gitcode 前缀——修复 atomgit mergeUrl 替换无效后请求落到 Web 页面、JSONArray 解析失败的问题；未命中域名时不替换，保持历史行为。
5. **DB 兜底重查只做一层**：`getRepoInfo` / `getVersionReposId` 原域名未命中 → `normalizeToPrimaryDomain`（别名→主域名）重查一次；主域名未命中不反向兜底（atomgit→gitcode 单向），避免双查询放大。
6. **移除 `replaceAtomgitDomain` 入口改写**：atomgit URL 原样入库（与 `atomgit-domain-compat` spec 决策一致）；代价是同仓库可能存在双域名两条 repo 记录，由 5 的兜底重查兼容存量数据。
7. **`queryRepoSizeKb` 拼接修复**：生产配置 `gitcode.v5.url` 已含 `/repos` 后缀，去掉追加 `/repos` 的写法直接拼 `owner/repo`（配合 `gitcode.domain.apis` 映射后基址语义统一为"含 /repos 的 v5 基址"）。
8. **Dockerfile 依赖治理**：`click<8.1.0` 是为旧版 scancode 兼容加的固定，与 scancode-toolkit 32.5.0（py3.10+ 要求 click>=8.2.0）冲突，直接移除；pluggy 1.7.0 的 hookspec 发现逻辑与 plugincode 32.0.0 不兼容（scancode import 即崩 `ValueError: did not find any 'pre_scan' hooks`），钉住 `pluggy<1.7.0`；构建期 `pip3 check && scancode --version` 让依赖冲突在镜像构建期暴露，避免运行期静默产出 null。

## GitcodeUrlUtil API 一览

| 方法                                  | 语义                                                                   |
| ------------------------------------- | ---------------------------------------------------------------------- |
| `isGitcodeUrl(url)`                   | 命中任一域名前缀返回 true（空白安全）                                  |
| `matchDomainBase(url)`                | 返回命中的域名前缀（配置顺序findFirst），未命中 null                   |
| `resolveApiBase(url, defaultApiBase)` | 按 `gitcode.domain.apis` 返回命中域名的 v5 基址，未配置/未命中回退默认 |
| `resolveApiHost(url, defaultApiHost)` | 映射基址去掉 `/api/v5` 及后缀返回 API host 根                          |
| `normalizeToPrimaryDomain(url)`       | 别名域名 → 主域名（`gitcode.url`）；未命中或已是主域名返回 null        |
| `stripDomain(url)`                    | 剥离命中前缀返回剩余路径（以 / 开头），未命中 null                     |

## 涉及文件

| 文件                                              | 操作                    | 说明                                                                                                                                                                                        |
| ------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `common/utils/GitcodeUrlUtil.java`                | 新增（182 行）          | 域名判定 / 映射 / 归一化工具                                                                                                                                                                |
| `common/utils/GitcodeUrlUtilTest.java`            | 新增（172 行，15 用例） | 双域名判定、映射解析、兜底归一化、配置容错                                                                                                                                                  |
| `IntegrationApiServiceImpl.java`                  | 修改                    | 移除 replaceAtomgitDomain；约 20 处 isGitcodeUrl；getRepoInfo/getVersionReposId 兜底重查；urlGitCodeAdd 按域名映射；queryRepoSizeKb /repos 修复；getCodeHostingPlatformFlag atomgit→gitcode |
| `analysis/utils/security/DownLoadFilesUtils.java` | 修改                    | downLoadGitcodeSence 按命中前缀映射 v5 基址；deleteRepoFromGitcode isGitcodeUrl                                                                                                             |
| `DownLoadFilesUtilsTest.java`                     | 修改                    | 新增 3 用例（atomgit/gitcode 映射 + domain.apis 生效）                                                                                                                                      |
| `IntegrationApiServiceImplTest.java`              | 修改                    | 注入真实 GitcodeUrlUtil（含尾斜杠配置）；atomgit URL 不改写、checkUrl/validatePrUrl、兜底重查、urlGitCodeAdd 映射、queryRepoSizeKb 修复等用例                                               |
| `Dockerfile`（license-scanner）                   | 修改                    | click 固定移除、pluggy<1.7.0 钉住、pip3 check + scancode 冒烟                                                                                                                               |
| `pom.xml`                                         | 修改                    | amqp-client 5.34.0 显式引入                                                                                                                                                                 |

## 配置项

| 配置键                | 默认                                      | 说明                                                                                                                                          |
| --------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `gitcode.domains`     | `https://gitcode.com,https://atomgit.com` | gitcode 平台域名前缀列表（逗号分隔）；须包含 `gitcode.url` 主域名，不含仅告警不阻断                                                           |
| `gitcode.domain.apis` | 空                                        | 域名→v5 API 基址映射（`Web域名=v5基址` 逗号分隔，如 `https://atomgit.com=https://api.atomgit.com/api/v5/repos`）；未配置回退 `gitcode.v5.url` |

## 行为逻辑（下载 URL 构造）

```
downLoadGitcodeSence(mergeUrl):
  domainBase = matchDomainBase(mergeUrl)          # 命中 gitcode.domains 任一前缀
  if domainBase == null: url = mergeUrl           # 未命中不替换（历史行为）
  else:
    apiBase = resolveApiBase(mergeUrl, gitcodeV5Url)   # gitcode.domain.apis 映射，回退默认
    url = mergeUrl.replace(domainBase, apiBase)
  url += "/files"; url.replace("pull", "pulls")
```

## 测试策略

- **单测**：GitcodeUrlUtilTest 覆盖判定/映射/归一化/空白/容错 15 用例；DownLoadFilesUtilsTest 用 ArgumentCaptor 断言 atomgit 与 gitcode 入参均映射到 v5 API 基址、domain.apis 配置后映射到各自 API host；IntegrationApiServiceImplTest 覆盖 atomgit URL 原样保留、checkUrl/validatePrUrl、兜底重查（命中/未命中）、urlGitCodeAdd 映射、queryRepoSizeKb 修复。CI 已通过。
- **手动**：双域名配置下文件下载；license-scanner 镜像构建冒烟。

## 风险与缓解

| 风险                                         | 缓解                                                                                        |
| -------------------------------------------- | ------------------------------------------------------------------------------------------- |
| atomgit URL 原样入库产生双域名 repo 记录     | getRepoInfo/getVersionReposId 主域名兜底重查兼容存量；上游统一发某一域名规避                |
| `gitcode.domain.apis` 配置错误指向不可达 API | 条目格式非法跳过并告警；未配置回退默认基址，行为与旧版一致                                  |
| `gitcode.domains` 遗漏主域名                 | init 校验仅告警（不阻断），日志明示"URLs built from gitcode.url may not be recognized"      |
| 与 PR #328 的 GitcodeUrlUtil 冲突            | 兄弟分支同源实现；#328 含尾斜杠归一化增强，合入顺序以先 #327 后 #328 为宜，冲突取 #328 版本 |
| click 固定移除后依赖解析变化                 | 构建期 pip3 check + scancode --version 冒烟兜底，问题前置到镜像构建                         |

## 跨仓影响

- 仅 `openlibing-sca`，无其他仓改动、无 DB schema 迁移；license-scanner 镜像需重新构建。
