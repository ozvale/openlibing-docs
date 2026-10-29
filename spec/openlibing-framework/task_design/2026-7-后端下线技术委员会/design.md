# 下线技术委员会模块 — 技术设计

## 方案概述

从 openlibing-framework 后端代码中移除技术委员会（CMC）模块的全部功能，包括 5 个 Controller（38 个端点）、10 个 Service、8 对 Mapper、相关 Entity/DTO/AOP/常量/测试，以及非 CMC 类中的 CMC 引用清理。CMC 模块删除后无调用方的关联 Entity/DTO 文件一并删除。

## 架构决策

### 决策 1：整体删除 vs 渐进废弃

**选择**：整体删除

**原因**：前端已在 `7ddcec03` 提交中删除了整个 CommitterManage 模块，API 层 44 个函数均为死代码。后端保留这些接口没有意义，反而增加维护成本。

### 决策 2：SigInfoManagerController 整体删除

**选择**：整体删除（用户确认）

**原因**：该 Controller 的 8 个端点中，2 个直接依赖 cmcId（check-all-sig-sha、query-role-info），其余 6 个虽然不直接依赖 cmcId，但其 Service 实现（SigInfoManagerServiceImpl）深度依赖 CmcInfoMapper 和 CmcInfoServiceImpl 进行权限校验和 yaml 同步。前端验证显示所有 sigInfo API 均为死代码。

### 决策 3：SelectController 的 get-sig-committer 删除

**选择**：删除（用户确认）

**原因**：前端无引用，且该接口读取外部 YAML API 的 sig-info 配置，与技术委员会的 sig 组管理有关联。

### 决策 4：SelectController 的 get-department 删除

**选择**：删除（用户确认）

**原因**：该接口原本返回产业-项目-CMC 层级数据，CMC 下线后仅剩产业-项目数据，前端已无调用方，直接删除。

### 决策 5：保留 get-committer 接口

**选择**：保留

**原因**：`POST /select/get-committer` 被前端 5 个组件活跃调用（SCA confirmBox、CodeCheck codeList、AntiPoisoning PoisoningResult、SCA referralComponent、SCA ScanEmailAddRuleDialog）。该接口读取外部 YAML API 获取三大门禁审核人信息，不依赖 CMC 数据库表。

### 决策 6：CMC 关联 Entity/DTO 整体删除

**选择**：整体删除（而非仅移除 cmcId 字段）

**原因**：CMC 模块的 Controller/Service/Mapper 全部删除后，committer/branchkeeper/reviewer/maintainer/field 相关的 Entity 和 DTO 文件已无任何调用方。保留这些文件只会产生死代码，因此一并删除。包括：
- `entity/gitcodeyaml/` 整个包（6 个文件）
- `entity/committer/`、`entity/branchkeeper/`、`entity/reviewer/`、`entity/maintainer/`、`entity/field/` 下的全部 Entity
- `dto/committer/`、`dto/branchkeeper/`、`dto/reviewer/`、`dto/maintainer/`、`dto/field/` 下的全部 DTO
- `dto/git/code/` 整个包（7 个文件）

### 决策 7：数据库 DDL 变更不在本次范围

**选择**：仅代码层面下线

**原因**：DDL 变更（删除表/列）需要 DBA 审批和数据迁移评估，风险较高。代码下线后，cmc_id 列和 cmc_info 表不再被访问，可后续单独处理 DDL。

### 决策 8：清理 SelectServiceImpl 死代码

**选择**：删除 `getSigUser` 方法及相关未使用的 import

**原因**：`getSigUser` 方法原本被已删除的 `getSigCommitter` 调用，CMC 模块下线后该方法无任何调用方。同时，该方法使用的 Gson、TypeToken、JsonObject 三个 import 也不再被其他代码使用，一并清理。

## 涉及文件

### 整体删除（~104 个文件）

#### Controller（5 个）

| 文件 | 端点数 |
|------|--------|
| `controller/CommitterManagerController.java` | 11 |
| `controller/BranchKeeperManagerController.java` | 4 |
| `controller/ReviewerManagerController.java` | 4 |
| `controller/FieldManagerController.java` | 9 |
| `controller/SigInfoManagerController.java` | 8 |

#### Service 接口 + 实现（10 个）

| 文件 | Javadoc |
|------|---------|
| `service/CmcInfoService.java` | 技术委员会管理、committer管理 |
| `service/impl/CmcInfoServiceImpl.java` | 技术委员会管理、committer管理 |
| `service/BranchKeeperInfoService.java` | 技术委员会-branchkeeper管理 |
| `service/impl/BranchKeeperInfoServiceImpl.java` | 技术委员会-branchkeeper管理 |
| `service/ReviewerInfoService.java` | 技术委员会管理-reviewer管理 |
| `service/impl/ReviewerInfoServiceImpl.java` | 技术委员会管理-reviewer管理 |
| `service/FieldManagerService.java` | 技术委员会-sig组管理 |
| `service/impl/FieldManagerServiceImpl.java` | 技术委员会-sig组管理 |
| `service/SigInfoManagerService.java` | sig信息管理服务 |
| `service/impl/SigInfoManagerServiceImpl.java` | sig信息管理服务 |

#### Mapper 接口 + XML（14 个文件，7 对）

| 文件 | Javadoc |
|------|---------|
| `mapper/CmcInfoMapper.java` + `CmcInfoMapper.xml` | 技术委员会数据库操作 |
| `mapper/CommitterInfoMapper.java` + `CommitterInfoMapper.xml` | 技术委员会-committer数据库操作 |
| `mapper/MaintainerInfoMapper.java` + `MaintainerInfoMapper.xml` | 技术委员会-maintianer管理数据库操作 |
| `mapper/ReviewerInfoMapper.java` + `ReviewerInfoMapper.xml` | 技术委员会-reviewer管理数据库操作 |
| `mapper/BranchKeeperInfoMapper.java` + `BranchKeeperInfoMapper.xml` | 技术委员会-branchkeeper管理数据库操作 |
| `mapper/FieldInfoMapper.java` + `FieldInfMapper.xml` | 技术委员会 |
| `mapper/YamlMapper.java` + `YamlMapper.xml` | 技术委员会-gitcode平台sig管理数据库操作 |

#### Entity（~23 个）

| 文件 | 说明 |
|------|------|
| `entity/cmc/CmcInfoEntity.java` | 技术委员会对象 |
| `entity/cmc/CmcWithDepartmentEntity.java` | CMC 扩展实体 |
| `entity/committer/CommitterInfoEntity.java` | CMC 删除后无调用方 |
| `entity/committer/CommitterAndRepoEntity.java` | CMC 删除后无调用方 |
| `entity/committer/UserInfoEntity.java` | CMC 删除后无调用方 |
| `entity/branchkeeper/BranchKeeperInfoEntity.java` | CMC 删除后无调用方 |
| `entity/reviewer/ReviewerInfoEntity.java` | CMC 删除后无调用方 |
| `entity/maintainer/MaintainerInfoEntity.java` | CMC 删除后无调用方 |
| `entity/field/FieldInfoEntity.java` | CMC 删除后无调用方 |
| `entity/field/FieldAndBranchKeeperEntity.java` | CMC 删除后无调用方 |
| `entity/field/FieldAndCommitterEntity.java` | CMC 删除后无调用方 |
| `entity/field/FieldAndRepoEntity.java` | CMC 删除后无调用方 |
| `entity/field/FieldAndReviewerEntity.java` | CMC 删除后无调用方 |
| `entity/gitcodeyaml/YamlEntity.java` | CMC 删除后无调用方 |
| `entity/gitcodeyaml/SigBasicEntity.java` | CMC 删除后无调用方 |
| `entity/gitcodeyaml/SigEntity.java` | CMC 删除后无调用方 |
| `entity/gitcodeyaml/SigBranchEntity.java` | CMC 删除后无调用方 |
| `entity/gitcodeyaml/SigEntryEntity.java` | CMC 删除后无调用方 |
| `entity/gitcodeyaml/SigRepoEntity.java` | CMC 删除后无调用方 |

#### DTO（~45 个）

| 文件 | 说明 |
|------|------|
| `dto/cmc/CmcInfoDTO.java` | 技术委员会-cmc |
| `dto/cmc/PermissionDTO.java` | 技术委员会-cmc |
| `dto/git/code/SigRoleDTO.java` | 仅被 SigInfoManagerServiceImpl 使用 |
| `dto/git/code/SigRoleInfoDTO.java` | 仅被 SelectServiceImpl CMC 查询方法使用 |
| `dto/git/code/ProcessYamlParam.java` | CMC 删除后无调用方 |
| `dto/git/code/BatchResult.java` | CMC 删除后无调用方 |
| `dto/git/code/CheckSigRepoDTO.java` | CMC 删除后无调用方 |
| `dto/git/code/QuerySigInfoDTO.java` | CMC 删除后无调用方 |
| `dto/git/code/SaveLogParam.java` | CMC 删除后无调用方 |
| `dto/git/code/SigMemberDTO.java` | CMC 删除后无调用方 |
| `dto/git/code/SigRepoDTO.java` | CMC 删除后无调用方 |
| `dto/git/code/SigRepoRawDTO.java` | CMC 删除后无调用方 |
| `dto/committer/CommitterInfoDTO.java` | CMC 删除后无调用方 |
| `dto/committer/UpdateCommitterDTO.java` | CMC 删除后无调用方 |
| `dto/committer/QueryCommitterDTO.java` | CMC 删除后无调用方 |
| `dto/committer/CommitterAndPlatformInfo.java` | CMC 删除后无调用方 |
| `dto/committer/CommitterAndRepoDTO.java` | CMC 删除后无调用方 |
| `dto/committer/CommitterWithUserInfoDTO.java` | CMC 删除后无调用方 |
| `dto/branchkeeper/BranchKeeperInfoDTO.java` | CMC 删除后无调用方 |
| `dto/branchkeeper/UpdateBranchKeeperDTO.java` | CMC 删除后无调用方 |
| `dto/branchkeeper/QueryBranchKeeperDTO.java` | CMC 删除后无调用方 |
| `dto/branchkeeper/BranchKeeperAndPlatformInfo.java` | CMC 删除后无调用方 |
| `dto/branchkeeper/BranchKeeperAndRepoDTO.java` | CMC 删除后无调用方 |
| `dto/reviewer/ReviewerInfoDTO.java` | CMC 删除后无调用方 |
| `dto/reviewer/UpdateReviewerDTO.java` | CMC 删除后无调用方 |
| `dto/reviewer/QueryReviewerDTO.java` | CMC 删除后无调用方 |
| `dto/reviewer/ReviewerAndPlatformInfo.java` | CMC 删除后无调用方 |
| `dto/reviewer/ReviewerAndRepoDTO.java` | CMC 删除后无调用方 |
| `dto/maintainer/MaintainerInfoDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldInfoDTO.java` | CMC 删除后无调用方 |
| `dto/field/UpdateFieldInfoDTO.java` | CMC 删除后无调用方 |
| `dto/field/QueryFieldDTO.java` | CMC 删除后无调用方 |
| `dto/field/QueryCommitterScheduleDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldUserInfoDTO.java` | CMC 删除后无调用方 |
| `dto/field/RoleLocationDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldUpdateContext.java` | CMC 删除后无调用方 |
| `dto/field/FieldAndBranchKeeperDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldAndCommitterDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldAndRepoDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldAndReviewerDTO.java` | CMC 删除后无调用方 |
| `dto/field/FieldRepoBranchDTO.java` | CMC 删除后无调用方 |
| `dto/field/GitcodePathDTO.java` | CMC 删除后无调用方 |
| `dto/field/GiteeDataProcessResult.java` | CMC 删除后无调用方 |
| `dto/field/RepoSyncResultContextDTO.java` | CMC 删除后无调用方 |
| `dto/field/RoleInfoDTO.java` | CMC 删除后无调用方（注意：与 permission/RoleInfoDTO 不同） |
| `dto/field/SyncFailedResults.java` | CMC 删除后无调用方 |
| `dto/field/SyncSuccessResults.java` | CMC 删除后无调用方 |

#### AOP / 常量（2 个）

| 文件 | Javadoc |
|------|---------|
| `common/aop/CmcLogHandler.java` | cmc管理日志切面处理类 |
| `common/constants/CommitterConstant.java` | 技术委员会管理常量类 |

#### 测试（7 个）

| 文件 |
|------|
| `test/.../CmcInfoServiceImplTest.java` |
| `test/.../CmcLogHandlerTest.java` |
| `test/.../BranchKeeperInfoServiceImplTest.java` |
| `test/.../ReviewerInfoServiceImplTest.java` |
| `test/.../FieldManagerServiceImplTest.java` |
| `test/.../SigInfoManagerServiceImplTest.java` |

### 移除 CMC 引用但保留（11 个文件）

#### Controller（1 个）

| 文件 | 操作 |
|------|------|
| `controller/SelectController.java` | 删除 8 个 CMC 端点（get-department、get-cmc-by-name、query-repo-by-cmc、query-committer-by-cmc、query-reviewer-by-cmc、query-branch-keeper-by-cmc、query-field-by-committer、get-sig-committer） |

#### Service 接口 + 实现（4 个）

| 文件 | 操作 |
|------|------|
| `service/SelectService.java` | 删除 8 个 CMC 方法声明（含 getDepartment、getSigCommitter） |
| `service/impl/SelectServiceImpl.java` | 删除 8 个 CMC 方法实现；移除 CmcInfoMapper 注入；移除 CmcInfoEntity/CmcWithDepartmentEntity 导入；删除 buildProjectData/buildProjectTree 私有方法；删除 getSigUser 死代码方法及相关未使用的 import（Gson、TypeToken、JsonObject） |
| `service/impl/ProductUserServiceImpl.java` | 移除 4 处 `PRODUCT_CMC` 角色守卫，替换为字面量 `"committer_product"` |
| `service/impl/ProjectUserServiceImpl.java` | 移除 4 处 `PROJECT_CMC` 角色守卫，替换为字面量 `"committer_project"` |

#### Mapper（2 个）

| 文件 | 操作 |
|------|------|
| `mapper/UserRoleMapper.java` + `UserRoleMapper.xml` | 移除 PermissionDTO 导入；移除 SQL 中 `product_cmc`/`project_cmc` 角色过滤 |
| `resources/mapper/GetLogsMapper.xml` | 移除 `log_cmc_info` 表名动态 SQL |

#### 常量 / 配置 / 日志（2 个）

| 文件 | 操作 |
|------|------|
| `common/constants/LogOperationAndModule.java` | 移除 CMC 管理常量段（22 个常量） |
| `common/log/LogDataCollectionName.java` | 移除 `CMC_INFO_LOG` 常量及 JSON 映射 |

#### 测试（3 个需改造）

| 文件 | 操作 |
|------|------|
| `test/.../SelectServiceImplTest.java` | 移除 CMC 相关测试用例（含 getDepartment 3 个、getSigCommitter 2 个、queryRepo/queryFieldCommitter/queryCommitterCmc/queryReviewerCmc/queryBranchKeeperCmc 等） |
| `test/.../ProductUserServiceImplTest.java` | 移除 PRODUCT_CMC 测试方法，替换 CommitterConstant 引用为字面量 |
| `test/.../ProjectUserServiceImplTest.java` | 移除 PROJECT_CMC 测试方法，替换 CommitterConstant 引用为字面量 |

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| 删除 CMC 类后，其他类编译失败 | 按依赖顺序删除：先删 Controller → Service → Mapper → Entity/DTO；每步编译验证 |
| 移除 `PRODUCT_CMC`/`PROJECT_CMC` 角色守卫后，用户管理功能异常 | 这些守卫仅阻止通过 API 添加/删除/修改 CMC 角色用户，删除后该角色不再被特殊保护，不影响正常功能 |
| 删除关联 Entity/DTO 后遗漏调用方 | 删除前用 grep 全量扫描确认无外部引用，仅保留死代码间的循环引用 |
| 遗漏 CMC 引用导致运行时错误 | 删除后用 grep 全量扫描 `src/main/java/` 和 `src/test/java/`，确保无遗漏 |

## 跨仓影响

无。本次变更仅涉及 openlibing-framework 后端仓，前端仓已提前下线相关页面。
