# 设计文档：openlibing-codecheck 适配 gitcode.com / atomgit.com 双域名

> 关联需求：`requiremnt_desc.md`（gitcode 代码仓新增域名 atomgit.com，两者均解析为 gitcode 平台）

## 1. 背景与目标

GitCode 代码仓新增域名 `atomgit.com`，与 `gitcode.com` 同属 gitcode 平台。本仓需要在平台识别、缺陷/屏蔽单的用户主页链接补全、文件内容读取、PR 评论回填等所有"URL → 平台"判定环节，保证 atomgit URL 正确归入 gitcode，避免误判为 gitee 或识别失败。

## 2. 现状分析（整仓扫描结论）

### 2.1 已支持 atomgit，无需修改

| 位置                                                                               | 说明                                                                                                                                                                                                                     |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `common/util/repo/RepoUrlParser.java`（KEYWORD_TO_REPO_TYPE，L38-48）              | 关键词表已含 `"atomgit" -> "gitcode"`，且有单测 `RepoUrlParserTest#shouldMapAtomgitToGitcode` 佐证；`buildRepoKey` 生成域名无关 key                                                                                      |
| `common/codeplate/CodePlateHelper#getCodePlate`（L117-133）                        | 已含 `repoAddress.contains("atomgit") -> "gitcode"`，token/用户名路由兼容。调用方 `getAccessToken` / `getUserLogin` / `getRepoFileContents` / `getParamModel`、`RestCodeCheckUtil#getAccountToken`（L1422-1431）自动兼容 |
| `business/impl/InternalCodeIncDelegateImpl#getCodeHostingPlatformFlag`（L336-351） | 已含独立的 `atomgit.com -> "gitcode"` 分支，PR 汇总跳转无感登录正常                                                                                                                                                      |
| `common/codeplate/GitCodePlate#getParamModel`（L69-93）                            | 已通过 `CodePlatformUtil.normalizeGitCodeDomain` 将 atomgit prUrl 派生的 gitUrl 归一化为 gitcode.com                                                                                                                     |
| `common/codeplate/GitCodeHelper#resolveRepoAccessToken`（L303-335）                | `url.contains("gitee.")` 之外（含 gitcode.com 与 atomgit.com）取 gitcode token，atomgit 行为正确                                                                                                                         |
| `common/codeplate/GitCodeHelper` API 地址                                          | 来自配置 `${gitcode.api.address}`，与用户输入域名无关                                                                                                                                                                    |
| 平台常量（`CodeCheckConstants.GITCODE`、`ProjectConstant.RepoPlatform` 等）        | 值域不变，无需新增                                                                                                                                                                                                       |
| webhook 入口（`WebhookController` 等）                                             | 接收方向，不拼接 gitcode 回调地址                                                                                                                                                                                        |

### 2.2 未适配点

见第 4 节。其中最严重的问题是 `CodePlatformUtil#getCodePlatform` 对 atomgit 的**静默误判为 gitee**。

## 3. 适配方案

1. **归一化优先**：仓内已有 `CodePlatformUtil.normalizeGitCodeDomain`（atomgit.com → gitcode.com 字符串替换，L75-77），但仅一个调用点使用。方案核心是把该归一化推广到所有"配置驱动平台识别 / 前缀 indexOf 解析"的入口，消除 atomgit 被误判为 gitee、解析错乱的根因。
2. **显式域名分支兜底**：对纯 `contains("gitcode.com")` 的判定点，显式追加 `contains("atomgit.com")`，不依赖归一化。
3. **平台标识值不变**：不新增平台常量；配置 `code.platform.address` 可不动（归一化后即可命中 gitcode 条目）。

## 4. 代码修改点

### 4.1 P0：`CodePlatformUtil#getCodePlatform`（`src/main/java/com/openlibing/codecheck/common/utils/codecheck/CodePlatformUtil.java`，L32-50）

现状逻辑：从配置 `code.platform.address` 逐平台取地址串，判断"配置值字符串 contains(protocol://host)"，全部不命中时 **fallback 返回 `"gitee"`**。atomgit host 不在任何配置值中 → **atomgit 被静默误判为 gitee**。

受影响的 4 个调用点（均在 `ProblemshieldDelegateImpl`）：L210、L215（`resolveHostingPlatform`）、L1490、L1499（通知方式分发——atomgit 会错误放行 gitee 站内信并查错账号表优先级）。

改法：方法入口先归一化再匹配：

```java
public String getCodePlatform(String repoUrl) {
  ...
  // atomgit.com 与 gitcode.com 同属 gitcode 平台，匹配前先归一化域名
  repoUrl = normalizeGitCodeDomain(repoUrl);
  ...
}
```

可选加固：`normalizeGitCodeDomain` 目前是纯子串替换（`xatomgit.com` 也会被替换），风险低，可收紧为按 host 段替换。

### 4.2 P0：`ProblemshieldDelegateImpl#resolveHostingPlatform`（`src/main/java/com/openlibing/codecheck/business/impl/ProblemshieldDelegateImpl.java`，L205-219）

现状：`contains("gitcode.net") || contains("gitcode.com") || getCodePlatform == gitcode` 判定 gitcode。atomgit URL 三个条件均不命中（getCodePlatform 在 4.1 修复前还会误判 gitee），导致 L221-241 `buildReviewerUserUrl` 走错平台分支。

改法：显式追加 `|| repoUrl.contains("atomgit.com")`（与 4.1 双保险）。修复后 L1490-1516 通知分发随 getCodePlatform 修复自动兼容（atomgit 正确走 gitcode 仅 EMAIL 分支）。

### 4.3 P1：`CheckboardDelegateImpl#getCodeHostingPlatform`（`src/main/java/com/openlibing/codecheck/business/impl/CheckboardDelegateImpl.java`，L1385-1396）

现状：只识别 `gitee.com` / `gitcode.net` / `gitcode.com`，atomgit 返回空串，导致调用方 `enrichDefectsWithUserUrls`（L1281-1294）直接 error 返回，看板缺陷的 `userUrl` / `reviewerUrl` 不再补全。

改法：gitcode 分支追加 `|| repoUrl.contains("atomgit.com")`。

### 4.4 P1：`CommonHelper#getProjectAndRepoNameFromUrl`（`src/main/java/com/openlibing/codecheck/common/utils/common/CommonHelper.java`，L57-59 配置注入，L257-274）

现状：与 coderepo 仓同款问题——用配置平台地址在 repoUrl 中 `indexOf` 定位后截取 owner/repo。atomgit URL 下 `indexOf` 返回 -1，substring 起点变成 `-1 + len + 1`，**不抛异常、静默解析出错误 owner**。

影响链路：`GitCodePlate#getRepoFileContents`（GitCodePlate.java L48-51，platform 固定传 gitcode）→ atomgit 仓查文件内容时 owner 错误。

改法（二选一）：

1. 入口对 repoUrl 先 `CodePlatformUtil.normalizeGitCodeDomain(repoUrl)`（与 4.1 同一手法，改动最小）；
2. 或改为域名无关解析（取协议后第一个 `/` 与最后一个 `/` 之间的段），与 coderepo 仓 4.3/4.4 方案对齐。建议采用方案 2，两仓保持一致。

### 4.5 P2：文案与测试补充

- 单测补充：`CodePlatformUtilTest` 补 atomgit URL → gitcode 用例（当前只测了 normalizeGitCodeDomain）；`ProblemshieldDelegateImpl`、`CheckboardDelegateImpl`、`CommonHelper` 对应的 atomgit 用例目前缺失。
- 涉及修改的 4 处均无既有单测覆盖 atomgit 场景，需新增。

## 5. 配置变更

| 配置项                  | 变更                                                | 说明                                                                                                  |
| ----------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `code.platform.address` | **可不改**（4.1 归一化后即可命中现有 gitcode 条目） | 若环境侧希望配置自解释，可同步追加 `https://atomgit.com`，但需先核对无消费方按单值 `indexOf` 语义解析 |
| `gitcode.api.address`   | 不变                                                | 前提是 atomgit 仓共用 GitCode `/v5` 开放 API                                                          |

## 6. 待确认点（不确定项）

1. **atomgit 仓开放 API 是否与 `api.gitcode.com` 同构**？影响：
   - `business/impl/PipelineDelegateImpl#submitCodeInspectionOpinions`（L250-256）硬编码 `https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{id}/comments` 回填评审意见。owner/repo 取 `split("/")[3]/[4]`，对 atomgit 同构 URL 索引成立；仅 API 域名是否共用待确认。共用则不改，独立则需配置化（参照 `${gitcode.api.address}`）。
2. **用户主页链接域名**：`CheckboardDelegateImpl#buildUserUrl`（L1398-1406）与 `ProblemshieldDelegateImpl#buildReviewerUserUrl`（L237-240）对 gitcode 平台硬编码拼 `https://gitcode.com/<login>`。若 atomgit 账号体系统一在 gitcode.com，则现状正确、不改；若账号独立，需按来源域名拼接。倾向不改，需产品确认。
3. **上游 webhook 的 platform 传参**：`SuppressionScanServiceImpl`（L278-311）按请求体 `request.getPlatform()`（gitee/gitcode/github）路由 API，不解析 URL 域名。需确认 GitCode Action/webhook 组装方对 atomgit 仓传入 `"gitcode"`，服务端代码无需改。
4. **环境配置核实**：`code.platform.address` 的实际值在仓内无定义文件（走外部配置中心），需环境核实。
5. （可选，非本次必须）`GitCodeHelper` L317、L330 的 `url.contains("gitee.")` 匹配过宽，建议收紧为 `gitee.com`，atomgit 行为不受影响。

## 7. 影响面与兼容性

- 数据库：无变更。
- 接口：无对外契约变化。
- 行为变化：
  - atomgit 仓缺陷/屏蔽单的用户主页链接补全恢复可用（4.2/4.3）；
  - atomgit 仓通知不再误走 gitee 站内信（4.1）；
  - atomgit 仓文件内容读取 owner 解析正确（4.4）；
  - 既有 gitcode.com / gitee / github 行为不变。
