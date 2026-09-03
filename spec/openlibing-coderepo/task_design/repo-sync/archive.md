# 【openlibing-coderepo】黄蓝协同代码同步（repo-sync）— 归档

## 关联

- 业务 Issue: [openlibing/openlibing-coderepo#112](https://gitcode.com/openlibing/openlibing-coderepo/issues/112)
- 业务分支: repo_sync-1（待合并 master）
- 归档 PR: [openlibing/openlibing-docs#945](https://gitcode.com/openlibing/openlibing-docs/merge_requests/945)（本 PR）

## 交付历程

| commit   | 说明                                                                      |
| -------- | ------------------------------------------------------------------------- |
| 4116b51e | 新增代码同步功能（PR 同步：动作映射 / 去重 / 预插流水线记录）             |
| e6fe4132 | 新增代码同步功能（评论同步：触发词识别 / UNAUTHORIZED / 标签 / 评论回复） |
| 1eb1fe4a | Merge remote-tracking branch 'origin/master'                              |
| 042c693c | 新增代码同步功能（push 同步 + webhook 订阅扩展 + @Value 默认值收尾）      |
| 74681c34 | 修复格式问题（格式收尾，HEAD）                                            |

分支内共 33 个文件变更（+2808 / -9），均为 main 源码，**未包含测试文件**。

## 用户自测反馈

- 暂无线上自测记录。跨区链路（MQS 消费、黄区流水线回调）需蓝黄双区联调验证，待分支合入后补充。

## 设计偏差与取舍

- **原计划 TDD（计划文档含 11+ 个单测场景）→ 实际分支未提交测试**：功能代码分 3 个 commit 直接提交，单测未随分支落地，补齐计划与责任人见「最终验证与后续计划」。
- **push 消息最小化**：原方案即定为 5 字段最小消息（req_type=push、不带 access_token），与 PR / 评论全字段消息分路径构建。
- **三平台 API 地址补默认值**：原 MergeRequestEventHandler / RepoServiceImpl / GitCode / Gitee 的 gitee / gitcode 地址为无默认值 @Value，本分支统一补默认值避免配置缺失启动失败（顺手修复，非功能必需）。
- **去重 key 沿用历史拼写**：gitcode 前缀为 `gitecodePr:`（历史上少个 i），与 cicd 保持一字不差，注释已标注勿改。
- **Mapper 类名缺字母 w**：流水线 Mapper 代码实际命名为 `YelloRegionPipelineMapper`（缺字母 w，实体为 `YellowRegionPipelineEntity`），spec 文档按代码如实记录该拼写（非笔误）；若后续代码重命名需同步归档文档。
- **早提 commit 存在格式问题**：4116b51e / e6fe4132 / 042c693c 格式问题在 74681c34 统一修复，属 AI 生成代码审查疏漏，教训：多文件提交前先跑格式化检查。

## 最终验证与后续计划

> 本归档 PR 仅归档 spec 文档，功能测试与验证在业务仓 openlibing-coderepo 侧推进。截至归档，编译 / 测试 / 跨区联调均未执行，**功能尚未完成验证，不可视为已验证上线**；补齐计划与责任人如下。

| 验证项       | 当前状态                                                  | 后续补齐计划                                     | 责任人                                |
| ------------ | --------------------------------------------------------- | ------------------------------------------------ | ------------------------------------- |
| 编译         | 待验证（归档未执行构建）                                  | repo_sync-1 合入 master 前执行 `mvn compile`     | 业务仓功能开发（#112 承接人）         |
| 全量单元测试 | 分支内无测试文件，存量 857 个测试待回归                   | 按 proposal / design 场景补齐 11+ 单测并全量回归 | 业务仓功能开发（#112 承接人）         |
| 跨区联调     | 待黄区消费端联调（MQS 消息体 / SEND_OK / 流水线记录回写） | 蓝黄双区部署后联调验证                           | 业务仓功能开发（#112 承接人）+ 黄区侧 |
