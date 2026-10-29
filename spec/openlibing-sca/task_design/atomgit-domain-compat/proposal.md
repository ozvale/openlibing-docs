# atomgit-domain-compat — gitcode 平台双域名兼容

## 需求背景

openlibing-sca 的仓库/PR 扫描来源域名将从 `https://gitcode.com/` 迁移到 `https://atomgit.com/`。
迁移尚未正式启动（"暂时还不切换"），过渡期内上游传入的 URL 可能带任一域名。
两平台 API 完全兼容（同一 token、同一路径 `/owner/repo`、同一 api/v5 响应结构），属于同一 gitcode 平台的域名别名。

现有代码仅靠 `startsWith(gitcodeUrl)` 单域名前缀判定平台，atomgit URL 会落入错误分支。
此前在 `IntegrationApiServiceImpl#replaceAtomgitDomain` 做过"atomgit 域名改写为 gitcode 域名"的紧急处理，
该处理只覆盖 PR 入口单点，属于临时方案，本次移除，改为系统性的双域名兼容。

## 功能描述

**做什么**：

- gitcode 平台支持域名前缀列表（`gitcode.domains`，默认 `https://gitcode.com,https://atomgit.com`）。
- 新增 `GitcodeUrlUtil` 集中提供 `isGitcodeUrl` / `stripDomain`，替换散落各处的 `startsWith(gitcodeUrl)` 判定。
- 移除 `replaceAtomgitDomain` 紧急改写逻辑，atomgit URL 按原样入库。
- `getCodeHostingPlatformFlag` 将 `atomgit.com` 识别为 `gitcode` 平台。

**不做什么**：

- 不改动 `ScanCommonServiceImpl`（按平台字符串 `"gitee"/"gitcode"` 分派，天然兼容）。
- 不改动 `CGitPackageUrlResolver`（白名单已含双域名）、`PlatformUtil`（token 按 `PLATFORM_GITCODE` 体系，atomgit 复用）。
- 不切换 `gitcode.url` 等既有配置语义（仍指向 gitcode.com，用于构造对外/下载/API URL）。
- 不做存量数据迁移。

## 验收标准

- [ ] 带 `https://gitcode.com/` 前缀的仓库/PR URL 行为与改造前一致。
- [ ] 带 `https://atomgit.com/` 前缀的仓库/PR URL 能正确通过 `checkUrl` 校验、完成平台判定、走 gitcode API 通道。
- [ ] `replaceAtomgitDomain` 紧急改写逻辑已删除，相关单测同步更新。
- [ ] 新增/更新单测覆盖双域名场景，编译与相关测试通过。
- [ ] `gitcode.domains` 未配置时使用默认值（含两个域名），配置后以配置为准。

## 影响范围

- `openlibing-sca`：`common/utils`（新增工具类）、`dm/service/impl/IntegrationApiServiceImpl`、`analysis/utils/security/DownLoadFilesUtils` 及对应单测。
- 无数据库 schema 变更；无对外接口契约变化。
- 风险：去掉改写后 atomgit URL 原样入库，若同一仓库此前以 gitcode 域名入过库会出现两条 repo 记录，由上游统一发某一域名规避。
