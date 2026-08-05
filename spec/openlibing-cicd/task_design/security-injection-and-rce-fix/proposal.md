# security-injection-and-rce-fix: 修复 SnakeYAML 反序列化 RCE 漏洞 (F-001)

## 需求背景

`openlibing-cicd` 项目 `PipelineFailEmailConsumer.parseRecipients` 使用 SnakeYAML 默认构造器 `new Yaml()` 解析来自 GitCode/Gitee 仓库的不可信 YAML 文件（`.notification.yaml`），存在远程代码执行风险（CVE-2022-1471）。

任何有权限向受影响项目对应仓库推送 `.notification.yaml` 的攻击者，可通过构造恶意 YAML Payload 触发 RCE。

## 功能描述

将 `PipelineFailEmailConsumer.parseRecipients` 方法的 YAML 解析方式从默认构造器替换为 `SafeConstructor`，并添加单元测试覆盖正常 / 恶意输入场景。

## 验收标准

- [ ] `parseRecipients` 使用 `SafeConstructor` 解析 YAML
- [ ] 单元测试：恶意 YAML（如 `!!javax.script.ScriptEngineManager []`）被拒绝
- [ ] 单元测试：恶意 YAML（如 `!!java.net.URLClassLoader []`）被拒绝
- [ ] 单元测试：正常 YAML（含 `notifications` 块和 `emails` 列表）正常解析
- [ ] 单元测试：空 / 非法 YAML 返回空列表且不抛异常
- [ ] 单元测试：无 `notifications` 键 / 非 `pipeline_fail` 类型返回空列表
- [ ] 编译通过，相关测试通过

## 影响范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/listener/PipelineFailEmailConsumer.java` | 修改 | `parseRecipients` 改用 SafeConstructor 解析 YAML |
| `openlibing-cicd/src/test/java/com/openlibing/cicd/business/listener/PipelineFailEmailConsumerTest.java` | 新增 | 7 个测试用例覆盖正常 / 恶意 / 异常 YAML 输入 |

## 关联 Issue

- yanzhaohong/openlibing-cicd#4（fork 仓业务 Issue，标题已更新为「【openLiBing】cicd注入修复」）
- 主仓 `openlibing/openlibing-cicd` 业务 Issue 申请被 403 拒绝（用户无主仓写权限），需用户提单后补充关联

## 关联审计报告

- [openlibing-cicd 注入类 & 命令执行类 深度审计报告（v2）](https://gitcode.com/yanzhaohong/openlibing-cicd/blob/fix-snakeyaml-rce-pipeline-fail-email/audit-report-injection-rce-v2.md)
