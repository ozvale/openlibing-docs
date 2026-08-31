# 对接接口管理服务，获取全量接口 — 技术设计

## 方案概述

通过 Feign 客户端对接外部接口管理服务，定时拉取全量接口数据，经数据比对后写入本地数据库。同时补充菜单 URL 与接口标识的同步逻辑、白名单 CRUD、误报接口管理等功能，实现接口权限的自动化管理。

## 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 远程调用方式 | Feign 客户端 | 与现有微服务架构一致，集成简单 |
| 同步方式 | 定时任务 + 异步线程 | 避免主线程阻塞，支持增量同步 |
| 数据比对 | 内存中 HashMap 匹配 | 全量数据量可控，内存匹配效率高 |
| 事务隔离 | 移除外层 @Transactional | 避免 REPEATABLE_READ 快照导致异步线程数据不可见 |
| 数据库索引 | 联合索引 (service_name, http_method, api_url, flag) | 覆盖查询条件，最左前缀原则 |
| 安全修复 | 防御性拷贝 + 不可变返回 | 修复 SpotBugs EI_EXPOSE_REP/EI_EXPOSE_REP2 |

## 涉及文件（38 个）

### 新增文件（21 个）

| 文件 | 说明 |
|------|------|
| `InterfaceManagementClient.java` | 接口管理服务 Feign 客户端，定义远程调用接口 |
| `InterfaceManagementFeignConfiguration.java` | Feign 配置类，配置请求拦截器、超时等 |
| `ServiceInterfaceInfoController.java` | 服务接口信息控制器，提供 CRUD + 分页 + 下线查询 |
| `InterfaceBo.java` | 接口管理服务返回的接口数据 BO |
| `InterfacePageInfo.java` | 分页信息 DTO |
| `InterfaceQueryListRequest.java` | 接口查询请求 DTO |
| `InterfaceQueryListResponse.java` | 接口查询响应 DTO |
| `TagBo.java` | 接口标签 BO |
| `MenuUrlQueryDTO.java` | 菜单 URL 查询 DTO（角色 + 分页） |
| `ServiceInterfaceInfoQueryDTO.java` | 服务接口信息查询 DTO |
| `ServiceInterfaceInfoUpdateDTO.java` | 服务接口信息更新 DTO |
| `WhitelistInterfaceInfoDTO.java` | 白名单接口信息 DTO |
| `ServiceInterfaceInfoEntity.java` | 服务接口信息实体 |
| `WhitelistInterfaceInfoEntity.java` | 白名单接口信息实体 |
| `ServiceInterfaceInfoMapper.java` | 服务接口信息 Mapper |
| `WhitelistInterfaceInfoMapper.java` | 白名单接口信息 Mapper |
| `ServiceInterfaceInfoService.java` | 服务接口信息 Service 接口 |
| `ServiceInterfaceInfoServiceImpl.java` | 服务接口信息 Service 实现（核心同步逻辑） |
| `MenuUrlInfoVO.java` | 菜单 URL 信息 VO |
| `SyncServiceInterfaceInfoJob.java` | 定时同步任务 |
| `api-scan.yml` | API 兼容性扫描工作流 |

### 修改文件（17 个）

| 文件 | 操作 | 说明 |
|------|------|------|
| `MenuController.java` | 修改 | 新增菜单 URL 同步接口 |
| `MenuEntity.java` | 修改 | 补充字段映射 |
| `MenuUrlInfoEntity.java` | 修改 | 补充字段映射 |
| `MenuUrlInfoMapper.java` | 修改 | 新增 flag 更新、条件查询 |
| `MenuService.java` | 修改 | 新增 queryMenuUrlByRole 接口 |
| `MenuServiceImpl.java` | 修改 | 实现 URL 同步和角色查询逻辑 |
| `ServiceInterfaceLogHandler.java` | 修改 | 补充接口管理相关日志切面 |
| `LogOperationAndModule.java` | 修改 | 补充日志操作和模块常量 |
| `db.changelog.xml` | 修改 | 引入新的 changelog 文件 |
| `menu_url_info.xml` | 修改 | 新增索引变更 |
| `service_interface_info.xml` | 修改 | 新增表结构和索引 |
| `whitelist_interface_info.xml` | 修改 | 新增表结构和索引 |
| `MenuInfoMapper.xml` | 修改 | 补充查询映射 |
| `MenuUrlInfoMapper.xml` | 修改 | 新增 SQL 查询和更新语句 |
| `ServiceInterfaceInfoMapper.xml` | 新增 | 接口信息查询 SQL |
| `WhitelistInterfaceInfoMapper.xml` | 新增 | 白名单查询 SQL |
| `MenuServiceImplTest.java` | 新增 | 单元测试 |

## 核心逻辑设计

### 1. 接口数据同步流程

```
定时任务触发
    ↓
Feign 调用接口管理服务获取全量接口数据
    ↓
异步线程执行 urlDataComparison
    ↓
数据比对（内存 HashMap 匹配）
    ├── 匹配到已有记录 → 更新 flag=1
    ├── 未匹配到         → 更新 flag=0
    └── 新增接口         → 插入新记录
    ↓
同步 menu_url_info 的 flag 标识
    ↓
保存结果
```

### 2. 事务处理

- 移除外层的 `@Transactional` 注解，避免 REPEATABLE_READ 隔离级别下异步线程无法看到主线程提交的数据
- 异步线程内使用 `TransactionTemplate` 手动管理事务，确保单次操作的事务性

### 3. 数据库索引

| 表 | 索引名 | 列 | 说明 |
|------|--------|------|------|
| `service_interface_info` | `idx_service_name_url_flag` | `service_name, http_method, api_url, url_flag` | 覆盖查询条件 |
| `whitelist_interface_info` | `idx_service_name_url_flag` | `service_name, http_method, api_url, url_flag` | 覆盖查询条件 |
| `menu_url_info` | `idx_menu_id` | `menu_id` | 关联查询加速 |
| `menu_url_info` | `idx_flag` | `flag` | flag 过滤加速 |

### 4. 安全编码修复

- **EI_EXPOSE_REP**：getter 方法返回 `Collections.unmodifiableList()` 包装
- **EI_EXPOSE_REP2**：setter 和构造方法使用 `new ArrayList<>(input)` 防御性拷贝
- **BC_VACUOUS_INSTANCEOF**：移除无意义的 instanceof 检查

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|----------|
| 接口管理服务不可用导致同步失败 | 定时任务重试机制，失败日志记录 |
| 全量同步数据量大影响性能 | 异步线程执行，数据库索引优化 |
| 数据一致性问题 | 原子性更新操作，事务隔离确保正确性 |
| 安全编码回归 | SpotBugs 检查纳入 pre-commit |

## 跨仓影响

无。所有变更均在 openlibing-framework 仓内，不涉及其他仓的接口变更。