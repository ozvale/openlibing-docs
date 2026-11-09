# add-sarif-private-obs-read — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-codecheck/issues/402
- 业务 PR: https://gitcode.com/openlibing/openlibing-codecheck/merge_requests/400
- docs PR: 本 PR

## 交付历程

- commit `71a9dc32`: 后端改为按平台凭证读取私有 OBS 对象，新增访问策略校验与大小上限，重写相关单测

## 最终验证

- `mvn test`：全量通过
- `mvn spotless:check`：通过
- `ObsBucketServiceImplTest` / `SarifParseServiceImplTest`：通过
- pre-commit（trailing-whitespace、gitleaks、spotless、checkstyle、spotbugs、pmd）：通过

## 设计偏差与取舍

- PR base 未使用 `add-static-alarm-github-adapt`（该分支仅存在于 fork，不能作为上游 PR 的 base），改以 `release_20261116_iter1` 为 base，PR diff 暂含 #391 的提交，待 #391 合入后自动收窄。
- 目录白名单默认正则去掉长度上限，对齐插件 `buildToolPrefix` 的实际规则（小写、仅 `[a-z0-9-]`、不截断）。
- `unknown-repo` 目录放行：页面展示的平台与仓库来自上报 `repoUrl` 解析，不读取对象路径，因此不影响展示。
- 存量公开对象不迁移、disappeared 清理语义不变；存量治理由插件侧另行改造。

## 可复用经验

- Nacos 下发的白名单配置配合 `@RefreshScope` + `@PostConstruct` 可在不重启的情况下重新解析。
- Spring 占位符 `${key:默认值}` 的默认值中若含 `}`（如正则量词）会被提前截断，默认值应放代码常量，`@Value` 默认部分留空。
- 逗号分隔的正则配置拆分需感知花括号，否则量词内的逗号会被误拆。

## 归档日期

2026-11-09
