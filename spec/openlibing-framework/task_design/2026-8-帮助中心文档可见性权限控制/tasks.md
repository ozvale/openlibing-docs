# 帮助中心文档可见性权限控制 — 实现任务

## 进度: 7/7 complete

- [x] Task 1: Liquibase changelog — wiki 表新增 visibility 列
  - 新建 `src/main/resources/db/changelog/v1.0.1/add_wiki_visibility.xml`
  - 使用 Liquibase `<addColumn>` 原生语法，`NOT NULL DEFAULT 0`
  - preConditions: `tableExists wiki` + `not columnExists visibility`，`onFail="MARK_RAN"`
  - 在 `db.changelog.xml` 末尾追加 include

- [x] Task 2: Entity 层 — WikiEntity + WikiChildEntity 新增 visibility 字段
  - `WikiEntity.java`: 新增 `private Integer visibility;`，注释: `/** 文档可见性: 0-对所有用户可见, 1-管理中心用户可见 */`
  - `WikiChildEntity.java`: 同上

- [x] Task 3: Mapper XML — WikiMapper.xml 更新
  - resultMap `wikiMap` 新增 `<result column="visibility" property="visibility"/>`
  - `insert`: 新增 `#{entity.visibility}`
  - `updateByEntity`: 新增 visibility 条件更新
  - `count` / `queryAll` / `queryPageByEntity` / `queryByParentId` / `queryChildWikiByPrentId` / `queryWikiDetailsById` / `queryRecycleFiles` / `queryRecycleFilesByIds`: 新增 `@Param("hasViewPermission")` 条件过滤 — 无权限时追加 `AND visibility = 0`

- [x] Task 4: Mapper 接口 — WikiMapper.java 方法签名更新
  - 上述 8 个方法均追加 `@Param("hasViewPermission") boolean hasViewPermission` 参数

- [x] Task 5: Service 层 — WikiServiceImpl.java 权限逻辑
  - 新增常量: `MANAGE_CENTER_ACCESS = "manage_config"`（复用现有管理中心权限标识）
  - 注入 `UserBasicService`，新增私有方法 `hasPermission(String userId, String accountId, String accountPlatform)`:
    - 调用 `userBasicService.getUserPermission(userId, accountId, accountPlatform)` 获取权限信息（该方法内部已实现 Redis 缓存读取和回写逻辑）
    - 解析返回结果中的 `permissions` 数组，判断是否包含 `manage_config`
    - 获取失败时返回 false（安全降级）
  - 读过滤（调用 Mapper 时传入 hasViewPermission）:
    - `queryAllWiki` / `queryWikiCondition` / `queryWikiDetailsById`: 传入 `hasPermission(userId, accountId, accountPlatform)`
  - 写控制:
    - `addWikiFile`: 如果 `wikiEntity.getVisibility() == 1`，校验 `manage_config` 权限
    - `updateWikiFile`: 如果目标文档是受控文档（`oldWiki.visibility == 1`）或请求中设置 `visibility=1`，校验 `manage_config` 权限
  - Redis 使用: 改用 `StringRedisTemplate` 替代 `RedisTemplate<String, String>`，与项目其他 ServiceImpl 保持一致

- [x] Task 6: Controller 层 — WikiController.java 调整
  - `queryAllWiki` / `queryWikiCondition` / `queryWikiDetailsById` / `addWikiFile` / `updateWikiFile`: 新增 `accountId` 和 `accountPlatform` 参数（网关自动注入）

- [x] Task 7: 测试 — WikiServiceImplTest.java 更新
  - 更新已有测试: 因 Mapper 方法签名变更，所有 mock 调用追加 `hasViewPermission` 参数
  - 更新已有测试: 因 Service 方法签名变更，所有调用追加 `accountId` 和 `accountPlatform` 参数
  - 新增测试用例:
    - `queryAllWiki_withPermission_returnsAllDocuments`: 有 manage_config 权限用户看到全部文档
    - `queryAllWiki_withoutPermission_excludesRestricted`: 无权限用户排除受控文档
    - `queryWikiDetailsById_restrictedDocument_noPermission`: 无权限查看受控文档详情
    - `hasPermission_callsGetUserPermission`: 调用 UserBasicService 获取权限
    - `hasPermission_serviceCallFails_returnsFalse`: 调用 UserBasicService 失败时安全降级
    - `addWikiFile_setVisibilityNoPermission_returnsFailure`: 无权限设置 visibility=1
    - `updateWikiFile_modifyRestrictedDocNoPermission_returnsFailure`: 无权限修改受控文档
