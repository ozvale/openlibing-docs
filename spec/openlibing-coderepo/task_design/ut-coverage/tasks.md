# UT 覆盖率上报与分支管理页展示 — 实现任务

## 进度: 0/4 complete

## 说明

- 关联 Issue：openlibing/openlibing-codecheck#190
- 三仓分支：coderepo/web = `feat-ut-coverage`；插件 = `feat-ut-coverage`；docs = `spec/openlibing-coderepo/ut-coverage`
- 存储方案（用户最终确认）：最新数据存分支表 `repo_branch` 新增字段；历史数据新建 `code_ut_record` 表；页面从分支表读最新

## Task 1: coderepo 后端（机机接口 + MQ + OBS + 双表存储 + 分支联动）

- [ ] Liquibase：changeSet 1 给 `repo_branch` 新增 6 字段（ut_line_coverage/ut_branch_coverage/ut_method_coverage/ut_class_coverage/ut_pipeline_run_id/ut_detection_time）；changeSet 2 新建 `code_ut_record` 表
- [ ] `CodeUtRecordEntity`（历史表实体，4 覆盖率可空 + coverageFileDetailJson）
- [ ] `CodeUtRecordMapper` / `CodeUtRecordMapper.xml`：insert、selectLatestByGitUrlBranch、selectByGitUrlBranchRunId
- [ ] `RepoBranchInfoEntity`：新增 6 个 UT 字段
- [ ] `RepoBranchInfoMapper.xml`：新增 upsert UT 覆盖率 UPDATE（按 repoId+branchName）
- [ ] `ObsBucketServiceImpl`：downloadToTempFile 前缀白名单扩展 `ut-coverage-action/`
- [ ] `UtCoverageReportDTO` / `UtCoverageFileDetailQueryDTO` / `UtCoverageFileDetailVO` / `UtCoverageFileItemVO` / `BranchUtCoverageVO`
- [ ] `UtCoverageRabbitConfig`（新队列 `ut_coverage_import_queue`）+ `UtCoverageImportConsumer`（复用 codeMetricsListenerContainerFactory）
- [ ] `UtCoverageService` / `UtCoverageServiceImpl`：OBS 下载 → JSON 解析 → 双写（历史表插入 + 分支表 upsert）→ 幂等（gitUrl+branchName+pipelineRunId）；下钻查询
- [ ] `UtCoverageController`：POST /coverage/ut/report + POST /coverage/ut/file-detail
- [ ] `RepoServiceImpl` / `RepoBranchInfoVO` / `ProjectBranchInfoVO`：queryRepoBranchInfo + buildProjectBranchInfoList 补充 utCoverage
- [ ] `application.yaml`：新增 `ut_coverage_import_queue` 配置
- [ ] 单元测试：DTO 校验、解析入库、双写、查询隔离、前缀白名单
- [ ] 验证：mvn 编译 + 相关单测通过

## Task 2: web 前端（分支页列 + 下钻弹窗）

- [ ] `branches.vue`：新增「UT覆盖率」列（显示 lineCoverage + %），点击 emit goUtCoverageDetail
- [ ] `UtCoverageDetailDialog.vue`：指标概览（仅展示有数据的指标）+ 文件明细表格（分页/排序）
- [ ] `index.vue`：goUtCoverageDetail 打开弹窗
- [ ] `api.ts` / `url.ts`：新增 utCoverageFileDetail 接口
- [ ] 验证：构建通过

## Task 3: 插件 upload-ut-action（解析 6 种报告 + OBS + 回调）

- [ ] 初始化插件仓（package.json / action.yml / index.js / .pre-commit-config.yaml / .gitcode workflow）
- [ ] `ReportScanner`：扫描目录识别工具报告（jacoco.xml / coverage.json / coverage.out / .gcov / lcov / coverage-final.json）
- [ ] 6 个解析器：JacocoParser、CoveragePyParser、GoTestParser、GcovParser、C8Parser、CargoLlvmCovParser → 统一中间结构
- [ ] `CoverageNormalizer`：转标准 JSON（lineCoverage 必填，branch/method/class 可缺省 + fileDetails）
- [ ] `ObsUploader`：OIDC 换证 + OBS 上传（ut-coverage-action/ 前缀 + public-read）+ APIG 回调 /coverage/ut/report，指数退避重试
- [ ] 单元测试（node --test）：各解析器 fixture + 转换 + 路径构建
- [ ] 验证：npm test 通过 + ncc 打包 dist + zip
- [ ] README 编写

## Task 4: 文档归档 + 一致性校验 + PR

- [ ] docs 仓：proposal.md/design.md/tasks.md 已生成，Phase 3 后与用户确认
- [ ] 用户自测/反馈循环
- [ ] 最终一致性校验（需求目标 / 不做什么 / 设计方案 / 范围控制）
- [ ] 三仓业务 PR（关联 codecheck#190，ai-assisted 标签）：
  - coderepo `taohuoquan:feat-ut-coverage` → openlibing master
  - web `taohuoquan:feat-ut-coverage` → openlibing master
  - 插件 `taohuoquan:feat-ut-coverage` → 主仓（taohuoquan 或 openlibing 视仓库归属）
