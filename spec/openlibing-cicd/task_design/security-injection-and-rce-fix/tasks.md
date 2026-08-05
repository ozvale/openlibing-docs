# security-injection-and-rce-fix — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 修改 `PipelineFailEmailConsumer.parseRecipients`，使用 `LoaderOptions` + `SafeConstructor` 替换默认构造器
- [x] Task 2: 新增 `PipelineFailEmailConsumerTest` 单元测试，覆盖 7 个正常 / 恶意 / 异常 YAML 输入场景
- [x] Task 3: 提交 commit `c22f3c61a` 并推送到 fork 仓，创建业务 PR #1

## 详细任务

### Task 1: 修改 parseRecipients

- 文件：`src/main/java/com/openlibing/cicd/business/listener/PipelineFailEmailConsumer.java`
- 改动：
  - 新增 import：`org.yaml.snakeyaml.LoaderOptions` / `org.yaml.snakeyaml.constructor.SafeConstructor`
  - `parseRecipients` 方法体第 1-2 行：`new Yaml()` → `new Yaml(new SafeConstructor(loaderOptions), loaderOptions)`
  - 添加中文注释说明修复原因

### Task 2: 新增单元测试

- 文件：`src/test/java/com/openlibing/cicd/business/listener/PipelineFailEmailConsumerTest.java`（新建）
- 7 个 `@Test` 用例：
  1. `testParseRecipients_normalYaml_returnsEmails`
  2. `testParseRecipients_maliciousYaml_scriptEngineManager_isRejected`
  3. `testParseRecipients_maliciousYaml_urlClassLoader_isRejected`
  4. `testParseRecipients_emptyOrNull_returnsEmpty`
  5. `testParseRecipients_invalidYaml_returnsEmpty`
  6. `testParseRecipients_noNotificationsKey_returnsEmpty`
  7. `testParseRecipients_nonPipelineFailType_returnsEmpty`
- 测试方式：通过 `ReflectionTestUtils.invokeMethod` 调用 private 方法

### Task 3: 提交并创建 PR

- commit hash: `c22f3c61a`
- commit message: `fix(listener): use SafeConstructor for parsing .notification.yaml (F-001)`
- 分支: `fix-snakeyaml-rce-pipeline-fail-email`
- 业务 PR: https://gitcode.com/yanzhaohong/openlibing-cicd/pulls/1
- 标签: `ai-assisted`

## 验证状态

| 验证项 | 状态 | 证据 |
|---|---|---|
| 业务仓代码修改 | ✅ 完成 | commit `c22f3c61a` |
| 业务仓单测编写 | ✅ 完成 | 7 个测试用例 |
| 业务仓 PR 创建 | ✅ 完成 | https://gitcode.com/yanzhaohong/openlibing-cicd/pulls/1 |
| 业务仓 PR 标签 `ai-assisted` | ✅ 完成 | `gitcode pr edit 1 --labels ai-assisted` |
| 本地 mvn 编译 | ❌ 环境限制 | openlibing-common-sdk 1.0.19.3 私有 Maven 仓 401 |
| 本地 mvn test | ❌ 环境限制 | 同上 |
| 用户本地自测 | ⏳ 待用户执行 | 拉取分支后 `mvn test -Dtest=PipelineFailEmailConsumerTest` |
| CI 流水线 | ⏳ 待 CI 触发 | GitCode PR 流水线自动执行 |
