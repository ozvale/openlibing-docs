# Tasks: filterDropdown 空选项列表误判全选修复

> 状态：代码实现已完成（openlibing-web `issue_fix` 分支，commit `a4cdb2541`）。

## 实现清单

- [x] `src/components/filterDropdown.vue` `checkedChanges()`：全选判定增加 `base.length > 0` 前置条件，空选项列表不再误判为全选（1 文件 3 行）

## 验证

- [ ] ESLint：改动文件 0 新增 error
- [ ] 手工回归（缺陷场景）：远程选项模式下输入搜索词 → 搜索结果仅展示不被自动勾选、全选框未选
- [ ] 手工回归（不回归项）：先全选再搜索仍自动勾选搜索命中项；手动全选/取消/半选正常；静态选项模式行为不变；重置后全选框复位
