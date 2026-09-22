# openLiBing 运营看板 Demo 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建一个纯前端静态页面的运营看板 Demo，展示 openLiBing 特性在各开源社区的覆盖情况。

**Architecture:** 采用经典表格矩阵布局，行展示 9 个开源社区，列展示 11 个特性，单元格使用状态灯（绿/黄/灰）展示对接状态。点击状态灯弹出详情卡片，展示用户指标（UV/PV）和特性专属业务指标。

**Tech Stack:** HTML5 + CSS3 (Grid/Flexbox) + JavaScript (原生)

**设计文档位置:** `D:\Git\openLiBing\openlibing-docs\temp_designs\2026-06-05-ops-dashboard-design.md`

---

## Task 1: 创建项目目录结构

**Files:**
- Create: `ops-dashboard-demo/`
- Create: `ops-dashboard-demo/styles/`
- Create: `ops-dashboard-demo/scripts/`
- Create: `ops-dashboard-demo/assets/`

**Step 1: 创建主目录**

```bash
mkdir ops-dashboard-demo
```

Expected: 创建 `ops-dashboard-demo` 目录成功

**Step 2: 创建 styles 子目录**

```bash
mkdir ops-dashboard-demo/styles
```

Expected: 创建 `ops-dashboard-demo/styles` 目录成功

**Step 3: 创建 scripts 子目录**

```bash
mkdir ops-dashboard-demo/scripts
```

Expected: 创建 `ops-dashboard-demo/scripts` 目录成功

**Step 4: 创建 assets 子目录**

```bash
mkdir ops-dashboard-demo/assets
```

Expected: 创建 `ops-dashboard-demo/assets` 目录成功

**Step 5: 验证目录结构**

```bash
ls ops-dashboard-demo
```

Expected: 输出包含 `styles`、`scripts`、`assets` 三个子目录

**Step 6: Commit**

```bash
git add ops-dashboard-demo
git commit -m "chore: create ops dashboard demo project structure"
```

Expected: 提交成功

---

## Task 2: 编写 HTML 主页面骨架

**Files:**
- Create: `ops-dashboard-demo/index.html`

**Step 1: 创建 HTML 文件并添加文档结构**

创建 `ops-dashboard-demo/index.html`，写入以下内容：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>openLiBing 特性覆盖看板</title>
    <link rel="stylesheet" href="styles/main.css">
</head>
<body>
    <!-- Header: 标题栏 -->
    <header class="header">
        <h1 class="title">openLiBing 特性覆盖看板</h1>
    </header>

    <!-- Main: 状态矩阵表格 -->
    <main class="main">
        <div class="table-container">
            <table class="status-table">
                <!-- 表头 -->
                <thead>
                    <tr>
                        <th class="col-community">社区</th>
                        <th class="col-feature">门禁检查</th>
                        <th class="col-feature">接口兼容性</th>
                        <th class="col-feature">流水线</th>
                        <th class="col-feature">测试框架</th>
                        <th class="col-feature">SBOM</th>
                        <th class="col-feature">漏洞视图</th>
                        <th class="col-feature">发布评审</th>
                        <th class="col-feature">工具市场</th>
                        <th class="col-feature">AI agent</th>
                        <th class="col-feature">Skill市场</th>
                        <th class="col-feature">数字化运营看板</th>
                    </tr>
                </thead>
                <!-- 表体 -->
                <tbody id="table-body">
                    <!-- 由 JavaScript 动态生成 -->
                </tbody>
            </table>
        </div>
    </main>

    <!-- Footer: 图例说明 -->
    <footer class="footer">
        <div class="legend">
            <span class="legend-item">
                <span class="status-light-demo active"></span>
                已使用
            </span>
            <span class="legend-item">
                <span class="status-light-demo in-progress"></span>
                对接中
            </span>
            <span class="legend-item">
                <span class="status-light-demo inactive"></span>
                未使用
            </span>
        </div>
    </footer>

    <!-- 详情卡片模态框 -->
    <div id="detail-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>对接详情</h3>
                <button class="modal-close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <!-- 基础信息 -->
                <div class="basic-info"></div>
                <!-- 用户指标 -->
                <div class="user-metrics"></div>
                <!-- 业务指标 -->
                <div class="business-metrics"></div>
                <!-- 备注 -->
                <div class="note-info"></div>
            </div>
            <div class="modal-footer">
                <button class="btn-close">关闭</button>
                <button class="btn-edit">编辑</button>
            </div>
        </div>
    </div>

    <script src="scripts/data.js"></script>
    <script src="scripts/main.js"></script>
</body>
</html>
```

Expected: 文件创建成功，包含完整的 HTML 骨架结构

**Step 2: 在浏览器中打开验证结构**

```bash
# Windows: 使用默认浏览器打开
start ops-dashboard-demo/index.html
```

Expected: 浏览器打开页面，显示标题"openLiBing 特性覆盖看板"（但样式未加载）

**Step 3: Commit**

```bash
git add ops-dashboard-demo/index.html
git commit -m "feat: add HTML structure for ops dashboard"
```

Expected: 提交成功

---

## Task 3: 编写 CSS 基础样式

**Files:**
- Create: `ops-dashboard-demo/styles/main.css`

**Step 1: 创建 CSS 文件并添加页面布局样式**

创建 `ops-dashboard-demo/styles/main.css`，写入以下内容：

```css
/* ========== 全局样式 ========== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: #f0f9ff; /* 浅蓝灰背景 */
    color: #1e40af; /* 深蓝主色 */
}

/* ========== Header 样式 ========== */
.header {
    height: 80px;
    background-color: #ffffff;
    border-bottom: 1px solid #3b82f6;
    display: flex;
    align-items: center;
    padding: 0 40px;
}

.title {
    font-size: 24px;
    font-weight: bold;
    color: #1e40af;
}

/* ========== Main 样式 ========== */
.main {
    padding: 40px;
}

.table-container {
    background-color: #ffffff;
    border: 2px solid #3b82f6;
    border-radius: 8px;
    overflow-x: auto;
}

/* ========== Footer 样式 ========== */
.footer {
    height: 60px;
    background-color: #ffffff;
    border-top: 1px solid #3b82f6;
    display: flex;
    justify-content: center;
    align-items: center;
}

.legend {
    display: flex;
    gap: 30px;
    font-size: 14px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
}
```

Expected: 文件创建成功，包含全局、Header、Main、Footer 基础样式

**Step 2: 在浏览器中刷新验证布局**

刷新浏览器页面 `ops-dashboard-demo/index.html`

Expected: 页面布局清晰，Header、Main、Footer 区域分隔明显，背景色为浅蓝灰

**Step 3: Commit**

```bash
git add ops-dashboard-demo/styles/main.css
git commit -m "feat: add basic layout CSS styles"
```

Expected: 提交成功

---

## Task 4: 编写 CSS 表格样式

**Files:**
- Modify: `ops-dashboard-demo/styles/main.css:32-56`（追加表格样式）

**Step 1: 添加表格样式**

在 `ops-dashboard-demo/styles/main.css` 文件末尾追加以下内容：

```css
/* ========== 表格样式 ========== */
.status-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}

.status-table thead {
    background-color: #eff6ff; /* 浅蓝表头 */
    position: sticky;
    top: 0;
}

.status-table th {
    padding: 20px 15px;
    font-size: 16px;
    font-weight: bold;
    color: #1e3a8a;
    border-bottom: 1px solid #cbd5e1;
    text-align: center;
}

.status-table tbody tr {
    height: 60px;
    transition: background-color 0.2s ease;
}

.status-table tbody tr:hover {
    background-color: #f1f5f9; /* hover 浅蓝灰 */
}

.status-table td {
    padding: 10px;
    border-bottom: 1px solid #cbd5e1;
    text-align: center;
}

/* 社区名称列样式 */
.col-community {
    width: 150px;
    background-color: #f8fafc;
    font-size: 14px;
    font-weight: bold;
    color: #1e40af;
    position: sticky;
    left: 0;
    z-index: 1;
}

/* 特性列样式 */
.col-feature {
    width: 100px;
    min-width: 100px;
}
```

Expected: 文件追加成功，表格样式定义完整

**Step 2: 在浏览器中刷新验证表格样式**

刷新浏览器页面

Expected: 表格布局整齐，表头固定在顶部，社区列固定在左侧（需等待数据加载后验证）

**Step 3: Commit**

```bash
git add ops-dashboard-demo/styles/main.css
git commit -m "feat: add table CSS styles with sticky columns"
```

Expected: 提交成功

---

## Task 5: 编写 CSS 状态灯样式

**Files:**
- Modify: `ops-dashboard-demo/styles/main.css:87-119`（追加状态灯样式）

**Step 1: 添加状态灯样式**

在 `ops-dashboard-demo/styles/main.css` 文件末尾追加以下内容：

```css
/* ========== 状态灯样式 ========== */
.status-light {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    display: inline-block;
    transition: all 0.2s ease;
    border: none;
}

/* 绿色：已使用 */
.status-light.active {
    background: radial-gradient(circle, #4ade80, #22c55e);
    box-shadow: 0 0 15px rgba(74, 222, 128, 0.6);
}

/* 黄色：对接中 */
.status-light.in-progress {
    background: radial-gradient(circle, #fbbf24, #f59e0b);
    box-shadow: 0 0 15px rgba(251, 191, 36, 0.6);
}

/* 灰色：未使用 */
.status-light.inactive {
    background: radial-gradient(circle, #d1d5db, #9ca3af);
}

/* Hover 效果 */
.status-light:hover {
    transform: scale(1.125);
    border: 2px solid #3b82f6;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
}

/* 图例中的状态灯演示 */
.status-light-demo {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-block;
}

.status-light-demo.active {
    background: radial-gradient(circle, #4ade80, #22c55e);
    box-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
}

.status-light-demo.in-progress {
    background: radial-gradient(circle, #fbbf24, #f59e0b);
    box-shadow: 0 0 8px rgba(251, 191, 36, 0.6);
}

.status-light-demo.inactive {
    background: radial-gradient(circle, #d1d5db, #9ca3af);
}
```

Expected: 文件追加成功，状态灯三种颜色及 hover 效果定义完整

**Step 2: 在浏览器中刷新验证状态灯**

刷新浏览器页面

Expected: Footer 图例中显示三个小状态灯（绿、黄、灰），视觉清晰可辨

**Step 3: Commit**

```bash
git add ops-dashboard-demo/styles/main.css
git commit -m "feat: add status light CSS styles with radial gradients"
```

Expected: 提交成功

---

## Task 6: 编写 CSS 模态框样式

**Files:**
- Modify: `ops-dashboard-demo/styles/main.css:120-152`（追加模态框样式）

**Step 1: 添加模态框样式**

在 `ops-dashboard-demo/styles/main.css` 文件末尾追加以下内容：

```css
/* ========== 模态框样式 ========== */
.modal {
    display: none; /* 默认隐藏 */
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.3); /* 半透明遮罩 */
    z-index: 1000;
    justify-content: center;
    align-items: center;
}

.modal.show {
    display: flex;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

.modal-content {
    width: 480px;
    max-height: 500px;
    background-color: #ffffff;
    border: 2px solid #3b82f6;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(59, 130, 246, 0.15);
    overflow-y: auto;
}

.modal-header {
    padding: 20px;
    background-color: #eff6ff;
    border-bottom: 1px solid #cbd5e1;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-header h3 {
    font-size: 18px;
    font-weight: bold;
    color: #1e40af;
}

.modal-close-btn {
    font-size: 24px;
    color: #64748b;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
}

.modal-close-btn:hover {
    color: #1e40af;
}

.modal-body {
    padding: 20px;
}

.modal-footer {
    padding: 15px 20px;
    border-top: 1px solid #cbd5e1;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}
```

Expected: 文件追加成功，模态框样式定义完整

**Step 2: 在浏览器中刷新验证模态框布局**

刷新浏览器页面

Expected: 模态框默认隐藏（display: none），布局准备就绪

**Step 3: Commit**

```bash
git add ops-dashboard-demo/styles/main.css
git commit -m "feat: add modal CSS styles with animations"
```

Expected: 提交成功

---

## Task 7: 编写 CSS 详情卡片内容样式

**Files:**
- Modify: `ops-dashboard-demo/styles/main.css:153-187`（追加详情卡片内容样式）

**Step 1: 添加详情卡片内容样式**

在 `ops-dashboard-demo/styles/main.css` 文件末尾追加以下内容：

```css
/* ========== 详情卡片内容样式 ========== */
.basic-info {
    margin-bottom: 20px;
}

.basic-info p {
    font-size: 14px;
    color: #1e40af;
    margin-bottom: 8px;
}

.basic-info strong {
    font-weight: bold;
}

.user-metrics,
.business-metrics {
    margin-bottom: 20px;
    border-top: 1px solid #cbd5e1;
    padding-top: 15px;
}

.user-metrics h4,
.business-metrics h4 {
    font-size: 16px;
    font-weight: bold;
    color: #1e40af;
    margin-bottom: 15px;
}

.user-metrics table,
.business-metrics table {
    width: 100%;
    border-collapse: collapse;
}

.user-metrics td,
.business-metrics td {
    padding: 8px;
    font-size: 14px;
    color: #1e40af;
}

.user-metrics td:first-child,
.business-metrics td:first-child {
    width: 50%;
}

.user-metrics td strong,
.business-metrics td strong {
    font-size: 18px;
    font-weight: bold;
    color: #3b82f6;
}

.note-info {
    margin-top: 20px;
    padding: 15px;
    background-color: #f8fafc;
    border-radius: 8px;
    font-size: 13px;
    color: #64748b;
}

.btn-close,
.btn-edit {
    padding: 8px 20px;
    font-size: 14px;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-close {
    background-color: #ffffff;
    color: #3b82f6;
}

.btn-close:hover {
    background-color: #eff6ff;
}

.btn-edit {
    background-color: #3b82f6;
    color: #ffffff;
}

.btn-edit:hover {
    background-color: #1e40af;
}
```

Expected: 文件追加成功，详情卡片内容样式完整

**Step 2: 在浏览器中刷新验证样式完整性**

刷新浏览器页面

Expected: CSS 样式完整加载，等待数据填充后验证视觉效果

**Step 3: Commit**

```bash
git add ops-dashboard-demo/styles/main.css
git commit -m "feat: add detail card content CSS styles"
```

Expected: 提交成功

---

## Task 8: 编写 Mock 数据文件

**Files:**
- Create: `ops-dashboard-demo/scripts/data.js`

**Step 1: 创建数据文件并定义社区和特性列表**

创建 `ops-dashboard-demo/scripts/data.js`，写入以下内容：

```javascript
// ========== 社区和特性定义 ==========
const COMMUNITIES = [
    'MindIE', 'PTA', 'MindSpeed', 'openEuler', 'HPCkit',
    'UBS Core', 'openUBMC', 'CANN', 'openLiBing'
];

const FEATURES = [
    '门禁检查', '接口兼容性', '流水线', '测试框架', 'SBOM',
    '漏洞视图', '发布评审', '工具市场', 'AI agent', 'Skill市场', '数字化运营看板'
];

// ========== 业务指标定义 ==========
const BUSINESS_METRICS_CONFIG = {
    '门禁检查': ['门禁平均时长', '门禁拦截率', '门禁成功率'],
    '接口兼容性': ['接口纳管数', '接口测试覆盖率', '接口变更次数'],
    '流水线': ['流水线执行次数', '平均耗时', '成功率'],
    '测试框架': ['用例数', '覆盖率', '自动化率'],
    'SBOM': ['构件数', '合规率', '漏洞发现数'],
    '漏洞视图': ['漏洞总数', '修复率', '高危漏洞数'],
    '发布评审': ['发布次数', '评审时长', '通过率'],
    '工具市场': ['工具数量', '下载次数', '活跃工具数'],
    'AI agent': ['Agent数量', '任务执行数', '成功率'],
    'Skill市场': ['Skill数量', '使用次数', '热门Skill排名'],
    '数字化运营看板': ['看板访问次数', '数据更新频率', '用户满意度']
};
```

Expected: 文件创建成功，包含社区和特性列表定义

**Step 2: 添加数据生成函数**

在 `ops-dashboard-demo/scripts/data.js` 文件末尾追加：

```javascript
// ========== 数据生成函数 ==========
function generateMockData() {
    const data = [];
    
    for (let community of COMMUNITIES) {
        for (let feature of FEATURES) {
            // 随机生成状态：active (50%), in-progress (30%), inactive (20%)
            const random = Math.random();
            let status;
            if (random < 0.5) status = 'active';
            else if (random < 0.8) status = 'in-progress';
            else status = 'inactive';
            
            const item = {
                community: community,
                feature: feature,
                status: status
            };
            
            // 生成用户指标
            if (status === 'active') {
                item.uv = Math.floor(Math.random() * 200) + 50;
                item.pv = Math.floor(Math.random() * 2000) + 500;
            } else if (status === 'in-progress') {
                item.uv = Math.floor(Math.random() * 50) + 10;
                item.pv = Math.floor(Math.random() * 500) + 100;
            } else {
                item.uv = 0;
                item.pv = 0;
            }
            
            // 生成业务指标
            if (status !== 'inactive') {
                const metricsConfig = BUSINESS_METRICS_CONFIG[feature];
                item.business_metrics = {};
                
                for (let metricName of metricsConfig) {
                    if (metricName.includes('率') || metricName.includes('比')) {
                        // 百分比指标
                        item.business_metrics[metricName] = 
                            (Math.random() * 30 + 70).toFixed(1) + '%';
                    } else if (metricName.includes('时长') || metricName.includes('耗时')) {
                        // 时长指标
                        item.business_metrics[metricName] = 
                            (Math.random() * 10 + 2).toFixed(1) + '分钟';
                    } else if (metricName.includes('数') || metricName.includes('次数')) {
                        // 计数指标
                        item.business_metrics[metricName] = 
                            Math.floor(Math.random() * 500) + 50 + '次';
                    } else if (metricName.includes('排名')) {
                        // 排名指标
                        item.business_metrics[metricName] = 'Top ' + Math.floor(Math.random() * 5 + 1);
                    } else if (metricName.includes('满意度')) {
                        // 满意度指标
                        item.business_metrics[metricName] = 
                            (Math.random() * 1 + 3.5).toFixed(1) + '星';
                    } else if (metricName.includes('频率')) {
                        // 频率指标
                        const frequencies = ['每日', '每周', '每月'];
                        item.business_metrics[metricName] = 
                            frequencies[Math.floor(Math.random() * frequencies.length)];
                    } else {
                        // 默认计数指标
                        item.business_metrics[metricName] = 
                            Math.floor(Math.random() * 100) + 10 + '个';
                    }
                }
                
                // 生成备注
                if (status === 'active') {
                    item.note = `已完成${feature}配置，支持完整功能`;
                    item.contact = '张三';
                    item.date = '2024-03-' + Math.floor(Math.random() * 28 + 1);
                } else {
                    item.note = `正在对接${feature}，预计 1 个月内完成`;
                    item.contact = '李四';
                    item.date = '2024-04-' + Math.floor(Math.random() * 28 + 1);
                }
            } else {
                item.note = '暂未对接，如有需求请联系运营团队';
                item.business_metrics = {};
            }
            
            data.push(item);
        }
    }
    
    return data;
}

// ========== 导出数据 ==========
const STATUS_DATA = generateMockData();
```

Expected: 文件追加成功，包含完整的数据生成逻辑

**Step 3: 在浏览器控制台验证数据生成**

刷新浏览器页面，打开开发者工具（F12），在控制台输入：

```javascript
console.log(STATUS_DATA.length);
console.log(STATUS_DATA[0]);
```

Expected: 输出 `99`（9社区 × 11特性），并显示第一条数据对象结构

**Step 4: Commit**

```bash
git add ops-dashboard-demo/scripts/data.js
git commit -m "feat: add mock data generation script"
```

Expected: 提交成功

---

## Task 9: 编写 JavaScript 表格渲染逻辑

**Files:**
- Create: `ops-dashboard-demo/scripts/main.js`

**Step 1: 创建脚本文件并添加表格渲染函数**

创建 `ops-dashboard-demo/scripts/main.js`，写入以下内容：

```javascript
// ========== 表格渲染函数 ==========
function renderTable() {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';
    
    // 按社区分组数据
    const groupedData = {};
    for (let item of STATUS_DATA) {
        if (!groupedData[item.community]) {
            groupedData[item.community] = {};
        }
        groupedData[item.community][item.feature] = item;
    }
    
    // 渲染每一行
    for (let community of COMMUNITIES) {
        const row = document.createElement('tr');
        
        // 社区名称列
        const communityCell = document.createElement('td');
        communityCell.className = 'col-community';
        communityCell.textContent = community;
        row.appendChild(communityCell);
        
        // 特性列（状态灯）
        for (let feature of FEATURES) {
            const featureCell = document.createElement('td');
            const item = groupedData[community][feature];
            
            // 创建状态灯
            const statusLight = document.createElement('span');
            statusLight.className = 'status-light ' + item.status;
            statusLight.dataset.community = community;
            statusLight.dataset.feature = feature;
            
            // 添加点击事件
            statusLight.addEventListener('click', () => showDetailModal(item));
            
            featureCell.appendChild(statusLight);
            row.appendChild(featureCell);
        }
        
        tbody.appendChild(row);
    }
}

// ========== 页面加载时渲染表格 ==========
document.addEventListener('DOMContentLoaded', () => {
    renderTable();
});
```

Expected: 文件创建成功，包含表格渲染函数

**Step 2: 在浏览器中刷新验证表格渲染**

刷新浏览器页面

Expected: 表格显示 9 行（对应 9 个社区），每行显示 11 个状态灯，状态灯颜色随机分布

**Step 3: Commit**

```bash
git add ops-dashboard-demo/scripts/main.js
git commit -m "feat: add table rendering logic with status lights"
```

Expected: 提交成功

---

## Task 10: 编写 JavaScript 模态框交互逻辑

**Files:**
- Modify: `ops-dashboard-demo/scripts/main.js:28-44`（追加模态框逻辑）

**Step 1: 添加模态框显示和关闭函数**

在 `ops-dashboard-demo/scripts/main.js` 文件末尾追加：

```javascript
// ========== 模态框交互函数 ==========
function showDetailModal(item) {
    const modal = document.getElementById('detail-modal');
    const modalContent = modal.querySelector('.modal-content');
    
    // 填充基础信息
    const basicInfo = modal.querySelector('.basic-info');
    const statusText = item.status === 'active' ? '已使用' : 
                       item.status === 'in-progress' ? '对接中' : '未使用';
    const statusLightHtml = `<span class="status-light-demo ${item.status}"></span>`;
    
    basicInfo.innerHTML = `
        <p><strong>社区：</strong>${item.community}</p>
        <p><strong>特性：</strong>${item.feature}</p>
        <p><strong>状态：</strong>${statusText} ${statusLightHtml}</p>
    `;
    
    // 填充用户指标
    const userMetrics = modal.querySelector('.user-metrics');
    if (item.status !== 'inactive') {
        userMetrics.innerHTML = `
            <h4>📊 用户指标</h4>
            <table>
                <tr><td>用户数(UV)</td><td><strong>${item.uv}</strong> 人</td></tr>
                <tr><td>访问量(PV)</td><td><strong>${item.pv}</strong> 次</td></tr>
            </table>
        `;
    } else {
        userMetrics.innerHTML = `
            <h4>📊 用户指标</h4>
            <table>
                <tr><td>用户数(UV)</td><td><strong>0</strong> 人</td></tr>
                <tr><td>访问量(PV)</td><td><strong>0</strong> 次</td></tr>
            </table>
        `;
    }
    
    // 填充业务指标
    const businessMetrics = modal.querySelector('.business-metrics');
    if (item.status !== 'inactive' && item.business_metrics) {
        let metricsHtml = '<h4>📈 业务指标</h4><table>';
        for (let [key, value] of Object.entries(item.business_metrics)) {
            metricsHtml += `<tr><td>${key}</td><td><strong>${value}</strong></td></tr>`;
        }
        metricsHtml += '</table>';
        businessMetrics.innerHTML = metricsHtml;
    } else {
        businessMetrics.innerHTML = `
            <h4>📈 业务指标</h4>
            <table>
                <tr><td>暂无数据</td><td>-</td></tr>
            </table>
        `;
    }
    
    // 填充备注
    const noteInfo = modal.querySelector('.note-info');
    if (item.status !== 'inactive') {
        noteInfo.innerHTML = `
            <p><strong>备注：</strong>${item.note}</p>
            <p><strong>负责人：</strong>${item.contact} | <strong>对接时间：</strong>${item.date}</p>
        `;
    } else {
        noteInfo.innerHTML = `<p>${item.note}</p>`;
    }
    
    // 控制编辑按钮显示
    const editBtn = modal.querySelector('.btn-edit');
    if (item.status === 'inactive') {
        editBtn.style.display = 'none';
    } else {
        editBtn.style.display = 'inline-block';
    }
    
    // 显示模态框
    modal.classList.add('show');
}

function closeDetailModal() {
    const modal = document.getElementById('detail-modal');
    modal.classList.remove('show');
}
```

Expected: 文件追加成功，包含模态框显示和关闭函数

**Step 2: 在浏览器中刷新并点击状态灯验证**

刷新浏览器页面，点击任意状态灯

Expected: 模态框弹出，显示详情信息（基础信息、用户指标、业务指标、备注），背景半透明遮罩

**Step 3: Commit**

```bash
git add ops-dashboard-demo/scripts/main.js
git commit -m "feat: add modal interaction logic with data filling"
```

Expected: 提交成功

---

## Task 11: 编写 JavaScript 关闭模态框事件绑定

**Files:**
- Modify: `ops-dashboard-demo/scripts/main.js:45-76`（追加关闭事件绑定）

**Step 1: 添加关闭模态框的事件监听**

在 `ops-dashboard-demo/scripts/main.js` 文件末尾追加：

```javascript
// ========== 关闭模态框事件绑定 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 关闭按钮
    const modal = document.getElementById('detail-modal');
    const closeBtn = modal.querySelector('.btn-close');
    const closeIconBtn = modal.querySelector('.modal-close-btn');
    
    closeBtn.addEventListener('click', closeDetailModal);
    closeIconBtn.addEventListener('click', closeDetailModal);
    
    // 点击遮罩层关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeDetailModal();
        }
    });
    
    // ESC 键关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            closeDetailModal();
        }
    });
});
```

Expected: 文件追加成功，包含多种关闭模态框的方式

**Step 2: 在浏览器中测试关闭功能**

刷新浏览器页面，点击状态灯打开模态框，然后测试：
1. 点击"关闭"按钮
2. 点击右上角 × 按钮
3. 点击模态框外的遮罩层
4. 按 ESC 键

Expected: 所有方式都能成功关闭模态框，模态框淡出消失

**Step 3: Commit**

```bash
git add ops-dashboard-demo/scripts/main.js
git commit -m "feat: add modal close event handlers (button, overlay, ESC)"
```

Expected: 提交成功

---

## Task 12: 整合与完整验证

**Files:**
- All previous files

**Step 1: 在浏览器中进行完整验证**

刷新浏览器页面 `ops-dashboard-demo/index.html`

**视觉验收清单：**
- [x] 页面背景为浅蓝灰色（#f0f9ff）
- [x] Header 显示标题，背景白色
- [x] 表格显示 9 行 12 列（社区 + 11特性）
- [x] 社区列固定在左侧
- [x] 状态灯三种颜色清晰可辨（绿、黄、灰）
- [x] Footer 显示图例说明
- [x] 表格 hover 效果流畅
- [x] 状态灯 hover 效果明显

**交互验收清单：**
- [x] 点击任意状态灯触发模态框
- [x] 模态框显示完整详情（基础信息、用户指标、业务指标、备注）
- [x] 绿色/黄色状态显示业务指标和负责人信息
- [x] 灰色状态隐藏编辑按钮，显示"暂未对接"备注
- [x] 多种方式关闭模态框正常

Expected: 所有验收项通过

**Step 2: 测试响应式布局**

调整浏览器窗口宽度，测试不同屏幕尺寸：

- 桌面端（> 1400px）：所有列完整展示
- 中等屏幕（1400px - 768px）：特性列横向滚动，社区列固定
- 移动端（< 768px）：布局简化

Expected: 响应式布局正常工作

**Step 3: 最终 Commit**

```bash
git add ops-dashboard-demo
git commit -m "feat: complete ops dashboard demo with all features

- HTML structure with table layout
- CSS styles with blue-white theme and status lights
- JavaScript interaction with modal details
- Mock data generation for 9 communities × 11 features
- All acceptance criteria verified

Co-authored-by: Claude Code <noreply@anthropic.com>
Generated-by: claude-sonnet-4-6"
```

Expected: 提交成功，包含所有文件

---

## Task 13: 创建 README 文档

**Files:**
- Create: `ops-dashboard-demo/README.md`

**Step 1: 创建 README 文件**

创建 `ops-dashboard-demo/README.md`，写入以下内容：

```markdown
# openLiBing 运营看板 Demo

## 项目简介

这是一个纯前端静态页面的运营看板 Demo，用于展示 openLiBing 特性在各开源社区的覆盖情况。

## 功能特性

- 状态矩阵表格：展示 9 个开源社区 × 11 个特性的覆盖情况
- 状态灯指示：绿色（已使用）、黄色（对接中）、灰色（未使用）
- 详情卡片：点击状态灯查看用户指标和业务指标
- 浅色蓝白主题：清晰的数据可视化风格

## 使用方法

1. 在浏览器中打开 `index.html`
2. 查看状态矩阵表格
3. 点击任意状态灯查看详情
4. 关闭详情卡片（点击关闭按钮、遮罩层或 ESC 键）

## 技术栈

- HTML5：页面结构
- CSS3：样式设计（Grid/Flexbox 布局）
- JavaScript：交互逻辑
- 无需任何依赖，可直接运行

## 目录结构

```
ops-dashboard-demo/
├── index.html          # 主页面
├── styles/
│   └ main.css        # 主样式文件
├── scripts/
│   ├── main.js         # 主逻辑脚本
│   └ data.js          # Mock 数据
├── assets/             # 资源文件（预留）
└── README.md           # 项目说明
```

## 后续扩展

- 对接真实数据源（API 或数据库）
- 导出数据功能
- 按社区或特性筛选
- 状态变更历史记录
- 集成到运营管理后台

## 设计文档

详细设计文档位于：`../openlibing-docs/temp_designs/2026-06-05-ops-dashboard-design.md`

## 作者

AI-assisted development with Claude Code
```

Expected: 文件创建成功，包含完整的项目说明

**Step 2: Commit**

```bash
git add ops-dashboard-demo/README.md
git commit -m "docs: add README for ops dashboard demo"
```

Expected: 提交成功

---

## Task 14: 最终交付

**Step 1: 检查所有文件是否已提交**

```bash
git status
```

Expected: 工作区干净，无未提交文件

**Step 2: 查看提交历史**

```bash
git log --oneline
```

Expected: 显示所有提交记录，包含功能实现和文档

**Step 3: 在浏览器中最终验证**

打开 `ops-dashboard-demo/index.html`，进行最终完整验收：

**验收清单：**
- [x] 页面布局正确（Header、Main、Footer）
- [x] 表格显示完整（9 行 × 12 列）
- [x] 状态灯颜色正确（绿、黄、灰）
- [x] Hover 效果流畅
- [x] 点击交互正常
- [x] 详情卡片数据完整
- [x] 关闭模态框功能正常
- [x] 响应式布局适配
- [x] README 文档完整

Expected: 所有验收项通过，Demo 完成交付

---

## 执行方式

计划完成并保存到 `docs/plans/2026-06-05-ops-dashboard.md`。

两种执行选项：

**1. Subagent-Driven (this session)** - 在当前会话中使用 subagent-driven-development skill，每个任务分配独立子代理，任务间可快速迭代

**2. Parallel Session (separate)** - 在新会话中使用 executing-plans skill，批量执行带检查点

**选择哪种执行方式？**