# Remove Product Quality Whitelist — 技术设计

## 方案概述

保留 `ProductQualityPermissionService` 的公共方法及 token 身份校验，移除白名单 Mapper 依赖和查询逻辑。身份验证通过后，读、写及负责人维护操作暂时均放行，并在服务中注明后续接入李冰系统权限的 TODO。

## 架构决策

- 保留权限服务，避免修改各产品质量业务服务及 Controller 的调用方式，并为后续权限方案保留统一适配点。
- 保留 `ProductQualityUserAdapter.getCurrentUserId(request)` 调用，确保本次只移除白名单，不放开匿名访问。
- 删除仅服务于白名单校验的 Mapper、XML 和 XML 测试，避免遗留无调用实现。
- 不删除 `pq_project_quality_owner` 表、建表 SQL 或领域模型，本次不包含数据库变更。

## 涉及文件

| 文件                                         | 操作 | 说明                                                 |
| -------------------------------------------- | ---- | ---------------------------------------------------- |
| `ProductQualityPermissionService.java`       | 修改 | 仅保留 token 校验，移除白名单查询并增加后续权限 TODO |
| `ProductQualityPermissionServiceTest.java`   | 修改 | 验证已认证用户放行、匿名及 query 伪造身份仍拒绝      |
| `ProductQualityPermissionMapper.java`        | 删除 | 移除白名单查询接口                                   |
| `ProductQualityPermissionMapper.xml`         | 删除 | 移除 `pq_project_quality_owner` 白名单查询 SQL       |
| `ProductQualityPermissionMapperXmlTest.java` | 删除 | 随白名单 Mapper XML 一并移除                         |

## 风险与验证

- 风险：已认证用户在临时阶段均可写产品质量数据，这是本次明确接受的过渡行为；后续必须通过李冰系统权限方案恢复细粒度授权。
- 验证：运行权限服务测试和产品质量相关测试，检查匿名请求行为不变，并确认产品代码不再引用白名单权限 Mapper。

## 跨仓影响

仅修改 `openlibing-ops` 业务实现及当前 `openlibing-docs` 设计记录，无外部接口、数据模型或部署变更。
