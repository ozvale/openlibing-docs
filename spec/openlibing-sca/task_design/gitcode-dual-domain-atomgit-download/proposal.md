# GitCode 双域名与 Atomgit 文件下载映射（20261019 iter1）

## 需求背景

本 PR 是 `atomgit-domain-compat` spec（gitcode 平台双域名兼容）的落地交付，并在其基础上扩展：

1. **双域名判定落地**：`gitcode.domains` 域名前缀列表 + `GitcodeUrlUtil` 工具类，替换 `IntegrationApiServiceImpl` 约 20 处与 `DownLoadFilesUtils` 中散落的单域名 `startsWith(gitcodeUrl)` 判定；移除 `replaceAtomgitDomain` 紧急改写逻辑，atomgit URL 原样入库。
2. **atomgit 文件下载故障**：PR 文件下载（`downLoadGitcodeSence`）按 gitcode 前缀做 URL 替换，atomgit mergeUrl 不含该前缀导致替换无效，请求落到平台 Web 页面返回 HTML，JSONArray 解析失败。
3. **存量数据兜底**：atomgit URL 原样入库后，此前以 gitcode 域名入库的仓库在 atomgit 域名下查不到，需要域名兜底重查。
4. **license-scanner 镜像构建故障**：过时的 `click<8.1.0` 固定与 scancode-toolkit 32.5.0 在 py3.10+ 要求 `click>=8.2.0` 冲突；pluggy 1.7.0 与 plugincode 32.0.0 不兼容导致 scancode import 即崩，运行期静默产出 null。

关联业务 Issue：

- openlibing/openlibing-sca#88 【合法合规】扫描兼容 atomgit.com 域名、审核逻辑及风险看板数据看板优化

## 功能描述

- **`GitcodeUrlUtil`（新增）**：`gitcode.domains`（默认 `https://gitcode.com,https://atomgit.com`）域名前缀列表；提供 `isGitcodeUrl` / `matchDomainBase` / `stripDomain` / `normalizeToPrimaryDomain`；初始化校验主域名 `gitcode.url` 包含在列表内（不含则告警）。
- **域名→API 基址映射**：新增 `gitcode.domain.apis` 配置（`Web域名=v5基址` 逗号分隔，如 `https://atomgit.com=https://api.atomgit.com/api/v5/repos`），`resolveApiBase` / `resolveApiHost` 按命中域名返回对应 API 基址，未配置/未命中回退默认值；非法条目跳过并告警。
- **atomgit 文件下载修复**：`downLoadGitcodeSence` 按 `matchDomainBase` 命中的域名前缀整体替换为对应 v5 API 基址（未命中保持原 URL，与历史行为一致）。
- **atomgit 域名兜底重查**：`getRepoInfo` / `getVersionReposId` 原域名查不到仓库时，`normalizeToPrimaryDomain` 换 gitcode 主域名重查；主域名查询未命中不兜底。
- **平台识别兼容**：`getCodeHostingPlatformFlag` 将 `atomgit.com` 识别为 `gitcode`；`checkUrl` / `validatePrUrl` 接受 atomgit PR URL。
- **queryRepoSizeKb 修复**：生产配置 `gitcode.v5.url` 已含 `/repos` 后缀，直接拼 owner/repo，不再重复追加。
- **Dockerfile 修复**：移除 `click<8.1.0` 固定，钉住 `pluggy<1.7.0`，新增构建期冒烟校验 `pip3 check && scancode --version`（依赖冲突直接让镜像构建失败）。
- pom.xml 显式引入 `com.rabbitmq:amqp-client:5.34.0`（与同迭代 PR #328/#329 对齐）。

## 验收标准

- [x] 单元测试通过（GitcodeUrlUtilTest 新增 15 个用例、DownLoadFilesUtilsTest 新增 3 个、IntegrationApiServiceImplTest 新增/适配约 10 个；CI 已过）。
- [x] CI 流水线通过（`ci-pipeline-passed` 标签）。
- [x] `replaceAtomgitDomain` 紧急改写逻辑已删除，atomgit URL 原样保留（单测断言）。
- [ ] 手动验证双域名配置下文件下载正常。
- [ ] 手动验证 license-scanner 镜像构建通过冒烟校验。

## 影响范围

- 仅 `openlibing-sca` 单仓，8 个文件（+668 / -63，7 commits），无 DB schema 变更、无对外接口契约变化。
- 新增配置项 `gitcode.domain.apis`（默认空，不配置回退既有 `gitcode.v5.url` 行为）；`gitcode.domains` 有默认值。
- 行为变化：atomgit URL 不再改写入库；atomgit 仓库查找未命中时多一次主域名兜底查询。
