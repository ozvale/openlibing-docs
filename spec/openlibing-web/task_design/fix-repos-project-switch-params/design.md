# Design: fix-repos-project-switch-params

## 方案概览

在 `Repos/index.vue` 的 `watch(projectInfo)` 中：

1. **早退分支**：`oldValue.projectId === newValue.projectId` 时直接 `return`，避免同 `projectId` 的 ref 变化触发重置。
2. **替换原 `needResetUrlQuery + onActivated`**：切项目时在 watcher 内同步清理 URL 参数，按当前路由分两种路径。
3. **强制重建 branches**：切项目时 `branchPaneKey.value++`，触发 `<component :is="...">` 重新挂载 `branches.vue`，其 `onMounted` 重新拉取分支数据。

## 实现逻辑

### 1. watch projectInfo 早退

```ts
watch(projectInfo, (newValue, oldValue) => {
  project.value = useApp.projectInfo;
  if (project.value.projectId) {
    // 同 projectId 但 ref 变化（Content.vue getProject 与 ProjectSelect.onMounted 各自 setProjectInfo）
    if (oldValue?.projectId && oldValue.projectId === project.value.projectId) {
      return;
    }
    // ...后续切项目逻辑
  }
});
```

### 2. 切项目时清理 URL（按当前路由分两种路径）

```ts
if (oldValue?.projectId) {
  if (route.name === "repos") {
    // 路径 A：当前在 Repos 路由，router.replace 清当前 URL
    // use-tabbar watch route.fullPath 会自动同步 store 里的 Repos tab
    const { repoId, branchName, pipelineRunId, metricType, ...restQuery } =
      route.query;
    if (repoId || branchName || pipelineRunId || metricType) {
      router.replace({ query: restQuery });
    }
  } else {
    // 路径 B：当前在别的 tab 切了项目
    // 直接清理 store 里 Repos tab 的旧 URL 参数
    // 避免点回 Repos tab 时 router.push(fullPath) 带回旧项目 metrics 参数
    const reposTab = tabbarStore.tabs.find((t) => t.name === "repos");
    if (reposTab?.query) {
      const { repoId, branchName, pipelineRunId, metricType, ...cleanQuery } =
        reposTab.query;
      if (repoId || branchName || pipelineRunId || metricType) {
        const { fullPath } = router.resolve({
          path: reposTab.path,
          query: cleanQuery,
        });
        // addTab 在 key 已存在时走"已存在更新分支"，用新 query/fullPath 覆盖老的
        tabbarStore.addTab({
          ...reposTab,
          query: cleanQuery,
          fullPath,
        });
      }
    }
  }
}
```

### 3. branchPaneKey++ 强制重建 branches.vue

```ts
branchPaneKey.value += 1;
```

绑定到 `<component :is="currentBranchComponent" :key="branchPaneKey">`，`key` 变化触发 Vue 重新挂载组件，`branches.vue` 的 `onMounted` 重新拉取分支列表。

## 类与组件

| 文件                                               | 角色            | 变更                                                                   |
| -------------------------------------------------- | --------------- | ---------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/Repos/index.vue`    | Repos 主容器    | 新增 `useTabbarStore`、watch 早退分支、URL 清理逻辑、`branchPaneKey++` |
| `@vben/stores` `useTabbarStore`                    | 多 tab 状态管理 | 仅消费，无改动                                                         |
| `apps/web-openlibing/src/views/Repos/Branches.vue` | 分支管理子组件  | 无改动（依赖 `onMounted` 重新执行）                                    |

## 数据模型

| 数据                                               | 来源                              | 写入策略                                                                      |
| -------------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------- |
| `route.query`                                      | `useRoute()`                      | 路径 A：`router.replace({ query: restQuery })`                                |
| `tabbarStore.tabs.find(name === 'repos').query`    | `useTabbarStore()`                | 路径 B：`tabbarStore.addTab({...reposTab, query: cleanQuery, fullPath})` 覆盖 |
| `tabbarStore.tabs.find(name === 'repos').fullPath` | `router.resolve({ path, query })` | 路径 B：同上覆盖                                                              |
| `branchPaneKey`                                    | `Repos/index.vue` 本地 ref        | 切项目时 `++` 触发重建                                                        |

## 性能

- watch 早退避免不必要 reset，开销可忽略。
- URL 清理仅在切项目时触发（`router.replace` / `tabbarStore.addTab` 均为 O(1)）。
- `branches.vue` 重建仅在切项目时触发，单次开销可控（一次 onMounted 重新拉分支列表）。

## API

无新增/变更接口。完全在前端路由 + tab 状态层修复。

## 安全

无新增风险。`router.replace` 不写历史栈，`tabbarStore.addTab` 覆盖策略由 `@vben/stores` 提供，不存在越权写入。

## 影响范围

- 仅影响 `openlibing-web` 仓 `Repos` 模块在「项目切换」场景下的 URL 与 tab 状态处理。
- 不影响其他模块、其他路由。
- 不影响后端接口、数据模型、构建链路。

## 回滚策略

如出现问题，可 revert `46017219a28f2cb9d9f1b4003d6fd6a3c504686a` 单 commit，恢复 `needResetUrlQuery + onActivated` 原方案（已知缺陷：非 keep-alive 切换不触发 `onActivated`，但能保证基本可用）。

Generated-by: GLM-5.2
