# gitcode-action插件形式实现sbom扫描任务 测试策略设计说明书

## 1. 基本信息

- **对应task(issueID)链接**: https://gitcode.com/openlibing/sbom-action/issues/1
- **需求名称**: 【openlibing-sbom】gitcode-action插件形式实现sbom扫描任务
- **核心目标**:
  实现代码化插件 `sbom-action`（Node action，单文件 index.js → ncc 打包 dist/index.js），主链路为：入参校验（fail-fast）→ 按 platform/arch 下载 `openlibing/trivy-sbom-tools` release 包并解压 → `trivy fs --format spdx-json --offline-scan` 扫描 target-dir → `addProduct` 注册产品（already exists 容忍）→ `publishSbomFile` 上传（`spdx_2.2_json_sbom`，OIDC callApig 认证：ID Token → STS → APIW V11 签名）→ 双通道输出（`steps.<id>.outputs.task-id` / `sbom-file` + `ATOMGIT_OUTPUT` 中文键概览）。入参定案：attribute 平铺为一级 input；`trivy-version`、`sbom-output` 不再作为入参（工具版本与输出路径由插件内置）；`project_name`（原 product-type）可选，不传时由插件采集 gitUrl 反查社区，多匹配默认取一、可手动指定修正；`env` 默认 prod，支持 prod/test 网关前缀切换；`debug` 默认 false，需区分插件日志与 OIDC SDK 日志并脱敏。上传侧插件自动采集并清洗 gitUrl（`git remote get-url origin`），上报需覆盖 gitcode 与 atomgit 双域名（HTTPS/SSH 两种 remote 形式）。详情链接可下载能力延至下月，本期不纳入测试范围。
- **开发责任人**: 陈洪亮
- **测试责任人**: 赵威

---

## 2. 测试维度确认

- [x] **功能自检测试**

> - **测试重点:** 最小入参端到端扫描与 OIDC 上报、入参校验 fail-fast 与已移除参数不生效、OIDC 权限缺失启动报错与恢复、project_name 自动反查与多社区归属（含 addProduct 上报 gitUrl 覆盖 gitcode/atomgit 双域名与 HTTPS/SSH 形式）、nightly 重跑 already exists 容忍、工具包 platform/arch 适配与内置版本、扫描范围与离线扫描选项、输出双通道与编程取数、env 生产/测试网关切换与数据落点、扫描与上报异常链路容错、debug 日志开关与日志分层。
> - **目的:** 确保插件在 GitCode 流水线中按定案入参稳定完成「扫描 → 注册 → 上传 → 输出」全链路，且归属、幂等、平台兼容与异常处理行为符合需求设计与串讲定案。
> - **触发条件:** 强制执行。

- [ ] **体验测试**
- [ ] **集成测试**
- [x] **安全与隐私测试**

> - **测试重点:** 认证维度（`permissions: id-token: write` 缺失时启动即失败并给出补全指引，恢复后 OIDC 认证成功）、敏感信息防护（debug 日志与全部输出通道无 OIDC ID Token / STS 临时凭证 / 签名串 / Authorization 明文；gitUrl 含 token 时上报前清洗，日志与输出无明文）。
> - **目的:** 确保插件不因调试开关或仓库地址配置导致联邦凭证、访问令牌泄漏，且认证前置条件缺失时快速失败并给出可操作指引。
> - **触发条件:** 强制执行。

- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.最小入参端到端SBOM扫描与OIDC上报验证**:

- 前置条件: sbom-action 插件可用（首个 release TAG 已发布，或引用特性分支构建的 dist 产物）；workflow 已声明 `permissions: id-token: write`；被测代码仓已在 coderepo 登记且归属唯一合法社区，target-dir 存在且含可解析依赖；openlibing-sbom 平台（env=prod）可访问，具备按 taskId 查询任务与制品权限
- 测试步骤:
  1. workflow 仅配置必填入参（attribute 平铺维度、target-dir），不配置 project_name / trivy-version / sbom-output / product-type
  2. 触发工作流，job 日志确认入参校验通过 → 按 platform/arch 下载 trivy 工具包并解压 → 执行 `trivy fs --format spdx-json --offline-scan`
  3. 断言 SBOM 文件在插件内部固定路径生成：文件存在、可解析为 SPDX 2.2 JSON、packages 非空且与 target-dir 依赖一致
  4. 断言 addProduct 请求包含已清洗 gitUrl、反查得到的 projectName 与全量维度，首次注册成功
  5. 断言 publishSbomFile 请求 `sbomContentType=spdx_2.2_json_sbom`，响应 202 且 `success=true`、`taskId` 非空
  6. 平台按 taskId 查询任务：状态推进至解析成功，SBOM 制品内容与步骤 3 文件一致
  7. 读取 `steps.<id>.outputs.task-id` / `steps.<id>.outputs.sbom-file` 与 `ATOMGIT_OUTPUT` 概览，断言与平台任务、实际文件一致
- 预期结果: 全链路一次通过：工具下载成功、扫描生成合法 SPDX 2.2 JSON、addProduct 与 publishSbomFile 均成功；平台任务成功，taskId 与输出一致；全流程无需用户指定 trivy-version 与输出路径

**2.入参校验与fail-fast错误提示验证**:

- 前置条件: action.yml 入参定稿可查（必填项、平铺维度、默认值）；测试仓库含 1 个正常 target-dir、1 个不存在路径、1 个空目录；平台侧可查询是否产生新增产品/任务
- 测试步骤:
  1. 逐一缺省必填项（attribute 平铺维度、target-dir）→ 断言插件启动阶段即失败、错误信息指明缺失项，且未下载工具包、未调用 addProduct/publishSbomFile
  2. target-dir 指向不存在路径 / 空目录 → 断言明确错误提示，不生成空 SBOM 并上报
  3. attribute 平铺维度传入非法值（版本为空、超长字符串、含特殊字符）→ 断言 fail-fast 提示可定位到具体字段
  4. 在 workflow 中传入已移除参数 `trivy-version` / `sbom-output` / `product-type` → 断言工具版本仍为内置值、输出路径仍为内部固定路径、product-type 不参与归属
  5. 不配置选填参数 → 断言 debug=false、env=prod、analyze-all-python=false 默认值在日志/请求中生效
  6. 检查全部错误信息 → 断言不包含 token、AK/SK 等敏感字段
- 预期结果: 非法输入全部在扫描前失败，错误信息可定位到具体入参，无上传副作用；已移除参数不生效；选填默认值符合 action.yml 定义

**3.OIDC权限缺失启动报错与恢复验证**:

- 前置条件: 被测仓库已录入平台，target-dir 可正常扫描，其余入参合法；可修改 workflow 的 permissions 配置
- 测试步骤:
  1. workflow 删除 `permissions: id-token: write`（或改为只读）→ 触发运行
  2. 断言插件在启动阶段（扫描前）即失败，错误信息包含补全 `permissions: id-token: write` 的明确指引
  3. 断言此时未调用 addProduct/publishSbomFile，平台无新增产品/任务
  4. 恢复 `permissions: id-token: write` 后重跑 → 断言可获取 OIDC ID Token，经 STS 换取临时凭证并完成 callApig 签名上传
  5. 断言 job 日志中 OIDC 相关输出无 ID Token / 临时凭证明文
  6. 在非 GitCode Action 环境（本地直接 `node dist/index.js`）执行 → 断言给出 OIDC 不可用的明确提示而非堆栈崩溃
- 预期结果: 权限缺失时快速失败且指引可操作，不产生任何平台副作用；恢复权限后认证链路成功；本地非 Action 环境失败提示明确

**4.project_name自动反查与多社区匹配归属验证**:

- 前置条件: coderepo 侧准备四类仓库：R1 唯一合法社区、R2 属多个合法社区、R3 未登记/无合法社区、R4 已登记但 project_name 非法；各仓库已在 GitCode 检出且可获取真实 origin；另准备同一仓的 `https://gitcode.com/<owner>/<repo>.git` 与 `https://atomgit.com/<owner>/<repo>.git` 及对应 SSH 形式；平台可查询产品所属社区
- 测试步骤:
  1. R1 不传 project_name 运行 → 断言 addProduct 上报的 projectName 为 R1 所属社区，注册成功
  2. R2 不传 project_name 运行 → 断言插件默认选取其中一个合法社区并成功注册（记录实际选取规则），平台归属与所选社区一致
  3. R2 显式传合法 project_name → 断言以用户指定为准
  4. R3 不传 project_name 运行 → 断言明确错误提示（未匹配到合法社区），不写入任何错误归属
  5. R4 显式传不存在的 project_name → 断言明确业务错误码/提示，不静默降级
  6. 构造同一 package_name 已在其他社区注册的场景 → 断言返回明确冲突错误（全局唯一），不产生半条产品数据
  7. 以 gitcode 域名为 origin 运行 → 断言 addProduct 请求中的 gitUrl 与 remote 一致，域名未被硬编码或截断
  8. 以 atomgit 域名为 origin 运行 → 断言 gitUrl 同样完整上报 atomgit 域名，注册成功
  9. 断言步骤 7、8 两种域名反查命中 coderepo 登记的同一社区，归属结果一致
  10. 以 SSH 形式 remote（`git@gitcode.com:<owner>/<repo>.git`、`git@atomgit.com:<owner>/<repo>.git`）运行 → 断言上报 gitUrl 已归一化为可反查地址，反查结果与 HTTPS 形式一致
- 预期结果: 唯一命中时自动归属正确；多匹配时默认取一且结果可见；手动指定优先生效；未命中/非法/同名冲突均给出明确错误，不产生错误归属或脏数据；addProduct 上报的 gitUrl 覆盖 gitcode 与 atomgit 双域名，HTTPS/SSH 两种 remote 形式均可正确采集与归一化，反查结果一致

**5.nightly重跑幂等与already exists容忍验证**:

- 前置条件: TC-ISSUE001-001 已首次运行成功，记录产品名、projectName、首次 taskId；平台可查询产品列表与任务列表
- 测试步骤:
  1. 以与首次运行完全相同的入参再次触发工作流 → 断言 addProduct 返回 already exists 被插件容忍，流程继续执行 publishSbomFile
  2. 断言 publishSbomFile 返回 202 且生成新的 taskId（不复用首次任务）
  3. 平台查询产品列表 → 断言该产品仅一条，字段与首次一致，无重复产品
  4. 连续重跑 2-3 次 → 断言每次均成功、产品数量不增加、任务数量随运行次数增加
  5. 修改代码后重跑（SBOM 内容变化）→ 断言新任务制品内容随之更新，旧任务制品不被覆盖
  6. 两次运行间修改产品维度值 → 记录 addProduct 的更新/忽略行为（以实现为准），断言不产生重复产品或脏数据
- 预期结果: nightly 重跑稳定成功，already exists 不导致失败；产品全局唯一，任务按次新增；制品随代码变化更新

**6.工具包平台架构适配与内置版本验证**:

- 前置条件: 可用的 GitCode 执行机（linux x64 必备；linux arm64 / darwin x64 / darwin arm64 / win32 视资源可用性）；可访问 `https://gitcode.com/openlibing/trivy-sbom-tools/releases/download/{tag}/`，内置 TAG 已与开发确认
- 测试步骤:
  1. 查看 action.yml → 断言不存在 trivy-version、sbom-output 入参；在 workflow 强行传入 trivy-version → 断言工具版本仍为内置值
  2. linux x64 执行机运行 → 断言下载 `sbom-tools-trivy.zip` 并使用 `trivy-linux-amd`，解压至 `os.tmpdir()/sbom-action-trivy`，权限 755，扫描成功
  3. linux arm64 执行机运行 → 断言使用 `trivy-linux-amd-arm`
  4. darwin x64 / arm64（如有 mac runner）→ 断言下载 `sbom-tools-trivy-mac.zip` 并分别使用 `trivy-darwin-amd` / `trivy-darwin-arm`
  5. win32 执行机（如有）→ 断言下载 `sbom-tools-trivy-win.zip` 并使用 `trivy-win.exe`
  6. 同一执行机连续运行两次 → 断言第二次复用已解压工具（日志体现缓存命中，不重复下载）
  7. 模拟工具包地址不可达 / zip 解压失败 → 断言明确错误并终止，不进入扫描与上报
- 预期结果: 各 platform/arch 均选对包与二进制，解压路径与权限符合设计；工具版本完全由插件内置，用户参数无法改变；缓存幂等复用；下载/解压异常时失败明确，不产生误报

**7.扫描范围与离线扫描选项验证**:

- 前置条件: 准备测试工程 P（含多目录依赖、单文件依赖清单、requirements.txt、空目录各一份）；执行机扫描阶段可离线
- 测试步骤:
  1. target-dir 为目录 → 断言递归扫描，SBOM 覆盖目录下全部可解析依赖
  2. target-dir 为单个依赖文件 → 断言仅解析该文件，SBOM 组件不包含同级其他文件
  3. 默认 analyze-all-python=false → 断言不解析 requirements.txt；置为 true → 断言解析并（按实现）pip 下载依赖，SBOM 增加对应组件，记录耗时增量
  4. analyze-dirs 传单个目录、多个目录（逗号分隔）→ 断言对应目录被纳入直接依赖解析，数量与目录数一致
  5. 断言命令包含 `--format spdx-json` 与 `--offline-scan`；断网或禁用漏洞库更新后运行仍能生成 SBOM
  6. 空目录 / 无依赖工程 → 断言生成合法空 SBOM 或给出明确提示（以实现为准记录），不产生非法 JSON
- 预期结果: 各扫描选项行为符合 trivy 参数语义，选项间互不污染；离线扫描可用，生成合法 SPDX 2.2 JSON；空输入不产生非法制品

**8.任务输出双通道与编程取数验证**:

- 前置条件: TC-ISSUE001-001 主链路可运行成功；workflow 中后续 step 可读取 `steps.<id>.outputs.*` 与 `ATOMGIT_OUTPUT`
- 测试步骤:
  1. 运行成功后读取 `steps.<id>.outputs.task-id` → 断言非空且与平台 taskId 完全一致
  2. 读取 `steps.<id>.outputs.sbom-file` → 断言指向实际生成的 SBOM 文件，文件存在且可解析
  3. 读取 ATOMGIT_OUTPUT → 断言包含中文键「任务ID」「SBOM文件」，值与步骤 1/2 一致，按 README 数组下标引用语法可正确取值
  4. 若实现支持 ATOMGIT_STEP_SUMMARY → 断言概览区展示可读信息
  5. 在后续 step 中按 README 示例引用输出 → 断言取值成功
  6. 断言输出内容不含 token、签名等敏感字段
- 预期结果: 编程取数与可读概览双通道均输出，值与平台任务一致；README 引用语法与实际输出匹配；输出无敏感信息

**9.env测试生产网关切换与数据落点验证**:

- 前置条件: prod 与 test 两套网关均可访问（prod `https://apig.openlibing.com:443`，test `https://f209a4ca505e492b96d2dc70f5578641.apic.cn-southwest-2.huaweicloudapis.com`）；两环境 openlibing-sbom 数据均可查询；prod 仅做只读验证（不调用 addProduct/publishSbomFile 写接口），端到端造数仅在 test 环境执行并留存审批记录
- 测试步骤:
  1. 不配置 env（默认 prod）运行，通过日志中的请求地址确认网关落点 → 断言请求发往 apig.openlibing.com；保持只读，不调用 addProduct/publishSbomFile 写接口，断言生产环境无本次新增产品与任务
  2. env=test 运行 → 断言请求发往测试网关，产品与任务落测试环境；端到端造数仅在 test 环境执行，执行前登记测试产品名并留存审批记录
  3. 断言两环境 taskId、产品互相隔离，查询接口不串数据
  4. 传入非法 env 值（如 uat）→ 断言明确报错或按默认 prod 处理（记录实现结论）
  5. 检查日志中的请求地址 → 断言地址与 env 对应，且无凭证明文
  6. 执行后清理 test 环境本次测试数据，复核生产环境无本次新增数据
- 预期结果: env 切换准确，数据落点与网关一致且互相隔离；生产环境仅做只读验证、无新增数据；非法 env 行为明确，不静默发往错误环境

**10.扫描与上报异常链路容错验证**:

- 前置条件: 主链路可运行；可构造异常条件（不可读/损坏文件、非法维度、错误网关、断网）；平台可查询是否产生新增产品/任务
- 测试步骤:
  1. target-dir 含无可读权限文件或损坏文件导致 trivy 扫描失败 → 断言插件以明确错误退出，未调用 addProduct/publishSbomFile
  2. addProduct 返回非 already exists 的失败（维度缺失 / 服务端 5xx）→ 断言终止后续上传，错误信息包含服务端 errorInfo
  3. publishSbomFile 返回 401/403（OIDC 凭证无效或权限不足）→ 断言流水线失败且不输出伪造 taskId
  4. 网关不可达 / 请求超时 → 记录重试策略（次数/间隔，以实现为准），断言最终失败明确、日志可定位
  5. 上传失败后检查执行机 → 断言 SBOM 文件仍保留；输出中无 taskId
  6. 检查流水线状态 → 断言失败步骤呈失败态（非静默成功）
- 预期结果: 任一环节失败均能快速定位，不误报成功、不产生半条产品数据；失败时保留本地 SBOM 产物

**11.debug日志开关与插件SDK日志分层验证**:

- 前置条件: action.yml 中 debug 入参描述已按评论区要求修订；主链路可运行
- 测试步骤:
  1. 查阅 action.yml → 断言 debug 描述已明确「区分插件日志与 OIDC SDK 日志」及默认值
  2. debug=false 运行 → 断言仅输出插件关键流程日志，无 OIDC SDK 调试细节
  3. debug=true 运行 → 断言输出 SDK 调试日志，且与插件日志有可识别区分（前缀/标签/分组）
  4. 传入非法 debug 值（如 yes）→ 断言按 false 处理或明确报错（记录实现结论）
  5. 两种模式均检查日志 → 断言无 ID Token、STS 凭证、签名串明文
- 预期结果: debug 开关行为符合 action.yml 描述，默认关闭；插件日志与 SDK 日志可区分；任一模式下均不泄漏凭证

### 3.2 安全与隐私测试专项

**12.调试日志与输出敏感信息脱敏验证**:

- 前置条件: 主链路可运行，debug=true 可开启 SDK 调试日志；可完整下载 job 日志，并可读取 ATOMGIT_OUTPUT / ATOMGIT_STEP_SUMMARY
- 测试步骤:
  1. debug=true 运行完整链路 → 下载完整 job 日志与概览输出
  2. 检索日志中是否出现 OIDC ID Token、STS 临时凭证、签名串、Authorization 头明文
  3. 检索 ATOMGIT_OUTPUT / ATOMGIT_STEP_SUMMARY 与插件输出 → 断言不含上述凭证
  4. 触发一次失败场景（如上传返回 401）→ 断言异常堆栈与错误信息中同样不打印凭证
  5. 检查脱敏形态 → 断言脱敏后仍可定位问题（保留非敏感上下文）
- 预期结果: 调试日志与所有输出通道均无凭证明文；失败堆栈不泄漏敏感字段；脱敏后保留可诊断信息

**13.gitUrl凭证清洗与上报内容无凭证验证**:

- 前置条件: 测试仓库 remote 可临时修改并在测试后恢复；平台可查询产品信息中的 gitUrl 字段；debug=true 便于观察请求内容（或具备网关抓包条件）
- 测试步骤:
  1. 将 remote 临时设置为含占位令牌的 HTTPS 地址（`https://dummy-user:dummy-token@gitcode.com/org/repo.git`，禁止使用真实令牌）→ 运行插件
  2. 获取 addProduct 上报的 gitUrl（平台产品信息 / 请求日志）→ 断言已去除 userinfo/token，仅保留协议+域名+路径
  3. 检索 job 日志、ATOMGIT_OUTPUT、ATOMGIT_STEP_SUMMARY → 断言无 token 明文
  4. 恢复为常规 HTTPS 地址（无 token）运行 → 断言 gitUrl 不被误改，归属反查正常
  5. 使用 SSH 地址（`git@gitcode.com:org/repo.git`）运行 → 断言按实现规范化后上报（记录转换规则），且可正常反查
  6. 测试结束恢复 remote 配置，检索确认 `.git/config`、shell 历史与 CI 日志均无 token 残留
- 预期结果: 含凭证地址被清洗后上报，任何输出通道无 token 明文；正常 HTTPS / SSH 地址不被破坏；环境恢复无残留
