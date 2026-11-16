# openlibing-anti-poison release_20261116_iter1 发布报告

- **发布分支**：release_20261116_iter1
- **合入 commit**：97222dd（!139 merge safe_202611 into release_20261116_iter1）
- **业务 PR**：openlibing/openlibing-anti-poison#139（safe_202611 → release_20261116_iter1，49 files，+5605/−988）
- **发布日期**：2026-11-16
- **提交规模**：73 commits（Richard-bean 71、zhaoyanzhen 1、openLiBingCI 1）

## 一、Issue 交付清单

| issueID | issue名称                                                                             | 责任人       | 评审结果 | 日期       |
| ------- | ------------------------------------------------------------------------------------- | ------------ | -------- | ---------- |
| #70     | 任务规则集更新接口缺少规则集归属社区一致性校验                                        | Richard-bean | 通过     | 2026-11-16 |
| #71     | 删除 4 个已废弃且无权限控制的查询接口                                                 | Richard-bean | 通过     | 2026-11-16 |
| #30     | 【安全】【墨菲扫描】由于调试信息不明确而导致的敏感系统信息泄露                        | Richard-bean | 通过     | 2026-11-16 |
| #31     | 【安全】【SENINFO】恶意代码执行&&系统命令注入                                         | Richard-bean | 通过     | 2026-11-16 |
| #33     | 凭据随 git/curl 命令出现在进程命令行                                                  | Richard-bean | 通过     | 2026-11-16 |
| #34     | 【提权专项】命令注入与提权风险、路径/软链接校验缺失、镜像构建期压缩包投毒防护         | Richard-bean | 通过     | 2026-11-16 |
| #35     | 【安全】PR 差异文件下载/复制链路 Shell 命令注入与路径穿越、ExecCmdUtil 字符串执行命令 | Richard-bean | 待验收   | 2026-11-16 |
| #36     | 【安全】全站接口未鉴权（红线 B-01/B-02）及命令注入、SSRF、凭据泄露等 16 项整改        | Richard-bean | 通过     | 2026-11-16 |
| #40     | 【安全】PR 扫描命令字符串拼接 workspace 导致命令注入风险                              | Richard-bean | 通过     | 2026-11-16 |
| #41     | 【安全】PR URL 解析未验证导致服务器端请求伪造（SSRF）                                 | Richard-bean | 通过     | 2026-11-16 |
| #52     | 【安全】问题屏蔽申请与审批接口 userId 参数可伪造导致授权绕过                          | Richard-bean | 通过     | 2026-11-16 |
| #55     | 【安全】【H-0005】YARA 编译规则被误删导致 Java 防投毒扫描规则静默失效                 | Richard-bean | 待验收   | 2026-11-16 |
| #60     | 【安全】【redos】/checkRule/query/rules desc 参数 ReDoS 及转义逻辑缺陷                | Richard-bean | 通过     | 2026-11-16 |
| #61     | 【安全】【CSV 注入】/checkRule/query/export/rules 导出防御缺陷及规则创建校验不全      | Richard-bean | 通过     | 2026-11-16 |
| #62     | 【安全】【敏感信息泄露】/action-pr/scan 接口打印明文 accessToken 及 password          | Richard-bean | 通过     | 2026-11-16 |
| #63     | 【安全】【权限控制不当】屏蔽申请可添加任意用户为审核对象                              | Richard-bean | 通过     | 2026-11-16 |
| #64     | 【安全】【冗余接口】多个接口疑似废弃且存在安全问题                                    | Richard-bean | 待验收   | 2026-11-16 |
| #65     | 【安全】【认证鉴权】多个 web 接口资源权限控制不当存在越权访问风险                     | Richard-bean | 通过     | 2026-11-16 |
| #66     | 【安全】【审计日志】多个接口无审计日志记录                                            | Richard-bean | 通过     | 2026-11-16 |
| #67     | 【安全】【认证鉴权】多个 APIG 接口无权限控制                                          | Richard-bean | 通过     | 2026-11-16 |

注：#35/#55/#64 三个 issue 状态仍为 open，主要整改项已随本迭代交付，遗留验收项见各 issue spec 归档（openlibing/openlibing-docs#1352）。

## 二、变更概要

### 1. 安全加固（对应 #30-#67 共 18 项安全 issue）

- **命令注入/RCE（#31/#35/#40/#41）**：PR 代码克隆/差异下载改用 JGit + OkHttp Basic Auth 替代 token 内嵌 shell 命令；命令黑名单增强引号与空白处理；阻断路径穿越与空字节；PR URL 严格前缀校验 + 禁用 HTTP 重定向防 SSRF。
- **鉴权与越权（#36/#52/#63/#65/#67/#70）**：全站接口补齐项目成员/仓库权限校验；屏蔽申请审核人存在性与仓库权限校验、禁止自审批、撤销限原审核人；updateTaskRule 增加规则集归属社区一致性校验；门禁任务查询校验 repo/branch 归属。
- **提权与文件安全（#34）**：tar 解压路径包含校验、软链接目标预检、既有文件属主与权限检查；镜像构建期压缩包投毒防护（Dockerfile tar 条目穿越检查）。
- **注入防御（#60/#61）**：规则查询正则转义修复防 ReDoS；Excel/CSV 公式注入前缀扩展与预编译校验。
- **敏感信息（#30/#33/#62）**：accessToken 全链路迁移至 Authorization 头；日志脱敏（不再打印含凭据的 PR 信息与内部错误细节）。
- **审计与治理（#64/#66/#71）**：关键接口补审计日志；删除 4 个废弃无权限查询接口及下拉/查询死代码（getPoisoningSelect、getPRPoisoningSelect、poisonPrquery、ExecCmdUtil）。

### 2. 缺陷修复

- gama/prod 环境 MongoDB TLS 连接恢复（Nacos URI 不带 tls=true 时强制 SSL）
- PR 任务组按 create_time 排序修复聚合乱序
- gitee pull ref 缺失时回退获取 gitcode merge-requests ref

### 3. 依赖与工程

- openlibing-common 1.0.21.2 → 1.0.21.5
- UT 行覆盖率提升至 67.68%（全仓）；AntiMainUtilTest 跨平台（Linux CI）修复
- 新增 6 个 YARA 密码扫描预编译规则

## 三、提交清单（73 commits）

```text
97222dd !139 merge safe_202611 into release_20261116_iter1
e8df01e chore(tools): add precompiled YARA rules and harden Dockerfile tar extraction
97ce3b4 refactor(util): remove unused ExecCmdUtil class
b218341 refactor(shield): remove getPoisoningSelect and getPRPoisoningSelect dead code
c93d45f refactor(poison): remove poisonPrquery dead code and related tests
e01da86 build(deps): upgrade openlibing-common to 1.0.21.5
0348048 fix(selection): enforce project member check on getPoisonSummaryProject
1f804bc test(ut): decouple validatePath test data from platform separator
2e66528 test(ut): make AntiMainUtilTest platform-neutral for Linux CI
d93225b fix(mongo): restore TLS for gama/prod MongoDB connections
8e8b039 Merge branch 'safe_202611_beta' into safe_202611
3e76493 refactor(controller): remove 4 deprecated unauthenticated query endpoints
96c193c Merge branch 'safe_202611' into safe_202611_beta
158bde7 fix(check-rule): validate task rule set belongs to repo project
fd82882 test(ut): raise line coverage to 67.68% with unit tests
27afde0 test(ut): align stale expectations with security-hardened behavior
6558b71 fix(docker): invert symlink pre-check condition for awk exit code
72d80de fix(docker): refine symlink target pre-check to avoid false blocks
af9e031 fix(docker): reject unsafe symlink targets in tar pre-check
31c1298 fix(file): enforce owner and permission checks on existing files
5c492f5 fix(shield): sort PR task group by create_time before aggregation
3d7cc34 fix(log): avoid leaking internal error details to clients
2643088 fix(pr-scan): harden path containment and tar extraction
53e40e2 fix(scan): align separator in path prefix validation
cc3f33d fix(pr-scan): pin raw_url host by strict prefix
bce9d1c fix(export): sanitize Excel cells against formula injection
efe1791 fix(shield): restrict select endpoints to GET
6eb5158 style(aop): apply google-java-format to TaskRuleHandler
2c71a92 Merge branch 'zyz_202611' into safe_202611
d482b03 fix(shield): enforce referral authorization rules
4d39258 fix(shield): restrict audit-pass revoke to original reviewer
662867a refactor(shield): dedupe auditAuth branches
ca17dc7 fix(shield): block self-approval in audit auth
ecbd2c3 fix(shield): switch audit approval to repo permission check
ac89f11 refactor(shield): fail-fast applicant check in revoke
42d83f2 fix(shield): harden shield revoke authorization
6c3cc03 fix(shield): reject cross-scan-task detailsId batches
0be34eb 审计日志补充
fcebc9a fix(shield): resolve repo from scan task for apply auth
40f70b5 fix(shield): enforce membership on audit approval endpoints
a99d5f2 docs(shield): annotate reviewer validation steps in shield apply
63e4e27 fix(shield): validate reviewer existence and repo permission on apply
73d2126 fix(checkcenter): validate repo and branch ownership before task query
6b57acc test(shield): cover project membership checks on scan result endpoints
4f6f30b fix(shield): enforce project membership on scan result queries
ef52cac fix(checkrule): reject blank-id rule set config query directly
71b1215 fix(checkrule): require project permission for blank-id rule set config query
216d42a fix(checkrule): verify rule set ownership before update in createRuleSet
f4e3da3 chore(util): remove obsolete duplicate LinuxCommandInjectCheck
a9a9a93 fix(pr-scan): block path traversal and null bytes in command blacklist
05c5b3b fix(pr-scan): fetch gitcode merge-requests ref when gitee pull ref missing
3679d0d fix(pr-scan): validate projectName in pr scan queue entry
ca39cdd fix(pr-scan): harden pr url parsing and disable http redirects against ssrf
a3fa815 fix(checkrule): fix regex escaping and add ruleDesc validation in rule query
d142fc8 fix(checkrule): clarify rule param validation error message
c5b729c fix(checkrule): validate remaining rule fields against CSV injection
57687f1 fix(export): extend CSV formula-injection prefixes and precompile pattern
5f77dcc fix(pr-scan): drop prInfo log line from action scan entry
037d1f7 fix(pr-scan): avoid logging PR info with credentials in action scan
413a6a7 style(pr-scan): apply google-java-format to security refactor files
e101108 chore(api): remove deprecated endpoints from controllers
a360f66 Merge branch 'safe_202611' into safe_202611_beta
d30fd54 fix(pr-scan): restore Locale import removed with shell command helpers
550b872 fix(pr-scan): correct RefSpec package and StandardCharsets import
adc5cc6 fix(scan): harden command injection blacklist with quoting and whitespace
3b8e7d4 refactor(pr-scan): remove unused gitlab diff download path
abaeb86 fix(pr-scan): download diff files via OkHttp Basic Auth instead of curl
843666f fix(scan): validate repoName, rulesName and info scanId before scan command
bec983b fix(pr-scan): clone and fetch PR code via JGit instead of token-embedded shell
e37d636 fix(pr-scan): clone PR code via JGit credentials instead of shell command
4478887 beta配置MongoDB恢复
e1681be fix(pr-scan): move all remaining access tokens from URL query to Authorization header
8a3b191 fix(pr-scan): pass access token via Authorization header instead of URL query
```
