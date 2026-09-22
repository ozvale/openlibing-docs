## 1. Service 层

- [x] 1.1 在 `UserBasicService.java` 中新增 `getAllServiceModules()` 方法签名：`DataResult<Set<String>>`
- [x] 1.2 在 `UserBasicServiceImpl.java` 中实现 `getAllServiceModules()`：
  - 查询一级菜单：`menuInfoMapper.queryByParentId(0)`
  - 查询二级菜单：`menuInfoMapper.queryByParentIds(一级IDs)`，过滤 menuType=0
  - 提取 menuName，使用 `Collectors.toSet()` 自动去重
  - 返回 `DataResult.successData(result)`
- [x] 1.3 添加注释说明查询逻辑

## 2. Controller 层

- [x] 2.1 在 `UserBasicController.java` 中新增 `GET /user/get-all-service-modules` 接口：
  - 无 userId 参数
  - 调用 `userBasicService.getAllServiceModules()`
  - 返回 `DataResult<Set<String>>`

## 3. 测试

- [x] 3.1 在 Service 测试类中为 `getAllServiceModules()` 新增单元测试：
  - 验证返回类型为 `Set<String>`
  - 验证去重效果（相同 menuName 只保留一个）