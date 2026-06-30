# 技术方案：接收 repository 字段并删除 feign 改用本地 mapper

## 关键决策

### 决策 1：file_detail 表不加 repository 字段

**选择**：`sec_option_scan_file_detail` 表不冗余存 `repository`，通过 `record_id` 关联 `record` 表获取。

**原因**：

- `repository` 是流水线级别的属性（一条 record 对应一个流水线运行），file_detail 是 record 的子记录
- 冗余存储会引入数据一致性维护成本（同一 record 下所有 file_detail 必须保持 repository 一致）
- 查询时通过 JOIN 即可获取，性能影响可忽略

### 决策 2：buildPipelineLink 保留 gitUrl 降级路径

**选择**：`buildPipelineLink(repository, gitUrl, pipelineRunId)` 优先用 `repository`，为空时降级用 `gitUrl` 解析。

**原因**：

- 历史数据：`sec_option_scan_record` 表中已有的记录没有 `repository` 字段值（changelog 添加列时为 NULL）
- 新数据：插件上报 `repository` 后，优先使用
- 保留 `extractOwnerRepo` 作为降级路径，避免历史数据无法展示流水线链接

```java
private String buildPipelineLink(String repository, String gitUrl, String pipelineRunId) {
    if (StrUtil.isBlank(pipelineRunId)) {
        return "";
    }
    if (StrUtil.isNotBlank(repository) && repository.contains("/")) {
        return gitcodeDomain + "/" + repository + "/actions/runs/" + pipelineRunId;
    }
    String ownerRepo = extractOwnerRepo(gitUrl);
    if (StrUtil.isBlank(ownerRepo)) {
        return "";
    }
    return gitcodeDomain + "/" + ownerRepo + "/actions/runs/" + pipelineRunId;
}
```

### 决策 3：repository 解析放在插件侧而非后端

**选择**：插件负责解析 `repository`（区分场景 A/B），后端只做接收和入库。

**原因**：

- 插件能直接拿到 `ATOMGIT_REPOSITORY` 环境变量和 `git remote` 输出，信息源最完整
- 后端拿不到 `ATOMGIT_REPOSITORY`，只能从 `gitUrl` 推断，无法区分场景 A/B
- 集中解析逻辑在插件侧，避免插件和后端各写一份解析逻辑

### 决策 4：feign → 本地 mapper 替换

**选择**：删除 `CodeRepoClient` feign 接口，新增 `RepoInfoMapper.queryRepoListByProjectId` 方法直接查询 `repo_info` 表。

**原因**：

- 本仓已包含 `repo_info` 表，数据已落地
- 跨服务 feign 调用增加部署耦合（cicd-fork 启动依赖 coderepo 服务可用）
- 跨服务调用增加故障传播面（coderepo 服务异常会影响 sec-option-scan 查询）
- 本地 mapper 查询性能更好（无网络开销）

**SQL 设计**：

```sql
SELECT repo_name AS repoName, repo_url AS repoUrl
FROM repo_info
WHERE project_id = #{projectId} AND assume_pr = '1'
  AND repo_url IS NOT NULL AND repo_url != ''
```

- 仅查询 `assume_pr='1'` 的仓（接管 PR 的仓，与原 feign 接口语义一致）
- 仅返回 `repoName + repoUrl`（最小字段集，避免数据冗余）
- 返回类型 `List<Map<String, String>>`（不引入新实体类，与原 feign 返回类型一致）

### 决策 5：changeset 含 precondition + rollback

**选择**：Liquibase changeset 包含 `<preConditions onFail="MARK_RAN">` 和 `<rollback>`。

**原因**：

- `preConditions` 确保列不存在时才添加，避免重复执行报错
- `rollback` 提供回滚路径，便于紧急回退
- `MARK_RAN` 策略：precondition 失败时标记为已执行，不阻断后续 changeset

## 影响范围

### 修改文件

| 文件 | 变更类型 |
|------|---------|
| `SecOptionScanReportDTO.java` | 新增字段 |
| `SecOptionScanRecordEntity.java` | 新增字段 |
| `RepoInfoMapper.java` | 新增方法 |
| `RepoInfoMapper.xml` | 新增 SQL |
| `SecOptionScanServiceImpl.java` | 重构 fetchGitUrlsByProjectId + buildPipelineLink |
| `CodeRepoClient.java` | 删除 |
| `db.changelog.xml` | 新增 changeset |

### 数据库变更

- 新增列：`sec_option_scan_record.repository VARCHAR(128) NULL`
- 新增索引：`idx_sec_option_record_repository`

### 兼容性

- 新增列允许 NULL，历史数据不受影响
- `buildPipelineLink` 保留 gitUrl 降级路径，历史数据可正常展示流水线链接
- feign 接口删除前已确认仓库内无其他调用方
