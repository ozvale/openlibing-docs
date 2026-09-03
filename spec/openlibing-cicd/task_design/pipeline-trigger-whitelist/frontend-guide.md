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
    "p-001": {
      "triggerRestricted": true,
      "canTrigger": false,
      "hasRunPermission": true
    },
    "p-002": {
      "triggerRestricted": false,
      "canTrigger": true,
      "hasRunPermission": true
    }
  }
}
```

| 字段                | 类型    | 说明                                                                              |
| ------------------- | ------- | --------------------------------------------------------------------------------- |
| `triggerRestricted` | boolean | 该流水线是否配置了触发人员限制                                                    |
| `canTrigger`        | boolean | 当前用户是否可触发（后端已算好 AND 结论）                                         |
| `hasRunPermission`  | boolean | 当前用户是否具备流水线执行权限（第一道门结论，供悬浮提示按拦截原因分流，见 C 节） |

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
    "triggerWhiteList": [
      { "userId": "65c71434e3a442b89736d1d89f46c246", "userName": "zhuangzt" }
    ],
    "selectableMembers": [
      { "userId": "65c71434e3a442b89736d1d89f46c246", "userName": "zhuangzt" },
      {
        "userId": "479378dffe1b429aa1f65bd72dc9ea93",
        "userName": "jiangzhichao"
      }
    ],
    "canEdit": true
  }
}
```

- `triggerWhiteList`：已配置的触发人员（`userId` = openlibing 平台用户ID/UUID，`userName` 展示用），空数组 = 未配置限制；userId 查不到对应用户时 `userName` 回退为 userId 本身
- `selectableMembers`：**当前项目全部成员**（下拉数据源，后端已按项目过滤并去重，前端无需再过滤）
- `canEdit`：当前用户是否可编辑名单（通过权限校验后恒为 true；无权限时接口直接报错，前端按错误处理隐藏/置灰入口）

### 3. 保存触发人员名单（全量覆盖语义）

`POST /project/pipeline/trigger-users/save?userId=xxx`

请求体：

```json
{
  "projectId": "300033",
  "pipelineId": "xxx",
  "triggerWhiteList": ["65c71434e3a442b89736d1d89f46c246"]
}
```

- **全量覆盖**：前端提交编辑后的完整 `userId` 列表（不是增量）
- 空数组 = 清除限制（等同于关闭）
- 后端校验：编辑权限（具备流水线运行权限的角色，后端按菜单 URL 动态查询，当前快照：admin / project_manager / project_cie / pipeline_executor）、目标流水线白名单已开启、userId 格式（32 位 UUID）、去重、上限 100 个
- 校验失败返回明确错误信息，直接 toast 展示即可

## 期望的前端表现

### A. 白名单管理页（PipelineManage.vue）：触发人员编辑入口

- 每行新增「触发人员」操作入口（与现有白名单开关并列）
- **仅白名单开关为开启状态的行**展示该入口（后端也校验，前端拦截只是体验层）
- 点击打开编辑弹窗：
  - 打开时调用查询接口，一次性拿到现有名单（`triggerWhiteList`，含 userName）与项目可选成员（`selectableMembers`）
  - **人员选择器（多选下拉）**：选项来自 `selectableMembers`，展示 `userName`（可带 userId 辅助区分重名），值为 `userId`；已配置名单默认选中
  - 已配置但已不在 `selectableMembers` 中的成员（如后来退出项目）：仍以 tag/选中项展示（数据来自 `triggerWhiteList`），可删除，避免静默丢失
  - 保存时全量提交选中项的 `userId` 列表，成功后关闭弹窗并刷新
  - `canEdit=false` 时入口置灰/隐藏（与后端校验对齐）
- **不做手动输入账号**：名单标识是平台 UUID（非可读账号），手输无意义；增减人员一律走选择器

### B. 运行/重试按钮统一置灰 + 悬浮提示（三个入口）

| 入口                   | 文件参考                          |
| ---------------------- | --------------------------------- |
| 流水线列表行内执行图标 | `src/views/pipeline/pipeline.vue` |
| 流水线详情页「运行」   | 详情页组件                        |
| 运行详情「重试」       | 运行详情组件                      |

置灰条件：`canTrigger === false && triggerRestricted === true`（未配名单的流水线即使 `canTrigger=false` 也不置灰——匿名/无角色用户对公开仓流水线的既有可触发行为保持不变，与后端放行逻辑精确对齐）。

`canTrigger === true` → 正常可点，无任何变化（含 `triggerRestricted=true` 但用户在名单内的情况——**不要**对名单内用户做任何额外提示）。

flags 接口失败、报错或映射中无该流水线 → 维持现状（按不限制处理，兼容后端未发布/灰度期间）。

### C. 悬浮提示按拦截原因分流（TriggerPermissionTip 组件）

被置灰的用户有两种病因，提示必须分流——**缺角色是平台权限问题（走统一角色申请体系），不在名单是流水线业务配置问题（找管理员加名单），申请角色解决不了名单问题，指引错路会造成无效申请**。

**前端决策表**（flags 三个布尔 → 表现，四行穷尽，零额外请求）：

| 场景                         | triggerRestricted | hasRunPermission | canTrigger | 表现                                                                                     |
| ---------------------------- | ----------------- | ---------------- | ---------- | ---------------------------------------------------------------------------------------- |
| 未配名单（任意用户，含匿名） | false             | \*               | \*         | 与现状完全一致：不置灰、无悬浮提示；点击后若被后端拦（私有仓无角色 403），走既有错误处理 |
| 配了名单，有角色，在名单内   | true              | true             | true       | 正常可点，无提示                                                                         |
| 配了名单，有角色，不在名单   | true              | true             | false      | 置灰，**模式二**（联系管理员加名单，只需办一件事）                                       |
| 配了名单，无角色             | true              | false            | false      | 置灰，**模式一**（并行指引：申请角色 + 联系管理员加名单，一次告知两个条件）              |
| 未登录且流水线配了名单       | true              | \*               | \*         | 置灰，**文案A**（请登录）                                                                |

（未登录场景 flags 无 userId 可查，`hasRunPermission`/`canTrigger` 恒为 false，直接走文案A；`triggerRestricted=false` 的未登录用户回归第一行，行为不变。）

**文案A（未登录，且该流水线配了名单）**：

> 该流水线已限制触发人员，请登录后确认是否在触发人员名单内

**模式一（无角色，且该流水线配了名单）——并行指引，一次告知两个条件**：视觉与文案对齐主应用 `NoPermissionPopover`（锁图标 + 标题 + 副标题），cicd-web 为 wujie 子应用无法直接复用主应用组件与 store，在本仓内按同款结构实现：

> 🔒 暂无权限 · 启动流水线
> 触发该流水线需同时满足以下两个条件，请并行办理：
> ① 申请下列任一角色（按最小权限粒度申请）：pipeline_executor / …（角色清单来源：`GET /user/get-operation-permissions`，权限码 `pipeline_run`，主应用 Content.vue 已在项目就绪时拉取；cicd-web 侧可自行请求一次同接口，或经 wujie props 从主应用透传 `operationPermissions`）
> ② 联系项目管理员（xx、xxx）在「白名单管理 → 触发人员」中将你加入名单（联系人可点击跳转，同模式二）

并行指引的设计动机：双缺用户若只被告知"申请角色"，办完回来又被拦才知还需名单，"串行踩坑"极易引发恼火；两条件一次摊开，且找的常是同一位管理员，一次沟通可办两件事。

**模式二（有角色但不在名单）**：对齐现有 `TipMemberListComp` 联系人模式：

> 🔒 该流水线已限制触发人员，你不在触发人员名单内
> 请联系项目管理员（xx、xxx）在「白名单管理 → 触发人员」中添加你
> （联系人可点击，跳转 `/apps/project?showCurrentProjectManagers=true`；名单数据源复用 `getUserRole({ userRole: 'project_manager' / 'project_cie' })`，同 Detail.vue 的 getCurrentProjectAuth）

**设计约束**：

- 不展示名单内成员（"当前可触发的人是谁"）——关键流水线的触发名单是敏感信息，不向名单外用户暴露
- 三处入口共用同一组件同一分流逻辑，避免文案/逻辑漂移
- 后端拦截时返回的统一文案（`该流水线已限制触发人员，需同时具备流水线执行权限并在触发人员名单内`）是接口级兜底，与悬浮提示并存不冲突

## 注意事项

1. **前端不做任何权限判断逻辑**，一切以 `canTrigger` 为准——不要在前端自行比对"当前用户是否在名单内"。
2. **重试与运行用同一套表现**：同一 `pipelineId` 的名单限制，文案相同。
3. **兼容性**：flags 接口可能失败或未部署（后端灰度期间），失败时按"不限制"处理，不得报错。
4. 一期**没有**跨流水线批量配置触发人员的能力（勾选多行批量操作不涉及触发人员），不要在批量操作里加相关入口。
5. 编辑弹窗内名单上限 100 个（后端兜底校验，选择器场景一般不会触达）。
6. 名单存的是平台用户ID（UUID）而非 GitCode 账号——openlibing 账号与 GitCode 账号是两个域，**不要**用 GitCode 用户名做任何匹配或展示联想。
