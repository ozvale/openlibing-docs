# security-injection-and-rce-fix — 归档

## 关联

| 类型 | 链接 |
|---|---|
| 业务 Issue (fork 仓) | https://gitcode.com/yanzhaohong/openlibing-cicd/issues/4 |
| 业务 Issue 标题 | 【openLiBing】cicd注入修复 |
| 业务 PR (fork 仓) | https://gitcode.com/yanzhaohong/openlibing-cicd/pulls/1 |
| 业务 PR 标题 | fix: 【openLiBing】cicd注入修复 |
| 业务 PR 分支 | fix-snakeyaml-rce-pipeline-fail-email → master |
| 业务 commit | c22f3c61a |
| 审计报告 (v2) | audit-report-injection-rce-v2.md |
| docs PR | (本 PR) |

## 交付历程

| commit | 说明 |
|---|---|
| c22f3c61a | fix(listener): use SafeConstructor for parsing .notification.yaml (F-001) |

## 用户自测反馈

- 本机 mvn 编译/测试受限（私有仓 401），用户需在本地或 CI 验证
- 用户明确指示「继续执行，PR 和 issue 名均为：【openLiBing】cicd注入修复」，跳过自测反馈循环直接进入归档

## 最终验证

| 项 | 结果 |
|---|---|
| 业务代码修改 | ✅ 已 commit |
| 单元测试编写 | ✅ 7 个测试用例 |
| 业务 PR | ✅ 已创建并打 `ai-assisted` 标签 |
| 漏洞修复 | ✅ SnakeYAML 默认构造器 → SafeConstructor |
| 业务 PR 合入 | ⏳ 待用户/评审合入 |
| 本地编译验证 | ❌ 环境受限（私有 Maven 仓 401） |
| CI 验证 | ⏳ 等待 PR 触发 |

## 设计偏差与取舍

| 取舍 | 原因 |
|---|---|
| 采用 SafeConstructor 而非 LoaderOptions TagInspector 白名单 | 业务仅需解析 Map/List/String，SafeConstructor 已足够，少 2 行代码 |
| 不升级 SnakeYAML 到 ≥ 2.0 | 避免传递依赖版本冲突 |
| 测试通过 `ReflectionTestUtils.invokeMethod` 调用 private 方法 | 避免将 `parseRecipients` 改为 package-private 破坏封装 |
| 业务 Issue 创建在 fork 仓 | 用户无 `openlibing/openlibing-cicd` 主仓写权限（403 CH.00000403） |

## 可复用经验

1. **YAML 反序列化 RCE 通用模式**：任何接收外部 YAML 输入（仓库文件、API 响应、配置文件）并使用 `new Yaml()` 的代码都存在 CVE-2022-1471 风险。**通用修复模板**：
   ```java
   LoaderOptions loaderOptions = new LoaderOptions();
   Yaml yaml = new Yaml(new SafeConstructor(loaderOptions), loaderOptions);
   ```
2. **不可信数据信任域**：仓库内的配置文件（即使命名为 `.notification.yaml`）也应视为不可信外部输入，不能直接反序列化。
3. **RabbitMQ 消息 ID 不可信**：`pipelineId/runId` 直接作为 DB 查询 key 之前需要做格式校验（虽然本次修复不涉及，但是潜在风险）。

## 归档日期

2026-07-04
