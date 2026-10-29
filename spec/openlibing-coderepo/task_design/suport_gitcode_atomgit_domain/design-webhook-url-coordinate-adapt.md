# 设计报告：外部 URL 反查 repo_info 全链路坐标化适配（域名无关）

> 需求来源：gitcode 平台启用新域名 atomgit.com 后，`isAutoFormat=true` 自动修复功能失效。跟踪日志确认根因：MR webhook payload 中 `project.git_http_url` 返回 **gitcode.com** 域名 URL，而 `repo_info.repo_url` 保存的是用户录入的 **atomgit.com** 域名 URL，`preCommitCheck` 按 repoUrl 全串精确匹配查库失败，请求中断。
>
> 本报告排查 coderepo 仓所有"外部 URL 与 `repo_info.repo_url` 全串匹配"的同类隐患并给出适配方案。前序工作：`62be0ef9`（录入 token 校验坐标比对）、`cb9ee483`（录入唯一性校验坐标比对）——本报告是同一系列问题的第三批收尾。

## 1. 问题模式抽象

域名适配后，同一仓库存在两种合法 URL 形态：

| 来源                             | 域名形态                                         | 示例                                 |
| -------------------------------- | ------------------------------------------------ | ------------------------------------ |
| 用户录入（`repo_info.repo_url`） | atomgit.com 或 gitcode.com（均合法）             | `https://atomgit.com/org1/repo1.git` |
| 平台 API / webhook payload       | 由托管平台决定，atomgit 仓库恒定返回 gitcode.com | `https://gitcode.com/org1/repo1.git` |

此外还有 `.git` 后缀、大小写等形态差异。凡是【外部输入 URL】与【DB repo_url】做**全串等值匹配**的场景，跨域名即失配。

修复口径（与 `62be0ef9`/`cb9ee483` 保持一致）：**比较双方经 `RepoUrlParser.parse` 解析出的平台坐标 `(repoType, owner, repo)`，忽略大小写；任一方解析失败时退回 URL 全串比较兜底**。

## 2. 排查结果清单

### 2.1 P0——自动修复/抑制评论 webhook 链路（本缺陷直接相关，必须修）

均位于 `MergeRequestEventHandler`，`prInfo.repoUrl` 统一取自 webhook payload 的 `project/repository.git_http_url`（gitcode 对 atomgit 仓库返回 gitcode.com 域名）：

| #   | 位置                                                                                   | 现状逻辑                      | 失效表现                                                                                                                                                                                        |
| --- | -------------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `preCommitCheck` L217 `queryWrapper.eq(RepoInfoEntity::getRepoUrl, prInfo.repoUrl)`    | payload URL 全串查 repo_info  | **自动修复不触发**（用户已确认，日志 `No repo config for auto-fix check`）                                                                                                                      |
| 2   | `preCommitCheck` L240 `vo.setRepoUrl(prInfo.repoUrl)`                                  | 将 payload URL 传给 codecheck | 即使 #1 修复，codecheck 侧 `GitCodeHelper.queryRepoInfosByUrl`（L259 `eq(repoUrl)`）查本地 repo_info 仍按 payload URL 全串匹配——若 codecheck 库同步的是录入域名则取不到仓库 token，降级公共账号 |
| 3   | `isSuppressionEnabled` L790 `queryEntity.setRepoUrl(prInfo.repoUrl)` + `queryRepoInfo` | payload URL 全串查 repo_info  | **抑制评论开关判定失效**（日志 `No repoInfo found ... default to suppression disabled`），atomgit 仓库的告警抑制评论功能整体不可用                                                              |
| 4   | `getAccessToken` L832 `queryEntity.setRepoUrl(repoUrl)` + `queryRepoInfo`              | payload URL 全串查 repo_info  | **PR 评论回写取不到 token**（日志 `No repoInfo found ... cannot get access token`）                                                                                                             |

### 2.2 P1——其他外部 URL 反查/比较 DB 的场景（同类必现，本次一并修）

| #   | 位置                                                                          | 现状逻辑                                                               | 失效表现                                                                                                |
| --- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 5   | `PushEventHandler#findRegisteredRepo` L193-201                                | payload 的 `git_http_url/clone_url/html_url` 逐个 `selectByUrl` 精确查 | atomgit 仓库 push 事件（分支创建/删除等）反查 repo_info 全部未命中，push 链路失效                       |
| 6   | `CodeMetricsServiceImpl#resolveFirstRepoByUrl` L773-788                       | 上报 URL 归一化后 `selectByRepoUrl`，仅补 `.git` 后缀重试，无域名兜底  | atomgit 仓库代码度量上报的跳转链接构建失败（旁路增强能力降级）                                          |
| 7   | `RepoServiceImpl` sig 导入 L4685 `existingUrls.contains(repoUrl)`             | sig 任务 URL 与项目内 DB URL 全串比对                                  | 已录入的 atomgit 仓库被判"未导入"重复导入（录入唯一性校验会拦截，但流程报错体验差）；反向形态则可能漏判 |
| 8   | `RepoServiceImpl` 外部仓库接入 L8174 `!existingRepoUrls.contains(url)`        | 组织 API 拉取的 URL 与 DB 全串比对过滤                                 | 已录入仓库被误列在"待录入"列表中                                                                        |
| 9   | `RepoServiceImpl#checkRepoUrl` L9182 `selectByRepoUrl(queryDTO.getRepoUrl())` | 前端录入预检接口按 URL 全串查                                          | 预检漏报：跨域名同仓库提示"可录入"，实际提交被唯一性校验拦截，体验不一致                                |

### 2.3 P2——确认自洽或待确认调用方（本次不改，说明理由）

| #   | 位置                                                                                                                                | 结论                                                                                                                                                                                |
| --- | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10  | `pr_suppression_comment` 表读写（`MergeRequestEventHandler` L1356/L2161 写入、L298 查询，`PrSuppressionCommentMapper.xml` L87/L98） | 读写均为 payload URL，**内部自洽**；P0 #3/#4 修复后功能即恢复。表内 repo_url 与 repo_info 域名不一致属数据一致性瑕疵，如需统一（写入时先反查 DB URL）涉及存量数据迁移，建议单独立项 |
| 11  | `NotifyConfigEventHandler`（`repo_notify_config` 按 webhook URL upsert/查询）                                                       | 读写同源 webhook URL，自洽，同理不动                                                                                                                                                |
| 12  | `RepoTokenServiceImpl#fetch`（L76 `query.setRepoUrls(urls)` → XML `repo_url IN`）                                                   | 对外 HTTP 接口，调用方传入 URL 来源待确认（仓库表全量小、IN 精确匹配是密钥下发接口的谨慎设计）。建议先确认调用方传参形态，再决定是否坐标化                                          |
| 13  | `RepoServiceImpl#internalQueryBranchListByUrl` L1011（XML `selectByRepoUrl`）                                                       | 内部 feign 接口，注释明确"精确匹配是当时设计"；调用方传参形态待确认（传 DB URL 则安全）                                                                                             |
| 14  | codecheck `GitCodeHelper#queryRepoInfosByUrl` L259 `eq(repoUrl)`                                                                    | P0 #2 改传 DB URL 后自然对齐，codecheck 侧无需改动；如需彻底加固（调用方可能传外部 URL 的其他场景）建议 codecheck 单独立项坐标化                                                    |
| 15  | `RepoInfoMapper.xml` L201/L686/L865 动态条件 `repo_url = #{}`                                                                       | 为 #1/#3/#4 与 `queryRepoInfo` 各调用的底层 SQL，调用侧坐标化后此处保留精确匹配作为快路径，无需改动                                                                                 |
| 16  | `RepoServiceImpl` L859（静态告警数回填）                                                                                            | 全量拉取后按坐标解析，无 URL 匹配，安全                                                                                                                                             |
| 17  | `RepoInfoMapper.xml` L868 `repo_url like`                                                                                           | 前端关键字筛选，用户主动行为，语义正确，不属缺陷                                                                                                                                    |

## 3. 修复方案设计

### 3.1 核心：新增统一的"URL 坐标反查 repo_info"公共能力

新增组件 `RepoCoordinateResolver`（`business/service`，或按项目习惯挂到 `CommonService`）：

```java
public interface RepoCoordinateResolver {
  /** 按 URL 坐标反查已录入仓库：优先 URL 全串精确查（快路径），
   *  未命中时解析坐标做域名无关兜底查询（慢路径） */
  List<RepoInfoEntity> resolveByCoordinate(String repoUrl);

  /** 判断两个 URL 是否指向同一代码仓（坐标忽略大小写，解析失败退回全串比较） */
  boolean isSameRepo(String urlA, String urlB);
}
```

实现要点：

1. **快路径**：`repo_url = #{url}` 精确查（命中存量同域名数据，零额外开销，覆盖绝大多数流量）；
2. **慢路径（本次新增）**：快路径未命中时，`RepoUrlParser.parse` 解析 `(repoType, owner, repo)`：
   - 解析失败 → 返回空（与现状一致）；
   - 解析成功 → 按 `platform = repoType` 过滤拉取候选（避免全表），SQL 增加 `repo_url LIKE '%/owner/repo%'` 预过滤缩小候选集，内存中逐条 `RepoUrlParser` 解析比对（忽略大小写）；
3. **比较逻辑复用**：将 `cb9ee483` 引入的坐标比对逻辑（`matchesExistingRepo`）下沉为本组件的静态方法（或迁入 `RepoUrlParser`），`checkRepoUniqueness` 改为调用同一实现，保证全仓唯一比较口径；
4. 组件内全量 try-catch 降级：解析/查库异常时退回"URL 全串查询"结果，**绝不阻断 webhook 主流程**（与既有降级约定一致）。

### 3.2 P0 四点改造（MergeRequestEventHandler）

1. **#1 preCommitCheck**：L216-218 替换为 `repoCoordinateResolver.resolveByCoordinate(prInfo.repoUrl)`；
2. **#2 传 DB URL 下游**（关键决策）：L240 改为 `vo.setRepoUrl(op.getRepoUrl())`——以 DB 录入 URL 作为与 codecheck 及 auto-fix.sh 的契约值。副作用：pre-commit 流水线参数、修复 commit 的 clone 地址均变为录入域名 URL（atomgit.com），git 客户端对两域名均可达，需在测试环境验证 auto-fix.sh clone 通畅；
3. **#3 isSuppressionEnabled**：L789-791 替换为坐标反查；
4. **#4 getAccessToken**：L832-834 替换为坐标反查。

### 3.3 P1 五点改造

| #   | 改造方式                                                                                                                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5   | `findRegisteredRepo` 候选 URL 全部未命中后，追加 `resolveByCoordinate` 兜底一次（保留现有逐候选精确查为快路径）                                                            |
| 6   | `resolveFirstRepoByUrl` 既有 `.git` 重试仍未命中时，追加坐标反查兜底                                                                                                       |
| 7   | `existingUrls.contains(repoUrl)` 替换为：先 `existingRepoByUrl.get(repoUrl)` 快路径，未命中遍历 `existingRepos` 做 `isSameRepo` 坐标比对（项目内集合内存比对，无额外查库） |
| 8   | 同 #7 模式：`allRepoUrls` 过滤时逐个与 `existingRepoUrls` 做坐标比对（先 contains 快路径）                                                                                 |
| 9   | `checkRepoUrl` 改为 `resolveByCoordinate`，与 `cb9ee483` 录入唯一性口径对齐（预检结果与提交行为一致）                                                                      |

### 3.4 性能评估

- webhook 事件量级下，快路径命中时零额外开销；慢路径仅跨域名场景触发，SQL 带 `platform` + `LIKE '%/owner/repo%'` 预过滤，候选集极小；
- #7/#8 为内存比对（项目内/组织内集合），无新增查库；
- `repo_info` 若数据量大，可后续为 `repo_url` 增加反序索引或冗余 `owner/repo` 坐标列（本次不做，当前量级无需）。

## 4. 兼容性分析

- 存量 gitcode.com 录入仓库：payload 与 DB 同域名，快路径命中，行为不变；
- 存量 atomgit.com 录入仓库：由失效转为可用（修复目标）；
- 解析失败的历史脏数据 URL：快路径与现状全串比较行为一致，无回归；
- `vo.repoUrl` 契约变化（#2）：codecheck 侧所有消费点（token 查询、auto-fix.sh、流水线参数）均以 DB URL 为准，需联调验证；如有第三方消费 pre-commit 参数需同步确认。

## 5. 测试设计

单测（`RepoCoordinateResolverTest` + 各改造点所在测试类）：

1. 快路径：同域名 URL 精确命中；
2. 慢路径：payload gitcode.com URL 反查 atomgit.com 录入仓库（核心场景）；
3. 慢路径：大小写差异、`.git` 后缀差异；
4. 双方均解析失败：退回全串比较；
5. 解析异常降级不抛出；
6. `preCommitCheck`：断言 `vo.repoUrl` 为 DB URL（非 payload URL）；
7. `isSuppressionEnabled`/`getAccessToken`：跨域名命中后开关开启、token 获取成功；
8. `findRegisteredRepo`：候选 URL 全部未命中后坐标兜底命中；
9. #7/#8：跨域名仓库不重复导入/不出现在待录入列表；
10. `checkRepoUrl`：跨域名同仓库预检正确报"已存在"。

回归：既有 webhook 相关测试、`RepoServiceImplTest` 全量。

## 6. 待确认问题

1. **#2 传 DB URL**：`vo.setRepoUrl(op.getRepoUrl())` 后 auto-fix.sh 用 atomgit.com 域名 clone，测试环境需验证网络与凭证可用性——请确认是否按此方案执行；
2. **P2 #12/#13**（RepoTokenController 调用方、internalQueryBranchListByUrl 调用方）的传参形态，如有线上日志或调用方代码线索请提供，确认后决定是否纳入本次；
3. **P2 #10/#11**（suppression/notify 表内 URL 域名一致性）是否需要单独立项做存量数据统一，本次默认不动。
