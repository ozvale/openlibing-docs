# 【openlibing-coderepo】仓库令牌权限校验与告警（repo-token-scope-check）— 归档

## 关联

- 业务 Issue: 无（随功能分支交付）
- 业务分支: feature/repo-token-scope-check（commit 链 f588d9c0..25a38570，共 14 个提交）
- 归档文档: 本目录（proposal.md / design.md / tasks.md）

## 交付历程

| commit | 日期 | 说明 |
| ------ | ---- | ---- |
| f588d9c0 | 09-16 | 基础框架：TokenPermissionEvaluator / PlatformTokenErrorResolver / TokenPermissionAlertBuilder / check-token-permission 接口 / repo_info 四列 DDL / XxlJob 刷新回填 |
| c793b887 | 09-17 | 加固：区分平台探测失败与令牌无效、编辑场景统一以库中实体解析、批量元数据刷新移出保存事务、刷新查询带 token_status/repo_url 及可观测日志 |
| 3ffaab89 | 09-17 | GitHub 令牌校验与登录名解析合并为单次 GET /user（GithubLoginResult），消除重复请求 |
| e3003b73 | 09-17 | Excel 导出新增 8 令牌列；check 仅 isEditAccessToken=true 触发；GitCode scope 别名覆盖；告警文案调整 |
| 6c7c7bbe | 09-17 | 批量修改令牌前置校验（跨平台混选拒绝 / 唯一平台单次校验 / 空 token 放行） |
| 8f0d4c8a | 09-18 | GitHub 上级 scope（user/project）覆盖 read:user / read:project，修复误判 abnormal |
| a63f6098 | 09-19 | filterMeta 三维度筛选 + isInheritProjectToken；令牌失效账号名写空串覆盖；批量刷新改 afterCommit + 专用线程池 |
| 1c077230 | 09-20 | 访问权校验文案常量统一移至类头部常量区（纯重构） |
| 53be2ac0 | 09-20 | 移除角色解析 owner 前置特判，统一 collaborators 权限接口，角色取值收敛 admin/maintain/write/read |
| 8c72b2bd | 09-21 | 顺手清理：移除 PR 合入限制配置下发（gitcodePullRequestSettings）及导出两列 |
| 8d0506e8 | 09-21 | 令牌无效细分错误信息透传（TokenMetadataDTO.tokenErrorMessage → 弹框） |
| a379bb4b | 09-21 | 告警文案简化与排版优化（纯重构） |
| efb2d801 | 09-22 | GitHub Fine-grained PAT（github_pat_）跳过 scope 校验，token_scope_status 置空，文案补充说明 |
| 25a38570 | 09-22 | GitHub 角色解析改用 GET /repos/{owner}/{repo}（read 令牌可调用）并放宽至 maintain+；批量校验并行化 + 元数据缓存；移除探测失败 DB 降级 |

分支内共 27 个文件变更（+3687 / -275），含 main 源码、DDL、mapper、接口文档与 8 个测试文件。

## 用户自测反馈

- 暂无线上自测记录。GitCode/GitHub 平台侧真实令牌（各角色 / 各 scope / Fine-grained PAT）的弹框文案与四字段入库需合入后自测验证。

## 设计偏差与取舍

- **探测失败降级读库 → 移除**：c793b887 引入"平台探测失败时降级读库中四字段"，25a38570 评估后移除——库值可能过期产生误导性告警，改为直接跳过告警（宁可漏报不误报）。spec 按最终口径记录。
- **GitHub 角色接口两次切换**：初版 owner 前置特判（53be2ac0 移除）→ collaborators 权限接口（该接口要求 write+ 权限，低角色令牌 403）→ 最终 `GET /repos/{owner}/{repo}` 仓库详情接口（read 令牌可调用），并相应将角色最低要求由 owner/admin 放宽至 maintain+。
- **GitCode 角色仍走 collaborators 列表接口**：该接口可满足当前 GitCode 侧要求（角色取 role_name_cn），保留现状；若后续 GitCode 低角色令牌出现同类 403，可参考 GitHub 方案迁移。
- **Fine-grained PAT 不自动校验 scope**：平台不返回 OAuth scope，强制校验必误报，最终选择跳过 + 文案说明，由用户自行确认仓库与账号权限。
- **批量混选平台的两种口径**：阻断性前置校验（批量保存 validateBatchAccessTokenUpdate）拒绝跨平台混选；非阻断弹框校验（checkBatchTokenPermission）对 gitcode+github 混选跳过校验（探测口径因平台而异，混选无统一标准）。
- **PR 合入限制清理随行**：8c72b2bd 移除 gitcodePullRequestSettings 下发与导出两列，与本主题无直接关联，为分支内顺手清理，已在 tasks.md 单独标注。

## 最终验证与后续计划

> 功能代码与单元测试已随分支提交，编译与全量测试回归建议在合入 master 前执行；平台侧联调依赖真实令牌场景。

| 验证项 | 当前状态 | 后续补齐计划 |
| ------ | -------- | ------------ |
| 编译 | 待分支合入前执行 `mvn compile` | 业务仓功能承接人 |
| 单元测试 | 分支内已新增 8 个测试类/增量用例，存量测试待全量回归 | 合入前执行 `mvn test` |
| GitCode 平台自测 | 待验证（scope 覆盖 / 维护者角色判定 / 细分错误文案） | 合入后按验收标准逐条自测 |
| GitHub 平台自测 | 待验证（Classic PAT scope 头解析 / Fine-grained PAT 跳过 / maintain+ 角色 / repo 详情双路径解析） | 合入后按验收标准逐条自测 |
| Gitee 回归 | 需确认无行为变化（校验跳过、文案保留现网口径） | 合入后回归仓库保存与批量编辑 |
