# 需求背景

## 业务场景

openEuler 发布评审详情页（发布管理 → 更新/发布评审详情）通过横向流程节点驱动 Jenkins 任务，评审人员需要按顺序触发各节点并观察执行结果。本轮迭代新增"同步仓库"与"生成CVE公告"节点，并引入"自动执行"能力，减少人工逐个点击节点的操作成本。

## 问题痛点

1. **节点缺失**：发布评审流程缺少"同步仓库"节点与"生成CVE公告"节点，构建结果无法在前端触发同步，CVE 公告需离开页面到其他入口生成。
2. **人工串联成本高**：一次评审涉及多个 Jenkins 任务，需人工逐个点击、等待并判断状态，容易漏点或重复触发。
3. **状态不可见**：自动执行期间无法看到当前进度与开始时间，评审人员无法判断任务是否卡住。
4. **批量操作误触**：生成类操作未限制数据条数，多选时会生成错误范围的数据。

## 需求目标

1. 新增"同步仓库"横向节点，支持在评审详情页触发 `syncBuildResultToRepo`。
2. 新增"生成CVE公告"横向节点，支持在评审详情页触发 `generateUpdateinfo`。
3. 新增"自动执行"按钮，支持一键启动并联查自动执行状态，执行中按 1 分钟轮询刷新节点状态。
4. 页面初始化时优先读取自动执行状态，执行中则只走自动执行轮询，避免与手动轮询冲突。
5. 展示"自动执行开始时间"与"当前流程开始时间"，格式为 `YYYY-MM-DD HH:mm:ss`。
6. 更新组件下拉新增"生成updateinfo"操作，且仅允许选择一条数据。

## 验收标准

### 功能验收

1. **同步仓库节点**
   - 横向流程新增"同步仓库"节点，状态字段 `syncBuildResult`
   - 点击执行调用 `POST /publish/jenkins/syncBuildResultToRepo`，`reviewId` 通过请求体传递
2. **生成CVE公告节点**
   - 横向流程新增"生成CVE公告1"节点，状态字段 `generateSafeNoticeResult1`
   - 点击执行调用 `POST /publish/jenkins/generateUpdateinfo`，返回成功后节点直接置为成功，不轮询
   - 竖向原有"生成CVE公告"节点文案调整为"生成CVE公告2"
3. **自动执行**
   - 有权限时展示"自动执行"按钮，按钮文案/颜色随状态变化：自动执行中 / 自动执行成功 / 自动执行失败
   - 点击后调用 `POST /publish/jenkins/startUpdateAutomation`，返回状态写入按钮，并立即查询一次自动执行状态
   - 页面初始化读取 `jenkinsJobExecStatusInfo.updateAutomationStatus`，为执行中时启动自动执行轮询
   - 自动执行期间不启动手动节点轮询，且点击自动执行时清空手动节点定时器
   - 执行中轮询间隔为 1 分钟，调用 `POST /publish/jenkins/queryUpdateAutomation` 刷新节点状态，结束后停止轮询
4. **时间展示**
   - 从 `jenkinsJobExecStatusInfo` 读取 `updateAutomationStartTime`（自动执行开始时间）与 `updateAutomationStepTime`（当前流程开始时间）
   - 有值时按 `YYYY-MM-DD HH:mm:ss` 展示在自动执行按钮右侧，无值时不展示
5. **生成updateinfo 下拉操作**
   - 更新组件"更多操作"新增"生成updateinfo"
   - 未选择数据时提示"请选择数据"；选择多条时提示"请选择一条数据！"

### 非功能验收

1. 不改变既有节点执行顺序与其他节点行为
2. 自动执行轮询与手动轮询互斥，页面销毁时清理所有定时器
3. 代码通过 ESLint / Prettier / pre-commit 检查

## 关联 Issue

[openlibing/openlibing-platform-release#125](https://gitcode.com/openlibing/openlibing-platform-release/issues/125)
