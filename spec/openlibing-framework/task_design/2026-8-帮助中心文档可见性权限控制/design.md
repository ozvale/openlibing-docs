# 帮助中心文档可见性权限控制 — 技术设计

## 方案概述

在 `wiki` 表新增 `visibility` 字段区分公开文档和受控文档，后端查询接口根据用户是否拥有 `manage_config` 权限过滤受控文档，写入接口校验用户是否有权限操作受控文档。

## 架构决策

### 1. 字段设计：visibility INT NOT NULL DEFAULT 0

- `0` = 对所有用户可见（公开文档）
- `1` = 管理中心用户可见（受控文档）

选择 INT 而非 BOOLEAN，便于未来扩展更多可见性级别。`NOT NULL DEFAULT 0` 保证存量数据自动公开且不会出现 null 值，SQL 过滤条件简化为 `AND visibility = 0`，无需 `OR visibility IS NULL` 兜底。

Liquibase 使用 `<addColumn>` 原生语法（非 `<sql>` 原生 SQL），保证跨数据库兼容性。

### 2. 权限标识：复用 manage_config

复用现有的 `manage_config` 权限标识，不新增自定义权限码。

**原因**：

- `manage_config` 是管理中心入口权限，只有 super_admin 角色拥有
- 管理中心相关文档的目标受众就是拥有管理中心权限的用户
- 无需在菜单管理界面额外配置新权限码

**权限判断逻辑**：调用 `UserBasicService.getUserPermission()` 获取用户 permissions 数组，检查是否包含 `manage_config`。

### 3. 权限获取方式

Wiki Service 中需要获取当前用户的 permissions 信息。评估了三种方案：

- **方案 A（选用）**：Service 内部调用 `UserBasicService.getUserPermission()` 获取权限信息（该方法内部已实现 Redis 缓存读取和回写逻辑）
- **方案 B**：Controller 层增加 permissions 参数传递
- **方案 C**：调用 `commonService.verifyPermissions(userId, productId, projectId, repoId, url)`

**选择方案 A 的原因**：

1. `commonService.verifyPermissions()` 是 URL 级别的 API 鉴权，需要传入 productId/projectId/repoId 上下文，而 Wiki 是平台级功能，不绑定任何项目/组织/仓库，不适配该模式
2. `commonService.verifyPermissions()` 每次调用都做多次 DB 查询（URL→Menu→Role→User），性能开销大；Wiki 查询接口调用频繁，不适合
3. `UserBasicService.getUserPermission()` 内部已实现 Redis 缓存读取（24h TTL）和缓存未命中时的回写逻辑，无需在 WikiServiceImpl 中重复实现缓存读取
4. 复用已有逻辑，避免重复造轮子

### 4. 读过滤策略

在 SQL 层面过滤，而非 Java 层过滤，避免查出大量数据后再裁剪：

- 有 `manage_config` 权限：查询不过滤 visibility（`hasViewPermission = true`）
- 无 `manage_config` 权限：查询条件追加 `AND visibility = 0`（`hasViewPermission = false`）

受影响的查询方法：`queryAll`、`count`、`queryPageByEntity`、`queryByParentId`、`queryChildWikiByPrentId`、`queryWikiDetailsById`、`queryRecycleFiles`、`queryRecycleFilesByIds`。

### 5. 写控制策略

由于普通文档修改与受控文档修改共用同一个接口（`addWikiFile` / `updateWikiFile`），无法通过网关 RBAC 区分，因此在 Service 层增加权限校验：

- **addWikiFile**：如果请求中 `visibility=1`，校验用户是否拥有 `manage_config` 权限
- **updateWikiFile**：如果目标文档是受控文档（`oldWiki.visibility == 1`）或请求中设置 `visibility=1`，校验用户是否拥有 `manage_config` 权限
- 无权限时返回错误提示，不静默忽略

### 6. Redis 使用规范

使用 `StringRedisTemplate` 替代 `RedisTemplate<String, String>`，与项目其他 ServiceImpl 保持一致。两者序列化器均为 `StringRedisSerializer`，对线上 Redis 数据无影响。

## 涉及文件

| 文件                                                             | 操作 | 说明                                                                                                                                        |
| ---------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/resources/db/changelog/v1.0.1/add_wiki_visibility.xml` | 新增 | Liquibase changelog，`wiki` 表加 `visibility` 列（NOT NULL DEFAULT 0）                                                                      |
| `src/main/resources/db/changelog/db.changelog.xml`               | 修改 | 追加 include                                                                                                                                |
| `WikiEntity.java`                                                | 修改 | 新增 `visibility` 字段（Integer），注释说明 0=对所有用户可见，1=管理中心用户可见                                                            |
| `WikiChildEntity.java`                                           | 修改 | 新增 `visibility` 字段（Integer），同上注释                                                                                                 |
| `WikiMapper.xml`                                                 | 修改 | resultMap 加映射；insert/update 加字段；8 个查询加 `hasViewPermission` 条件过滤                                                             |
| `WikiMapper.java`                                                | 修改 | 8 个方法签名加 `@Param("hasViewPermission") boolean hasViewPermission` 参数                                                                 |
| `WikiService.java`                                               | 修改 | `queryAllWiki`、`queryWikiCondition`、`queryWikiDetailsById`、`addWikiFile`、`updateWikiFile` 新增 accountId/accountPlatform 参数           |
| `WikiServiceImpl.java`                                           | 修改 | 新增 `hasPermission()` 方法（调用 UserBasicService）；查询方法传入权限标记；写入方法校验 manage_config 权限；Redis 改用 StringRedisTemplate |
| `WikiController.java`                                            | 修改 | 5 个接口新增 accountId/accountPlatform 参数（网关自动注入）                                                                                 |
| `WikiServiceImplTest.java`                                       | 修改 | 更新已有 mock 签名 + 新增 7 个权限相关测试用例                                                                                              |

## 风险 & 缓解

| 风险                                             | 缓解                                                |
| ------------------------------------------------ | --------------------------------------------------- |
| Redis 权限缓存过期（24h TTL）导致权限判断不准    | 可接受，权限变更后最多 24h 生效，与现有权限体系一致 |
| 前端未同步改造，用户无法通过 UI 设置 visibility  | 过渡期通过 SQL 手动标记；前端后续跟进               |
| addWikiFile 未传 visibility 时 NOT NULL 约束报错 | Service 层默认设置 `visibility=0`                   |

## 跨仓影响

- 前端仓 `openlibing-web` 需后续配合改造（不在本次范围）
- 网关已自动注入 `accountId` 和 `accountPlatform` 参数，无需网关改动

## 关联

- 业务 Issue: [openlibing/openlibing-framework#82](https://gitcode.com/openlibing/openlibing-framework/issues/82)
