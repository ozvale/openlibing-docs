# Tasks: 修复 openlibing-coderepo 注入类漏洞与命令执行类漏洞

## 实现步骤

### V1: SnakeYAML 不安全反序列化 RCE（CWE-502）

- [x] 1. `NotifyConfigEventHandler.java`：新增 import `LoaderOptions`、`SafeConstructor`
- [x] 2. `NotifyConfigEventHandler.java#parseYaml`：将 `new Yaml()` 改为 `new Yaml(new SafeConstructor(new LoaderOptions()))`
- [ ] 3. 验证：构造含 `!!javax.script.ScriptEngineManager` tag 的恶意 YAML，确认被 SafeConstructor 拒绝
- [ ] 4. 验证：正常 `.notification.yaml` 解析功能不受影响

### V2: MyBatis `${}` ORDER BY SQL 注入（CWE-89）

- [x] 1. `RepoInfoMapper.xml`：将 `order by ${info.sortField} ${info.sortOrder}` 改为 `<choose>/<when>` 白名单
- [x] 2. 白名单键名与 Java 层 `resolveRepoSortField` 输出保持一致（使用 DB 列名：`create_at`、`update_at`、`platform_create_time`、`last_sync_time`）
- [x] 3. sortOrder 白名单仅匹配 `asc`（移除 `ASC` 冗余分支，Java 层已做小写归一化）
- [ ] 4. 验证：4 个白名单字段排序功能正常（createTime → create_at 升序/降序等）
- [ ] 5. 验证：异常 sortField（如 `create_at; DROP TABLE`）回退到 `create_at`
- [ ] 6. 验证：内部接口 `doInternalQueryRepoInfo` 路径排序正常

### V3: URL 查询参数拼接参数污染（CWE-233）

- [x] 1. `SelectServiceImpl.java`：新增 import `URLEncoder`、`StandardCharsets`
- [x] 2. `SelectServiceImpl.java#getSigUser`：4 个字段均使用 `URLEncoder.encode(..., StandardCharsets.UTF_8)`
- [ ] 3. 验证：含 `&`、`#`、`?` 的 community/repo 被 URL 编码
- [ ] 4. 验证：`getSigUser` 调用 sig-info 接口功能正常

### 全量回归

- [ ] 5. webhook 通知配置同步功能正常（GitCode/Gitee 双平台）
- [ ] 6. 仓库列表查询排序、分页功能正常
- [ ] 7. SIG committer 查询与 PR 评审流程正常
