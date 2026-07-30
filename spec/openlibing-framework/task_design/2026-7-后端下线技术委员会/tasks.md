# 下线技术委员会模块 — 实现任务

## 进度: 10/10 complete

### Task 1: 删除 CMC Controller（5 个文件）

- [x] 删除 `controller/CommitterManagerController.java`
- [x] 删除 `controller/BranchKeeperManagerController.java`
- [x] 删除 `controller/ReviewerManagerController.java`
- [x] 删除 `controller/FieldManagerController.java`
- [x] 删除 `controller/SigInfoManagerController.java`

### Task 2: 删除 CMC Service 接口 + 实现（10 个文件）

- [x] 删除 `service/CmcInfoService.java`
- [x] 删除 `service/impl/CmcInfoServiceImpl.java`
- [x] 删除 `service/BranchKeeperInfoService.java`
- [x] 删除 `service/impl/BranchKeeperInfoServiceImpl.java`
- [x] 删除 `service/ReviewerInfoService.java`
- [x] 删除 `service/impl/ReviewerInfoServiceImpl.java`
- [x] 删除 `service/FieldManagerService.java`
- [x] 删除 `service/impl/FieldManagerServiceImpl.java`
- [x] 删除 `service/SigInfoManagerService.java`
- [x] 删除 `service/impl/SigInfoManagerServiceImpl.java`

### Task 3: 删除 CMC Mapper 接口 + XML（14 个文件）

- [x] 删除 `mapper/CmcInfoMapper.java` + `CmcInfoMapper.xml`
- [x] 删除 `mapper/CommitterInfoMapper.java` + `CommitterInfoMapper.xml`
- [x] 删除 `mapper/MaintainerInfoMapper.java` + `MaintainerInfoMapper.xml`
- [x] 删除 `mapper/ReviewerInfoMapper.java` + `ReviewerInfoMapper.xml`
- [x] 删除 `mapper/BranchKeeperInfoMapper.java` + `BranchKeeperInfoMapper.xml`
- [x] 删除 `mapper/FieldInfoMapper.java` + `FieldInfMapper.xml`
- [x] 删除 `mapper/YamlMapper.java` + `YamlMapper.xml`

### Task 4: 删除 CMC Entity / DTO / AOP / 常量（8 个文件）

- [x] 删除 `entity/cmc/CmcInfoEntity.java`
- [x] 删除 `entity/cmc/CmcWithDepartmentEntity.java`
- [x] 删除 `dto/cmc/CmcInfoDTO.java`
- [x] 删除 `dto/cmc/PermissionDTO.java`
- [x] 删除 `dto/git/code/SigRoleDTO.java`
- [x] 删除 `dto/git/code/SigRoleInfoDTO.java`
- [x] 删除 `common/aop/CmcLogHandler.java`
- [x] 删除 `common/constants/CommitterConstant.java`

### Task 5: 删除 CMC 测试（6 个文件）

- [x] 删除 `test/.../CmcInfoServiceImplTest.java`
- [x] 删除 `test/.../CmcLogHandlerTest.java`
- [x] 删除 `test/.../BranchKeeperInfoServiceImplTest.java`
- [x] 删除 `test/.../ReviewerInfoServiceImplTest.java`
- [x] 删除 `test/.../FieldManagerServiceImplTest.java`
- [x] 删除 `test/.../SigInfoManagerServiceImplTest.java`

### Task 6: 删除无调用方的关联 Entity/DTO（~65 个文件）

- [x] 删除 `entity/gitcodeyaml/` 整包（6 个文件）
- [x] 删除 `entity/committer/` 整包（3 个文件）
- [x] 删除 `entity/branchkeeper/` 整包（1 个文件）
- [x] 删除 `entity/reviewer/` 整包（1 个文件）
- [x] 删除 `entity/maintainer/` 整包（1 个文件）
- [x] 删除 `entity/field/` 整包（5 个文件）
- [x] 删除 `dto/committer/` 整包（6 个文件）
- [x] 删除 `dto/branchkeeper/` 整包（5 个文件）
- [x] 删除 `dto/reviewer/` 整包（5 个文件）
- [x] 删除 `dto/maintainer/` 整包（1 个文件）
- [x] 删除 `dto/field/` 整包（18 个文件）
- [x] 删除 `dto/git/code/` 整包（7 个文件）
- [x] 清理空目录

### Task 7: 移除 SelectController/Service 中的 CMC 端点（3 个文件）

- [x] `controller/SelectController.java`：删除 8 个 CMC 端点（get-department、get-cmc-by-name、query-repo-by-cmc、query-committer-by-cmc、query-reviewer-by-cmc、query-branch-keeper-by-cmc、query-field-by-committer、get-sig-committer）
- [x] `service/SelectService.java`：删除 8 个 CMC 方法声明（含 getDepartment、getSigCommitter）
- [x] `service/impl/SelectServiceImpl.java`：删除 8 个 CMC 方法实现；移除 CmcInfoMapper 注入；移除 CmcInfoEntity/CmcWithDepartmentEntity 导入；删除 buildDepartmentStructure/buildProjectData/buildProjectTree 私有方法

### Task 8: 移除非 CMC 类中的 CMC 引用（~8 个文件）

- [x] `service/impl/ProductUserServiceImpl.java`：移除 4 处 `PRODUCT_CMC` 角色守卫，替换为字面量 `"committer_product"`，移除 CommitterConstant 导入
- [x] `service/impl/ProjectUserServiceImpl.java`：移除 4 处 `PROJECT_CMC` 角色守卫，替换为字面量 `"committer_project"`，移除 CommitterConstant 导入
- [x] `mapper/UserRoleMapper.java`：移除 PermissionDTO 导入，修改 queryUserPermissionsByUserId 返回类型为 List<UserRoleInfoEntity>
- [x] `resources/mapper/UserRoleMapper.xml`：移除 SQL 中 `product_cmc`/`project_cmc` 角色过滤，修改 resultType 为 resultMap
- [x] `resources/mapper/GetLogsMapper.xml`：移除 `log_cmc_info` 表名动态 SQL
- [x] `common/constants/LogOperationAndModule.java`：移除 CMC 管理常量段（22 个常量）
- [x] `common/log/LogDataCollectionName.java`：移除 `CMC_INFO_LOG` 常量及 JSON 映射

### Task 9: 改造测试 + 全量编译验证

- [x] `test/.../SelectServiceImplTest.java`：移除 CMC 相关测试用例（16 个）和 mock（5 个 @Mock 字段）
- [x] `test/.../ProductUserServiceImplTest.java`：移除 PRODUCT_CMC 测试方法（4 个），替换 CommitterConstant 引用为字面量
- [x] `test/.../ProjectUserServiceImplTest.java`：移除 PROJECT_CMC 测试方法（3 个），替换 CommitterConstant 引用为字面量
- [x] 全量编译：`mvn clean compile` — BUILD SUCCESS
- [x] 全量测试：`mvn test` — Tests run: 2012, Failures: 0, Errors: 0, Skipped: 0
- [x] 最终验证：grep 扫描确认无 CMC 残留引用

### Task 10: 清理 SelectServiceImpl 死代码

- [x] 删除 `getSigUser` 方法（29 行，无调用方）
- [x] 删除 `Gson` 实例字段
- [x] 删除未使用的 import（Gson、TypeToken、JsonObject）
- [x] 编译验证通过
