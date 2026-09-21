# UT 覆盖率上报与分支管理页展示 — 归档

## 关联

- 业务 Issue: [openlibing/openlibing-codecheck#190](https://gitcode.com/openlibing/openlibing-codecheck/issues/190)
- 业务 PR:
  - [openlibing-coderepo #189](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/189)：head `taohuoquan:feat-ut-coverage` → base `release_20260923_iter2`
  - [openlibing-web #789](https://gitcode.com/openlibing/openlibing-web/merge_requests/789)：head `taohuoquan:feat-ut-coverage` → base `release_20260923`
- 插件 upload-ut-action：个人仓 `taohuoquan/upload-ut-action`，分支 `feat-ut-coverage` 已推送，未提 PR
- docs PR: 待合入后回填

## 交付历程

### coderepo（openlibing-coderepo）

- commit `90e02d2f`: feat(ut-coverage): add UT coverage report import and branch display support
- commit `34b8d1d4`: feat(ut-coverage): fill UT coverage into branch lists and extend OBS whitelist
- commit `ab4bdc29`: fix(ut-coverage): normalize gitUrl to match repo_info storage
- commit `1936e9b8`: refactor(ut-coverage): keep only lineCoverage metric
- commit `4dad4e94` / `9eafb2e8`: fix(liquibase): restore original changeset checksum for ut-coverage
- commit `6e6033ae` / `b4ad71a8`: 去除不必要的字段（清理遗留字段）
- commit `12686014`: chore(ut-coverage): apply spotless google-java-format
- commit `d59a01d1`: 修改 pre-commit 问题

### web（openlibing-web）

- commit `d3dca9ce`: feat(repos): add UT coverage column and file detail drill-down
- commit `7adc93d7`: refactor(repos): show percent for UT coverage and keep only lineCoverage
- commit `92a154dc`: fix(repos): rename UT coverage column to UT line coverage

### 插件（upload-ut-action）

- commit `c9429c6`: Initial commit
- commit `30bd5ed`: feat(ut-coverage): add report parser, OBS upload and APIG callback
- commit `a6e10b1`: refactor(ut): normalize only lineCoverage output

## 用户自测反馈

- 开发过程中用户明确要求：**仅保留 lineCoverage 行覆盖率指标，移除 branch/method/class 覆盖率**。三仓联动收敛：
  - coderepo：删除可选指标字段（DTO/实体/VO/SQL/changelog 12 个文件），并恢复被误改的既有 changeSet 校验和
  - web：下钻弹窗移除可选指标展示，覆盖率值补充 `%`
  - 插件：CoverageNormalizer 仅输出 lineCoverage，重新 ncc 打包 dist/zip
- pre-commit 首轮 Maven Spotless 自动格式化 7 个文件导致失败，重跑后全部通过

## 最终验证

- pre-commit 全绿：Spotless / CheckStyle / SpotBugs / PMD 通过
- coderepo 推送后远端 Git Hooks `[PASSED]`
- 单元测试：UtCoverageServiceImplTest / UtCoverageControllerTest / UtCoverageImportConsumerTest 通过
- web 构建通过；插件 `npm test` 通过

## 设计偏差与取舍

- **接口路径**：设计文档为 `/coverage/ut/*`，实际实现为 `/ut/coverage/*`（`UtCoverageController` 类级 `@RequestMapping("/ut/coverage")`）：上报接口 `POST /ut/coverage/report`、下钻接口 `POST /ut/coverage/file-detail`
- **存储方案**相对 proposal.md 有演进：proposal 曾写"复用 code_metrics_record + record_type"，最终按用户确认改为最新数据存 `repo_branch` 新增字段 + 历史数据新建 `code_ut_record` 表（已在 design.md 记录）
- **指标范围收敛**：从"4 个总体指标"收敛为"仅 lineCoverage"，design.md「指标缺省」决策已同步
- **插件仓归属**：upload-ut-action 为个人仓 `taohuoquan/upload-ut-action`（无 openlibing 主仓），分支已推送、未提 PR

## 可复用经验

- 修改既有 Liquibase changeSet 会破坏 checksum 校验（本次经历了两次 checksum 修复 commit）；调整表结构应**新增 changeSet**，不要改动已执行过的 changeSet
- Maven Spotless apply hook 首轮必然改写文件并报"files were modified"，属正常流程，重跑一次即通过；commit 时 hooks 会再次全量执行，需确保第二轮全绿后再推送

## 归档日期

2026-09-21
