# security-enhance-purchase-confirm — 完整设计方案（design-full）

> 本文档为完整版设计方案，与简版 `design.md` 并存。关联业务 Issue: https://gitcode.com/openlibing/openlibing-web/issues/275

## 1. 方案设计

### 1.1 背景与目标

“代码检查安全增强”类规则（分类标识 `security_enhance`）属于付费增强能力，需优先购买增强规则集包。当前规则集配置页（`CustomRuleConfig.vue`）保存时不做购买确认，未购买用户可能保存无法生效的规则集。

目标：保存规则集时，若本次保存内容包含安全增强类规则，弹窗提示并让用户确认购买状态——确认已购买则继续保存，选择未购买则中断保存。

### 1.2 方案选型

| 方案 | 检测方式 | 优点 | 缺点 | 结论 |
|------|---------|------|------|------|
| A | 前端本地判定：最终保存 `ruleIds` × 已加载 `ruleList` 的 `ruleTages` | 零额外请求、实现简单、与用户可见范围一致 | 无法覆盖未加载分页的规则 | ✅ 采用 |
| B | 保存前调 `rules/setting/account` 反查全量规则标签 | 覆盖全量 | 多一次网络请求、需处理分页上限、覆盖的是用户不可见规则 | 放弃 |
| C | 仅检测用户本次新勾选（`newRule`） | 最窄最简单 | 遗漏基于规则集带入的增强规则，不满足“所有保存场景”要求 | 放弃 |

### 1.3 总体流程

```text
用户点击"保存"
    │
    ▼
submitForm()
    │
    ├─ handleSubmitData() 组装保存数据（含最终 ruleIds）
    │
    ├─ getSecurityEnhanceRules(ruleIds) 检测
    │       │
    │       ├─ 命中 0 条 ──────────────────► doSubmit()（原保存流程）
    │       │
    │       └─ 命中 N 条
    │               │
    │               ▼
    │       ElMessageBox.confirm 购买确认弹窗
    │               │
    │               ├─「已购买，继续保存」──► doSubmit()
    │               └─「未购买」──────────► 中断（不发请求，停留当前页）
    │
    ▼
doSubmit()
    ├─ 复制到社区场景（copyProjectId 非空）──► 复制确认弹窗 ──► handleSubmit()
    └─ 普通场景 ──────────────────────────► handleSubmit() ──► addCodeCheckRuleset API
```

### 1.4 交互设计

- 触发范围：新增（add）/ 复制（copy）/ 修改（config）三种保存场景统一拦截
- 弹窗样式：`ElMessageBox.confirm`，`type: 'warning'`，与页面现有“复制到社区”确认弹窗风格一致
- 文案：`已勾选"代码检查安全增强"类规则（共 N 条），此类规则需优先购买增强规则集包，请确认是否已购买。`
- 按钮：确认 = `已购买，继续保存`；取消 = `未购买`
- 弹窗链式顺序：购买确认 → （复制到社区确认）→ 提交

## 2. 实现逻辑设计

### 2.1 检测函数逻辑

```text
输入：ruleIdsStr（handleSubmitData 产出的最终保存 ruleIds，逗号分隔字符串）
处理：
  1. ruleIdsStr.split(',').filter(Boolean) → 构建 Set<ruleId>（O(n)）
  2. ruleList.filter(item =>
       Set.has(item.ruleId)
       && item.ruleTages?.toLowerCase().includes('security_enhance'))
     （O(m)，m = 已加载规则数）
输出：命中的规则项数组（用于弹窗计数）
```

判定口径与后端 `RuleDelegateImpl#filterByCriteria` 完全一致：`ruleTages` 小写化后包含 `security_enhance`。

### 2.2 submitForm 重构逻辑

```text
submitForm():
  data = handleSubmitData()
  isCopyTo = copyProjectName || ruleInForm.projectName

  doSubmit():
    if copyProjectId:
      ElMessageBox.confirm(复制到社区确认) → handleSubmit(data, isCopyTo)   // 原逻辑原样保留
    else:
      handleSubmit(data, isCopyTo)

  securityEnhanceRules = getSecurityEnhanceRules(data.ruleIds)
  if securityEnhanceRules.length > 0:
    ElMessageBox.confirm(购买确认文案含 length)
      .then(doSubmit)      // 已购买
      .catch(noop)         // 未购买 → 静默中断
  else:
    doSubmit()
```

### 2.3 边界场景矩阵

| 场景 | option | copyProjectId | 含增强规则 | 行为 |
|------|--------|---------------|-----------|------|
| 新增-未勾选增强 | add | - | 否 | 直接保存（与现状一致） |
| 新增-勾选增强 | add | - | 是 | 弹窗 → 已购买保存 / 未购买中断 |
| 复制-本社区 | copy | 空 | 是 | 弹窗 → 已购买 → 保存 |
| 复制-跨社区 | copy | 非空 | 是 | 弹窗 → 已购买 → 复制确认 → 保存 |
| 修改-含增强 | config | - | 是 | 弹窗（覆盖基于规则集带入的增强规则） |
| 任意-未购买 | * | * | 是 | 中断，不发请求，`newRule/oldRule` 状态保留，页面可继续编辑 |

### 2.4 幂等与状态

- 中断保存不改变任何页面状态（`newRule`、`oldRule`、表格勾选均保留），用户可调整后再次保存
- 弹窗期间无并发风险（`ElMessageBox` 模态阻塞）

## 3. 类设计

前端 `<script setup>` 无类定义，本节映射为模块内函数/常量职责设计。

### 3.1 改动文件

`apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/children/CustomRuleConfig.vue`

### 3.2 新增成员

| 成员 | 类别 | 签名 | 职责 |
|------|------|------|------|
| `SECURITY_ENHANCE_TAG` | 模块常量 | `string = 'security_enhance'` | 安全增强分类标识，单一事实来源，避免魔法字符串 |
| `getSecurityEnhanceRules` | 函数 | `(ruleIdsStr: string) => Array<RuleItem>` | 输入最终保存 ruleIds，返回命中的增强类规则项列表 |

### 3.3 重构成员

| 成员 | 变化 |
|------|------|
| `submitForm` | 原复制确认 + 提交逻辑抽取为内部 `doSubmit()` 闭包；新增检测与购买确认前置拦截 |

### 3.4 不新增的东西（YAGNI）

- 不新建组件、composable、工具模块（检测函数仅此一处使用）
- 不引入 TypeScript interface 声明文件（该文件为 JS 风格 `<script setup>`，无既有类型标注惯例）
- 不改动 `handleSubmitData` / `handleSubmit` / `handleIsSave` 等既有函数

### 3.5 依赖关系

```text
submitForm ──调用──► handleSubmitData（既有）
          ──调用──► getSecurityEnhanceRules（新增）
          ──读取──► ruleList（既有响应式列表，检测数据源）
          ──调用──► ElMessageBox.confirm（既有依赖）
getSecurityEnhanceRules ──读取──► ruleList、SECURITY_ENHANCE_TAG
```

## 4. 数据模型设计

### 4.1 涉及的既有数据结构（后端契约，不修改）

规则列表项（`POST /rules/setting/account` 响应 `codeCheckRuleAccountVos[]`，后端 `CodeCheckRuleAccountVo`）：

| 字段 | 类型 | 说明 | 本方案用途 |
|------|------|------|-----------|
| `ruleId` | string | 规则唯一 ID | 与最终保存 ruleIds 匹配 |
| `ruleName` | string | 规则名称 | 预留（弹窗文案可扩展展示） |
| `ruleTages` | string | 规则标签（如 `security_enhance,...`） | 检测依据 |
| 其余字段 | - | `ruleSeverity`/`ruleLanguage`/`ruleConfigList` 等 | 不涉及 |

保存请求体（`POST /project/ruleSet/custom`，前端 `handleSubmitData()` 产出）：

| 字段 | 类型 | 说明 | 本方案用途 |
|------|------|------|-----------|
| `ruleIds` | string | 最终启用规则 ID，逗号分隔 | 检测输入 |
| `uncheckIds` | string | 本次取消启用的规则 ID | 不涉及 |
| 其余 | - | `templateId`/`templateName`/`language`/`isDefault` | 不涉及 |

### 4.2 新增数据结构

仅一个运行时临时结构，无持久化模型：

```text
getSecurityEnhanceRules 返回值：Array<CodeCheckRuleAccountVo 子集>
  —— 直接复用规则列表项结构，不新建类型
```

### 4.3 数据变更

无。不改数据库、不改后端模型、不改接口契约、不改本地存储。

## 5. 性能设计

| 维度 | 分析 |
|------|------|
| 时间复杂度 | Set 构建 O(n)（n=最终 ruleIds 数）+ 列表过滤 O(m)（m=已加载规则数，分页 20/页，典型 ≤ 数百）；单次保存仅执行一次，总耗时可忽略（<1ms 量级） |
| 网络开销 | 零新增请求（方案 A 核心收益；对比方案 B 每次保存多一次接口往返） |
| 渲染性能 | 无列表渲染变化；弹窗为瞬时模态交互，不引入额外响应式依赖 |
| 内存 | 临时 `Set` 与命中数组随函数调用结束即可回收，无驻留 |
| 用户体验 | 未勾选增强规则的保存路径零感知（不弹窗、不多任何计算可忽略） |

## 6. API 接口设计

**本方案不新增、不修改任何 API。**

### 6.1 依赖的既有接口

| 接口 | 前端封装 | 用途 | 与本方案关系 |
|------|---------|------|-------------|
| `POST /ci-portal/v2/grant/auth/rules/setting/account` | `getCodeCheckRuleSetConfig` | 分页获取规则（含 `ruleTages`） | 检测数据来源，调用时机不变 |
| `POST /ci-portal/v2/grant/auth/project/ruleSet/custom` | `addCodeCheckRuleset` | 保存规则集 | 本方案在其调用前增加拦截门，接口入参不变 |

### 6.2 契约不变性说明

- 若未来后端在规则项中补充独立 `ruleSecurity` 字段，检测函数可切换数据源而无需改调用方（检测细节收敛在 `getSecurityEnhanceRules` 内）
- 全量覆盖需求（方案 B 场景）如后续提出，需要后端提供按 `ruleIds` 批量返回分类的轻量接口，本期不设计

---

# 后端设计（openlibing-codecheck，2026-08-24 范围扩展新增）

> 背景：华为云对未购买增强包的租户返回 `{"error_code":"CC.00050006","error_msg":"error_service is: RulesCenterFusion, service_error_code is: CC.00101085.500, service_error_msg is: 未购买安全增强包"}`。经调查（详见 Issue #275 讨论），codecheck 仓对该返回的处理存在三类问题：公共层丢弃 `error_code`、保存路径透传原始英文拼接串、查询路径吞掉真实原因。

## 7. 方案设计（后端）

### 7.1 方案选型

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|------|------|------|------|------|
| 1. 公共层保留 `error_code` + 调整消费点 | `signAndExecute` 归一化时保留华为云原始 `error_code`，同步调整 4 处消费点 | 错误码可结构化传递 | `CC.00050006` 是通用码，无法识别"未购买"场景（该信息只在 `error_msg` 文本内），收益为零却引入 4 处行为变更风险（`getTaskProgress/Summary/Details` 错误消息质量回退、`getTaskCmetrics` 日志行为变化） | 放弃 |
| 2. 业务层识别 + 翻译（采用） | 只改 `customTaskRuleSet` / `listCriterions` 两个业务方法，对 `error_msg` 做核心词匹配并翻译为友好中文 | 爆炸半径最小（`listCriterions` 全仓仅 1 个调用方）、失配时回退现状不劣化 | 华为云改文案会失配（可接受，回退即现状） | ✅ 采用 |

### 7.2 总体流程（保存路径）

```text
华为云 POST /v2/ruleset 返回错误（HTTP 非 2xx）
    ▼
signAndExecute 归一化：{"code":"400","error_msg":"<华为云原始串>"}   ← 不改
    ▼
customTaskRuleSet 错误分支
    ├─ logger.error 记录原始 errorCode/errorMsg（可追溯）
    ├─ errorMsg 含"未购买安全增强包"
    │       ├─ 是 → BusinessException("规则集包含代码检查安全增强类规则，请先购买增强规则集包后再保存", 500)
    │       └─ 否 → parseInt 加固后抛 BusinessException(errorMsg, code)（原行为）
    ▼
callCustomTaskRuleSet 捕获（既有逻辑不改）
    ▼
前端 res.message = 友好中文 → ElMessage.error 展示
```

查询路径（`listCriterions`）同构：错误体识别 → 命中则抛友好 `BusinessException` → `getAccountRulesBySet` 捕获透出（替代"获取规则列表失败"）。

## 8. 实现逻辑设计（后端）

### 8.1 customTaskRuleSet 错误分支（改造后伪代码）

```text
errorMsg = error_msg ?: "创建规则集失败"
errorCode = error_code ?: "500"
logger.error("customTaskRuleSet failed, errorCode:{}, errorMsg:{}")
if errorMsg.contains("未购买安全增强包"):
    throw BusinessException("规则集包含代码检查安全增强类规则，请先购买增强规则集包后再保存", 500)
try: code = Integer.parseInt(errorCode)
catch NumberFormatException: code = 500        // 加固：CC.00050006 等非数字码
throw BusinessException(errorMsg, code)        // 其余错误原行为不变
```

### 8.2 listCriterions 错误体透出（改造后伪代码）

```text
result = signAndExecute(request)
if result.isPresent():
    response = deserialize<CriterionResponse>(result)
    if response.result != null: return Optional.of(ruleDetails)      // 成功路径不变
    hashMap = deserialize<HashMap>(result)                            // 二次解析错误体
    errorMsg = hashMap.error_msg ?: ""
    logger.error("list criterions error, errorMsg:{}", errorMsg)
    if errorMsg.contains("未购买安全增强包"):
        throw BusinessException("规则集包含代码检查安全增强类规则，请先购买增强规则集包", 500)
    // 其余非预期结构：维持现状返回 empty（调用方显示"获取规则列表失败"）
return Optional.empty()
```

方法签名追加 `throws BusinessException`（checked exception，编译期强制唯一调用方适配）。

### 8.3 调用方适配（getAccountRulesBySet）

```text
try:
    ruleDetailsOptional = listCriterions(region, params, akSkVo)
    ...（既有逻辑不变）
catch BusinessException e:
    return MultiResponse().code(e.getCode()).message(e.getErrorMessage())
```

与 `callCustomTaskRuleSet`（RuleDelegateImpl L626-629）既有捕获模式完全一致。

### 8.4 兼容性核对结论（Full 模式系统性核对）

| 消费点 | 核对结果 |
|--------|---------|
| `getTaskProgress/Summary/Details`（containsKey("error_code") 分支） | 不动公共层 → 行为零变化 |
| `getTaskCmetrics`（L1221 error_code 日志） | 同上，零变化 |
| `listCriterions` 调用方 | 全仓仅 `RuleDelegateImpl:985` 一处（rg 核对），签名变更编译期全覆盖 |
| `customTaskRuleSet` 调用链 | `callCustomTaskRuleSet` 已 catch `BusinessException`，异常类型不变，零适配 |
| 其余 `containsKey("code")` 消费点（6 处） | 逻辑不涉及，零影响 |

## 9. 类设计（后端）

| 类 | 变化 | 说明 |
|----|------|------|
| `RestCodeCheckUtil` | 修改 2 个方法 | `customTaskRuleSet`：错误分支增强（日志 + 识别翻译 + parseInt 加固）；`listCriterions`：签名加 `throws BusinessException` + 错误体识别。不新增公共方法，匹配逻辑内联（仅 2 处使用，YAGNI 不抽工具方法） |
| `RuleDelegateImpl` | 修改 1 处 | `getAccountRulesBySet` 增加 catch `BusinessException` 透出 |
| `BusinessException` | 不变 | 复用既有 `BusinessException(String errorMessage, int code)` |
| `RestCodeCheckUtilTest` | 新增用例 | 见 §12 测试设计 |

常量：匹配关键词 `"未购买安全增强包"` 与友好文案在两处使用——按仓内既有风格（如 `"language非法或无效"`）内联字符串，不抽常量类。

## 10. 数据模型设计（后端）

无新增模型。涉及的既有数据结构：

| 结构 | 来源 | 变化 |
|------|------|------|
| 归一化错误体 `{"code":"400","error_msg":"..."}` | `signAndExecute` 内部产物 | 不变 |
| `CriterionResponse` / `RuleDetails` | 华为云 `/v2/criterions` 响应映射 | 不变 |
| `MultiResponse{code, message}` | 平台统一响应 | 不变（仅错误场景 message 文案变化） |
| `BusinessException{errorMessage, code}` | 既有异常 | 不变 |

## 11. 性能设计（后端）

- 错误分支新增开销：一次 `contains` 字符串匹配（<1µs），仅在华为云返回错误时执行
- `listCriterions` 错误体二次反序列化：仅发生在 `result == null` 的异常路径，正常路径零开销
- 无新增网络调用、无锁、无内存驻留

## 12. API 接口设计（后端）

**对外 REST 契约零变更**，仅错误场景行为增强：

| 接口 | 变化 |
|------|------|
| `POST /ci-portal/v2/grant/auth/project/ruleSet/custom` | 错误场景：`message` 从华为云原始英文拼接串 → 友好中文（未购买时）；不再可能因 `NumberFormatException` 返回系统异常 |
| `POST /ci-portal/v2/grant/auth/rules/setting/account` | 错误场景：`message` 从"获取规则列表失败" → 真实原因友好提示（未购买时） |

测试设计（`RestCodeCheckUtilTest`，沿用 `@Spy + doReturn` 桩掉 `signAndExecute` 的既有模式）：

1. `customTaskRuleSet` 桩返回未购买错误体 → 断言抛 `BusinessException` 且消息为友好中文
2. `customTaskRuleSet` 桩返回非数字 `error_code` 错误体 → 断言 code=500 不抛 `NumberFormatException`
3. `customTaskRuleSet` 桩返回普通错误体 → 断言原样透传（回归保护）
4. `listCriterions` 桩返回未购买错误体 → 断言抛友好 `BusinessException`
5. `listCriterions` 桩返回正常体 → 断言返回规则详情（回归保护）
