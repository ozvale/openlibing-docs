# 【openlibing】代码仓管理新增日志记录功能-同步仓库记录 测试策略设计说明书

## 1. 基本信息

- **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2109711227
- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/137
- **需求名称**: 【openlibing】代码仓管理新增日志记录功能-同步仓库记录
- **核心目标**:
  仓库列表页「同步仓库」按钮触发后提供实时同步进度反馈（仓库级粒度，hover 可见），解决点击后无任何反馈、无法感知同步进行到哪个仓库及何时结束的问题。
- **开发责任人**: 陈明旭
- **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

- [x] **功能自检测试**

> - **测试重点:** 进度查询接口语义（none / running / finished 三态字段）、进度 Hash 字段正确性、进度 popover 三态展示、按钮 loading / disabled 状态机与串行轮询、手动与 XxlJob 双链路互斥、R1 total 口径对齐、R2 projectId 参数化、R3 全局配置中断重跑。
> - **目的:** 确保同步进度真实可观测、双链路互斥生效、三项验收补充调整按预期落地。
> - **触发条件:** 强制执行。

- [x] **体验测试**

> - **测试重点:** disabled 态下按钮 hover 仍可查看进度（popover 挂外层 wrapper）、失败数与触发方式可视、完成后自动恢复与单次刷新。
> - **目的:** 确保用户在同步全过程可获得清晰且不打断操作的进度反馈。
> - **触发条件:** 强制执行。

- [x] **集成测试**

> - **测试重点:** 前端（openlibing-web）与后端（openlibing-coderepo）端到端联调、定时链路与手动链路共享同一套进度查询、多实例部署下的跨实例互斥。
> - **目的:** 确保前后端契约一致、双链路在同一进度口径下协同工作、多实例部署安全。
> - **触发条件:** 强制执行。

- [x] **安全与隐私测试**

> - **测试重点:** 新增 `GET /project-repo/sync-progress` 接口的项目级横向越权校验、入参非空校验、进度数据不含 `accessToken`、Redis key 无注入面。
> - **目的:** 确保新增查询接口不引入越权与信息泄露风险。
> - **触发条件:** 强制执行（新增对外接口必选）。

- [x] **可靠性与韧性测试**

> - **测试重点:** 进程崩溃后进度随 TTL 自然终止（running → none）、超 30min 同步锁过期不泄漏 `inFlight`、锁 key 统一与滚动发布期跨版本互斥。
> - **目的:** 确保异常与长耗时场景下按钮可自愈、项目不永久卡「同步中」。
> - **触发条件:** 强制执行。

- [ ] **可服务性与可观测性测试**

- [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.手动同步进度端到端验证**:

- 前置条件: 项目已配置代码仓（`repo_info` 存在多条记录），页面处于仓库列表
- 测试步骤:
  1. 点击「同步仓库」，观察按钮进入 loading / disabled
  2. hover 按钮查看进度弹层，核对 total 是否等于该项目全量仓数
  3. 持续观察 completed 递增、currentRepo 切换与失败计数
  4. 同步结束后观察仓库列表自动刷新
- 预期结果: 进度从 0 递增至 total，currentRepo 实时切换，无失败时失败数为 0，结束后列表刷新一次

**2.进度 popover 三态展示验证**:

- 测试步骤:
  1. 空闲态（无同步任务）hover 按钮，检查弹层文案
  2. running 态 hover，检查进度条 / 已完成 x/y / 正在同步仓 / 失败数 / 触发方式
  3. finished 态 hover，检查完成态展示
- 预期结果: none 显示「暂无进行中的同步任务」；running 显示百分比进度条 + 已完成 x/y + 正在同步：{当前仓} + 失败数（>0 红色）+ 触发方式（手动/定时任务）；finished 显示完成态

**3.按钮状态与轮询状态机验证**:

- 测试步骤:
  1. running 期间检查按钮 disabled+loading，且重复点击无二次提交
  2. 轮询发现 finished 时检查按钮恢复、列表刷新一次、success 提示仅一次
  3. 轮询发现 none 时检查按钮恢复且不弹提示
  4. 观察请求节奏是否为「上一响应返回后延时 2s」串行轮询
- 预期结果: 状态完全由服务端 status 驱动，running → finished 触发一次恢复 + 刷新 + 提示，running → none 静默恢复，任意时刻最多一个在途查询请求

**4.页面进入 / 刷新状态恢复验证**:

- 测试步骤:
  1. 同步进行中刷新页面，检查按钮状态与进度是否恢复
  2. 同步进行中关闭再打开列表页，检查轮询是否续接
  3. 页面首屏查询即为 finished / none 时，检查是否触发列表刷新
- 预期结果: 首查 running 则按钮禁用 + 轮询续接；首查 finished / none 不触发列表刷新、不弹提示

**5.页面链路与 XxlJob 链路互斥验证**:

- 测试步骤:
  1. 页面触发同步期间再次点击「同步仓库」，检查提示文案
  2. 页面同步期间触发 XxlJob step2（或 step8 SIG 仓同步），查看该轮日志
  3. XxlJob step2 持有项目锁期间在页面点击同步，检查提示
- 预期结果: 二次点击返回「当前项目正在同步仓库信息，请稍后重试」；XxlJob 拿不到锁时跳过该项目本轮并记录日志、不阻塞整轮；两链路复用同一把 Redisson 锁

**6.R2 XxlJob projectId 参数化验证**:

- 测试步骤:
  1. 以参数 `projectId=xxx` 运行 `syncRepoInfoHandler`，检查 step1 / step2 / step5-6 / step8 是否仅处理该项目
  2. 检查 step3 / step4 / step7 是否仍按全局表级执行
  3. 传入非法 projectId，检查任务是否 handleFail 退出
  4. 不传参数运行，检查行为与改造前是否一致
- 预期结果: 指定 projectId 时仅该项目被同步；step3 / 4 / 7 保持全量；非法参数任务失败退出；不传参数行为不变

**7.R3 全局配置变更中断重跑验证**:

- 测试步骤:
  1. 手动触发同步，待其在耗时阶段（平台同步）运行中
  2. 提交全局配置变更（sig 路径或公共账号），触发新任务等待锁（60s）
  3. 观察旧任务是否在下一个仓边界检查点中断退出并释放锁
  4. 观察新任务是否获锁并按新配置全链路重跑
- 预期结果: 旧任务秒级内（仓边界）中断并释放锁，新任务在 60s 等待窗口内接续执行；过程中进度短暂 finished → running 属预期；配置变更后重跑不再被静默丢弃

### 3.2 体验测试专项

**1.disabled 态悬浮可用验证**:

- 测试步骤: 同步期间按钮为 disabled，鼠标 hover 按钮区域
- 预期结果: 仍能弹出进度弹层（popover 挂按钮外层 wrapper，未因 disabled 丢失 mouseenter）

**2.进度信息可读性验证**:

- 测试步骤: 制造仓库同步失败，hover 查看弹层
- 预期结果: 失败数红色显示且数值与实际失败仓数一致，触发方式（手动/定时任务）标识清晰

### 3.3 集成测试专项

**1.前后端端到端联调验证**:

- 前置条件: web 连 beta 后端
- 测试步骤: 点击同步 → 按钮禁用 → hover 看进度 → 完成后自动刷新列表
- 预期结果: 前端展示与后端进度 Hash 数据一致，状态流转正确

**2.定时链路进度可观察验证**:

- 测试步骤: 仅由 XxlJob step2 触发同步（页面不点击），在页面 hover 查看进度
- 预期结果: 可观察到进度，triggerSource=job，进度口径与手动链路一致

**3.多实例互斥验证**:

- 测试步骤: 在多实例部署下，于实例 A 页面触发同步，于实例 B 触发 XxlJob 或页面同步
- 预期结果: 因复用同一 Redisson 锁 key，跨实例互斥生效，不会并发写 `repo_info` / `repo_branch`

### 3.4 安全与隐私测试专项

**1.横向越权校验验证**:

- 测试步骤: 使用无该项目权限的 userId 查询 `GET /project-repo/sync-progress?userId=&projectId=`
- 预期结果: 被 `verifyPermissionsByProduct(..., REPO_QUERY)` 拒绝，无法查询非授权项目的进度

**2.入参校验验证**:

- 测试步骤: 分别传空 / 缺失 userId、projectId
- 预期结果: `@NotBlank` / `@NotNull` 校验生效，返回参数错误

**3.敏感信息与注入面验证**:

- 测试步骤: 检查进度返回字段与 Redis key 构成
- 预期结果: 进度数据不含 `accessToken` 等敏感信息；Redis key 由 Integer projectId 拼接，无注入面

### 3.5 可靠性与韧性测试专项

**1.进程崩溃自愈验证**:

- 测试步骤: 同步过程中强制终止 coderepo 实例（模拟崩溃，无 finishProgress 调用）
- 预期结果: 进度 status 停留 running 至 30min TTL 过期，查询返回 none，前端按钮自动恢复（不依赖 finish 回调）

**2.超长同步 inFlight 不泄漏验证**:

- 测试步骤: 构造同步耗时超过锁租约 30min 的场景，观察 `submitProjectSyncTask` finally 执行顺序
- 预期结果: finally 按 `inFlight-- → finishProgress → isHeldByCurrentThread 才 unlock` 执行，锁过期后 unlock 抛 `IllegalMonitorStateException` 不再跳过 `inFlight--`，项目不会被永久卡「同步中」

**3.锁 key 统一与跨版本互斥验证**:

- 测试步骤: 滚动发布期（新旧版本共存）分别由新旧实例触发手动与 job 同步
- 预期结果: job step2 / step8 复用 `PROJECT_SYNC_LOCK_PREFIX` 同一 key，跨版本互斥成立，进度 Hash 与锁 key 相互独立

---

## 4. 补充说明

1. 本测试策略对应 issue https://gitcode.com/openlibing/openlibing-coderepo/issues/137 ，关联 PR：openlibing-coderepo #193（→ release_20260923_iter2）、openlibing-web #792（→ release_20260923）。
2. issue #137 标题为「代码仓管理新增日志记录功能」，正文描述为「仓库同步进度展示与手动/定时同步互斥」，本测试策略以 **issue #137 正文内容**为准。
3. 验收以 proposal 验收标准为准：进度条三态展示真实、按钮状态跟随服务端 status、双链路互斥生效、进度与锁解耦、查询接口有项目级越权校验、R1 / R2 / R3 三项调整落地、coderepo 单测与 pre-commit 通过。
4. 测试维度在 8 月同类功能模板基础上新增「可靠性与韧性测试」，覆盖进程崩溃自愈、超长同步锁过期防御、R3 中断重跑等验收重点。
