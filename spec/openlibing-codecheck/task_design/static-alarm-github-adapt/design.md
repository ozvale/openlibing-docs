# 代码检查页 Github 结果展示与处理适配 - 技术设计

## 1. 方案设计

静态告警主链路（接收 → 存储 → SARIF 解析 → 聚合查询 → 屏蔽/指派/清理 → 告警数推送）对平台基本无感知，`repoType/owner/repo` 贯穿全链路透传。本次改造集中在接收入口与两个基础能力：

1. **来源枚举扩展**：`StaticAlarmSourceEnum` 新增 `GITHUB_ACTION`、`GITEE_ACTION`，并提供按平台推断来源的能力。
2. **来源缺省处理**：去掉固定兜底 `GITCODE_ACTION`，改为按解析出的 `repoType` 推断，并打 WARN 日志。
3. **平台识别可扩展**：`RepoUrlParser` 保留内置关键字匹配，新增可配置域名关键字，兼容 GitHub Enterprise 自定义域名。
4. **OBS 白名单扩展**：默认白名单增加 GitHub Action 桶，仍支持 Nacos 覆盖。
5. **防绕过**：上报入参 `repoType` 与 `repoUrl` 解析结果不一致时拒绝。

不改动 `CodePlatformUtil`、`CodePlateHelper`、`CheckboardDelegateImpl`、`ProblemshieldDelegateImpl`：这些属于代码检查执行链路与非静态告警页面，当前平台尚未全面接入 GitHub，改动会扩散风险且与本次需求无关。

## 2. 实现逻辑设计

### 2.1 接收流程

```
StaticAlarmReceiveController
  → StaticAlarmReceiveServiceImpl.receive(dto)
     → RepoUrlParser.parse(repoUrl, 额外域名关键字)
        解析失败 → 返回失败，不入库
        解析成功 → repoType/owner/repo
     → repoType 一致性校验（dto.repoType 非空且与解析结果不一致 → IllegalArgumentException）
     → source 处理
        显式传入 → 枚举校验，非法则拒绝（source 表示上报载体，与平台无强绑定，不做交叉校验）
        未传     → 按 repoType 推断（github→GITHUB_ACTION / gitee→GITEE_ACTION / gitcode→GITCODE_ACTION）
                  推断成功且为兜底 → WARN 日志（含 repoUrl、pipelineId、pipelineRunId）
                  无法推断（如 codehub）→ IllegalArgumentException，要求显式传入
     → resolveProjectIds(repoUrl)（坐标反查，委托 RepoInfoCoordinateResolver）
     → 写 static_alarm_scan_run → 发 MQ
```

### 2.2 平台识别优先级

1. 配置的域名关键字（`codecheck.repo-host-keywords`，按配置顺序）
2. 内置关键字：`gitcode` / `atomgit`→gitcode、`gitee`→gitee、`github`→github、`codehub`→codehub

配置仅做补充与优先覆盖，未配置时行为与现状完全一致。配置约束：

- 匹配对象是从 URL 解析出的 host（已转小写），采用包含匹配，不对整条 URL 做子串匹配。
- 平台值仅支持 `gitcode` / `gitee` / `github` / `codehub`（大小写不敏感，统一转小写）；配置其它值时该项被忽略并记 WARN，该 host 回退到内置关键字匹配，仍无法识别则 `repoUrl` 解析失败、上报被拒绝（fail-closed）。
- 同一关键字重复配置时后者覆盖前者，并记 WARN；配置关键字优先级高于内置关键字，不校验与内置关键字的冲突；误配（如 `gitcode:github`）会把对应平台判错，配置后需按域名逐一验证。

### 2.3 兼容性

- 显式传 source 的上报方（CICD 传 `HUAWEI_PIPELINE`、GitCode Action 传 `GITCODE_ACTION`）行为不变；已核验 CICD 侧 DTO 默认值即为 `HUAWEI_PIPELINE`，仓内不存在依赖缺省 source 的调用方。`source` 表示上报载体，与仓库托管平台无强绑定关系，因此不做交叉校验。
- 未传 source 且平台无对应来源枚举（如 codehub）的上报，由改动前的"入库为 `GITCODE_ACTION`"变为拒绝入库；该类上报方接入前必须显式传 source。
- 存量 `repoType=gitcode/gitee` 数据不受影响。
- 新增枚举值不会改变已有数据的读写口径。

### 2.4 配置项与兜底值

| 配置项                               | 是否必配 | 代码兜底值                                                                                                                     | 说明                                                                                                                                                                                      |
| ------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `codecheck.alarm.obs-host-whitelist` | 否       | `openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com,openlibing-github-action.obs.cn-southwest-2.myhuaweicloud.com` | 当前 Nacos 未配置该项，走代码默认双桶；若后续显式配置，必须同时包含两个桶，否则会覆盖默认值导致 GitHub SARIF 下载被白名单拒绝                                                             |
| `codecheck.repo-host-keywords`       | 否       | 空 Map，仅使用内置关键字 `gitcode` / `atomgit` / `gitee` / `github` / `codehub`                                                | 仅 GitHub Enterprise 自定义域名需要在 Nacos 配置，格式 `域名关键字:平台`，如 `git.corp.example.com:github`；关键字按 host 包含匹配，平台值限定 `gitcode` / `gitee` / `github` / `codehub` |

两项均未在 Nacos 配置，本次上线不需要变更任何配置；`code.platform.address` 在静态告警链路中未被引用，无需增加 github 项（问题屏蔽页的 GitHub 用户主页链接不在本次范围）。

## 3. 类设计

| 类                                | 改动                                                                                                                          |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `StaticAlarmSourceEnum`           | 新增 `GITHUB_ACTION`、`GITEE_ACTION`；新增 `inferByRepoType(String)` 静态方法                                                 |
| `StaticAlarmReceiveDTO`           | 删除 `DEFAULT_SOURCE_CODE` 常量；`source` 字段注释补充取值                                                                    |
| `StaticAlarmReceiveServiceImpl`   | 注入域名关键字配置；新增 repoType 一致性校验、source 推断、WARN 日志                                                          |
| `RepoUrlParser`                   | 新增 `parse(String, Map<String,String>)` / `isSameRepo(String, String, Map<String,String>)` 重载；内置映射抽为不可变常量      |
| `RepoHostKeywordSettings`（新增） | `@Value("${codecheck.repo-host-keywords:}")` + `@RefreshScope`，解析为不可变 `Map<String,String>`，含平台值白名单校验，默认空 |
| `RepoInfoCoordinateResolverImpl`  | 坐标反查调用带额外关键字的重载                                                                                                |
| `SarifParseServiceImpl`           | OBS 白名单默认值增加 GitHub Action 桶                                                                                         |
| 实体 / VO / DTO 注释              | repoType、source 取值说明补充 github / GITHUB_ACTION / GITEE_ACTION                                                           |

## 4. 数据模型设计

无数据库结构变更。

- `static_alarm_scan_run.repo_type` 新增取值 `github`（字符串，无需 DDL）。
- `static_alarm_scan_run.source` / `static_alarm_issue_instance.source` / history.source 新增取值 `GITHUB_ACTION`、`GITEE_ACTION`（字符串，无需 DDL）。
- Mongo 索引按 `repo_type` 建立，天然覆盖新平台，无需新增索引。

## 5. 性能设计

无额外性能开销：新增逻辑均为内存字符串匹配与枚举查找，调用次数与现有单次上报一致。域名关键字配置为启动时加载的不可变 Map。

## 6. API 接口设计

无接口签名变更。

- `POST /internal/codescan/v1/result/receive`：`source`、`repoType` 取值集合扩展；缺省行为由"固定 GITCODE_ACTION"改为"按平台推断"。
- 静态告警查询类接口：返回字段 `repoType`、`source` 新增取值，前端需要补充展示映射。

## 7. 安全设计

1. **防伪造**：`repoType` 与 `repoUrl` 解析结果不一致时拒绝，避免调用方绕过接口伪造平台归属；`source` 表示上报载体（华为云流水线 / 各平台 Action），与平台无强绑定关系，仅做枚举合法性校验，不做交叉比对。
2. **SSRF 防护**：OBS 下载白名单仍为强校验，仅新增明确的 GitHub Action 桶域名；host 为精确匹配，白名单域名的子域名或后缀拼接域名均被拒绝；仍禁止重定向。
3. **日志安全**：新增 WARN 日志仅输出仓库地址、流水线标识，不输出 token 等敏感信息；URL 统一经 `LogSanitizer` 处理。
4. **配置安全**：域名关键字配置不参与鉴权，但会决定解析出的 `repoType`，进而影响 repoType 一致性与 source 推断结果；约束为按 host 包含匹配（不对整条 URL 匹配）、平台值限定 `gitcode` / `gitee` / `github` / `codehub`，非法平台值的配置项被忽略并记 WARN。误配会导致平台判错或上报被拒（fail-closed），不会放开任何接口访问控制。
