# upload-sarif-action 遗留安全 issue 定性分析（2026-11-03）

> 分析基准：`upstream/main`（HEAD: 22fc664），逐条对照源码核实，不按 issue 标题定性。
> 上一版：`security-issues-analysis-20261012.md`（#10~#20 批次 + 2026-10-29 复核）。
> 本批覆盖 main 上仍 open 的 8 条安全 issue：#11 #24 #25 #26 #27 #28 #29 #31。
> 用户裁决（2026-11-03）：#28 直接删除产物；#26 不做限制；#24 暂不处理；#29 按观察项。

## 汇总

| 分类                           | Issue           | 处理建议                                                                                     |
| ------------------------------ | --------------- | -------------------------------------------------------------------------------------------- |
| 真问题·等价加固（本批实施）    | #27 #31 #28     | 临时文件治理 / 日志清洗 / 删除入库 zip，行为等价，合并为 PR-A                                |
| 非问题（用户决策，2026-11-03） | #26             | 不做扩展名/大小限制，理由见第二节                                                            |
| 非问题/观察项（2026-11-03）    | #29             | 输入源为 CI 配置（半可信），跨插件均无 region 校验，维持现状                                 |
| 暂缓（用户决策，2026-11-03）   | #24             | pwn request 结构问题暂不处理，结论与 #17 的冲突留待后续对齐                                  |
| 暂缓（平台/后端依赖）          | #11 #25（残留） | 对象 ACL 维持 `public-read`，待后端支持带凭证/签名 URL 下载后统一实施（2026-10-29 决策延续） |

---

## 一、等价加固（PR-A：#27 + #31 + #28）

### #27 转换产物临时目录不清理【中】

- **位置**：`index.js:802-804`（`convertOutDir = os.tmpdir()/sarif-convert-output`，仅 `mkdirSync`）、`816-817`、`834`
- **核实**：真实。`index.js` 无任何 `fs.rmSync` / `unlinkSync`，转换产物在 job 结束后长期残留于 runner 磁盘，含源码片段（与 #11 SENS-14 同源风险）。
- **整改**：流程结束（含失败路径）统一清理本次使用的转换产物目录。产物需先供后续 `putObject` 上传，清理点放在上传完成之后（`finally` / `process.on('exit')` 兜底），只清理 `sarif-convert-output` 目录，不触碰用户 `report_file` / `sarif_file` 原始文件。
- **等价性**：上传时序与产物内容不变，仅缩短磁盘残留时间窗。属硬规则 1「临时文件治理」。
- **验证**：转换 + 上传成功路径目录被清理；转换失败路径同样清理；原有单测全过；`npm run package` 重建 dist。

### #31 日志注入（外部可控内容直接拼日志行）【中】

- **位置**：
  - `index.js:142-144` `sanitizePath` 仅替换 IP，不处理 `\r\n` 与控制字符
  - `index.js:303` `warnings` 含报告原文片段（`src/parser/CodeCheckReportParser.js:244` 拼入 `JSON.stringify(item).slice(0,200)`）
  - `index.js:362` 来自输入 `codeCheck_task_url`；`684/693/698` 路径来自输入
  - `src/api/CodeArtsCheckApi.js:180/183` 错误消息内嵌 `resp.body.slice(0,200/300)`，经 `index.js:1031` 输出
- **核实**：真实。上述内容可由 PR 代码 / 输入参数 / 服务端响应影响，含 `\r\n` 时可在 CI 日志伪造独立行。
- **整改**：新增 `sanitizeLogValue()`（剔除 `\r`、`\n`、`\u0000-\u0008`、`\u000b`、`\u000c`、`\u000e-\u001f`、`\u007f`），接入**全部**含外部内容的日志点（`sanitizePath` 保留 IP 脱敏并串联调用），不只改扫描命中处。
- **等价性**：仅日志渲染变化，不改变上传内容、参数、退出码；正常单行日志清洗后与原文一致。属硬规则 1「日志脱敏」。
- **验证**：构造含 `\r\n` 的 `sarif_file` 名 / `codeCheck_task_url` / 报告 warnings，确认日志单行；原有单测全过；dist 重建。

### #28 zip 打包产物入库【低】

- **位置**：`openlibing-upload-sarif.zip`（`git ls-tree upstream/main` 仍跟踪）；`.gitignore` 已有 `*.zip` 但对已跟踪文件无效
- **核实**：真实。zip 仅由 `zip.js` 生成，源码不消费。
- **整改（2026-11-03 用户决策：直接删除）**：`git rm openlibing-upload-sarif.zip`，索引与工作区一并移除；`.gitignore` 已覆盖，无需新增规则。
- **等价性**：运行时走 `dist/index.js`，不读取该 zip；发版需要 zip 时由 `npm run package` 重新生成。

---

## 二、非问题 / 观察项（用户决策 + 跨插件对照）

### #26 上传约束缺失（不做限制，2026-11-03 用户决策）

- **位置**：`index.js:664-701` `collectSarifFiles`（目录扫描过滤 `.sarif`；显式文件路径不校验扩展名）；`index.js:960` `putObject` 无大小上限
- **跨插件对照**（本次核实）：

| 插件                                | 上传内容来源                                                           | 扩展名校验                                | 大小上限 |
| ----------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------- | -------- |
| upload-ut-action                    | 内部生成 JSON（`src/obs/ObsUploader.js:112-142`）                      | 无（内容自生成，无外部文件）              | 无       |
| security-compilation-options-action | 不自建 OBS client，workflow 中由 OBS 上传步骤处理（endpoint 显式配置） | 无                                        | 无       |
| upload-sarif-action                 | 用户 `sarif_file` / `report_file`                                      | 目录扫描隐式限定 `.sarif`，显式路径不校验 | 无       |

- **结论**：显式路径允许任意命名文件属易用性取舍（用户可能用 `.json`、`.log` 等自定义命名的报告），其他插件同样不做扩展名/大小限制；且上传目标、Bucket 由 workflow 配置控制，非外部用户可任意指定。按非问题记录，本轮不做限制。

### #29 SSRF（region 拼接 host，观察项，2026-11-03 用户决策）

- **位置**：`index.js:146-161` `resolveRegion()` → `src/api/CodeArtsCheckApi.js:139` `this.host = ${CODEARTS_HOST_PREFIX}.${region}.${CODEARTS_API_DOMAIN}`
- **跨插件对照**（本次核实）：
  - upload-ut-action：OBS `server = https://obs.${region}.myhuaweicloud.com`，region 来自 `configure({})`（OIDC SDK 返回值，**非用户输入**），未做校验
  - security-compilation-options-action：不自建 OBS client，endpoint 由 workflow 显式配置，插件侧无 region 拼接
  - upload-sarif-action：OBS region 同样来自 `configure({})`；SSRF 命中点是 **CodeArts Check API** 的 region（input / 环境变量 / `codeCheck_task_url`）
- **结论**：issue 原文即注明"输入源受 workflow 配置控制，未发现外部用户可直接控制的路径，按观察项记录"。三个插件均无 region 校验，region 非法时请求会因 DNS/证书失败而终止，无数据外带路径。**维持现状，不改代码**；若后续要求落实规则 23.1，可加 `^[a-z0-9][a-z0-9-]*$` 格式校验（合法 region 全通过，属新增输入拒绝，需单独评审）。

### #24 workflow pwn request（暂不处理，2026-11-03 用户决策）

- **位置**：`.gitcode/workflows/pre-commit.yml:9`（`pull_request_target`）、`:46-49`（检出 PR merge commit + `allow-unsafe-pr-checkout: true`）、`:58`（`npm install`）、`:32/:85`（`ROBOT_TOKEN`）
- **现状**：与 2026-10-13 对 #17 的"非问题"结论存在冲突（当时理由含"该工作流不存在 `allow-unsafe-pr-checkout`"，与当前代码不符）。
- **结论**：本轮暂不处理，issue 保持 open。后续若重启，候选方案：A 移除 `allow-unsafe-pr-checkout`；B 拆分 workflow（PR 仅打标、检查由 push 触发）；C 执行 PR 代码的 job 与 `ROBOT_TOKEN` 彻底隔离。

---

## 三、暂缓（平台/后端依赖）

| Issue | 内容                                              | 状态                                                                                                                                                               |
| ----- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| #11   | SENS-14：tmp 残留 + public-read 上传 + 工作区回写 | 部分整改：#27 本轮解决 tmp 残留，snippet 掩码此前已完成；ACL 维持 `index.js:959-964` `public-read`（后端 SarifParseServiceImpl 匿名 GET 依赖），**暂缓待后端联动** |
| #25   | 任意文件读取 → public-read 源码片段泄露链         | 前两跳已斩断（#16/#18 路径边界 + realpath 校验、#12 snippet 掩码）；第三跳 = ACL，同 #11 暂缓                                                                      |

---

## 四、PR 计划

| 批次 | 覆盖 issue      | 性质                                               | 状态     |
| ---- | --------------- | -------------------------------------------------- | -------- |
| PR-A | #27 + #31 + #28 | 等价加固（临时文件治理 / 日志脱敏 / 删除入库产物） | 本批实施 |
| —    | #26             | 非问题                                             | 不做     |
| —    | #29             | 观察项                                             | 不做     |
| —    | #24             | 暂缓                                               | 不做     |

实现后同步合并到 `fix-security-remediation` 分支供统一自测；dist 由 `npm run package` 重建。

---

## 五、不纳入本批

| Issue | 原因                                                  |
| ----- | ----------------------------------------------------- |
| #21   | 功能需求（接入接口兼容性扫描 workflow），非安全 issue |
| #1    | 缺陷单（pre-commit workflow 报错），非安全 issue      |
