## ADDED Requirements

### Requirement: 获取全量服务模块
系统应提供接口返回所有可用服务模块的名称，不做权限过滤，自动去重。

#### Scenario: 成功获取全量服务模块
- **WHEN** 客户端调用 GET /user/get-all-service-modules
- **THEN** 系统返回 DataResult，包含 Set<String>，元素为 menuName 字符串

#### Scenario: 返回一级菜单下的二级菜单
- **WHEN** 客户端调用 GET /user/get-all-service-modules
- **THEN** 系统包含所有 parentId 为一级菜单（parentId=0）且 menuType=0 的菜单名称

#### Scenario: 自动去重
- **WHEN** 存在相同 menuName 的菜单项
- **THEN** 系统返回 Set 自动去重，相同名称只保留一个

### Requirement: 无需用户参数
系统不应要求 userId 或其他用户相关参数。

#### Scenario: 接口无需 userId
- **WHEN** 客户端调用 GET /user/get-all-service-modules 且不带 userId 参数
- **THEN** 系统正常处理请求