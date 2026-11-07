# Remove Product Quality Whitelist Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 移除产品质量模块的 `pq_project_quality_owner` 白名单权限校验，同时保留 token 身份校验和后续李冰权限接入点。

**Architecture:** 保留 `ProductQualityPermissionService` 公共接口，由 `ProductQualityUserAdapter` 验证有效 token 后直接放行。删除不再使用的白名单 Mapper、XML 及对应测试，不变更业务调用方和数据库。

**Tech Stack:** Java 21、Spring Boot、MyBatis、JUnit 5、Mockito、AssertJ、Maven。

**交付约束：** 按用户要求，本次不执行 commit、push 或 PR 创建。

## 进度: 4/4 complete

### Task 1：用失败测试锁定新权限行为

**Files:**
- Modify: `openlibing-ops/src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityPermissionServiceTest.java`

- [x] 将“非白名单用户无权限”测试改为“已认证用户不依赖白名单即可获得读、写、维护权限”，保持匿名及 query 伪造身份拒绝测试不变。
- [x] 运行 `mvn "-Dtest=ProductQualityPermissionServiceTest" test`。
- [x] 预期 RED：已认证但非白名单用户的断言仍返回 `false`，测试失败。

### Task 2：移除白名单实现并保留 token 校验

**Files:**
- Modify: `openlibing-ops/src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityPermissionService.java`
- Modify: `openlibing-ops/src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityPermissionServiceTest.java`
- Delete: `openlibing-ops/src/main/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityPermissionMapper.java`
- Delete: `openlibing-ops/src/main/resources/mapper/productquality/ProductQualityPermissionMapper.xml`
- Delete: `openlibing-ops/src/test/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityPermissionMapperXmlTest.java`

- [x] 删除服务中的 `ProductQualityPermissionMapper` 依赖、`isWhitelisted` 方法及白名单异常处理。
- [x] `canRead`、`canWrite`、`canManageOwners` 均先调用 `userAdapter.getCurrentUserId(request)`，再返回 `true`。
- [x] 更新类和方法注释，并增加 `TODO`：待李冰系统权限方案确定后补充权限校验。
- [x] 清理测试中的 Mapper mock、白名单异常/空结果用例和旧构造器参数，保留匿名与 query 身份伪造防护测试。
- [x] 删除白名单专用 Mapper、XML 和 XML 测试，不修改建表 SQL、表模型及其他业务文件。

### Task 3：运行相关验证

**Files:**
- Verify: `openlibing-ops/src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityPermissionServiceTest.java`
- Verify: `openlibing-ops/src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityMilestoneServiceTest.java`
- Verify: `openlibing-ops/src/test/java/com/openlibing/ops/api/controller/ProductQualityMilestoneControllerTest.java`

- [x] 权限测试完成 RED → GREEN：旧实现下已认证非白名单用户用例如预期失败，修改后 3 个权限用例全部通过。
- [x] 定向编译并运行权限、里程碑服务及里程碑 Controller 测试，共 16 个用例通过，0 failures、0 errors、0 skipped，`BUILD SUCCESS`。
- [x] 全量 `testCompile` 受当前分支既有目录测试编译错误阻塞：相关测试引用了主代码中不存在的目录查询方法；与本次权限改动无关，未扩大修改范围。
- [x] 检索 `ProductQualityPermissionMapper` 和 `isWhitelisted`，确认业务代码及测试中无遗留引用。

### Task 4：交付前自检

**Files:**
- Review: `openlibing-ops` 工作区差异
- Review: `openlibing-docs/spec/openlibing-ops/task_design/remove-product-quality-whitelist/`

- [x] 检查仅包含已确认的权限实现、测试、删除文件和本需求 spec，无无关格式化或重构。
- [x] 检查有效 token 仍必需、白名单查询已移除、李冰权限 TODO 已保留。
- [x] 检查数据库表、SQL、接口路径和响应结构未变更。
- [x] 使用 `git status --short` 和 `git diff --check` 检查最终差异，不执行 commit 或 push。
