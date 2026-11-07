# 里程碑分页查询调整为项目列表查询

## 需求背景

产品质量里程碑不再需要分页查询接口，详情接口调整为按项目查询全部里程碑；同时修复目录根查询链路重构后遗留的测试关联错误。

## 功能描述

- 删除 `/projects/product-quality/milestones/getPage` 及其应用层、领域层、Mapper/XML 和测试中的分页专用代码。
- `/projects/product-quality/milestones/detail` 删除 `id` 入参，仅保留 `projectId`，返回 `Result<List<MilestoneResp>>`。
- 列表按 `id DESC` 排序，无记录时返回空数组。
- 修复 `listMilestoneRootCatalogs()` 新链路相关测试，不恢复已删除的基础目录旧接口。
- 保留工作区现有权限变更；本轮不 commit、不 push、不创建 PR。

## 验收标准

- [ ] `/getPage` 及其分页专用关联代码全部移除。
- [ ] `/detail?projectId=xxx` 返回项目全部里程碑集合，空结果返回空数组。
- [ ] 更新和删除仍按 `id + projectId` 定位单条里程碑，不受列表查询调整影响。
- [ ] 目录测试使用当前根目录、非根目录查询方法，不再引用不存在的旧方法。
- [ ] 相关测试通过；若受环境阻塞，记录具体阻塞原因和已完成的替代检查。
