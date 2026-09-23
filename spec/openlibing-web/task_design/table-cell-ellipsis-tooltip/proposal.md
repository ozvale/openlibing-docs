# 需求背景

## 需求描述

解决全局表格单元格内容超出列宽时文字换行导致的表格行高不一、可读性差的问题。改为：超长内容单行省略号显示，悬停通过 tooltip 展示完整内容；同时覆盖表头超长、时间列、链接列等场景。涉及全局表格组件（myTable.vue）与十余个业务页面的局部表格。

## 关联 Issue

- [openlibing/openlibing-web#283](https://gitcode.com/openlibing/openlibing-web/issues/283)（[缺陷]: 文字小于表格宽度时展示省略和tooltip提示，而不是文字换行）

## 验收标准

1. ✅ 单元格内容超出列宽时单行省略显示，悬停 tooltip 展示完整内容
2. ✅ 短内容正常显示，无多余 tooltip
3. ✅ 时间列、链接列显示正常，筛选下拉、排序图标与省略号不重叠
4. ✅ 覆盖页面：账号管理、反馈管理、检测中心、发布管理（制品列表）、合法合规（规则表）、工具管理、0-day 漏洞列表、用户管理、角色管理、CVE 列表、机器管理（账号/接口）、管理中心（公告板、用户看板、操作日志）
5. ✅ 纯展示层优化，不涉及接口与数据变更

## 变更范围

18 个文件（+753 / -159），核心为：

- `src/components/myTable.vue`（全局表格组件）
- `src/components/filterDropdown.vue`（筛选下拉）
- `src/views/` 下 15 个业务页面/配置文件

## 优先级

中（全局体验优化）

## 关联 PR

- [PR #797 feat(table): 表格单元格超长文本省略显示并增加 tooltip 悬停提示](https://gitcode.com/openlibing/openlibing-web/pull/797)（已合入 release_20260923，2026-09-22）
