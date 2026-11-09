# add-sarif-private-obs-read — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-codecheck/issues/402
- 业务 PR: https://gitcode.com/openlibing/openlibing-codecheck/merge_requests/401
- docs PR: 本 PR

## 交付历程

- commit `71a9dc32`: 后端改为按平台凭证读取私有 OBS 对象，新增访问策略校验与大小上限，重写相关单测
- commit `9d300026`: 按检视意见修复 OBS 响应流未关闭、URL 解码异常穿透、桶名转小写 Locale 与测试临时文件未清理

## 最终验证

- `mvn test`：全量通过
- `mvn spotless:check`：通过
- `ObsBucketServiceImplTest` / `SarifParseServiceImplTest`：通过
- pre-commit（trailing-whitespace、gitleaks、spotless、checkstyle、spotbugs、pmd）：通过

## 设计偏差与取舍

- 业务 PR 起初以 `release_20261116_iter1` 为 base，为避免 diff 混入上游分支改动，后将 `add-static-alarm-github-adapt` 推送至主仓，并改以该分支为 base 重新提交 PR。
- 目录白名单默认正则去掉长度上限，对齐插件 `buildToolPrefix` 的实际规则（小写、仅 `[a-z0-9-]`、不截断）。
- `unknown-repo` 目录放行：页面展示的平台与仓库来自上报 `repoUrl` 解析，不读取对象路径，因此不影响展示。
- 存量公开对象不迁移、disappeared 清理语义不变；存量治理由插件侧另行改造。

## 可复用经验

- Nacos 下发的白名单配置配合 `@RefreshScope` + `@PostConstruct` 可在不重启的情况下重新解析。
- Spring 占位符 `${key:默认值}` 的默认值中若含 `}`（如正则量词）会被提前截断，默认值应放代码常量，`@Value` 默认部分留空。
- 逗号分隔的正则配置拆分需感知花括号，否则量词内的逗号会被误拆。

## 归档日期

2026-11-09
