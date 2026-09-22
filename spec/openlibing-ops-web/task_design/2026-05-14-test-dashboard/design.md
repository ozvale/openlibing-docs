# 测试看板设计文档

## 技术架构

### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.5+ | 前端框架 |
| TypeScript | 5.9+ | 类型安全 |
| Element Plus | 2.13+ | UI组件库 |
| ECharts | 6+ | 图表可视化 |
| Tailwind CSS | 4+ | 样式框架 |
| Pinia | 3+ | 状态管理 |

### 目录结构

```
src/
├── views/
│   └── dashboard/
│       └── test-dashboard/           # 测试看板模块
│           ├── index.vue             # 主入口页面
│           ├── config.ts             # 配置文件
│           ├── components/           # 组件目录
│           │   ├── kpi-cards.vue     # KPI卡片组件
│           │   ├── org-project-table.vue    # 组织-项目表格
│           │   ├── org-project-cards.vue    # 组织-项目卡片
│           │   ├── pipeline-table.vue       # 流水线表格
│           │   ├── task-table.vue           # 测试任务表格
│           │   ├── case-table.vue           # 测试用例表格
│           │   ├── trend-chart.vue          # 趋势图表
│           │   └── breadcrumb-nav.vue       # 面包屑导航
│           ├── hooks/                # 组合式函数
│           │   ├── use-pagination.ts # 分页逻辑
│           │   └── use-view-mode.ts  # 视图模式切换
│           └── types/                # 类型定义
│               └── index.ts
├── api/
│   └── dashboard/
│       └── test-dashboard.ts         # API接口
└── stores/
    └── test-dashboard-store.ts       # 状态管理
```

## 页面设计

### 1. 组织-项目汇总页面

#### 布局结构

```
┌────────────────────────────────────────────────────────────────┐
│  时间筛选: [今日] [近7天] [近30天] [近90天] [自定义日期范围]    │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 任务vCPU │  │ 任务NPU  │  │ 用例CPU  │  │ 用例NPU  │       │
│  │  31,006  │  │  11,100  │  │  18,500  │  │   6,800  │       │
│  │   核时   │  │   卡时   │  │   核时   │  │   卡时   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
├────────────────────────────────────────────────────────────────┤
│  组织资源消耗对比趋势（近30天）                                 │
│  ┌─────────────────────────┐  ┌─────────────────────────┐     │
│  │     vCPU消耗趋势图       │  │     NPU消耗趋势图       │     │
│  └─────────────────────────┘  └─────────────────────────┘     │
├────────────────────────────────────────────────────────────────┤
│  视图切换: [表格] [卡片]                                        │
├────────────────────────────────────────────────────────────────┤
│  组织-项目资源明细表格                                          │
│  ┌────────┬──────────┬─────────┬─────────┬─────────┬────────┐ │
│  │  组织  │   项目   │ 任务vCPU│ 任务NPU │ 用例CPU │ 用例NPU│ │
│  ├────────┼──────────┼─────────┼─────────┼─────────┼────────┤ │
│  │ Ascend │  MindIE  │  5,230  │  1,200  │  3,100  │   720  │ │
│  │ Ascend │MindSpore │  4,840  │  1,180  │  2,900  │   680  │ │
│  │  ...   │   ...    │   ...   │   ...   │   ...   │   ...  │ │
│  └────────┴──────────┴─────────┴─────────┴─────────┴────────┘ │
│  分页: < 1 2 3 ... >                                           │
└────────────────────────────────────────────────────────────────┘
```

#### 卡片视图

```
┌────────────────────────────────────────────────────────────────┐
│  组织: Ascend                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │ MindIE               │  │ MindSpore            │            │
│  │ ──────────────────── │  │ ──────────────────── │            │
│  │ 任务vCPU: 5,230 核时 │  │ 任务vCPU: 4,840 核时 │            │
│  │ 任务NPU:  1,200 卡时 │  │ 任务NPU:  1,180 卡时 │            │
│  │ 用例CPU:  3,100 核时 │  │ 用例CPU:  2,900 核时 │            │
│  │ 用例NPU:    720 卡时 │  │ 用例NPU:    680 卡时 │            │
│  │ ──────────────────── │  │ ──────────────────── │            │
│  │ [vCPU进度条]  85%    │  │ [vCPU进度条]  78%    │            │
│  │ [NPU进度条]   72%    │  │ [NPU进度条]   65%    │            │
│  └──────────────────────┘  └──────────────────────┘            │
└────────────────────────────────────────────────────────────────┘
```

### 2. 流水线层级页面

#### 布局结构

```
┌────────────────────────────────────────────────────────────────┐
│  面包屑: 全部 > Ascend > MindIE                                 │
├────────────────────────────────────────────────────────────────┤
│  Tab切换: [PR流水线] [Nightly流水线] [测试用例]                 │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 任务vCPU │  │ 任务NPU  │  │ 用例CPU  │  │ 用例NPU  │       │
│  │  5,230   │  │  1,200   │  │  3,100   │  │   720    │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
├────────────────────────────────────────────────────────────────┤
│  流水线列表                                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 流水线名称          │状态│执行时间    │时长  │vCPU │NPU │...││
│  ├────────────────────────────────────────────────────────────┤│
│  │ PR #1247 - 优化调度 │成功│05-06 14:32│45min │ 320 │ 80 │...││
│  │ PR #1245 - 修复内存 │失败│05-06 10:15│38min │ 280 │ 60 │...││
│  └────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

### 3. 测试任务层级页面

```
┌────────────────────────────────────────────────────────────────┐
│  面包屑: 全部 > Ascend > MindIE > PR #1247                      │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────┐│
│  │ 任务vCPU │  │ 任务NPU  │  │ 用例CPU  │  │ 用例NPU  │  │通过率│
│  │   320    │  │    80    │  │   210    │  │    60    │  │ 100% │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────┘│
├────────────────────────────────────────────────────────────────┤
│  任务列表                                                       │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 任务名称    │状态│开始时间│时长  │vCPU │NPU │用例CPU│用例NPU││
│  ├────────────────────────────────────────────────────────────┤│
│  │ unit-test   │成功│ 14:32 │12min │ 120 │ 30 │  120  │  30  ││
│  │ integration │成功│ 14:45 │33min │ 200 │ 50 │  200  │  50  ││
│  └────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

### 4. 测试用例层级页面

```
┌────────────────────────────────────────────────────────────────┐
│  面包屑: 全部 > Ascend > MindIE > PR #1247 > unit-test          │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────┐│
│  │ 任务vCPU │  │ 任务NPU  │  │ 用例CPU  │  │ 用例NPU  │  │通过率│
│  │   120    │  │    30    │  │   120    │  │    30    │  │ 100% │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────┘│
├────────────────────────────────────────────────────────────────┤
│  用例列表                                                       │
│  ┌────────────────────────────────────────────────────────────┐│
│  │用例编号│仓库     │分支        │代码路径        │级别│结果│...││
│  ├────────────────────────────────────────────────────────────┤│
│  │TC-001  │k8s-runtime│feat/opt│pkg/scheduler/...│P0  │通过│...││
│  │TC-002  │k8s-runtime│feat/opt│pkg/scheduler/...│P1  │通过│...││
│  └────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

## 下钻展示方式设计

### 页面跳转模式

- 点击行后跳转到新路由
- URL 结构：`/dashboard/test-dashboard/:orgId/:projectId/:pipelineId/:taskId`
- 优点：支持浏览器前进/后退、可分享链接
- 适用场景：需要完整查看详情的场景

> **注意**：其他下钻方式（抽屉、弹窗、内嵌展开）暂不实现，后续根据需求迭代。

## 组件设计

### KPI 卡片组件 (kpi-cards.vue)

```typescript
interface KPICardProps {
  title: string;
  value: number;
  unit: string;
  icon: string;
  color: 'blue' | 'purple' | 'amber' | 'green';
  progress?: {
    current: number;
    target: number;
  };
}
```

### 表格组件通用属性

```typescript
interface TableProps {
  data: any[];
  columns: TableColumn[];
  loading: boolean;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  onRowClick: (row: any) => void;
}
```

### 面包屑导航组件

```typescript
interface BreadcrumbItem {
  label: string;
  path?: string;
  onClick?: () => void;
}
```

## API 设计

### 接口列表

```typescript
// 获取组织-项目汇总数据
GET /api/test-dashboard/overview
Query: { startDate, endDate, page, pageSize }
Response: {
  totalVCPU: number;
  totalNPU: number;
  totalCaseCPU: number;
  totalCaseNPU: number;
  orgs: Organization[];
}

// 获取项目流水线数据
GET /api/test-dashboard/projects/:projectId/pipelines
Query: { type: 'PR' | 'Nightly', startDate, endDate, page, pageSize }
Response: { pipelines: Pipeline[]; total: number; }

// 获取流水线任务数据
GET /api/test-dashboard/pipelines/:pipelineId/tasks
Query: { page, pageSize }
Response: { tasks: Task[]; total: number; }

// 获取任务用例数据
GET /api/test-dashboard/tasks/:taskId/cases
Query: { page, pageSize }
Response: { cases: TestCase[]; total: number; }

// 获取趋势数据
GET /api/test-dashboard/trend
Query: { entityType: 'org' | 'project', entityIds: string[], metric: 'vcpu' | 'npu', days: number }
Response: { series: TrendSeries[]; }
```

### 数据类型定义

```typescript
interface Organization {
  id: string;
  name: string;
  vcpu: number;
  npu: number;
  vcpuCase: number;
  npuCase: number;
  projects: Project[];
}

interface Project {
  id: string;
  name: string;
  orgId: string;
  vcpu: number;
  npu: number;
  vcpuCase: number;
  npuCase: number;
}

interface Pipeline {
  id: string;
  name: string;
  type: 'PR' | 'Nightly';
  status: 'success' | 'failed' | 'running' | 'pending';
  time: string;
  duration: string;
  vcpu: number;
  npu: number;
  vcpuCase: number;
  npuCase: number;
  taskCount: number;
}

interface Task {
  id: string;
  name: string;
  status: 'success' | 'failed' | 'running' | 'pending';
  time: string;
  duration: string;
  vcpu: number;
  npu: number;
  vcpuCase: number;
  npuCase: number;
  caseCount: number;
}

interface TestCase {
  id: string;
  caseNumber: string;
  repo: string;
  branch: string;
  path: string;
  level: 'P0' | 'P1' | 'P2' | 'P3';
  result: 'passed' | 'failed' | 'skipped';
  vcpu: number;
  npu: number;
  time?: string;
}
```

## 状态管理

```typescript
// stores/test-dashboard-store.ts
interface TestDashboardState {
  // 当前导航状态
  currentLevel: 'overview' | 'org' | 'project' | 'pipeline' | 'task';
  selectedOrgId: string | null;
  selectedProjectId: string | null;
  selectedPipelineId: string | null;
  selectedTaskId: string | null;
  pipelineTab: 'PR' | 'Nightly';
  
  // 视图设置
  viewMode: 'table' | 'card';
  drillMode: 'navigate' | 'drawer' | 'dialog' | 'expand';
  
  // 时间筛选
  dateRange: [string, string];
  timeRange: 'today' | '7d' | '30d' | '90d' | 'custom';
  
  // 分页状态
  pagination: {
    overview: PaginationState;
    pipelines: PaginationState;
    tasks: PaginationState;
    cases: PaginationState;
  };
}
```

## 样式规范

### 颜色系统

```css
:root {
  --primary: #2563EB;      /* vCPU 相关 */
  --primary-light: #DBEAFE;
  --purple: #8B5CF6;       /* NPU 相关 */
  --purple-light: #EDE9FE;
  --warning: #F59E0B;      /* 用例CPU */
  --warning-light: #FEF3C7;
  --success: #10B981;      /* 用例NPU */
  --success-light: #D1FAE5;
  --error: #EF4444;        /* 失败状态 */
  --error-light: #FEE2E2;
}
```

### 状态徽章样式

| 状态 | 颜色 | 样式类 |
|------|------|--------|
| 成功/通过 | 绿色 | badge-success |
| 失败 | 红色 | badge-error |
| 运行中 | 蓝色 | badge-info |
| 待执行 | 灰色 | badge-muted |

### 级别徽章样式

| 级别 | 颜色 | 说明 |
|------|------|------|
| P0 | 红色 | 最高优先级 |
| P1 | 橙色 | 高优先级 |
| P2 | 蓝色 | 中优先级 |
| P3 | 灰色 | 低优先级 |

## 交互设计

### 动画效果

1. **页面切换**：淡入淡出 (fade, 200ms)
2. **卡片悬停**：上浮 + 阴影增强
3. **表格行悬停**：背景高亮
4. **进度条动画**：从左到右填充
5. **数字计数动画**：从 0 递增到目标值

### 响应式设计

| 断点 | KPI 卡片 | 表格列 |
|------|----------|--------|
| > 1100px | 4 列 | 全部显示 |
| 768px - 1100px | 2 列 | 隐藏次要列 |
| < 768px | 1 列 | 仅显示核心列 |

## 性能优化

1. **虚拟滚动**：大数据量表格使用虚拟滚动
2. **懒加载**：图表组件按需加载
3. **缓存策略**：已加载数据缓存到 Pinia store
4. **防抖节流**：搜索、筛选操作防抖处理
5. **分页加载**：默认每页 10 条，支持调整
