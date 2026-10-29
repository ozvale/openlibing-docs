# 【openlibing-web】代码仓管理令牌体系重构 — 技术设计

## 状态机与核心交互

### 令牌类型（仅前端交互态，不上送后端）

```
accessTokenType: 'manual' | 'inherit'
initialAccessTokenType: 编辑打开时由 row.isInheritProjectToken 反显（true→inherit / false→manual）
```

| 状态       | 条件                                                   | 输入框行为                                      | 校验      | 提交                                   |
| ---------- | ------------------------------------------------------ | ----------------------------------------------- | --------- | -------------------------------------- |
| 锁定态     | edit 且未点"修改令牌"且（isSetAccessToken 或 inherit） | 禁用；已配置未修改时展示掩码 `*** (公共账号名)` | 不校验    | 保留原令牌（isEditAccessToken=false）  |
| 手动输入态 | 手动 + （未配置 或 已进入修改）                        | 可输入（password + show-password）              | blur 必填 | isEditAccessToken=true，传输入值       |
| 继承态     | 类型选择 inherit                                       | 禁用、值强制空                                  | 不校验    | accessToken 传空，后端回落项目公共账号 |

- 切换到 inherit：清空 `formData.accessToken`；若已配置令牌则同时 `isEditAccessToken=true`（视为修改），切换后 `clearValidate('accessToken')` 清残留错误
- 取消修改：还原 `initialAccessTokenType`、清空输入值、清校验
- `isInheritProjectToken` 仅为列表反显字段，不入参（由 accessToken 是否为空表达）

### 编辑锁定解锁链路

```
openDialog('edit', row)
  → accessTokenType / initialAccessTokenType 按 isInheritProjectToken 反显
  → isEditAccessToken = !row.isSetAccessToken && type !== 'inherit'
  → tokenEditLocked = edit && !isEditAccessToken && (isSetAccessToken || inherit)
onTokenStartEdit  → isEditAccessToken=true（保持当前类型）
onTokenCancelEdit → isEditAccessToken=false + 还原类型 + 清值清校验
```

## 保存前权限检查

```
submit() 表单校验通过
  → proceedToSave()
      → checkTokenPermission({ params:{userId}, data: getSavePayload() })
          needAlert=true  → 弹"令牌权限确认"（确认→继续保存 / 取消→中止）
          needAlert=false → doSaveRepo()
      → 检查接口异常：catch 吞掉，不阻断保存
  → doSaveRepo()（add→addRepo / edit→updateRepo，入参复用 getSavePayload()）
```

- `getSavePayload()` 抽取 add/edit 共用构建逻辑，保证权限检查与实际保存入参完全一致；剔除 `languageTableData`、`defaultBranchName`、`isInheritProjectToken` 三个非入参字段
- `formatTokenAlertInfo()`：先 HTML 转义（& < > "）防注入，字面 `\n` 与真实换行统一转 `<br>`，`【xxx】` 段加粗高亮；警告图标以内联 SVG 放正文首行（不用 MessageBox type 图标，避免独占一列）
- 批量编辑 confirm() 同样先 `checkTokenPermission`（入参与 batchUpdateRepo 一致）再 `batchUpdateRepo`，弹窗期间关闭按钮 loading

## 批量编辑平台受限字段

```
disabledFieldKeys = computed：
  选中仓库 platforms 含 gitee/github → isAutoFormat
  选中仓库 platforms 含 gitee        → isSuppressionEnabled
isAllSelected / toggleSelectAll 均基于 enabledKeys 计算
el-option :disabled 同步禁选；令牌字段单独走复合输入 + 必填校验
```

## 平台限制矩阵

| 开关                   | gitcode | gitee  | github | 处理手段                                                 |
| ---------------------- | ------- | ------ | ------ | -------------------------------------------------------- |
| isAutoFormat           | 支持    | 不支持 | 不支持 | radio 禁用 + watch 重置 + lastConfig 预填跳过 + 批量禁选 |
| isSuppressionEnabled   | 支持    | 不支持 | 支持   | radio 禁用 + watch 重置 + 预填跳过 + 批量禁选            |
| assumePr / autoTrigger | 支持    | 支持   | 不支持 | watch 重置为 '0' + 预填跳过                              |
| autoTriggerDesignScan  | 支持    | 不支持 | 不支持 | watch 重置为 '0' + 预填跳过                              |

- 统一由 `watch(() => formData.platform)` 在平台变化时重置，覆盖"先填 gitcode 仓开启开关后切 URL 到其他平台"的残留场景
- `applyLastConfig` 预填时按当前 URL 对应平台跳过不兼容字段，避免覆盖 watch 已重置的结果

## 列表与筛选扩展

- 新增列：tokenMemberRole（文本）/ tokenRoleStatus（normal/abnormal tag）/ tokenScopeStatus（normal/abnormal tag），均纳入 `checkedColumnKeys` 列配置
- 新增筛选 ref：tokenMemberRoleFilter / tokenRoleStatusFilter / tokenScopeStatusFilter，查询入参 `tokenMemberRoles` / `tokenRoleStatuses` / `tokenScopeStatuses`
- tokenMemberRole 选项完全依赖后端 filterMeta（值域随平台不同），tokenRoleStatus / tokenScopeStatus 前端兜底 正常/异常
- 列头 ColumnFilter 与 CategorySearch（"令牌信息"分组）通过既有 getSearchArray 双向联动模式接入

## 移除项清理

- `disallowSelfMerge`、`disallowUnresolvedDiscussionsMerge`：表单项、el-table 列、FORM_FIELD_KEYS、SWITCH_FIELDS、knownColumnsBaseline、formData 初始化、changePlatform 重置逻辑全部移除

## 关键技术决策

| 决策                       | 说明                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------- |
| 令牌类型仅前端交互态       | 后端无类型字段，继承语义由 accessToken 传空表达，避免接口契约变更                       |
| 权限检查与保存共用入参构建 | `getSavePayload()` 单一来源，杜绝检查通过但实际保存入参不一致的漏洞                     |
| 检查失败不阻断保存         | 权限检查是辅助提醒，检查接口异常时按正常流程继续，避免检查服务故障导致无法保存          |
| alertInfo 前端转义后再渲染 | `dangerouslyUseHTMLString` 场景必须先 HTML 转义防 XSS，再排版增强（换行/高亮/内联图标） |
| 平台重置收敛到单一 watch   | 平台相关开关的重置集中在 `watch(formData.platform)`，预填、切换、批量三个入口行为一致   |
| 复合输入 prepend 下拉锁宽  | 全局存在更高特异性宽度覆盖，prepend 内类型下拉用 `!important` 锁 105px 并统一下调字号   |
| 弹窗统一防误关             | 四个高频弹窗（录入/编辑、批量编辑、全局配置）统一 `close-on-click-modal=false`          |

## 影响面分析

- 改动集中在 `views/Repos/` 目录（index.vue + 两个 dialog），公共组件零改动，无路由/菜单变化
- API 层仅新增一个 POST 接口定义，既有接口出入参不变
- 移除的下线字段后端已不再消费，前端同步移除避免脏数据提交
