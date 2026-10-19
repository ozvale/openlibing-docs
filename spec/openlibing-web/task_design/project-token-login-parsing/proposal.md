# Proposal: project-token-login-parsing

## 背景与现象

`openlibing-web` 新增/修改项目表单（`Project/projectAddEditForm.vue`）中，gitee/gitcode/github 三个平台的「公共账号令牌」与「公共账号用户名」需分别手动填写，用户名易抄错且无法与令牌自洽，缺少即时校验手段。

另：工具管理-我的工具的图标上传接口缺少 `projectId` 参数，多项目场景下图标归属错乱（用户随本次需求一并修复）。

## 需求目标

| 目标         | 验收点                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------ |
| 令牌实时解析 | 输入完公共账号令牌（change 触发）即调 `POST /project/parse-token-login`（data 传 `token`、`platform`） |
| 用户名回显   | 接口返回 `code === 200` 时，将公共账号用户名回显到对应平台的用户名输入框（disabled 展示）              |
| 三平台覆盖   | gitee / gitcode / github 三平台令牌输入框统一接入                                                      |
| 展示时机     | 三个「公共账号用户名」表单项移除编辑态限制，新增项目时也展示                                           |
| 图标上传修正 | `toolItem.vue` 工具图标上传接口两处补传 `projectId`（`app.projectInfo?.projectId`）                    |

## 不在本次范围

- 令牌有效性失败提示（解析失败时用户名保持原状，不额外弹错）
- 令牌明文存储策略（沿用既有表单提交链路）
- 其他模块的令牌解析

## 关联 Issue

- `https://gitcode.com/openlibing/openlibing-framework/issues/116`（跨仓关联，由用户在 Issue 页面手动关联）

## 关联 PR

- 业务 PR：`openlibing/openlibing-web` [PR #824](https://gitcode.com/openlibing/openlibing-web/merge_requests/824)（`feat(project): parse public account login from token input`）
- docs PR：本 PR

## 关联 commit

- `06b5a6cb3` `feat(project): parse public account login from token input`

Generated-by: GLM-5.3
