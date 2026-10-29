# Proposal: publish-token-config

## 背景与现象

`openlibing-web` 发布评审-发布设置页已有「中心仓配置」等模块，但发布过程中使用的各平台（gitee/gitcode）公共账号令牌缺少统一管理入口，令牌的增删改查只能线下维护，无法追溯创建人与创建时间。

## 需求目标

在发布设置页新增「发布令牌配置」模块（交互对齐「中心仓配置」），提供发布令牌的列表查询、新建、编辑、删除、批量删除能力。

| 目标     | 验收点                                                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 菜单入口 | 发布设置页左侧第三个 listBox 菜单「发布令牌配置」，点击右侧渲染对应模块                                                                                     |
| 列表展示 | 表格列：令牌类型（tokenType）、账号用户名（login）、账号令牌（tokenMasked，脱敏展示前 4 位 + `*` + 后 4 位）、创建人（creatorName）、创建时间（createTime） |
| 新建     | 「新建」按钮打开弹窗表单：令牌类型（选择框 gitee/gitcode）、账号用户名、账号令牌，三项必填                                                                  |
| 编辑     | 操作列编辑图标打开弹窗回显；令牌类型在编辑时禁用修改                                                                                                        |
| 删除     | 操作列删除图标，二次确认后删除                                                                                                                              |
| 批量删除 | 「批量删除」按钮（含 `v-uem-record` 埋点）；未勾选时提示「请选择至少一条数据」                                                                              |
| 接口     | 4 个占位接口：`/config/queryPublishTokenInfo`、`/config/addPublishTokenInfo`、`/config/updatePublishTokenInfo`、`/config/deletePublishTokenInfo`            |

## 不在本次范围

- 令牌加密存储与脱敏逻辑（后端完成 `tokenMasked` 脱敏：前 4 位 + `*` + 后 4 位）
- 令牌有效性实时校验（仅表单必填校验）
- 令牌权限粒度控制（模块入口沿用发布设置页现有权限）

## 关联 Issue

- `https://gitcode.com/openlibing/openlibing-platform-release/issues/63`（跨仓关联，由用户在 Issue 页面手动关联）

## 关联 PR

- 业务 PR：`openlibing/openlibing-web` [PR #821](https://gitcode.com/openlibing/openlibing-web/merge_requests/821)（`feat(publishSetting): add publish token config module`）
- docs PR：本 PR

## 关联 commit

- `8142d4ce0` `feat(publishSetting): add batch delete and align token form fields`
- `8e3b70a9e` `feat(publishSetting): add publish token config module`

Generated-by: GLM-5.3
