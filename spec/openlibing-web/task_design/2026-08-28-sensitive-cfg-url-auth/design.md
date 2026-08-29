# 2026-08-28 敏感词集操作页 URL 权限校验加固 - 技术方案

## 1. 问题根因

`CustomRuleConfig.vue` 通过 `watch(projectInfo)` 监听 projectId 驱动页面初始化：projectId 首次有值时直接调用 `init()` 完成初始化。该链路存在三个问题：

1. **无操作级校验**：列表页入口靠按钮权限隐藏控制，但操作页路由 URL 可直接访问，初始化流程不校验当前用户是否具备 `sensitive_rule_set_add/update/query` 操作权限。
2. **权限数据时序依赖**：权限数据来自全局 store（`appStore.operationPermissions`），URL 直接进入时全局权限接口可能尚未返回，页面在权限数据缺失时放行。
3. **项目切换缓存失效**：切换项目后 store 中仍是旧项目的权限数据，无法反映新项目下的真实权限。

## 2. 修复方案

在操作页初始化链路中插入操作级权限校验闸门，权限不通过时提示并跳回敏感词集列表页（`/apps/sensitiveDict`）。

### 校验链路

```text
watch(projectInfo)
  ├─ projectId 首次有值（初始化）
  │    └─ checkOptionAuth()
  │         ├─ config（查看）→ 不校验，直接 init()
  │         └─ 其他操作 → doCheckOptionAuth(auth)
  │              ├─ 读 store.operationPermissions[auth]（命中直接判定）
  │              ├─ 未命中 → fetchOperationPermission(auth) 主动拉后端
  │              ├─ parseOperationPermission(op) 解析
  │              │    ├─ 通过 → authReady = true; init()
  │              │    └─ 不通过 → denyAccess()
  │              └─ 异常 → denyAccess()（fail-closed）
  └─ projectId 变动（切换项目）
       └─ recheckOptionAuth()
            └─ 强制 fetchOperationPermission 重新校验（store 可能是旧项目数据）
                 ├─ 通过 → 停留在当前页
                 └─ 不通过/异常 → denyAccess()
```

### 关键设计点

| 设计点           | 说明                                                                                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 权限码映射       | `OPTION_AUTH_MAP`：add/copy → `sensitive_rule_set_add`，edit → `sensitive_rule_set_update`，query → `sensitive_rule_set_query`；config（查看）不校验          |
| fail-closed      | store 无数据时主动拉后端；拉取异常按无权限处理，不静默放行                                                                                                    |
| 双份数据源       | 优先读全局 store（正常入口低延迟），未就绪时回源后端（URL 直入场景兜底）                                                                                      |
| 项目切换强制回源 | store 中可能是旧项目数据，切换项目后必须从后端重新拉取                                                                                                        |
| 防竞态           | `recheckOptionAuth` 使用自增序号 `_authCheckSeq`，快速连续切换项目时只采纳最新一次校验结果                                                                    |
| 延迟跳转         | `denyAccess` 中跳转 `setTimeout(..., 0)` 延迟到下一宏任务，避免与 layout 渲染时序冲突导致跳转后列表页内容区空白（此前验证过立即导航会出现空白，需刷新才恢复） |
| 权限解析         | `parseOperationPermission` 跳过 `level === 'repo'` 的角色组（敏感词集为项目级操作），任一角色 `hasPermission` 或整体 `op.hasPermission === true` 即通过       |
| 返回结构兼容     | `fetchOperationPermission` 兼容 `res.data.operations` 与 `res.data.data.operations` 两种结构，与 `Content.vue` 既有解析逻辑一致                               |
| 重入保护         | `doCheckOptionAuth` 使用 `_authChecking` 标志防止并发重复校验                                                                                                 |

### 具体变更

| 文件                   | 变更内容                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CustomRuleConfig.vue` | 新增 `OPTION_AUTH_MAP` 操作权限码映射常量                                                                                                        |
| `CustomRuleConfig.vue` | data 新增 `authReady` 状态字段                                                                                                                   |
| `CustomRuleConfig.vue` | watcher 初始化分支前置 `checkOptionAuth()`，项目切换分支接入 `recheckOptionAuth()`                                                               |
| `CustomRuleConfig.vue` | 新增 `checkOptionAuth` / `doCheckOptionAuth` / `fetchOperationPermission` / `recheckOptionAuth` / `parseOperationPermission` / `denyAccess` 方法 |
| `CustomRuleConfig.vue` | 从 `@/api/api.ts` 增加导入 `getOperationPermissions`                                                                                             |

## 3. 影响范围

- 仅 `CustomRuleConfig.vue` 单文件（+108/-3），无后端接口、路由、数据模型变更
- config（查看）操作行为不变
- 无权限用户从 URL 直入操作页或切换到无权限项目时被拦截并跳回 `/apps/sensitiveDict`

## 4. 回退方案

如需回退，revert 业务仓 commit `ecb41b98` 即可恢复原有初始化逻辑。
