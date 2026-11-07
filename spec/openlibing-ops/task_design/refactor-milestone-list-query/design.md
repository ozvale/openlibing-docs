# 里程碑分页查询调整为项目列表查询 — 技术设计

## 方案概述

采用项目维度列表查询替代分页查询：Controller 的 `get` 直接调用应用服务获取 `List<MilestoneResp>`，领域层通过项目 ID 查询全部记录，Mapper 使用独立列表 SQL 并固定 `ORDER BY id DESC`。分页专用方法完整删除，避免保留无效代码或复用分页容量模拟全量查询。

## 架构决策

- 复用 `/detail` 路径和 `MilestoneResp`，仅将响应数据调整为集合并删除 `id` 参数。
- 项目无里程碑时返回空列表，不再沿用单条详情不存在时的业务异常。
- `selectByIdAndProjectId` 继续服务更新和删除，不随分页代码删除。
- 目录部分以当前 `listMilestoneRootCatalogs` / `listMilestoneNonRootCatalogs` 链路为准修正测试，不恢复 `listBasicCatalogs` 旧链路。

## 涉及文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `ProductQualityMilestoneController.java` | 修改 | 删除 page，get 改为项目列表 |
| `ProductQualityMilestoneService.java` | 修改 | 删除分页转换，返回响应列表 |
| `ProductQualityMilestoneDomainService.java` | 修改 | 删除分页领域查询，新增项目列表查询 |
| `PqMilestoneMapper.java` / `PqMilestoneMapper.xml` | 修改 | 分页 SQL 改为项目列表 SQL |
| `ProductQualityMilestone*Test.java` / Mapper XML 测试 | 修改 | 覆盖列表、空结果、项目隔离和代码移除 |
| `ProductQualityCatalog*Test.java` | 修改 | 对齐当前目录根/非根查询链路 |
| `ProductQualityCatalogController.java` | 不修改 | 保持当前接口参数约束，仅对齐失效测试 |

## 风险与验证

- 对外响应由单个对象变为数组，属于调用方契约变化，需以前端同步调整为前提。
- 全量列表适合当前项目里程碑规模，不引入新的过滤或排序参数。
- 先更新测试形成失败用例，再实现代码；运行相关测试和差异检查。若 Maven 私有依赖持续返回 401，明确记录无法执行完整测试的环境原因。

## 跨仓影响

仅修改 `openlibing-ops` 业务代码及本目录 spec，不修改其他业务仓。
