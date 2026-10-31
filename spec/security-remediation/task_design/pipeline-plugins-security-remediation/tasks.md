# tasks: 流水线插件安全整改实施清单

- **关联**: [proposal.md](./proposal.md) / [design.md](./design.md)
- **日期**: 2026-10-31

## Phase 0 准备

- [x] 确定目标仓集合（8 仓）与流程模式（Full）
- [x] 建立双知识库：`issue_docs/security-remediation-playbook.md`、`issue_docs/security-non-issue-catalog.md`
- [x] 固化整改 skill：`.agents/skills/gitcode-security-remediation/`（四阶段 + 六条硬规则 + 暂缓回退机制）

## Phase 1 批量定性（闸门 ①：用户逐条确认）

- [x] upload-sarif-action：#10 ~ #31 定性，`issue_docs/upload-sarif-action/security-issues-analysis-20261012.md`（含 2026-10-29 现状复核）
- [x] upload-ut-action：#1 ~ #25 定性，`issue_docs/upload-ut-action/security-issues-analysis-20261020.md`
- [x] pre-commit-action：#20 ~ #37 定性，`issue_docs/pre-commit-action/security-issues-analysis-20261012.md`
- [x] pr-label-action：#3 ~ #9 定性，`issue_docs/pr-label-action/security-issues-analysis-20261012.md`
- [x] pr-sync-action：#1 ~ #22 定性（双基线复检），`issue_docs/pr-sync-action/security-issues-analysis-20261020.md`
- [x] security-compilation-options-action：#17 ~ #43 定性，`issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
- [x] code-metrics-action：30 条定性（PR A-D 分组），`issue_docs/code-metrics-action/security-issues-analysis-20261027.md`
- [x] huaweicloud-oidc-sdk-nodejs：#5 ~ #21 定性（双基线核实），`issue_docs/huaweicloud-oidc-sdk-nodejs/security-issues-analysis-20261026.md`
- [x] 跨仓重复根因比对，非问题模式回写 non-issue-catalog

## Phase 2 合并整改

### upload-sarif-action

- [x] #10 端点集中配置（`src/config/endpoints.js`，5 项端点，默认值逐字一致）
- [x] #12/#31 凭证 snippet 与 `message.text` 掩码（保留前 2 后 2）
- [x] #16/#18 SARIF uri 边界 + `realpathSync` 二次校验
- [x] #20 `find` → `execFileSync` 数组传参
- [x] #19/#30 OBS TLS：`sslVerify: obsSslCaFile || true`
- [ ] #27 临时目录清理（等价加固，待提 PR）
- [ ] #31 日志注入清洗（等价加固，待提 PR）
- [ ] #28 zip 构建产物出库（等价加固，待提 PR）
- [ ] #26 扩展名/大小校验、#29 region 校验（须评审，先出影响评估）
- [ ] #11/#25 对象 ACL 改 private（暂缓，待后端带凭证下载）

### upload-ut-action

- [x] #2 端点多环境变量注入 + `obs_acl` 可选参数（缺省保持原行为）
- [x] #16/#20 `find` → `fs.readdirSync` 递归
- [x] #5 临时文件名加随机后缀
- [x] runId 清洗
- [x] #8/#14/#24 `ssl_verify: true`（原生键名）
- [x] 回归缺口修复（commit `aafeebd`：obsAcl 声明、putObject ACL 透传、ssl_verify 键名）
- [ ] #1/#15/#18/#21 OBS ACL 暂缓

### pre-commit-action

- [x] #22/#35/#36 `gc_token` → `GIT_ASKPASS`（不落盘、不进 argv、0o700、finally 删除）
- [x] #12 镜像与环境变量注入
- [x] #15 临时报告目录清理
- [x] #23 `pre-commit==X.Y.Z` 版本固定
- [x] #31 删除 `GONOSUMDB=*`
- [x] #26 `execCapture` 改 `execFile` 数组传参
- [x] #32 bump-version 正则小 bug、#37 README 补 `gc_token` 说明
- [ ] #48 日志注入清洗
- [ ] #43 报告目录跨任务残留（评估后提 PR）

### pr-label-action

- [x] #3 `GITCODE_API_BASE` 集中配置化（`src/config/endpoints.js`）
- [x] #4 全链路脱敏 + Bearer 头
- [x] #9 删除 `?access_token=`，三接口统一 Bearer（`2dd81f9`）
- [x] #5 标签名 `encodeURIComponent` + 危险字符拒绝（`ddd0116`，已批准新增输入拒绝）
- [ ] #8 标签并发竞态（逻辑 bug，用户决策暂缓）

### pr-sync-action

- [x] #5/#7/#16/#21/#22 请求体与 OIDC 响应脱敏
- [x] #6/#17 Gitee token 改 `Authorization: Bearer`
- [x] #8 `GITCODE_API_URL` / `GITEE_API_URL` 环境变量注入
- [ ] #11/#16/#21/#22 AppCode 响应日志与非 2xx 错误消息补脱敏（半整改收口）
- [ ] #9/#12/#13/#18 四条须评审项（影响评估待出）
- [ ] #10 App Code 静态凭证回退（暂缓，待平台）

### security-compilation-options-action

- [x] #35/#36/#37 日志单通道 + 路径 basename 化 + `sanitize()` 覆盖 `ATOMGIT_OUTPUT`
- [x] #39 pip 安装在 `mkdtemp` 临时空目录执行
- [x] #38 gitUrl 任意 scheme 去 userinfo（已批准）
- [x] #42 Python 扫描 symlink 越界拒绝（已批准）
- [x] #23/#24/#26/#31 掩码收紧、死 fallback 删除等
- [x] #28 win32 死分支删除
- [ ] #21 端到端报告签名（合规需求，延期后端联调）

### code-metrics-action

- [x] gitUrl 正则泛化
- [x] 路径日志脱敏 + `sanitize()`
- [x] scc / pip 调用数组化 + 临时 cwd
- [x] 临时文件 0600 + 随机名
- [x] 死 fallback 删除
- [x] obsutil → `esdk-obs-nodejs` 迁移，删除在线下载链路
- [ ] 检视意见收口（按「非必要不改」口径回复）
- [ ] lizard 模块遮蔽评估

### huaweicloud-oidc-sdk-nodejs

- [x] #7/#15 npmrc `umask 077` + `if: always()` 清理
- [x] #10/#17/#21 日志脱敏（含 audience 单行化）
- [x] #13 `x-sdk-date` 大小写兼容
- [x] #20 OBS TLS 校验
- [x] #19 `undici` 零依赖回退（内置 `http`/`https`，超时 300s）
- [x] region / STS 参数白名单校验
- [ ] #11 账号 ID 是否属敏感信息（建议非问题归档，待裁决）

## Phase 3 交付

- [x] 每批整改提交一次 commit，附业务逻辑影响声明
- [x] 每仓同步 `fix-security-remediation` 统一测试分支
- [x] 创建业务 PR 并关联 issue
- [x] PR 补打 `ai-assisted` 标签
- [x] 中文 PR body 走 `--body-file` + UTF-8

## Phase 4 闭环

- [x] 用户自测确认后合入默认分支
- [x] 非问题项附结论关闭 issue
- [x] 方案回写 `security-remediation-playbook.md`
- [x] 非问题回写 `security-non-issue-catalog.md`
- [x] 生成归档文档 `archive.md`
- [ ] 遗留项清零跟踪（见 archive.md 第 4 节）
- [ ] 平台 / 后端联动事项登记（ACL、runner 隔离、permissions 收敛、端到端签名）
