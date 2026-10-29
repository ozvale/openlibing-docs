# Proposal: 合法合规批量分析弹窗审核人空状态提示

## 需求背景

合法合规批量分析/分析弹窗（`views/sca/softInformation/confirmBox.vue`，被 PR 合法合规、个人扫描任务、软件信息三处复用）中，「审核人」下拉数据来自后端 `/select/get-committer` 接口。当接口返回空列表或请求失败时，下拉框点开是空白（默认「无数据」），没有任何引导，用户不清楚审核人从何而来、如何添加，只能猜测或求助。

后端接口逻辑（openlibing-framework `SelectServiceImpl.getCommitter`）：审核人来源为代码仓 sig-info.yaml 的 committer 配置（仓库级 + 目录级），sig 侧为空时兜底查平台 `user_role_info` 中该仓库的 committer 角色用户；同时排除当前操作人本人、过滤未注册/已注销用户。因此空列表存在多种成因（未配置、唯一 committer 是本人、committer 全被过滤），需要在提示中给出完整指引。

## 功能描述

- 「审核人」下拉框增加**空状态提示**（`el-select` 的 `#empty` 插槽），按场景区分文案：
  - **数据为空**（接口成功但返回空列表）：说明审核人两个来源及账号前置条件，引导用户完成配置
  - **获取失败**（接口请求异常）：提示稍后重试
- **生效范围仅限合法合规菜单**（顶部页签为版本扫描 + PR 扫描）：confirmBox.vue 为三处复用的共享组件，通过新增 prop（默认关闭）控制空提示显隐，仅合法合规菜单的两个入口开启：
  - PR 扫描页签（`PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue`，路由 `/apps/sca/PRComponentAnalysis`）
  - 版本扫描页签（`softInformation/gitUrlList.vue`，`componentAnalysis` 详情态内嵌，仅被 `componentAnalysis/index.vue` 引用）
- 个人扫描任务详情（`personalScandTaskInfor/analysisTable.vue`，入口为发布评审→移交测试链路，非合法合规菜单）**不传该 prop，行为不变**

## 验收标准

- [ ] 合法合规两个入口（PR 扫描页签、版本扫描页签详情）中，审核人接口返回空列表时，点开下拉展示「数据为空」引导文案（含 sig-info.yaml committer 配置与平台代码合并者两个来源说明）
- [ ] 合法合规两个入口中，审核人接口请求失败时，点开下拉展示「获取失败，请稍后重试」文案
- [ ] 个人扫描任务详情入口行为与改造前完全一致（空列表时仍为默认「无数据」）
- [ ] 审核人正常返回时，各入口下拉列表展示与改造前完全一致，无回归
- [ ] 下拉选项中的既有禁用态提示（未注册/未绑定 tooltip）不受影响
- [ ] lint 通过，无新增告警

## 关联

- 业务仓：openlibing-web（分支待建 `feat-batch-analysis-committer-tip`）
- 后端接口依据：openlibing-framework `SelectController#getCommitter` → `SelectServiceImpl#getCommitter`（`/select/get-committer`，POST）
