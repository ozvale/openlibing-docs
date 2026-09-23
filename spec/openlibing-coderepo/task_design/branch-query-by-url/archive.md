# Archive：【黄蓝协同】黄蓝协同新增映射实时校验及失败信息展示功能（openlibing-coderepo 侧）

- FE 需求名称：【黄蓝协同】黄蓝协同新增映射实时校验及失败信息展示功能
- 业务 Issue：openlibing/openlibing-coderepo#140（https://gitcode.com/openlibing/openlibing-coderepo/issues/140）
- 业务 PR：!196（https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/196）
  - 分支：`sync-repo` → `release_20260923_iter2`
  - 合入内容 head：`c907f89d`（permalink：https://gitcode.com/openlibing/openlibing-coderepo/blob/c907f89dd600ed8eb76026b21c0449ec470935b4 ）
  - CI：pre-commit 门禁通过（`ci_state_passed=true`）
- 归档时间：2026-09-22

## 交付内容

1. **按仓库地址查询分支接口** `GET /project-repo/query-repo-branch-by-url`：网关层鉴权，repoUrl 逐字符精确匹配，实时返回分支列表（name + isDefault）；未录入 / 平台 404 / token 失效 / 无分支 / 编码态与格式非法入参分别返回明确提示；令牌不出服务端。
2. **webhook 评论事件订阅下线**：新录入仓库创建 webhook 时 gitee/gitcode `note_events=false`、github events 不含 `issue_comment`；push / merge_requests 订阅不变；存量 webhook 不受影响；`PrSyncCommentEventHandler` 一并删除。
3. **PR 源分支更新 commit 粒度去重**：去重 key 追加 `last_commit.id`，每次 push（不同 commit）均重新触发流水线；消息 `req_type=open` 不变，黄区消费端透明；gitee 平台因载荷无可靠 commit 字段保持原 PR 粒度去重（TTL 窗口内一次）。

## 关键决策记录

- 分支查询接口放 `/project-repo` 网关鉴权路径而非 `/internal`：内部命名空间被 `openlibing-common` 的 `InternalAuthFilter`（`X-Internal-Token`）拦截，使用方要求由网关鉴权。
- token 信息永不通过接口返回；失败提示区分平台 404 与令牌失效（解析平台客户端 IOException message 中的状态码）。
- 源分支更新去重升级为 commit 粒度是为满足「每次 push 重跑」语义，同时保留对同一条事件重复投递的幂等防护；消息协议不变是黄区兼容的前提。

## 可复用经验（已同步 ai_memory.md）

- `InternalAuthFilter` 的路径匹配是 URI **contains** 语义，前缀配置覆盖面需按此理解；绕过方式是路径不含命中前缀（由网关鉴权），而非关闭开关。
- mvn-spotless 钩子是 `spotless:apply`（会修改文件），pre-commit 判定「files were modified」即失败：本地提交前应先跑 `mvn spotless:apply`（离线可用本地缓存依赖版本执行，格式化规则与 CI 一致）。
- gitcode-cli（npm `gitcode-cli`，bin 名 `gitcode-cli`/`gc`，注意 `gc` 与 PowerShell 内置别名冲突）：`pr create` 支持 `--body-file`/`--label`，无 `pr edit` 子命令；中文标题需 UTF-8 bytes 防护片段。

## 遗留事项

- 本机缺少私仓凭据（`openlibing_mvn_repo_username/password`），本地无法跑 mvn 类 pre-commit 钩子与依赖 1.0.20.6 的构建；CI 环境不受影响。
- `.claude/settings.local.json` 存有 gitcode token 明文（未入仓库），建议轮换。
