# 技术方案

## 方案概述

在 openEuler 发布评审详情组件 `PublishingProcessComponent.vue` 与流程配置 `taskConfig.js` 中扩展流程节点，并新增自动执行能力；相关接口在 `api/PlatformRelease` 中补充。整体沿用既有 "节点配置 + 状态字段 + Jenkins 任务" 模式，不引入新的状态管理。

## 接口设计

| 用途            | 路径                                          | 说明                                    |
| --------------- | --------------------------------------------- | --------------------------------------- |
| 生成 updateinfo | `POST /publish/jenkins/generateUpdateinfo`    | 生成CVE公告节点调用，成功即视为节点完成 |
| 启动自动执行    | `POST /publish/jenkins/startUpdateAutomation` | 返回自动执行状态                        |
| 查询自动执行    | `POST /publish/jenkins/queryUpdateAutomation` | 轮询刷新各节点状态                      |
| 同步仓库        | `POST /publish/jenkins/syncBuildResultToRepo` | `reviewId` 通过请求体传递               |

## 流程节点变更

`taskConfig.js`：

- 新增常量 `SYNC_REPOSITORY = 'syncBuildResult'`、`GENERATE_NOTICE = 'generateSafeNoticeResult1'`
- 横向 `taskSteps` 首位新增"同步仓库"节点（`fnName: startSyncRepository`）
- 横向 `taskSteps` 在"导入测试repo"之后新增"生成CVE公告1"节点（`fnName: startGenerateNoticeTask`）
- 竖向 `taskStepsVertival` 中原"生成CVE公告"改名为"生成CVE公告2"

## 自动执行设计

```javascript
// 是否处于自动执行中
autoExecuting() {
  return this.autoExecStatus === EXECUTING;
}
```

- 初始化：`initAutoExecuteStatus()` 读取 `jenkinsJobExecStatusInfo[UPDATE_AUTOMATION]`，若为执行中则 `startAutoExecuteInterval()`
- 手动轮询拦截：`startReleaseInterval` / `isInitInterval` 在 `autoExecuting` 时直接 return，保证节点状态只来自自动执行轮询
- 启动：`startAutoExecute` 先清空全部手动 `releaseTimer`，调用启动接口，写入返回状态并立即 `queryUpdateAutomation()`
- 轮询：`autoExecuteTimer` 间隔 1 分钟调用查询接口，状态非执行中时清理定时器
- 中英文案：`autoExecute`、`executingStatus`、`executeSuccessStatus`、`executeFailedStatus`

## 时间展示

```javascript
formatAutomationTime(field) {
  const statusInfo = this.dataList?.jenkinsJobExecStatusInfo || {};
  const startTime = statusInfo[field];
  if (!startTime) {
    return '';
  }
  const time = dayjs(startTime);
  return time.isValid() ? time.format('YYYY-MM-DD HH:mm:ss') : '';
}
```

- `autoExecuteStartTime` → `updateAutomationStartTime`
- `autoExecuteStepTime` → `updateAutomationStepTime`

## 更新组件下拉

`release.vue` 的 `dropdownButtons` 新增"生成updateinfo"，`handleAnnouncement` 中 `generateUpdateinfo` 类型校验 `selectedData.length !== 1` 时提示"请选择一条数据！"。

## 改动文件

| 文件                                                                                                                      | 改动说明                                               |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `apps/web-openlibing/src/api/PlatformRelease/url.ts`                                                                      | 新增 4 个接口常量                                      |
| `apps/web-openlibing/src/api/PlatformRelease/api.ts`                                                                      | 新增 4 个请求方法                                      |
| `apps/web-openlibing/src/i18n/zh/platform.js`、`en/platform.js`                                                           | 新增节点文案、自动执行状态与时间文案                   |
| `apps/web-openlibing/src/views/Publish/platformRelease/updateComponents/releaseComponents/taskConfig.js`                  | 新增同步仓库/生成CVE公告节点，原公告节点改名           |
| `apps/web-openlibing/src/views/Publish/platformRelease/updateComponents/releaseComponents/PublishingProcessComponent.vue` | 节点执行方法、自动执行按钮与轮询、时间展示、定时器互斥 |
| `apps/web-openlibing/src/views/Publish/platformRelease/updateComponents/release.vue`                                      | 下拉新增"生成updateinfo"及单条数据校验                 |
| `apps/web-openlibing/src/views/Publish/platformRelease/updateComponents/common.less`                                      | 自动执行栏样式                                         |

## 影响范围

- **影响页面**：发布管理 → openEuler 发布评审详情（更新组件）
- **依赖后端字段**：`jenkinsJobExecStatusInfo` 中的 `updateAutomationStatus`、`updateAutomationStartTime`、`updateAutomationStepTime`，以及各节点状态字段
- **不影响**：其他发布类型、其他流程节点执行逻辑、权限控制

## 风险分析

1. **后端字段依赖**：自动执行状态与时间字段需后端同步返回，字段缺失时按钮不展示状态、时间区域为空，不影响手动执行。
2. **轮询频率提升**：间隔由 3 分钟调整为 1 分钟，接口 QPS 会相应增加，需后端确认可承受。
3. **定时器泄漏**：自动执行与手动轮询共用组件生命周期，已在启动自动执行时清空手动定时器、`beforeUnmount` 统一清理，仍需回归验证切换流程时不残留轮询。
4. **单条数据限制**：`generateUpdateinfo` 仅支持单条数据，多选时前端拦截，后端需同样校验。
