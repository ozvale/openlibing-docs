# 下线技术委员会模块

## 需求背景

经 SIG 评审，决定下线 openlibing-framework 中的技术委员会（CMC）相关功能。前端仓（openlibing-web）已在 `7ddcec03` 提交中删除了整个 `CommitterManage` 模块（17 个文件，5301 行），API 层 44 个函数均为死代码，无组件调用。后端需同步清理对应的接口、服务、数据模型和常量。

## 功能描述

### 做什么

1. **整体删除** Javadoc 直接描述为"技术委员会"的类：Controller、Service、Mapper、Entity、DTO、AOP、常量、测试
2. **整体删除** CMC 模块删除后无调用方的关联 Entity/DTO 文件（gitcodeyaml 包、committer/branchkeeper/reviewer/maintainer/field 相关 Entity/DTO、dto/git/code 包）
3. **移除 CMC 引用**但保留的类：SelectController/Service 中的 CMC 端点（含 get-department）、ProductUserServiceImpl/ProjectUserServiceImpl 中的 CMC 角色守卫、日志常量
4. **移除 HTTP 接口**：38 个端点（5 个 Controller 全部端点 + SelectController 8 个 CMC 端点含 get-department）
5. **清理死代码**：SelectServiceImpl 中的 `getSigUser` 方法及相关未使用的 import（Gson、TypeToken、JsonObject）

### 不做什么

1. 不修改 `POST /select/get-committer`（三大门禁审核人查询，前端 5 个组件活跃使用）
2. 不修改 PlatformRelease 模块的 sig 相关接口（属于发布模块，非 CMC）
3. 不修改 CVE 模块的 SIG_COLUMNS（仅表格列名，非 CMC 功能）
4. 不处理前端残留硬编码（`product_cmc`/`project_cmc` 角色名在 3 个 Vue 文件中，无害死代码，由前端仓单独清理）
5. 不处理数据库表/列的废弃（仅代码层面下线，DDL 变更不在本次范围）

## 验收标准

- [x] 后端编译通过，无 CMC 相关类引用错误
- [x] 38 个 CMC HTTP 接口不可访问
- [x] 前端活跃功能（三大门禁审核人查询、发布看板 sig、CVE sig 列）不受影响
- [x] 无新增测试失败（仅删除/改造 CMC 相关测试）— Tests run: 2012, Failures: 0
- [x] `product_cmc`/`project_cmc` 角色守卫移除后，用户管理功能正常

## 影响范围

- **后端仓**：openlibing-framework（~104 个文件删除 + 11 个文件编辑）
- **前端仓**：openlibing-web（无功能性影响，3 处硬编码为无害死代码）
- **数据库**：代码层面下线，DDL 变更不在本次范围

## 关联

- 业务 Issue: openlibing/openlibing-framework#77
- 前端下线提交: openlibing-web `7ddcec03`
