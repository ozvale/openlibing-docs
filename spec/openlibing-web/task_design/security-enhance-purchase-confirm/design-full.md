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
