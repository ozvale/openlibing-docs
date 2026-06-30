# 技术方案：代码度量流水线链接支持动态仓路径

## 关键决策

### 决策 1：gitcodeDomain 从完整路径改为基础域名

**选择**：`gitcodeDomain` 配置从 `https://test.gitcode.net/weeknd/test-devops/actions/runs/` 改为 `https://test.gitcode.net`。

**原因**：

- 完整路径写死了仓路径（`weeknd/test-devops`），无法适配不同仓库
- 改为基础域名后，由 `buildPipelineLink` 运行时拼接 `{domain}/{repository}/actions/runs/{runId}`
- 测试/生产环境切换只需改一个域名，不需要知道具体仓库路径

### 决策 2：buildPipelineLink 接收 repository 参数动态拼接

**选择**：`buildPipelineLink(repository, pipelineRunId)` 优先用 `repository` 拼接，`repository` 为空时回退到仅拼接 `pipelineRunId`。

**原因**：

- 新数据：插件上报 `repository` 后，优先使用，生成正确的 `/{owner}/{repo}/actions/runs/{runId}` 链接
- 历史数据：`repository` 为空时回退到原有逻辑（`gitcodeDomain + pipelineRunId`），保证历史数据仍可展示
- `repository` 为 `owner/repo` 格式，合法值必含 `/`，空值或不合法值自动降级

```java
private String buildPipelineLink(String repository, String pipelineRunId) {
    if (StringUtils.isBlank(pipelineRunId)) {
        return "";
    }
    if (StringUtils.isNotBlank(repository)) {
        return gitcodeDomain + "/" + repository + "/actions/runs/" + pipelineRunId;
    }
    // repository 为空时回退到仅拼接 pipelineRunId（兼容历史数据）
    return gitcodeDomain + pipelineRunId;
}
```

### 决策 3：repository 解析放在插件侧而非后端

**选择**：插件负责解析 `repository`（区分场景 A/B），后端只做接收和入库。

**原因**：

- 插件能直接拿到 `ATOMGIT_REPOSITORY` 环境变量和 `git remote` 输出，信息源最完整
- 后端拿不到 `ATOMGIT_REPOSITORY`，只能从 `gitUrl` 推断，无法区分场景 A/B
- 集中解析逻辑在插件侧，避免插件和后端各写一份解析逻辑

### 决策 4：selectByPipelineRunId 查询包含 repository 列

**选择**：在 `selectByPipelineRunId` 查询的 SELECT 列表中增加 `repository`。

**原因**：

- `getFileDetail` 方法需要从 record 中获取 `repository` 来构建流水线链接
- 原查询只返回部分列，缺少 `repository` 会导致 `buildPipelineLink` 无法获取该值

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
| `CodeMetricsController.java` | 日志增加 repository 字段 |
| `CodeMetricsReportDTO.java` | 新增 repository 字段 + BigDecimal import 优化 |
| `CodeMetricsRecordEntity.java` | 新增 repository 字段 |
| `CodeMetricsServiceImpl.java` | 重构 buildPipelineLink + reportMetrics 存储 repository |
| `db.changelog.xml` | 新增 changeset |
| `CodeMetricsRecordMapper.xml` | resultMap 增加 repository + selectByPipelineRunId 增加 repository 列 |
| `CodeMetricsServiceImplTest.java` | gitcodeDomain 测试值更新为基础域名 |

### 数据库变更

- 新增列：`code_metrics_record.repository VARCHAR(255) NULL`

### 兼容性

- 新增列允许 NULL，历史数据不受影响
- `buildPipelineLink` 保留回退路径，历史数据可正常展示流水线链接
- `gitcodeDomain` 配置值变更需同步更新部署配置
