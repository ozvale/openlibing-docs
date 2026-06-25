# resolve-outdated-comments — 实现任务

## 进度: 8/8 complete

### Phase 3 实现任务

- [x] Task 1: 在 `MergeRequestEventHandler.java` 新增 import
  - import `HashSet`、`Set`（用于 discussion_id 去重）

- [x] Task 2: 新增 `fetchPrDiffComments(PrInfo prInfo)` 方法
  - 分页拉取，URL 含 `page`、`per_page=100`、`comment_type=diff_comment`、**`view=all`**
  - 仅支持 gitcode/gitee，其他平台返回空列表
  - 返回数量 < per_page 时停止翻页

- [x] Task 3: 新增 `resolveExpiredComments(PrInfo prInfo)` 与 `resolveSingleDiscussion` 方法
  - 主逻辑：拉取评论 → 过滤（`is_outdated==true`）→ 按 `discussion_id` 去重收集 → 调用 PUT resolve
  - `is_outdated` 字段通过 `comment.getBooleanValue("is_outdated")` 读取
  - PUT URL: `/v5/repos/{owner}/{repo}/pulls/{prNumber}/comments/{discussionId}`，body `{"resolved": true}`
  - 异常仅打印日志，不抛出

- [x] Task 4: 在 `handle` 方法中接入调用
  - 在 `postSuppressionComments` 之后，若 `"UPDATE".equals(prInfo.eventType)` 调用 `resolveExpiredComments(prInfo)`
  - 调整控制流：UPDATE 事件无论 scanResults 是否为空都要触发 resolve（改为 if/else 而非 early return）

### Phase 3 测试任务

- [x] Task 5: 补充 `MergeRequestEventHandlerTest` 测试用例
  - 测试 1: UPDATE 事件 + 过期评论（`is_outdated=true`）→ sendPut 被调用 1 次
  - 测试 2: 未过期评论（`is_outdated=false`）→ sendPut 不被调用
  - 测试 3: CREATE 事件 → 不触发 resolve
  - 测试 4: 评论列表为空 → 不触发 resolve
  - 测试 5: fetchPrDiffComments URL 包含 `view=all` 与 `comment_type=diff_comment`

### 验证

- [x] `mvn compile` 编译通过
- [x] `mvn test -Dtest=MergeRequestEventHandlerTest` 全部测试通过（18/18）
- [x] 自检清单逐条确认

### 生成前约束清单

- [x] 只修改 `MergeRequestEventHandler.java` 和对应测试
- [x] 遵循现有命名/日志/错误处理风格（LOGGER.info/warn/error）
- [x] 不引入无关重构（保持 master 现有 getAccessToken 逻辑）
- [x] 无硬编码凭证（token 通过现有 getAccessToken 获取）
- [x] 行为变化有匹配测试
- [x] 异常不阻塞主流程（try-catch + 日志）
- [x] 不带 spec 文件进入业务仓 PR
- [x] 不引入新依赖（移除了 ProjectCommonAccountInfoMapper 依赖）
