# 测试策略 - ISSUE-078

## 1. Issue 信息

| 字段 | 内容 |
|------|------|
| Issue编号 | ISSUE-078 |
| Issue标题 | 【蓝区】 Nightly流水线看板增加汇总数据展示、明细增加失败类型和导出能力 |
| 关联需求 | https://gitcode.com/openlibing/openlibing-ops/issues/78 |
| 所属微服务 | openlibing-ops |
| 所属模块 | nightly_dashboard |
| 负责人 | tester-a |
| 创建日期 | 2026-08-11 |
| 状态 | 进行中 |

## 2. 需求摘要

本需求围绕 Nightly 流水线看板（nightly-dashboard）进行三项增强（开发设计文档版本 2026-07-24）：

1. **明细增加"失败任务类型"字段及筛选**：流水线运行明细（category=`nightly-dashboard-detail`）新增 `failedTaskType` 字段，取值枚举为"构建任务 / 测试任务 / 其他任务 / 流水线未失败"；支持按 3 种失败类型（构建任务/测试任务/其他任务）进行筛选，成功流水线通过 `pipelineStatus` 筛选。
2. **增加项目级汇总表格**：新增项目级单行汇总接口（category=`nightly-dashboard-summary`），将所选时间范围内匹配 projectId 的所有流水线运行记录聚合为一行，返回 26 个字段（E2E 时长、构建/测试任务时长、测试用例指标），P50/P90/P95 基于原始明细用 Doris PERCENTILE 计算。
3. **主列表导出能力**：新增导出接口 `POST /common/export/nightly-dashboard`，导出主列表全量数据为 xlsx 二进制文件流；汇总与明细接口暂不支持导出。

接口路由：三个查询接口共用 `POST /common/detail`，通过请求体 `category` 字段路由；导出接口 category 作为 path variable。

其他变更：`PipelineJobResp` 中 BUILD 类型中文标签由"编译任务"改为"构建任务"。

## 3. 测试目标

- 验证明细接口 `failedTaskType` 字段返回正确、枚举合法、筛选逻辑（构建任务 > 测试任务 > 其他任务 优先级）符合设计文档
- 验证项目级汇总接口聚合逻辑正确、26 个字段完整、返回结构（PageResult，total 为 0 或 1）符合设计文档
- 验证主列表导出接口返回 xlsx 二进制流、文件命名格式符合约定
- 验证 UI 层失败任务类型列展示与筛选、汇总表格渲染、导出按钮交互正常
- 验证相关接口响应时间满足阈值，未认证访问被拒绝

## 4. 测试范围

| 测试类型 | 是否覆盖 | 说明 |
|----------|----------|------|
| UI功能测试 | 是 | 失败任务类型列展示与筛选、项目级汇总表格渲染、导出按钮交互（beta 环境） |
| API接口测试 | 是 | 汇总接口、明细接口（含 failedTaskType 筛选）、导出接口（test 环境） |
| 性能测试 | 是 | 汇总接口、明细接口响应时间（test 环境） |
| 安全测试 | 是 | 汇总/导出接口未认证访问拒绝验证（test 环境） |

## 5. 测试策略

### 5.1 手工测试

- 本期无手工用例。所有功能点均可通过自动化覆盖（UI 自动化 + API 自动化）。
- 手工用例归档位置: `assets/docs/openlibing/openlibing_ops/issues/ISSUE-078/`

### 5.2 自动化测试

- **UI 层**（beta 环境，复用已有脚本）：
  - `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/`：失败任务类型列存在、值合法、未失败展示、筛选功能
  - `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/`：导出按钮、xlsx 下载
  - 页面对象已具备对应方法（`mindie_dashboard_page.py` Issue #78 扩展段）
- **API 层**（test 环境，新建脚本）：
  - `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/`：汇总/明细/导出接口测试
- 自动化用例归档位置: `assets/docs/openlibing/openlibing_ops/issues/ISSUE-078/test_cases.md`
- 自动化脚本位置: `src/tests/openlibing/openlibing_ops/{ui,api}/beta/nightly_dashboard/`

### 5.3 用例复用原则

- 明细/汇总接口为新增接口，无既有用例可复用，全部新建
- UI 层失败任务类型与导出相关测试脚本已在 beta 目录存在，直接选用并归档到本 Issue

## 6. 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 接口路径前缀不确定（本地 `/` vs 环境 `/ops`） | API 用例可能因路径错误失败 | 脚本中兼容两种路径，先探测再请求 |
| `failedTaskType` 判定依赖 job 数据口径 | 筛选结果与预期不符 | 用例断言采用"合法枚举 + 数量可验证"策略，不硬编码具体行数 |
| 导出接口在 beta 环境可能未注册 | 导出用例失败 | UI 用例做"按钮存在性"兜底；API 用例做状态码兼容 |
| 页面对象已有 Issue #78 方法但未经过 beta 全量验证 | 定位器可能失效 | 执行前先跑冒烟，失败及时调整 |

## 7. 依赖与前置条件

- 依赖1：test/beta 环境可访问（beta.openlibing.com），登录凭证已在 `.env` 配置
- 依赖2：Nightly 看板页面（projectId=300036, MindIE）存在流水线运行数据
- 依赖3：浏览器自动化（Playwright chromium）可用
- 依赖4：gitcode CLI 用于远端写操作（当前环境不可用，执行阶段以本地 pytest 为主，提交阶段需用户确认后处理）

## 8. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-11 | tester-a | 初始版本 |
