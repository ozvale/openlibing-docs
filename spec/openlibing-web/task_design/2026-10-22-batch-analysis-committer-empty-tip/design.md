# Design: 合法合规批量分析弹窗审核人空状态提示

## 方案选型

| 方案                                   | 说明                             | 结论                                                                         |
| -------------------------------------- | -------------------------------- | ---------------------------------------------------------------------------- |
| **A. el-select `#empty` 插槽（采用）** | 下拉空状态内嵌场景化提示文案     | 用户点开下拉即在第一视线内；改动最小（单组件单插槽）                         |
| B. 表单项下方常驻提示条                | 接口返回空即在表单项下方展示提示 | 否决：占用弹窗纵向空间，且用户未点开下拉前未必关心该项；用户已确认采用方案 A |
| C. `el-form-item` rules 校验提示       | 提交时才提示                     | 否决：时机过晚，不解决"如何添加审核人"的指引问题                             |

## 核心设计（方案 A）

### 1. 状态模型

`confirmBox.vue` 的 `queryBranchCommiter()` 现状：`.then` 赋值 `committers`，**无 catch**（请求失败时 `committers` 保持空数组，与"接口成功返回空"不可区分）。新增一个请求状态字段：

```js
committerLoadState: "init" | "success" | "error";
```

- 请求发起（弹窗打开触发 `queryBranchCommiter`）置 `init`
- `.then` 成功 → `success`（仅在 `success` 且列表为空时，`#empty` 插槽展示引导文案）
- 新增 `.catch` → `error`（仅请求真正失败时置 `error`；发起阶段不得置 `error`，避免在途请求窗口期被 `#empty` 插槽误判为「获取失败」）

### 2. 生效范围控制：新增 prop

confirmBox.vue 被三处复用，本次**仅对合法合规菜单生效**，通过新增 prop 控制（默认关闭，非合法合规入口行为不变）：

| 入口                                                                    | 菜单归属                                                                                                            | 调用传参                     | 处理                                    |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------- | --------------------------------------- |
| `PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue` | 合法合规 → **PR 扫描**页签（`/apps/sca/PRComponentAnalysis`）                                                       | `is-personal`                | **新增传 `enable-committer-empty-tip`** |
| `softInformation/gitUrlList.vue`                                        | 合法合规 → **版本扫描**页签（`componentAnalysis` 详情态内嵌，`gitUrlList` 仅被 `componentAnalysis/index.vue` 引用） | `is-repaired` + `nodes-path` | **新增传 `enable-committer-empty-tip`** |
| `personalScandTaskInfor/analysisTable.vue`                              | 非合法合规（noMenu，入口为发布评审→移交测试链路）                                                                   | `is-personal`                | 不传，行为不变                          |

合法合规菜单（`views/sca/layout/index.vue` 顶部页签）仅含版本扫描（`productScand` → `componentAnalysis`）与 PR 扫描（`PRScand` → `PRComponentAnalysis`）两个列表页签；版本扫描下的看板（`communityList`）与二进制列表（`binaryList`/`binaryLicenseList`）无批量分析入口，社区管理（`managerConfiguration`）的 `ScanEmailAddRuleDialog` 虽调用同一审核人接口但非批量分析弹窗，均不在本需求范围。

不能复用现有 prop 区分：PR 合法合规与个人扫描任务两入口均传 `is-personal`，语义也与本需求无关；`is-repaired` 是目录树选中提示。故新增独立布尔 prop：

```js
enableCommitterEmptyTip: {
  type: Boolean,
  default: false, // 默认关闭，未开启时 #empty 插槽不渲染自定义内容，保持默认「无数据」
},
```

### 3. 模板：el-select `#empty` 插槽

```html
<el-select v-model="form.committers" filterable>
  <template v-for="item in committers" :key="item.key">
    <!-- 既有 el-option 渲染，不动 -->
  </template>
  <template #empty>
    <!-- enableCommitterEmptyTip 开启时：
         committerLoadState === 'error' → 获取失败文案
         否则（success 且列表为空）→ 数据为空引导文案
         未开启时不渲染自定义内容（保持默认「无数据」） -->
  </template>
</el-select>
```

项目 Element Plus 2.13+，`el-select` 支持 `#empty` 插槽（替代默认「无数据」文案）。

### 4. 提示文案（最终确认版）

**数据为空**（接口成功返回空列表）：

> 暂无可选审核人。可选审核人来源于以下配置：
>
> 1. 代码仓 sig-info.yaml 中配置的 committer（含仓库级和目录级）；
> 2. 平台上为该仓库配置的代码合并者。
>    请确认已完成上述配置，且审核人已注册 openLiBing 账号、绑定 Gitee/GitCode 账号并完善邮箱信息。

**获取失败**（请求异常）：

> 审核人列表获取失败，请稍后重试。

文案与后端逻辑的对应关系（`SelectServiceImpl.getCommitter`）：

| 文案要点                                   | 后端依据                                                                           |
| ------------------------------------------ | ---------------------------------------------------------------------------------- |
| sig-info.yaml committer（仓库级 + 目录级） | `getSigInfo` + `getMatchCommitterIds`（仓库级 data 与目录级 entryConfigs 并集）    |
| 平台代码合并者                             | sig 侧为空时兜底查 `user_role_info`（`repo_committer` 角色）                       |
| 注册 openLiBing 账号                       | 未注册用户 `userId=null`、`unboundPlatform='openLiBing'`（下拉禁用态，不计入可选） |
| 绑定 Gitee/GitCode 账号                    | 未绑定三方账号同样进入禁用态                                                       |
| 完善邮箱信息                               | 后端标记 `unboundEmail='1'`                                                        |
| （隐含）排除本人                           | 后端 `users.removeIf(userId == input.userId)`——唯一 committer 为本人时列表为空     |

### 5. 样式

空文案在 `#empty` 插槽内多行展示（有序列表），复用 el-select 空状态默认内边距，必要时补充 `line-height` / 文字颜色（次要灰 `#9199ab` 系，与弹窗既有 tooltip 图标色一致）。避免过宽：文案按 1/2/3 断行，单行不超过下拉宽度。

## 影响范围

| 文件                                                                              | 变更                                                                                                                                             |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `views/sca/softInformation/confirmBox.vue`                                        | 新增 `enableCommitterEmptyTip` prop（默认 false）；`queryBranchCommiter` 增加 catch 与状态字段；el-select 增加 `#empty` 插槽及场景文案；少量样式 |
| `views/sca/PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue` | confirm-box 调用处新增传 `:enable-committer-empty-tip="true"`                                                                                    |
| `views/sca/softInformation/gitUrlList.vue`                                        | confirm-box 调用处新增传 `:enable-committer-empty-tip="true"`                                                                                    |

- 接口调用参数、后端契约无变化
- **个人扫描任务入口（`personalScandTaskInfor/analysisTable.vue`）不改动**：不传新 prop，confirmBox 默认关闭空提示，行为与改造前一致
- `projectComplianceConfirmBox.vue`（项目合规批量分析）无审核人字段，不受影响

## Trade-off（有意接受）

1. 失败场景的「请稍后重试」无自动重试/手动重试按钮：`queryBranchCommiter` 在弹窗打开时触发，用户关闭重开弹窗即重试；本轮不加按钮，保持最小改动
2. 不区分「sig 未配置」与「配置了但全被过滤（如唯一 committer 是本人）」两种空成因：接口未返回成因信息，前端无法区分，文案统一给出全部来源指引
