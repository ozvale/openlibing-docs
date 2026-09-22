# 工具管理模块功能增强技术设计方案

## 技术方案概述

本次功能增强采用前端 Vue 3 + Element Plus 实现，遵循现有工具管理模块架构，通过新增组件、扩展 API 接口、增强现有页面功能的方式实现。

## 模块设计

### 1. 工具与标签绑定

**设计思路**：
- 在工具管理配置文件（config.ts）中扩展标签配置
- 在工具表格组件（toolTable.vue）中增加标签列和标签管理弹窗
- 新增 API 接口：
  - `POST /api/tool/tag/bind` - 绑定标签
  - `GET /api/tool/tag/list` - 获取工具标签列表

**数据结构**：
```typescript
interface ToolTag {
  id: string;
  name: string;
  description?: string;
}

interface ToolTagBinding {
  toolId: string;
  tags: ToolTag[];
}
```

### 2. 工具与项目空间绑定

**设计思路**：
- 在工具详情页（details.vue）增加项目空间绑定功能入口
- 新增绑定操作弹窗，支持选择项目空间
- 新增 API 接口：
  - `POST /api/tool/project-space/bind` - 绑定项目空间
  - `DELETE /api/tool/project-space/unbind` - 解除绑定
  - `GET /api/tool/project-space/list` - 获取绑定关系列表

**数据结构**：
```typescript
interface ProjectSpaceBinding {
  toolId: string;
  projectSpaceId: string;
  projectSpaceName: string;
  bindTime: Date;
}
```

### 3. 一键举报机制

**设计思路**：
- 在工具详情页（details.vue）增加举报按钮
- 在待办中心新增三个举报相关页面：
  - `ToolReportApplication.vue` - 举报申请
  - `ToolReportReview.vue` - 举报审核
  - `ToolReportReviewHistory.vue` - 举报历史

**举报流程**：
1. 用户点击工具详情页举报按钮
2. 填写举报原因，提交举报申请
3. 举报进入待办中心审核队列
4. 审核员在待办中心审核举报
5. 审核结果记录到举报历史

**数据结构**：
```typescript
interface ToolReport {
  id: string;
  toolId: string;
  toolName: string;
  reporterId: string;
  reporterName: string;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewerId?: string;
  reviewerName?: string;
  reviewComment?: string;
  createTime: Date;
  reviewTime?: Date;
}
```

### 4. 安全提示内容

**设计思路**：
- 工具上传（toolItem.vue）：在文件选择前弹出安全提示确认框
  - 使用 ElMessageBox.confirm 显示 HTML 格式安全提示
  - 确认后继续文件选择流程

- 工具审核（myToDo.vue）：在审核弹窗顶部增加安全提示区域
  - 使用样式化 div 显示提示内容
  - 提示内容固定显示，不影响审核流程

- 工具下载（details.vue）：在下载确认弹窗中增加安全提示
  - 使用 v-html 渲染 HTML 格式提示内容
  - 显示上传者信息和安全注意事项

**提示内容结构**：
- 工具上传：禁止内容列表 + 违规后果说明
- 工具审核：审核职责列表 + 谨慎审核提示
- 工具下载：上传者信息 + 安全注意事项 + 免责声明

### 5. 审核日志查看

**设计思路**：
- 新增组件 `reviewHistory.vue` 展示审核日志
- 在工具管理页面增加审核日志入口
- 调用现有审核日志 API 获取数据

**数据结构**：
```typescript
interface ReviewLog {
  id: string;
  toolId: string;
  reviewerId: string;
  reviewerName: string;
  action: 'approve' | 'reject' | 'comment';
  comment?: string;
  time: Date;
}
```

## API 变化

新增以下 API 接口（在 api.ts 和 url.ts 中添加）：

```typescript
// 标签绑定
export const bindToolTag = (toolId: string, tags: string[]) => request.post(url.bindToolTag, { toolId, tags });
export const getToolTags = (toolId: string) => request.get(url.getToolTags, { params: { toolId } });

// 项目空间绑定
export const bindProjectSpace = (toolId: string, projectSpaceId: string) => request.post(url.bindProjectSpace, { toolId, projectSpaceId });
export const unbindProjectSpace = (toolId: string) => request.delete(url.unbindProjectSpace, { params: { toolId } });
export const getProjectSpaceBindings = (toolId: string) => request.get(url.getProjectSpaceBindings, { params: { toolId } });

// 举报
export const createReport = (data: ReportData) => request.post(url.createReport, data);
export const getReports = (status: string) => request.get(url.getReports, { params: { status } });
export const reviewReport = (reportId: string, data: ReviewData) => request.post(url.reviewReport(reportId), data);
export const getReportHistory = (toolId?: string) => request.get(url.getReportHistory, { params: { toolId } });

// 审核日志
export const getReviewLogs = (toolId: string) => request.get(url.getReviewLogs, { params: { toolId } });
```

## 前端组件变化

### 新增文件

- `apps/web-openlibing/src/views/ToDoCenter/ToolReportApplication.vue`
- `apps/web-openlibing/src/views/ToDoCenter/ToolReportReview.vue`
- `apps/web-openlibing/src/views/ToDoCenter/ToolReportReviewHistory.vue`
- `apps/web-openlibing/src/views/ToolManagement/ToolManage/components/reviewHistory.vue`
- `apps/web-openlibing/src/assets/images/common/report.png` (举报图标)
- `apps/web-openlibing/src/assets/images/common/discontinued.png` (下架图标)

### 修改文件

- `apps/web-openlibing/src/views/ToolManagement/MyTool/components/toolItem.vue` (增加上传安全提示)
- `apps/web-openlibing/src/views/ToolManagement/MyTool/myToDo.vue` (增加审核安全提示)
- `apps/web-openlibing/src/views/ToolManagement/ToolMarket/details.vue` (增加下载安全提示、举报按钮、项目空间绑定)
- `apps/web-openlibing/src/views/ToolManagement/ToolManage/index.vue` (增加标签管理、审核日志入口)
- `apps/web-openlibing/src/views/ToolManagement/components/toolTable.vue` (增加标签列)
- `apps/web-openlibing/src/views/ToolManagement/config.ts` (扩展标签配置)
- `apps/web-openlibing/src/views/ToDoCenter/ToDoCenter.vue` (增加举报工具菜单)
- `apps/web-openlibing/src/api/api.ts` (新增 API 函数)
- `apps/web-openlibing/src/api/url.ts` (新增 API URL)

## 数据模型变化

无数据模型 Schema 变化（使用现有工具管理数据模型扩展字段）。

## 安全影响

- 增加安全提示增强用户安全意识
- 举报机制提升平台治理能力
- 无新增安全漏洞风险

## 部署影响

- 前端资源需更新部署
- 后端 API 需同步部署新增接口
- 无数据库迁移需求

## 测试策略

### 单元测试

- 测试新增 API 函数调用
- 测试组件渲染和交互

### 集成测试

- 测试标签绑定完整流程
- 测试项目空间绑定完整流程
- 测试举报申请→审核→历史查看完整流程

### UI 测试

- 测试安全提示弹窗显示和交互
- 测试各新增页面布局和样式

## 技术债务

- 无新增技术债务
- 建议后续优化举报审核效率（如批量审核）