# Proposal: filterDropdown 空选项列表误判全选导致搜索命中项被自动勾选

## 需求背景

通用筛选下拉组件 `src/components/filterDropdown.vue` 在**远程选项模式**（父组件监听 `getOptions` 并回调 `setOptions` 注入选项）下存在缺陷：

搜索时组件先清空 `showOptions` 再异步拉取选项，此间隙 `checkedChanges()` 以 `this.options`（远程模式为空）或 `showOptions`（已清空）为基准计算全选状态，`checkedCount === base.length` 出现 `0 === 0` 误判为**已全选**（`checkAll = true`）。随后搜索结果经 `setOptions()` 回调注入时，其内部 `if (this.checkAll)` 分支会把全部搜索命中项自动写入 `checkedOptions`——用户仅输入了搜索词，未做任何勾选，筛选条件却被静默污染。

影响面：该组件被 10 处页面引用（cve 漏洞总览、SLO 详情抽屉、社区软件列表、SBOM 组成分析、巡检中心、门禁增量检查、发布评审等），其中使用远程选项模式的页面均受影响。

## 功能描述

`checkedChanges()` 的全选判定增加空列表前置条件：

```diff
- this.checkAll = checkedCount === base.length;
+ // 空选项列表不能判定为全选（远程模式搜索时会先清空 showOptions 再异步
+ // 拉取选项，0===0 会误置 true，导致搜索命中项被 setOptions 自动勾选）
+ this.checkAll = base.length > 0 && checkedCount === base.length;
```

- 空选项列表（`base.length === 0`）一律判定为**未全选**，阻断 `setOptions` 的自动勾选分支
- 非空列表行为不变（`checkedCount === base.length` 仍判定全选）
- `isIndeterminate` 判定（`checkedCount > 0 && checkedCount < base.length`）天然不受空列表影响，无需修改

## 范围外（明确不做）

- `setOptions` 自动勾选机制本身保留（「先全选再搜索」场景仍应自动勾选搜索结果，属既有设计）
- 组件其余行为（静态选项模式、radio 类型、分页加载）不变

## 验收标准

- [ ] 远程选项模式下输入搜索词：搜索结果仅展示，不被自动勾选；勾选框保持未选状态
- [ ] 先点全选再搜索：搜索命中项仍被自动勾选（既有全选语义不回归）
- [ ] 手动全选/取消全选、半选状态展示正常（非空列表行为不变）
- [ ] 静态选项模式（`options` 直接传入）全选/半选/重置行为不回归

## 关联

- 业务仓分支：`issue_fix`（openlibing-web），commit `a4cdb2541`
