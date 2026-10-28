# 帮助中心文档可见性权限控制

## 需求背景

当前帮助中心（Wiki 模块）的所有文档对所有已登录用户可见，包括管理中心后台相关的文档（如权限配置、角色管理、运营看板等内部操作指南）。这导致普通用户可以看到不应展示的管理类文档。

需要对文档进行可见性控制，确保管理中心相关文档仅对有管理中心权限（`manage_config`）的用户展示和编辑。

## 功能描述

### 做什么

1. `wiki` 表新增 `visibility` 字段（INT, NOT NULL, DEFAULT 0）
   - `0` = 对所有用户可见（公开文档）
   - `1` = 管理中心用户可见（受控文档）
2. **读过滤**：查询接口根据用户是否拥有 `manage_config` 权限排除 `visibility=1` 的文档
   - `queryAllWiki`：树形列表过滤
   - `queryWikiCondition`：分页查询过滤
   - `queryWikiDetailsById`：详情接口过滤
   - `queryChildWikiByPrentId`：子文档查询过滤
3. **写控制**：写入接口校验用户是否拥有 `manage_config` 权限
   - `addWikiFile`：新增文档时，若设置 `visibility=1` 则校验权限
   - `updateWikiFile`：修改受控文档（`visibility=1`）或设置 `visibility=1` 时校验权限
4. **权限标识**：复用现有 `manage_config` 权限，通过 `UserBasicService.getUserPermission()` 获取用户权限数组判断
5. 存量数据默认 `visibility=0`（全部公开），上线后由管理员手动标记受控文档

### 不做什么

- 不改前端（前端由前端团队单独改造）
- 不在代码中新增菜单数据（菜单由系统管理界面配置）
- 不做多级可见性（只区分公开/受控两级）
- 不做自动标记存量数据

## 验收标准

- [ ] `wiki` 表新增 `visibility` 字段，存量数据默认为 0
- [ ] 无权限用户调用 `queryAllWiki` 时，返回的树形列表中不包含 `visibility=1` 的文档
- [ ] 无权限用户调用 `queryWikiCondition` 时，分页结果中不包含 `visibility=1` 的文档
- [ ] 无权限用户调用 `queryWikiDetailsById` 查询受控文档时，返回无权限提示
- [ ] 无权限用户调用子文档查询时，不包含 `visibility=1` 的子文档
- [ ] 无权限用户无法通过 `addWikiFile` 设置 `visibility=1`
- [ ] 无权限用户无法通过 `updateWikiFile` 修改受控文档或设置 `visibility=1`
- [ ] 无权限用户无法通过 `browsingHistory` 获取受控文档元数据
- [ ] 无权限用户无法通过 `deleteWikiFile` 删除受控文档
- [ ] 无权限用户无法通过 `restoreWikiFile` 恢复受控文档
- [ ] 无权限用户无法通过 `deleteWikiFileComplete` 彻底删除受控文档
- [ ] 无权限用户无法通过 `updateParent` 移动受控文档
- [ ] 有权限用户可正常查看和编辑受控文档
- [ ] 权限复用 `manage_config`，不新增自定义权限码
- [ ] 存量文档不受影响（默认公开）

## 影响范围

| 模块       | 文件                                       | 说明                                                    |
| ---------- | ------------------------------------------ | ------------------------------------------------------- |
| DB         | Liquibase changelog                        | 新增 `visibility` 列（NOT NULL DEFAULT 0）              |
| Entity     | `WikiEntity.java`, `WikiChildEntity.java`  | 新增 `visibility` 字段                                  |
| Mapper XML | `WikiMapper.xml`                           | resultMap、insert、update、8 个查询加过滤条件           |
| Mapper     | `WikiMapper.java`                          | 8 个方法签名加 `hasViewPermission` 参数                 |
| Service    | `WikiService.java`, `WikiServiceImpl.java` | 查询加过滤、写入加权限校验、新增 `hasPermission()` 方法 |
| Controller | `WikiController.java`                      | 5 个接口新增 accountId/accountPlatform 参数             |
| Test       | `WikiServiceImplTest.java`                 | 更新已有 mock + 新增 7 个权限测试用例                   |

## 关联

- 业务 Issue: [openlibing/openlibing-framework#82](https://gitcode.com/openlibing/openlibing-framework/issues/82)
