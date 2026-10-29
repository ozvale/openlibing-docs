# 设计文档：openlibing-coderepo 适配 gitcode.com / atomgit.com 双域名

> 关联需求：`requiremnt_desc.md`（gitcode 代码仓新增域名 atomgit.com，两者均解析为 gitcode 平台）

## 1. 背景与目标

页面上可配置的代码仓类型目前有 gitcode / gitee / github 三种。GitCode 代码仓域名新增了 `atomgit.com`，与 `gitcode.com` 同属 gitcode 平台。本仓需要在"URL → 平台类型"解析、域名校验、URL 结构化解析（owner/repo 提取）等所有环节，保证包含 `atomgit.com` 的仓库 URL 被正确识别为 gitcode 平台。

## 2. 现状分析（整仓扫描结论）

### 2.1 已支持 atomgit，无需修改

| 位置                                                                  | 说明                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `common/util/repo/RepoUrlParser.java`（KEYWORD_TO_REPO_TYPE，L37-47） | 域名关键词映射表已含 `"atomgit" -> "gitcode"`，host 小写后包含匹配。唯一调用点 `RepoServiceImpl#fetchStaticAlertCountMap`（L838）自动兼容                                                                                                    |
| `common/utils/RepoUrlUtil.java#parseOwnerAndRepo`（L22-33）           | 纯路径切分，不识别域名，天然兼容                                                                                                                                                                                                             |
| `common/utils/GitCode.java`                                           | gitcode API 地址来自配置 `gitcode.api.address`（默认 `https://api.gitcode.com`），不依赖用户输入 URL 的域名                                                                                                                                  |
| 所有 `PLATFORM_GITCODE.equals(platform)` 平台分支                     | 判断的是数据库/DTO 中的平台字段值 `"gitcode"`，与域名无关，入口归一后自动兼容（涉及 `PlatformTokenErrorResolver`、`TokenPermissionEvaluator`、`CommonServiceImpl#getAccessToken`、`RepoServiceImpl`、`ProjectConfigServiceImpl` 等约 30 处） |
| `CodeMetricsServiceImpl`、`SuppressionCommentBuilder` 的链接拼接      | 域名继承用户输入 URL，天然兼容                                                                                                                                                                                                               |
| 常量定义（`ProjectConstant.RepoPlatform`、`RepoType.GITCODE` 等）     | 平台名字符串 `"gitcode"` 不变，无需新增常量；数据库 platform 字段值域不变，无 DDL 变更                                                                                                                                                       |

### 2.2 未适配点（本次改造范围）

见第 4 节修改点清单。

## 3. 适配方案

1. **平台标识值不变**：atomgit.com 归入 gitcode 平台，不新增平台枚举/常量/数据库值。
2. **域名识别双域名化**：所有"包含 `gitcode.com` 判定为 gitcode"的代码点，扩展为"`gitcode.com` 或 `atomgit.com`"。
3. **解析逻辑域名无关化**：依赖 `code.platform.address` 配置做前缀匹配的解析逻辑（`indexOf` 定位）在 atomgit URL 下会错位，需改为按 URL 结构（域名之后路径）解析，彻底摆脱对单域名配置的依赖。
4. **配置与代码双保险**：`checkRepoAddress` 类配置驱动校验，代码侧对 gitcode 平台显式放行双域名，不完全依赖配置中心改动。

## 4. 代码修改点

### 4.1 P0：`SigInfoClient#parsePlatformFromUrl`（`src/main/java/com/openlibing/coderepo/common/utils/SigInfoClient.java`，L56-71）

现状只匹配 `gitcode.com`，atomgit 的 sig-info 路径会返回空串，导致 sig 路径校验（`ProjectConfigServiceImpl` L512、L727）与同步前校验（`RepoServiceImpl#collectInvalidSigPaths` L3352）全部失败。

改法：

```java
String lowerUrl = url.toLowerCase(Locale.ROOT);
if (lowerUrl.contains("gitcode.com") || lowerUrl.contains("atomgit.com")) {
  return ProjectConstant.RepoPlatform.PLATFORM_GITCODE;
}
```

修复后，`parseLocation`、`ProjectConfigServiceImpl` 保存校验、`RepoServiceImpl#collectInvalidSigPaths` 等全部调用方自动兼容。

### 4.2 P0：`OrgLocationUtil#expectedHost`（`src/main/java/com/openlibing/coderepo/common/utils/OrgLocationUtil.java`，L185-192，调用点 normalizeUrl L113-119）

现状 gitcode 平台只接受 host `gitcode.com`，用户填 `https://atomgit.com/<org>` 组织主页会被"组织路径域名与所选平台不一致"拒绝。

改法：将 `expectedHost` 返回单域名的实现改为 host 匹配判断，gitcode 平台接受 `gitcode.com` / `atomgit.com` 两个域名（忽略大小写）：

```java
private static boolean isHostMatched(String platform, String host) {
  return switch (platform) {
    case RepoPlatform.PLATFORM_GITCODE ->
        "gitcode.com".equalsIgnoreCase(host) || "atomgit.com".equalsIgnoreCase(host);
    case RepoPlatform.PLATFORM_GITEE -> "gitee.com".equalsIgnoreCase(host);
    case RepoPlatform.PLATFORM_GITHUB -> "github.com".equalsIgnoreCase(host);
    default -> false;
  };
}
```

注意：`extractLoginFromSegments`（L143-158）按 gitcode 组织路径规则（`/<org>`、`/org/<x>`、`/org/<x>/repos`）提取组织名，需确认 atomgit 组织主页路径结构一致（见第 6 节待确认项）。

### 4.3 P0：`CommonServiceImpl#getProjectAndRepoNameFromUrl`（`src/main/java/com/openlibing/coderepo/business/service/impl/CommonServiceImpl.java`，L789-807）

现状逻辑：从配置 `code.platform.address` 取平台对应的**单个**地址前缀（如 `https://gitcode.com`），用 `repoUrl.indexOf(前缀)` 定位后截取 owner/repo。当 repoUrl 为 `https://atomgit.com/owner/repo.git` 时 `indexOf` 返回 -1，substring 起点错位，**静默解析出错误的 projectName**（可能抛 `StringIndexOutOfBoundsException`）。该方法被令牌权限校验（`TokenPermissionEvaluator` L314）、仓库访问权校验、成员同步等广泛调用，是本仓适配的**最高风险点**。

改法：改为域名无关解析——取协议之后第一个 `/` 与最后一个 `/` 之间的段作为 projectName，repoName 逻辑不变（本就是 `lastIndexOf("/")`）：

```java
// 按域名之后的路径解析 owner/repo，与具体域名无关，兼容 gitcode.com 与 atomgit.com
String pathAfterHost = repoUrl.substring(repoUrl.indexOf("://") + 3);
String projectName =
    pathAfterHost.substring(pathAfterHost.indexOf('/') + 1, repoUrl.lastIndexOf("/"));
```

### 4.4 P0：`RepoServiceImpl#getProjectAndRepoNameFromUrl`（`src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java`，L5230-5248）

与 4.3 逐行相同的重复实现（类注释自述"建议直接用 CommonService 中的，只维护一个"，但 L5133/L5164 等处仍在用）。与 4.3 **同步修改**；后续可收敛为单一实现（非本次必做）。

### 4.5 P0：`RepoServiceImpl#checkRepoAddress`（同文件 L5117-5135，配置注入 L468-469）

现状：校验"repoUrl 的 host 是否在配置中心 `code.platform.address` 对应平台的地址串内"。atomgit host 不在配置值中时新增/导入 atomgit 仓会被拒（调用点 L2050 新增仓库、L4626 外部导入）。

改法（代码 + 配置双保险）：

1. 代码侧：platform 为 gitcode 且 host 为 `gitcode.com` / `atomgit.com` 时直接放行，再走原配置 contains 校验兜底其它平台。
2. 配置侧：配置中心为 `code.platform.address` 的 `gitcode` 值追加 `https://atomgit.com`（见第 5 节）。
3. 失败提示文案（L2053"请确认 gitee、gitcode 或 github 代码仓地址"）同步更新，提及 atomgit。

### 4.6 P1：`RepoServiceImpl#buildRepoUrl`（同文件 L6942-6952）

反向拼接仓库 URL 时从配置取 gitcode 平台单地址前缀。多域名下拼出的 URL 域名选哪个（gitcode.com 还是 atomgit.com）**需要明确规则**（见第 6 节待确认项）。若约定"atomgit 仅是仓库备用域名、平台主域名统一为 gitcode.com"，则无需改代码，仅补充说明。

### 4.7 P2：提示文案与测试补充

- `ProjectConfigServiceImpl` L515、L729、L737 的"仅支持 gitcode/gitee/github"提示文案，更新为包含 atomgit 说明。
- 单测补充：`OrgLocationUtilTest`（现有 fixture 全为 gitcode.com，**必须补 atomgit 用例**，覆盖域名校验与组织名提取）、`ProjectConfigServiceImplTest`（sig 路径校验补 atomgit 用例）、`SigInfoClient` 相关（`parsePlatformFromUrl` 补 atomgit.com / 大小写混合 / 误匹配防护用例）。
- `RepoServiceImplTest` 等其余测试仅 fixture 使用 gitcode.com，行为不变，可选补充。

## 5. 配置变更（配置中心，非代码仓内）

| 配置项                  | 变更                                     | 影响点                                                                |
| ----------------------- | ---------------------------------------- | --------------------------------------------------------------------- |
| `code.platform.address` | gitcode 平台值追加 `https://atomgit.com` | `checkRepoAddress`（4.5）；若该配置被其他消费方按单值解析，需逐一核对 |
| `gitcode.api.address`   | 默认 `https://api.gitcode.com` 不变      | 前提是 atomgit 仓 REST API 与 api.gitcode.com 同构（见第 6 节）       |

## 6. 待确认点（不确定项）

1. **atomgit 开放 API 是否与 `api.gitcode.com` 同构同端点**？影响 `GitCode.java`（API 全配置驱动）、`RepoServiceImpl` L279-314 webhook 硬编码常量、各处 `@Value("https://api.gitcode.com/api/v5/user")`（`RepoServiceImpl` L507、`ProjectConfigServiceImpl` L171、`PrAccessTokenServiceImpl` L56、`NotifyConfigEventHandler` L98、`MergeRequestEventHandler` L104）。若共用则全部不改；若独立域名则需按仓库 host 动态路由 API 地址（架构级改动）。
2. **atomgit 组织主页 URL 路径结构**是否与 gitcode 一致（影响 `OrgLocationUtil#extractLoginFromSegments` 是否需要扩展）。
3. **通过组织同步导入 atomgit 仓后**，gitcode API 返回的 `html_url` 域名形态（影响 `GitCode#mapGitcodeRepoToEntity` L437-450 落库 URL，以及下游按 URL 域名的判断是否闭环）。
4. **`buildRepoUrl` 多域名拼接规则**（4.6）：拼 gitcode.com 还是 atomgit.com，需要业务决策。
5. **配置中心 `code.platform.address` 当前实际值**（仓内 application*.yaml 均未定义，走外部注入），需环境核实。

## 7. 影响面与兼容性

- 数据库：无 DDL 变更，platform 字段值域不变。
- 接口：无对外契约变化。
- 行为变化：仅"atomgit.com URL 之前被拒绝/误判"的场景放行为 gitcode 平台；既有 gitcode.com / gitee / github 行为不变（4.3/4.4 的域名无关解析对既有域名结果等价）。
- 上线顺序建议：配置中心更新 `code.platform.address` 与代码发布同窗口执行；代码侧 4.5 已做双保险，可先发代码后改配置。
