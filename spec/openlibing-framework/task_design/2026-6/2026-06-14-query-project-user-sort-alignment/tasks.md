## 1. DTO 与实体扩展

- [x] 1.1 在 `UserDTO.java` 增加可选字段 `sortColumn`、`sortOrder`（String，无校验注解）
- [x] 1.2 在 `QueryProjectUserEntity.java` 增加 `sortDbColumn`、`sortDirection`（String，Service 层赋值）

## 2. Service 层排序映射

- [x] 2.1 在 `ProjectUserServiceImpl` 新增 `mapSortColumn`、`mapSortOrder`、`applySortParams` 私有方法（白名单：`createTime` → `create_time`；`ascending` → `ASC`，其余 → `DESC`）
- [x] 2.2 在 `queryProjectUser(String userId, UserDTO)` 构建 `QueryProjectUserEntity` 后调用 `applySortParams`，确保三条查询路径均携带 sort 参数

## 3. MyBatis Mapper 动态排序

- [x] 3.1 修改 `ProjectUserRoleInfoMapper.xml` 中 `queryProjectUserByLimit`：`ORDER BY ${info.sortDbColumn} ${info.sortDirection}, id DESC, user_identifier DESC, source_table DESC`
- [x] 3.2 修改 `queryProjectUserByUserIdLimit`：`ORDER BY ${info.sortDbColumn} ${info.sortDirection}, id DESC`
- [x] 3.3 修改 `queryProjectUserByAccountLimit`：`ORDER BY ${info.sortDbColumn} ${info.sortDirection}, id DESC`

## 4. 单元测试

- [x] 4.1 在 `ProjectUserServiceImplTest` 增加测试：`sortColumn=createTime, sortOrder=ascending` 时 mapper 收到的 entity 为 `create_time`/`ASC`
- [x] 4.2 增加测试：空 sort 参数默认 `create_time`/`DESC`
- [x] 4.3 增加测试：非法 `sortColumn`（如 `userName`）回退默认 `create_time`/`DESC`
- [x] 4.4 增加测试：`sortOrder=null` 时默认 `DESC`
- [x] 4.5 运行 `ProjectUserServiceImplTest` 及相关模块测试，确认通过

## 5. 验收与文档

- [x] 5.1 对照 `design.md` 前后端契约对齐表，在 PR 描述中列出 5 个场景的 expected ORDER BY
- [x] 5.2 确认响应 `createTime` 格式未变，前端 `projectUserManage.vue` 无需改动
