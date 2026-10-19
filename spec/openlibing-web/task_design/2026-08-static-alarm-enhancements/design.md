## Context

StaticAlarm 告警列表页面原有展示"待处理"和"已关闭"两个状态标签，后端接口返回 `unresolvedCount` 和 `closedCount` 两个数量字段，列表查询使用 `closed` 和 `statuses` 参数。后端重构后：

- 返回更细粒度的字段：`pendingCount`（待处理）、`ignoredFalsePositiveCount`（误报数）、`ignoredTestUsageCount`（测试使用数）、`ignoredWontFixCount`（不修复数）、`resolvedAutoCount`（已修复数）
- 新增 `shieldTypes` 字段返回屏蔽原因列表（`{code, desc}[]`）
- 列表查询改用 `tab` 参数（PENDING/IGNORED/RESOLVED）
- 已修复状态值从 `RESOLVED_AUTO` 改为 `RESOLVED`

现有项目模式参考：

- 其他页面（如漏洞公告）也使用类似的 `tab` 参数切换状态
- `searchQualifiers` 模式在多个告警/漏洞页面通用

## Goals / Non-Goals

**Goals:**

- 适配后端接口字段重构，正确展示三态数量
- 将已关闭标签拆分为已修复和已忽略，各态独立展示数量
- 列表查询参数改为 `tab` 字段
- 新增忽略原因筛选，仅在已忽略状态下展示
- 数据来源筛选改为单选
- 状态值 `RESOLVED_AUTO` 同步为 `RESOLVED`

**Non-Goals:**

- 不改变告警列表的表格行数据结构
- 不改造其他告警类型页面（如 SCA/CodeCheck 的告警页面）
- 不引入新的 UI 组件库
- 不修改后端接口

## Decisions

### 1. 状态标签拆分：三态独立标签

**选择**: 将原有的"已关闭"标签拆分为"已修复"和"已忽略"两个独立 el-tab-pane

**理由**: 后端接口已返回 `resolvedAutoCount` 和 `ignored*Count` 三字段，拆分后用户可分别筛选已修复和已忽略的告警，避免混淆。已忽略告警下还新增了忽略原因筛选，标签独立使 UI 逻辑更清晰。

**替代方案**: 不拆分，仍用已关闭标签 → 拒绝，无法展示忽略原因筛选

### 2. 忽略原因筛选项：仅在已忽略状态下展示

**选择**: 在 `searchQualifiers` 中为忽略原因添加 `visible: query.status === 'IGNORED'` 条件，切换状态时重置 `shieldTypes`

**理由**: 忽略原因仅在已忽略状态下有意义，避免在其他状态下多此一举。切换状态时重置避免残留筛选条件导致接口报错。

**实现**:

```typescript
searchQualifiers() {
  const qualifiers = [
    // ...其他筛选条件
    {
      key: '忽略原因',
      label: '忽略原因',
      visible: this.query.status === 'IGNORED',
      options: this.options.shieldTypes.map((item) => ({
        label: `${item.desc} (${this.shieldTypeCount(item.code)})`,
        token: `忽略原因:${item.desc}`,
        value: item.desc,
      })),
    },
  ];
  return qualifiers.filter((item) => item.visible !== false);
},
changeStatus(status) {
  this.query.status = status;
  this.query.shieldTypes = [];
  this.fetchList();
}
```

### 3. 忽略原因选项显示数量

**选择**: 在忽略原因下拉选项的 label 后拼接 `(数量)`，数量来源为数量接口的 `ignoredFalsePositiveCount`、`ignoredTestUsageCount`、`ignoredWontFixCount`

**理由**: 用户要求直观展示各忽略原因的数量，方便了解分布情况。无需额外接口，利用已有数量字段即可。

### 4. 数据来源改为单选

**选择**: 将 `sources` 类型从 `string[]` 改为 `string`，从 `MULTI_FILTER_KEYS` 中移除，筛选组件设置 `multiple: false`

**理由**: 后端接口只接受单值，多选时前端虽能勾选多个但传给接口只有第一个值，产生误导。改为单选后 UI 与接口行为一致，用户操作更清晰。

**替代方案**: 保持多选，修改接口适配 → 拒绝，后端接口为通用设计，不应为单页面改动

### 5. 状态值同步：RESOLVED_AUTO → RESOLVED

**选择**: 将前端所有 `RESOLVED_AUTO` 替换为 `RESOLVED`，包括类型定义、状态映射、模板判断等

**理由**: 后端已将该值改为 `RESOLVED`，前端需同步。`RESOLVED_AUTO` 在项目中仅用于 StaticAlarm 页面，改动范围可控。

## Risks / Trade-offs

- **[忽略原因数量刷新]** → 忽略原因选项数量依赖数量接口返回，切换状态时重新获取。如果数量接口返回不及时，下拉选项数量可能短暂显示为 0。
- **[数据来源单选用户体验]** → 此前用户可勾选多个，现在改为单选，已习惯多选操作的用户可能需要适应。
- **[tab 参数兼容性]** → 旧版接口仍在使用 `closed`/`statuses` 参数，需确保前端只发送 `tab` 参数，不发送已被废弃的字段。
