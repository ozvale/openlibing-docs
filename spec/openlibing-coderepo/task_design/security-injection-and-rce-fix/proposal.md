# Proposal: 修复 openlibing-coderepo 注入类漏洞与命令执行类漏洞

## 需求背景

依据 `opencode-agents-main` 深度安全审计框架对 `openlibing-coderepo` 进行深度审计，聚焦注入类漏洞（D1: SQL/NoSQL/命令/SSTI/JNDI/SpEL 注入）与命令执行类漏洞（D4: 反序列化/RCE/脚本引擎/JNDI/表达式注入），采用 sink-driven + taint-analysis 方法论，发现 5 处可疑问题。

经真实性复核（Source 真实性 → 可达性 → 净化有效性三重验证）与必要性评估，确认 **3 处需要修复**，2 处当前不可利用暂不修改：

| 编号 | 严重度 | CWE | 问题 | 修复状态 |
|------|--------|-----|------|---------|
| V1 | 🔴 高 | CWE-502 | SnakeYAML 不安全反序列化 RCE | ✅ 已修复 |
| V2 | 🟡 中 | CWE-89 | MyBatis `${}` ORDER BY SQL 注入 | ✅ 已修复 |
| V3 | 🟡 中 | CWE-233 | URL 查询参数拼接参数污染 | ✅ 已修复 |
| V4 | 🟡 中 | — | Webhook owner/repo 路径拼接 | ❌ 不修复（三层防护） |
| V5 | 🟡 中 | CWE-117 | 日志注入 CRLF | ❌ 不修复（已有 logback 缓解） |

### V1: SnakeYAML 不安全反序列化 RCE

**位置**：`NotifyConfigEventHandler.java#parseYaml`（第 411-417 行）

**问题**：`new Yaml()` 默认使用 `Constructor`，会通过 `!!javax.script.ScriptEngineManager` 等 YAML tag 触发任意 Java 类实例化（CWE-502 反序列化 RCE）。

**数据流**：
```
Webhook Merge Request Hook
  → WebHookEventController.handleGitCodeEvent (HMAC 签名校验)
  → NotifyConfigEventHandler.handle
  → readYamlFile (GitCode/Gitee API 读取仓库 master 分支 .notification.yaml)
  → parseYaml(yamlContent)
  → new Yaml().load(content)  ← RCE Sink
```

**Source 真实性**：TRUE_SOURCE — 拥有仓库写权限的开发者/CI 账号可向 master 分支推送恶意 `.notification.yaml`。

**修复方式**：`new Yaml(new SafeConstructor(new LoaderOptions()))`，限制反序列化类型为标准 Java 集合/基本类型。

### V2: MyBatis `${}` ORDER BY SQL 注入

**位置**：`RepoInfoMapper.xml` 第 269 行

**问题**：`order by ${info.sortField} ${info.sortOrder}` 使用字符串直接插值（MyBatis `${}` 机制），存在 SQL 注入风险。

**当前缓解**：`RepoServiceImpl.queryRepoInfo` 已使用 `resolveRepoSortField()` 白名单映射 DTO 字段名到 DB 列名；但内部接口 `doInternalQueryRepoInfo` 未调用白名单，存在"安全债务"。

**修复方式**：MyBatis XML 改用 `<choose>/<when>` 白名单，彻底消除 `${}` sink。白名单键名必须与 Java 层 `resolveRepoSortField` 的输出（DB 列名）一致：
- `create_at`、`update_at`、`platform_create_time`、`last_sync_time`
- sortOrder 仅匹配 `asc`（Java 层 `resolveRepoSortOrder` 已做小写归一化）

### V3: URL 查询参数拼接参数污染

**位置**：`SelectServiceImpl.java#getSigUser`（第 131 行）

**问题**：`sigUserUrl + "?community=" + community + "&repo=" + repo + ...` 未做 URL 编码，参数边界（`&`、`#`、`?`）绕过可导致参数污染。

**数据流**：
```
repoInfoEntity.getRepoUrl() → split("/") 解析出 community/repo
  → getSigUser(community, community + "/" + repo, "committer", "repo")
  → URL 拼接 → HttpRequestUtil.sendGet(url)
```

**Source**：`community`/`repo` 来自数据库 `repoUrl` 解析，间接用户可控（通过录入仓库接口写入）。

**修复方式**：4 个字段均使用 `URLEncoder.encode(..., StandardCharsets.UTF_8)`。

### V4/V5 不修复理由

| 编号 | 不修复理由 |
|------|-----------|
| V4 | 三层防护（HMAC-SHA256 签名 + 平台规范化 + HTTP 客户端校验）已足够；已通过 1536 条现有仓库数据 100% 符合 `[A-Za-z0-9_.-]+` 规范 |
| V5 | logback-spring.xml 已配置 `%replace` 替换控制字符；本地日志文件不直接对外暴露 |

## 验收标准

1. V1：使用恶意 YAML（含 `!!javax.script.ScriptEngineManager` 等 tag）测试 `parseYaml`，应被 SafeConstructor 拒绝（抛 ConstructorException），服务不崩溃
2. V1：正常 `.notification.yaml` 解析功能不受影响（notifications 配置同步正常）
3. V2：构造异常 sortField（如 `create_at; DROP TABLE`）测试，应回退到 `create_at` 缺省值
4. V2：4 个白名单字段（createTime/updateTime/platformCreateTime/lastSyncTime）排序功能正常，排序结果与修复前一致
5. V2：内部接口 `doInternalQueryRepoInfo` 路径不再受异常 sortField 影响
6. V3：构造含 `&`、`#`、`?` 的 community/repo 测试，应被 URL 编码为 `%26`、`%23`、`%3F`
7. V3：`getSigUser` 调用 sig-info 接口功能正常
8. 全量回归：webhook 通知配置同步、仓库列表查询、sig committer 查询三大功能链路无回归

## 关联

- 业务仓 Issue：openlibing/openlibing-coderepo#65
- 业务仓 PR：openlibing/openlibing-coderepo!85
- 修复分支：`security-injection-and-rce-fix`
