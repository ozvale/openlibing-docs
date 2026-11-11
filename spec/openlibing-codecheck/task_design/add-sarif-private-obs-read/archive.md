# add-sarif-private-obs-read — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-codecheck/issues/402
- 业务 PR: https://gitcode.com/openlibing/openlibing-codecheck/merge_requests/402
- docs PR: 本 PR

## 交付历程

- commit `d1746357`: 后端改为按平台凭证读取私有 OBS 对象，新增访问策略校验与大小上限，重写相关单测
- commit `ce5ad92f`: 按检视意见修复 OBS 响应流未关闭、URL 解码异常穿透、桶名转小写 Locale 与测试临时文件未清理
- commit `333d7795`: 收紧 `unknown-repo` 校验并改写参数错误提示
- commit `046194cc`: 补充仓库名含加号的字面路径用例
- commit `aa87eb17`: 损坏 SARIF 按 URL 隔离，工具目录匹配放宽大小写
- commit `37342e2e`: 桶白名单改用共享配置 `obs.action.buckets`
- commit `93a41355`: 按业务 PR 检视意见修复——删除不可达的前导斜杠校验、统一按 URL 隔离解析异常、补齐仓库目录大小写与路径段数用例
- commit `8b8c818b`: 拆分 `SarifObsAccessPolicy` 配置 Bean，`ObsBucketServiceImpl` 去掉 `@RefreshScope`，避免配置刷新关闭 `ObsClient`

## 最终验证

- `mvn test`：全量通过
- `mvn spotless:check`：通过
- `ObsBucketServiceImplTest` / `SarifParseServiceImplTest`：通过
- pre-commit（trailing-whitespace、gitleaks、spotless、checkstyle、spotbugs、pmd）：通过

> 存量兼容性全量验证（Task 6.1 / 6.2）**尚未执行**，本归档不代表存量 URL 对新访问策略的覆盖率已验证；首轮只读核查结论与残余风险见 tasks.md Task 6 备注。

## 设计偏差与取舍

- 业务 PR 最初以依赖分支 `add-static-alarm-github-adapt` 为 base 提交，以免 diff 混入上游分支改动；该依赖分支合入 `release_20261116_iter1` 后，改为以 release 为 base 重放本次 6 个提交，PR 只含 7 个文件。
- 目录白名单默认正则去掉长度上限，对齐插件 `buildToolPrefix` 的实际规则（小写、仅 `[a-z0-9-]`、不截断）。
- `unknown-repo` 目录改为拒绝：插件 key 结构为 `{tool}-results/unknown-repo/{yyyyMMdd.HH}/{runId|manual}/{basename}`，第 4、5 段可预测，放行可被构造路径绕过归属校验；改为接收阶段拒绝入库、读取阶段拒绝读取。生产与 BETA 存量命中均为 0，无兼容影响；页面展示来自上报 `repoUrl` 解析，不读取对象路径。
- 存量公开对象不迁移、disappeared 清理语义不变；存量治理由插件侧另行改造。

## 可复用经验

- 白名单与大小上限拆到独立 `SarifObsAccessPolicy`（`@RefreshScope` + `@PostConstruct`），Nacos 变更只重建该 Bean，OBS 客户端生命周期跟随应用，不打断在途下载。
- Spring 占位符 `${key:默认值}` 的默认值中若含 `}`（如正则量词）会被提前截断，默认值应放代码常量，`@Value` 默认部分留空。
- 逗号分隔的正则配置拆分需感知花括号，否则量词内的逗号会被误拆。

## 归档日期

2026-11-09
