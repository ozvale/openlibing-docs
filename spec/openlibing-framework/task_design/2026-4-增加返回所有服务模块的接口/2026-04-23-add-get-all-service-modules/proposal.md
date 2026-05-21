## Why

分配服务单（assignFeedBackInfo）时，评审人（feedback_manager）需要指定服务模块名称（serviceModule）。现有接口 `getUserRootPermission` 仅返回用户有权限访问的模块，无法满足评审人需要从全量服务模块列表中进行选择的场景。

## What Changes

- 新增接口 `GET /user/get-all-service-modules`，返回全量服务模块名称，不做权限过滤
- 返回类型为 `Set<String>`，只包含 `menuName`，自动去重
- 无需用户参数，认证由公共层处理

## Capabilities

### New Capabilities
- `get-all-service-modules`: 查询全量服务模块名称（一级菜单下的二级菜单 menuType=0），返回去重后的 menuName 集合

### Modified Capabilities
- 无

## Impact

- **Controller**: `UserBasicController.java` - 新增接口
- **Service**: `UserBasicService.java` - 新增方法签名
- **ServiceImpl**: `UserBasicServiceImpl.java` - 实现查询逻辑
- **DTO**: 不使用 DTO，直接返回 `Set<String>`