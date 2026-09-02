# 前端参考方案：流水线白名单人员维度配置（openlibing-cicd-web）

> 本文档面向 openlibing-cicd-web 的开发（含 AI 辅助开发），说明后端已定稿的设计意图、接口契约与期望的前端表现。后端实现见同目录 design.md。

## 需求一句话

在「流水线白名单管理」页为单条流水线配置触发人员名单；配置后，仅名单内人员（且具备现有执行权限）可对该流水线执行「手动运行 / 重试」。

## 核心设计意图（为什么这么设计）

1. **权限模型是 AND 叠加**：现有角色权限（项目管理员/CIE，走既有权限链路）是第一道门，触发人员名单是第二道门，**两道都过才能触发**。名单只能收紧不能放大——没有角色权限的人即使被列入名单也触发不了。
2. **前后端契约收口为两个布尔字段**：前端不实现任何校验逻辑，只消费后端返回的 `triggerRestricted` + `canTrigger`。这样后端未来调整校验规则（改组合方式、迁移存储、引入用户组）前端零改动。
3. **未配置 = 不限制**：名单为空的流水线行为与现状完全一致，前端零打扰（不置灰、不提示）。
4. **多入口表现必须一致**：列表页执行图标、详情页运行按钮、详情页重试按钮，三处共用同一判断来源与同一文案，不允许各自实现。

## 接口契约（后端提供）

### 1. 批量查询触发权限标记（列表/详情页加载时调用一次）

`POST /project/pipeline/trigger-users/flags?userId=xxx`

请求体：`{ "projectId": "300033", "pipelineIds": ["p-001", "p-002"] }`（`pipelineIds` 可选，缺省查项目下全部已开启白名单的流水线；`userId` query 参数可选，缺省时 `canTrigger` 为 false）

响应（示意）：

```json
{
  "code": 200,
  "data": {
    "p-001": { "triggerRestricted": true, "canTrigger": false },
    "p-002": { "triggerRestricted": false, "canTrigger": true }
  }
}
```

| 字段                | 类型    | 说明                                      |
| ------------------- | ------- | ----------------------------------------- |
| `triggerRestricted` | boolean | 该流水线是否配置了触发人员限制            |
| `canTrigger`        | boolean | 当前用户是否可触发（后端已算好 AND 结论） |

映射中不存在的流水线 = 不限制（保持现状）。因流水线列表响应为华为云 SDK 类型无法直接加字段，标记通过本独立接口获取。

### 2. 查询触发人员名单

`POST /project/pipeline/trigger-users/query?userId=xxx`

请求体：`{ "projectId": "300033", "pipelineId": "xxx" }`

响应（示意）：

```json
{
  "code": 200,
  "data": {
    "pipelineId": "xxx",
    "triggerWhiteList": ["cisu42", "zhangsan"],
    "canEdit": true
  }
}
```

- `triggerWhiteList`：账号（用户名）数组，空数组 = 未配置限制
- `canEdit`：当前用户是否可编辑名单（通过权限校验后恒为 true；无权限时接口直接报错，前端按错误处理隐藏/置灰入口）

### 3. 保存触发人员名单（全量覆盖语义）

`POST /project/pipeline/trigger-users/save?userId=xxx`

请求体：`{ "projectId": "300033", "pipelineId": "xxx", "triggerWhiteList": ["cisu42", "zhangsan"] }`

- **全量覆盖**：前端提交编辑后的完整名单（不是增量）
- 空数组 = 清除限制（等同于关闭）
- 后端校验：编辑权限（具备流水线运行权限的角色：admin / project_manager / project_cie / pipeline_executor）、目标流水线白名单已开启、账号格式（`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`）、去重、上限 100 个
- 校验失败返回明确错误信息，直接 toast 展示即可

## 期望的前端表现

### A. 白名单管理页（PipelineManage.vue）：触发人员编辑入口

- 每行新增「触发人员」操作入口（与现有白名单开关并列）
- **仅白名单开关为开启状态的行**展示该入口（后端也校验，前端拦截只是体验层）
- 点击打开编辑弹窗：
  - 打开时调用查询接口，**现有名单以 tag 形式展示**，每个 tag 可 × 单个删除
  - 输入框支持**批量粘贴多个账号**（分隔符：空格/逗号/分号，中英文标点均可）→ 解析、格式校验、去重后追加为 tag——交互可直接参考现有 `pipelineWebhookSettings.vue` 中 `commentWhiteList` 的实现（`parseCommentWhiteListTokens` 等函数）
  - 无效格式账号给 warning 提示：`账号仅支持字母、数字、下划线和连字符，且需以字母或数字开头`
  - 保存时全量提交，成功后关闭弹窗并刷新
  - `canEdit=false` 时入口置灰/隐藏（与后端校验对齐）

### B. 运行/重试按钮统一置灰 + 悬浮提示（三个入口）

| 入口                   | 文件参考                          |
| ---------------------- | --------------------------------- |
| 流水线列表行内执行图标 | `src/views/pipeline/pipeline.vue` |
| 流水线详情页「运行」   | 详情页组件                        |
| 运行详情「重试」       | 运行详情组件                      |

表现规则：

- `canTrigger === false` 且 `triggerRestricted === true` → 按钮置灰（disabled），悬浮显示统一文案：

  > 该流水线已限制触发人员，需同时具备流水线执行权限并在触发人员名单内

- `canTrigger === true` → 正常可点，无任何变化（含 `triggerRestricted=true` 但用户在名单内的情况——**不要**对名单内用户做任何额外提示）
- flags 接口失败、报错或映射中无该流水线 → 维持现状（按不限制处理，兼容后端未发布/灰度期间）

### C. 建议封装统一组件

参考 `openlibing-web` 仓 `NoPermissionPopover` 的思路，封装一个 `TriggerPermissionTip`（或类似）组件：接收 `canTrigger`（及可选 `triggerRestricted`），内部处理置灰 + tooltip 文案，三处入口统一套用，避免文案/逻辑漂移。

## 注意事项

1. **前端不做任何权限判断逻辑**，一切以 `canTrigger` 为准——不要在前端自行比对"当前用户是否在名单内"。
2. **重试与运行用同一套表现**：同一 `pipelineId` 的名单限制，文案相同。
3. **兼容性**：flags 接口可能失败或未部署（后端灰度期间），失败时按"不限制"处理，不得报错。
4. 一期**没有**跨流水线批量配置触发人员的能力（勾选多行批量操作不涉及触发人员），不要在批量操作里加相关入口。
5. 编辑弹窗内名单上限 100 个、去重逻辑前端也做一份（后端兜底），提升体验。
