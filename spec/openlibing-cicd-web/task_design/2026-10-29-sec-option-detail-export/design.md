# Design: 安全编译选项扫描结果支持导出（前端）

## 1. 方案设计

复用平台既有「提交导出任务 + wujie bus 通知主站导出中心」的异步导出约定（与 `TestResult.vue`、`JobLog.vue` 的导出链路一致），前端不直接处理文件流：

```
PackageDetailView（导出按钮）
  → POST /build-artifact/sec-option/detail/export（projectId + recordId）
  → extractExportIdFromResponse 提取任务 ID
  → notifyHostExportTask 经 wujie bus $emit('host-export-task')
  → 主站导出中心浮窗展示进度 → 后端生成 Excel 上传 OBS → 自动下载
```

选择该方案的原因：文件生成、进度查询、下载均由后端与主站导出中心完成，子应用只负责任务提交与事件上报，改动面最小且与全站导出体验一致。

## 2. 实现逻辑设计

`PackageDetailView.vue` 新增 `handleExport` 流程：

1. **防抖**：`exportLoading` 为 true 时直接返回，防重复点击
2. **参数获取**：`projectId` 取自 `useAppStore().projectInfo`（宿主经 wujie props / `projectInfoChange` 事件注入），`recordId` 取自父组件传入的 `props.row.id`
3. **参数校验**：`projectId` 或 `recordId` 缺失时 `ElMessage.warning('缺少项目或扫描记录信息，暂时无法导出')` 并返回，不静默（检视意见修复项）
4. **任务创建**：调用 `buildArtifactSecOptionDetailExport`，`disabledLoading: true` 避免全局 loading 遮罩，错误由请求拦截器统一提示
5. **结果分支**（`code === 200`）：
   - 无任务 ID → `ElMessage.error('导出任务创建失败')`
   - 有任务 ID → `notifyHostExportTask` 上报 `{ id, projectId, source: 'sec-option-detail', taskName: '安全编译选项扫描详情_{产物名称}', type: 'SEC_OPTION_DETAIL' }`；返回 `true` 提示「已提交导出任务」，返回 `false`（非 wujie 宿主或无 bus，事件不会送达）降级提示「后台任务已创建，但未检测到导出中心，请稍后手动查看」，避免静默失败（检视意见修复项）
6. **状态恢复**：`finally` 中恢复 `exportLoading`

## 3. 类设计

无新增类/组件。改动集中在既有视图组件 `PackageDetailView.vue` 的 `<script setup>` 内（新增 `exportLoading` ref 与 `handleExport` 函数），复用既有工具函数：

| 复用单元                            | 职责                                     |
| ----------------------------------- | ---------------------------------------- |
| `notifyHostExportTask(): boolean`   | 组装 payload 并经 wujie bus 上报导出任务 |
| `extractExportIdFromResponse(data)` | 从导出接口响应中提取任务 ID              |
| `useAppStore()`                     | 提供宿主注入的 `projectInfo.projectId`   |

## 4. 数据模型设计

无前端数据模型变更。接口入参/出参见第 6 节；Excel 文件内容（Sheet1 扫描概览 + Sheet2 文件扫描结果）由后端生成，详见 openlibing/openlibing-cicd#495。

## 5. 性能设计

- 单次点击仅发起一个轻量 POST 请求（创建任务），无轮询、无大 payload 传输
- `disabledLoading: true` 避免全局遮罩阻塞页面其他交互
- `exportLoading` 按钮级 loading 防重复提交，避免产生重复导出任务

## 6. API 接口设计

### POST /build-artifact/sec-option/detail/export

后端契约（详见 openlibing/openlibing-cicd#495），前端仅消费：

| 项目 | 内容                                                    |
| ---- | ------------------------------------------------------- |
| 入参 | `projectId: string`、`recordId: string`                 |
| 出参 | `code: 200`，`data` 中含导出任务 ID                     |
| 鉴权 | gateway 纵向鉴权 + 项目成员横向校验 + recordId 归属校验 |

### wujie bus 事件 `host-export-task`

| 字段        | 值                                  |
| ----------- | ----------------------------------- |
| `id`        | 导出任务 ID（必填）                 |
| `projectId` | 项目 ID                             |
| `source`    | `sec-option-detail`                 |
| `taskName`  | `安全编译选项扫描详情_{产物名称}`   |
| `type`      | `SEC_OPTION_DETAIL`（后端新增枚举） |

## 7. 安全设计

- 无新增前端鉴权逻辑：导出数据范围与详情页可见范围严格一致（后端负责项目成员横向校验与 recordId 归属校验，防跨项目越权）
- `recordId` 来源于父组件内部状态而非用户可篡改的 URL 参数，`projectId` 来源于宿主注入的全局状态，均经 `String()` 规范化后传参
- 不涉及本地存储、动态 HTML 渲染或外部输入拼接，无 XSS/注入面
