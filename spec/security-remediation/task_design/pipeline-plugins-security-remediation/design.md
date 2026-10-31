# design: 流水线插件安全整改技术方案

- **关联 proposal**: [proposal.md](./proposal.md)
- **日期**: 2026-10-31
- **定位**: 说明定性模型、分类型整改手法、逐仓落地方式、工程规范与验证设计；完整论述见 `e:\work\huawei\fork\设计文档.md`

## 1. 设计原则

1. **场景优先于扫描结论**：先核实变量来源、调用方、部署形态，再判断风险是否成立；扫描器只提供线索。
2. **等价变换优先**：优先选择「改变执行方式、不改变对外行为」的改法。
3. **拿不准就归「须评审」**：归错类的代价远高于多问一轮。
4. **全调用点收口**：鉴权通道、凭证传递类改动必须一次覆盖全部调用点，禁止双通道并存。
5. **产物与源码同源**：`dist/` 只由打包生成，禁止在产物上打补丁。
6. **一切结论留痕**：定性理由、决策日期、代码位置、验证证据写入文档。

## 2. 四类定性模型

| 分类 | 判定标准 | 后续动作 |
|---|---|---|
| 真问题 · 等价加固 | 落在白名单内：日志脱敏、注入式参数化且默认值不变、白名单登记、临时文件治理、新增可选参数且缺省保持原行为、依赖固定、凭证传递加固 | 直接实施，附影响声明 |
| 真问题 · 需验证 | 方案明确但结论依赖运行环境（如 `ssl_verify: true` 在自签 CA / TLS 代理下是否可用） | 统一测试分支实测后定案 |
| 真问题 · 须评审 | 触及七类行为变更：输出契约、默认值/默认行为、鉴权通道、失败语义、新增输入拒绝、资源限制阈值、数据处理链路 | 先出《业务逻辑影响评估》，批准后编码 |
| 非问题 | 业务设计固有形态、易用性取舍、扫描器噪音、受信配置方输入、平台/后端依赖、命中代码不可达 | 用户逐条确认后归档，新扫描按模式去重 |

补充口径：

- **平台 / 后端依赖不单列第五类**：归入「非问题 + 暂缓，待联动后统一实施」。
- **「命中代码已消失」视为已解决**：整段链路重构导致命中代码不复存在时，随迁移关闭。

## 3. 双知识库

| 知识库 | 回答的问题 | 组织方式 | 维护时机 |
|---|---|---|---|
| `issue_docs/security-remediation-playbook.md` | 这类问题**怎么改** | 按问题类型组织：识别特征、风险本质、按项目形态分派的方案、等价性约束、验证方式、实施案例 | 方案经确认或实施验证后回写 |
| `issue_docs/security-non-issue-catalog.md` | 这类问题**为什么不用改** | 按模式组织，只收录跨仓可复用的判定 | 用户确认非问题后回写 |

与具体仓业务绑定的判定（桶 ACL 策略、静态 AK/SK 取舍）留在各仓定性文档，不进通用库，避免错误套用。

## 4. 流程与两道闸门

```text
ENTRY  指定仓库 + 分支，读取全部 open 安全 issue，比对历史定性文档 / 双知识库去重
  ▼
Phase 1  批量定性（代码定位 → 核对运行场景 → 比对非问题库 → 四类定性 → 落盘定性文档）
  ▼ 闸门 ①：定性结论由用户逐条确认（AI 只收集证据，不决定真伪）
Phase 2  合并整改（同根因/同代码段合并 PR → 最小等价改动 → dist 重建 → 本地回归）
  ▼
Phase 3  交付（一 issue 组一 PR → 业务逻辑影响声明 → ai-assisted 标签 → 同步 fix-security-remediation）
  ▼ 闸门 ②：用户自测明确确认后，才允许合入默认分支
Phase 4  闭环（合入 → 检视意见处置 → 核实关闭 issue → 方案入 playbook / 非问题入 catalog）
```

## 5. 分类型整改方案

### 5.1 公网地址 / 域名硬编码

1. 噪音剥离：lockfile、标准格式声明 URL、三方库文案、公开协议端点直接排除。
2. 功能性地址收敛到 `src/config/endpoints.js`，代码 `require` 读取，保留同名环境变量覆盖。
3. 默认值与原硬编码**逐字节一致**。

**注意**：ncc 打包剥离注释，`gitleaks:allow` 只对 src 生效；dist 中配置值仍以字符串形态存在，需在定性文档预置说明，避免下轮重复开单。

### 5.2 凭证传递与留存

统一原则：**令牌不进命令行参数、不进 URL、不落盘、不进日志**。

| 子形态 | 原状 | 设计 | 落地 |
|---|---|---|---|
| 令牌拼进 git remote URL | `remote set-url` 写进 `.git/config` 并进 argv | `GIT_ASKPASS` 临时脚本（0o700），`finally` 即时删除 | pre-commit #22/#35/#36 |
| token 走 URL 查询串 | `?access_token=` 拼接 | 统一 `Authorization: Bearer`，删除 query 拼接 | pr-label #4/#9、pr-sync #6/#17 |
| 凭证经子进程 argv 传递 | `obsutil -i=AK -k=SK -t=Token` | 迁移 `esdk-obs-nodejs`，凭证仅在内存构造；删除 obsutil 在线下载链路 | code-metrics #36/#46/#55/#59/#58/#69/#63 |
| npm token 落盘 | `echo ... > ~/.npmrc` 无权限控制 | `(umask 077 && ...)` 子 shell + `if: always()` 清理 | oidc-sdk #7/#15 |
| 日志回显凭证 | 请求/响应体、异常消息整包打印 | 统一 `redact()` / `maskBody()`，URL query 值掩码、保留 method/host/path | pr-label #4、pr-sync #5/#7/#11/#16/#21/#22、oidc-sdk #10/#17/#21 |

验证：实跑完整链路（打标/清标、发布、上传）确认 2xx 且无 401；日志断言不含明文令牌。

### 5.3 命令执行与参数拼接

1. 能用 Node 原生 API 消除子进程的直接消除（`find` → `fs.readdirSync` BFS）。
2. 必须调用外部程序的改 `execFileSync(cmd, argsArray)`，零 shell 解析。
3. Python `-m` 模块遮蔽：执行 cwd 切到 `mkdtemp` 空目录，`finally` 清理。

等价性约束：查找范围、首个命中语义、日志输出、兜底行为、退出码均不变；`find -maxdepth N` 需对齐「距根 N 跳」语义。

### 5.4 路径与输入边界

1. 定义合法根集合（`source_path` + workspace 兜底），解析结果必须满足 `resolved === root || resolved.startsWith(root + path.sep)`。
2. `file://`、绝对路径、相对路径三条分支统一 `path.resolve` 归一化后校验。
3. **realpath 二次校验**：词法前缀挡不住「路径在界内、目标在界外」的符号链接，统一经 `realpathSync` + 二次边界判断终裁。
4. 越界降级为「跳过 / snippet 缺失」，不中断主流程。

属「新增输入拒绝」，须评审；评审时须说明「合法越界场景是否存在」。

### 5.5 日志与输出卫生

1. 新增统一 `sanitize()` / `sanitizeProcessOutput()`，折叠 `\r\n\t` 与控制字符，接入全部外部字符串输出点（含 `ATOMGIT_OUTPUT` 输出行）。
2. 路径类日志：debug 级删除，info 级改 `path.basename()` 或相对 `sourceDir`。
3. 失败路径不打整段响应体，只保留 `HTTP ${status}`；错误明细随返回值进上报 payload。
4. 凭证类规则命中的 snippet / contextRegion / `message.text` 统一掩码（保留前 2 后 2）。

等价性约束：日志级别、出现时机、异常类型、消息前缀不变；上报字段语义不变。

### 5.6 临时文件治理

| 子问题 | 设计 |
|---|---|
| 残留 | `process.on('exit')` 兜底 + try/finally，覆盖正常结束与 `process.exit(1)` |
| 权限过宽 | `writeFileSync(..., { mode: 0o600 })`；`.npmrc` 用 `umask 077` |
| 文件名可预测 | 追加 `crypto.randomUUID()`，保留时间戳便于排查 |
| 用途/生命周期 | 不改变，仅收紧权限与可预测性 |

### 5.7 第三方依赖与不安全默认值

| 子形态 | 设计 | 落地 |
|---|---|---|
| SDK 默认关闭 TLS 校验 | 显式传 SDK 原生键名 `ssl_verify: true`；自签 CA 用 `NODE_EXTRA_CA_CERTS` 兜底，禁止回退关闭 | upload-ut #8/#14/#24、upload-sarif #19/#30、oidc-sdk #20 |
| 旧版 HTTP 依赖漏洞 | 优先零依赖：删除 `undici`，用 Node 内置 `http`/`https` 实现最小 fetch 兼容层（超时对齐 300s）；Node 18+ 仍走内置 fetch | oidc-sdk #19 |
| 供应链版本漂移 | `pre-commit==X.Y.Z` 精确固定，不做 `--require-hashes`；删除 `GONOSUMDB=*` | pre-commit #23/#31 |
| 内联第三方代码命中 | 本仓源码 → 回源码改；`@actions/*` 传递依赖内联 → 非问题归档 | 各 Action 仓 dist 命中 |

**分类注意**：`ssl_verify: true` 属「失败语义变化（fail-open → fail-closed）」，须评审；`undici` 升大版本连带要求 Node ≥ 18，能用零依赖回退时优先回退。

### 5.8 构建产物治理

- `dist/` 是产物不是源码：只改 `index.js` / `src/**`，执行 `npm run package` / `npm run build` 重新生成，源码与产物同提交。
- `git rm --cached` 移除版本库中的构建产物，`.gitignore` 修正为 `*.zip`。
- 多个 PR 同改 `dist` 时按目标分支重新构建，不解二进制冲突。

### 5.9 门禁形态与供应链类（非问题为主）

| 模式 | 判定要点 | 处置 |
|---|---|---|
| `pull_request_target` + 检出并执行 PR 代码 | 门禁必须执行 PR 代码；凭证 job 与执行 job 隔离；`allow-unsafe-pr-checkout` 为显式开关 | 核实缓解因素后归档 |
| 自有配置中的可变 tag | 引用对象为一方插件或平台内置 Action | 归档，可选低优先级固化 SHA |
| `id-token: write` | OIDC 联邦换临时凭证的必需权限 | 归档 |
| workflow 级 permissions 偏宽 / 长期 PAT | 插件侧已隔离凭证，剩余属平台侧配置优化 | 登记平台侧 |

## 6. 逐仓落地

| 仓库 | 改动要点 | 遗留 |
|---|---|---|
| upload-sarif-action | 端点集中配置；凭证 snippet 掩码（含 `message.text`）；URI 边界 + realpath 终裁；`execFileSync find`；`sslVerify: obsSslCaFile \|\| true` | #27 tmp 不清理、#31 日志注入、#28 zip 入库（等价加固待提 PR）；#26 扩展名/大小校验、#29 region 校验（须评审）；#11/#25 ACL 暂缓 |
| upload-ut-action | 端点多环境变量注入 + `obs_acl` 可选参数；`find` → `fs` 递归；临时文件名随机后缀；runId 清洗；`ssl_verify: true` | #1/#15/#18/#21 ACL 暂缓；#9/#10 判定当前不可利用 |
| pre-commit-action | 镜像与环境变量注入；`gc_token` → `GIT_ASKPASS`；临时报告目录清理；`GONOSUMDB` 删除；版本固定 | #48 日志注入、#43 报告目录跨任务残留 |
| pr-label-action | 端点集中配置；Bearer 收口；全链路脱敏；标签名 `encodeURIComponent` + 危险字符拒绝 | #8 标签并发竞态（逻辑 bug，暂缓） |
| pr-sync-action | token 改 Bearer；日志脱敏；域名环境变量注入 | #11/#16/#21/#22 补 AppCode 响应/错误脱敏；#9/#12/#13/#18 须评审；#10/#20 暂缓 |
| security-compilation-options-action | 日志单通道 + 路径 basename 化；sanitize 覆盖 `ATOMGIT_OUTPUT`；pip 临时空目录；gitUrl 任意 scheme 去 userinfo；symlink 越界拒绝；win32 死分支删除 | #21 端到端签名（合规需求，延期后端联调） |
| code-metrics-action | gitUrl 正则泛化；路径日志脱敏；sanitize；scc/pip 数组化 + 临时 cwd；临时文件 0600 + 随机名；死 fallback 删除；obsutil → SDK 迁移 | 检视意见按「非必要不改」口径回复；lizard 模块遮蔽需评估 |
| huaweicloud-oidc-sdk-nodejs | npmrc 权限 + 清理；日志脱敏（含 audience 单行化）；`x-sdk-date` 大小写兼容；OBS TLS 校验；`undici` 零依赖回退；region / STS 参数白名单校验 | #11 账号 ID（建议非问题归档）；profile / dist 同步类检视意见 |

## 7. 工程规范

- 分支：业务仓 `fix-<description>`（Windows 禁 `/`）；docs 仓 `spec-<repo>-<change>`。统一自测分支 `fix-security-remediation`。
- PR 拆分：默认一 issue 一 PR；同根因 / 同文件同函数 / 共用大体积产物（ncc 单文件 dist）合并。
- commit：`fix(security): <summary>`，body 关联 `Refs #n` / `Fixes #n`；每轮交付一 commit，不 amend。
- 标签：PR 创建后补 `ai-assisted`；`ci-pipeline-passed` 与 `lgtm` 只能由 openLibingCI 添加（评论 `/pre-commit` 触发）。
- 中文 PR 描述必须 `--body-file` + 显式 UTF-8 写盘。
- 每轮交付必须给出影响声明：「本改动未触及业务逻辑」或逐条列出触及点并分类（等价加固 / 契约变化 / 行为变化）。

## 8. 验证设计

| 层级 | 内容 | 适用 |
|---|---|---|
| L1 单测与边界用例 | 越界路径、越界 symlink、CRLF 注入、凭证 URL、大小写 header、fallback 分支 | 全部等价加固项 |
| L2 产物一致性 | `dist` 重建后 diff 只含预期改动；lock 依赖条目核对；源码与产物 grep 交叉验证 | 所有 Action / SDK 仓 |
| L3 环境实测 | 统一测试分支联跑上传/打标/门禁链路；自签 CA 场景验证 TLS | 「需验证」项 |

### 已固化的回归缺口对策

| 缺口 | 根因 | 对策 |
|---|---|---|
| `sslVerify` vs `ssl_verify` | 第三方 SDK 只认原生键名，驼峰被静默忽略 | 单测断言构造参数键名；回读 SDK 源码确认 |
| `obsAcl` 未声明 | 解构了从未读取的 input | 新增 input 必须有读取点 + 默认值 + 白名单校验 |
| `putObject` 写死 ACL | 形参透传遗漏 | 参数链路端到端断言（input → 调用 → SDK 参数） |
| 词法边界被 symlink 绕过 | 前缀校验只看字符串 | 全部解析分支统一 `realpathSync` 二次校验 |
| dist 未重建 | 产物与源码不同步 | 交付自检强制「改源码 → 打包 → diff → 同提交」 |
| dist 构建时依赖外置 | 打包环境未装依赖，ncc 外置为运行期 require | 构建前 `npm ci`；产物不得出现运行期外部 require |
| 基线混淆 | 把在途分支的修复记为 master 已修复 | 双基线核实（交付态 + 在途态） |
| 半整改 / 描述夸大 | 只改了一个调用点 | 全调用点清点表 + 复检 diff 逐条比对 PR 描述 |

## 9. 风险与回滚

| 风险 | 影响 | 缓解 |
|---|---|---|
| 等价加固实际改变行为 | 下游流水线失败 | 默认值逐字节比对；统一测试分支联测；保留原路径兜底 |
| TLS 校验开启导致自签 CA 环境失败 | 上传中断 | 提供 `obs_ssl_ca_file` / `NODE_EXTRA_CA_CERTS` 注入企业根证书，禁止回退关闭 |
| 掩码导致前端高亮退化 | 内容匹配改为按行号定位 | 安全优先的预期取舍，评审与 PR 中明示 |
| 后端匿名下载依赖 public-read | ACL 改 private 后下载失败 | 维持 `public-read`，标「暂缓」待后端支持带凭证下载 |
| 构建产物冲突 | PR 无法合并 | 按目标分支重新构建，不手工解冲突 |
| 扫描器重复开单 | 同结论反复处理 | 定性文档 + 非问题库去重，标注决策日期 |

**回滚**：一 issue（组）一 PR/分支，可独立 revert；回退时只回退目标 issue 的改动点；回退后重建产物、新 commit（不 amend）、双分支同步、定性文档迁移到「暂缓回退」。
