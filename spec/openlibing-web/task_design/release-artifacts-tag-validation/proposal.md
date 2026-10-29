# Proposal: release-artifacts-tag-validation

## 背景与现象

`openlibing-web` 发布评审详情页-制品信息中的 tag 名称输入（选择框 allow-create 与输入框两种场景）此前仅有「最长不超过 50 个字符」的 placeholder 提示，无格式校验。用户输入非法 tag（如以 `/` 结尾、`/` 连续、以 `.lock` 结尾等）直接提交，会导致后端/代码托管平台侧创建 tag 失败，报错信息不友好。

## 需求目标

对 tag 名称输入添加前端实时校验，规则参考 GitCode 网站新建 tag 的校验规则：

| 规则         | 说明                                                                    |
| ------------ | ----------------------------------------------------------------------- |
| 首字符       | 只能以中文、字母或数字开头                                              |
| 字符集       | 中文、字母、数字及 `_`、`.`、`-`、`/`                                   |
| `/` 连续性   | `"/"` 不能连续（禁止 `//`）                                             |
| 长度         | 最多 50 个字符                                                          |
| 结尾限制     | 不能以 `"/"`、`"."`、`".lock"` 结尾                                     |
| 校验失败行为 | `ElMessage.error` 展示完整规则提示，并清空输入框                        |
| 校验通过     | 继续执行原有 `handleChange` 流程，不影响既有逻辑                        |
| 场景覆盖     | 两个 tag 输入场景共用：选择框 allow-create `@change` + 输入框 `@change` |

## 不在本次范围

- 后端 tag 校验（前端校验仅作第一道防线，最终以后端/代码托管平台为准）
- tag 重名校验
- 其他模块的 tag 输入（仅发布评审详情页-制品信息）

## 关联 Issue

- `https://gitcode.com/openlibing/openlibing-platform-release/issues/63`（跨仓关联，由用户在 Issue 页面手动关联）

## 关联 PR

- 业务 PR：`openlibing/openlibing-web` [PR #822](https://gitcode.com/openlibing/openlibing-web/merge_requests/822)（`feat(publishReview): add tag name validation in release artifacts`）
- docs PR：本 PR

## 关联 commit

- `c77e233bb` `feat(publishReview): add tag name validation in release artifacts`

Generated-by: GLM-5.3
