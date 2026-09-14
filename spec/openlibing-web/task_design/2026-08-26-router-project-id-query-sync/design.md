# 2026-08-26 路由 query 项目参数同步 - 技术设计

## 1. 总体方案

采用「路由守卫（导航时机）+ store watch（非导航时机）」双机制闭环，统一只写 `projectId`：

```text
导航目标 query 状态判定（setProjectQueryGuard）
├─ store 无 projectId（初始化中/登出）      → 放行不处理（分享链接参数原样到达 getProject）
├─ projectId 为当前项目且无 projectName     → 放行（目标状态，避免无谓重定向）
├─ 缺 projectId（路由跳转/刷新落地）        → 补写当前项目 projectId（next(to) 重定向）
├─ 旧项目的 projectId（历史页签）           → 删旧写新，改写为当前项目
└─ 携带 projectName（历史分享链接）         → 删除 projectName，统一替换为 projectId
```

非导航时机（刷新落地页后 projectInfo 异步就绪，不发生路由跳转，守卫无执行时机）由 store watch 兜底：

```text
watch(projectInfo.projectId) 触发
├─ store 无 projectId            → 不动 URL（防登出误清）
├─ 已是目标状态                   → no-op
└─ 缺参/旧参/带 projectName       → router.replace（query-only，只写 projectId）
```

## 2. 关键设计决策

| #   | 决策                                             | 理由                                                                                                                           |
| --- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| 1   | 守卫改写用 `next(to)` 重定向                     | 与既有 `setPlatformFlagGuard` 同机制；第二圈守卫命中目标状态即放行，无死循环                                                   |
| 2   | store 为空时守卫不介入                           | 保证 `?projectId=X` / `?projectName=X` 分享链接在初始导航（store 未加载）时原样到达 `Content.vue` 的 `getProject` 完成项目还原 |
| 3   | `Content.getProject` 统一写 `app.projectInfo`    | 使 watch 立即触发时拿到的 projectId 与当前路由一致，避免初始化后又被 watch 改写一次 URL                                        |
| 4   | projectName 全部移除、只写 projectId（用户要求） | 收敛参数风格；分享链接兼容性靠「还原逻辑保留 + 还原后 URL 转换」实现                                                           |
| 5   | watch 监听源用单一 `projectId` 而非数组          | 减少无谓触发（此前 projectName 变化也会触发）                                                                                  |

## 3. 不重载视图的论证

- 主布局页组件 `:key="getTabKey(route)"` 取 `title || name || path`，**不含 query** → query-only 变更时 key 不变，KeepAlive 复用实例，不重挂载
- `addTab` 按 key（`equalTab`）合并更新 → 不产生重复页签；页签持久化签名 key-based → 不触发服务端保存
- 守卫补参/改写发生在导航确认前，`router-view` 只为最终 URL 渲染一次
- 全仓无 `onBeforeRouteUpdate`；监听 `route.query` 的视图均针对特定 key，不受新增参数影响
- wujie 子应用 `:key="wujieAppName"` 为 path/name 维度，query 变化不重载子应用

## 4. 影响范围

| 维度     | 影响                                                                                                    |
| -------- | ------------------------------------------------------------------------------------------------------- |
| 文件     | `guard.ts`（守卫重写）、`app.ts`（watch 简化）、`Content.vue`（首个 commit 已含，projectInfo 统一写入） |
| 接口     | 无变更                                                                                                  |
| 数据模型 | 无变更                                                                                                  |
| 页签     | 旧页签激活时一次性自愈迁移为当前项目地址                                                                |
| 子应用   | 启动 URL 携带 projectId（`buildSubAppUrl` 拼主应用 query），不重载                                      |
