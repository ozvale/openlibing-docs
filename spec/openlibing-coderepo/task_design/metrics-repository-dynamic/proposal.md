# openlibing-coderepo: 代码度量流水线链接支持动态仓路径

## 需求背景

`code-metrics-scan` 后端服务（位于 `openlibing-coderepo` 仓）在构建流水线链接时存在路径错误问题，本变更与 `openlibing-cicd` 仓的 sec-option-scan 改动配套，共同修复流水线链接仓路径拼接问题。

### 问题：流水线链接拼接依赖硬编码域名路径

`CodeMetricsServiceImpl.buildPipelineLink` 当前将 `gitcodeDomain` 配置为完整路径前缀（如 `https://test.gitcode.net/weeknd/test-devops/actions/runs/`），直接拼接 `pipelineRunId` 生成链接。这导致：

1. **不同仓库无法共用配置**：每个仓库需要单独配置 `gitcodeDomain`，无法统一管理
2. **测试环境域名切换困难**：测试环境使用 `test.gitcode.net`，生产使用 `gitcode.com`，切换时需修改配置并重新部署
3. **与插件侧 repository 字段不匹配**：插件已新增 `repository`（owner/repo 格式）字段上报，后端未接收和存储

## 验收标准

- [x] `CodeMetricsReportDTO` 新增 `repository` 字段
- [x] `CodeMetricsRecordEntity` + `code_metrics_record` 表新增 `repository` 列
- [x] Liquibase changelog 完整（含 precondition + rollback）
- [x] `gitcodeDomain` 配置改为仅存储基础域名（如 `https://test.gitcode.net`）
- [x] `buildPipelineLink` 使用 `repository` 字段动态拼接链接，`repository` 为空时降级到仅用 `pipelineRunId`
- [x] `selectByPipelineRunId` 查询包含 `repository` 列
- [x] Controller 日志增加 `repository` 字段打印
- [x] DTO 内部类 `BigDecimal` 引用统一使用 import 而非全限定名

## 关联 Issue

- openlibing/openlibing-coderepo#（待关联）

## 关联 PR

- openlibing/openlibing-coderepo#（待关联）
