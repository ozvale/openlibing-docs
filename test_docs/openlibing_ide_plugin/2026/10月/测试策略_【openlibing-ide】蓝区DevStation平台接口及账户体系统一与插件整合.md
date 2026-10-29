# 测试策略 — issue_61_【openlibing-ide】蓝区 DevStation 平台接口及账户体系统一与插件整合

> **模板版本**: v3.10
> **对应规则**: AGENTS.md「规则 01 — 需求驱动的测试策略与设计」+「月度版本工作模式」
> **使用说明**: 由 `python src/utils/version_tracker.py new-issue` 自动生成到
> `assets/testcase_pro/软件实现&持续集成工具链团队/05_202610/20261029/issue_61_【openlibing-ide】蓝区 DevStation 平台接口及账户体系统一与插件整合/测试过程数据/`；
> 过程文档目录承载（测试策略 / 测试设计脑图 / 需求串讲 / 测试反串讲 / 需求开发自验证 / 测试报告.md），
> case_list.md（issue 级清单）位于 issue 目录根（v3.10 上移）；
> 用例本体为 issue 目录内逐用例 `.md`，
> 执行结果见同目录 `测试报告.md` 与本 issue 目录 `执行记录跟踪表.xlsx`（需求级）

---

> 团队：软件实现&持续集成工具链团队 | 月度：202610 | 版本发布日期：20261029 | issue 编号：61 | issue 标题：【openlibing-ide】蓝区 DevStation 平台接口及账户体系统一与插件整合
> 文档状态：设计中 | 创建日期：2026-10-26 | 负责人：[待填写]

---

## 1. 测试策略

> 业务输入**唯一来源**为需求串讲纪要（2026-10-23）+ 用户表述需求信息，AI/测试人员不得超出串讲范围发散。

### 1.1 Issue 信息

| 字段 | 内容 |
|------|------|
| Issue编号 | 61 |
| Issue标题 | 【openlibing-ide】蓝区 DevStation 平台接口及账户体系统一与插件整合 |
| 关联需求 | https://gitcode.com/openlibing/openlibing-ide-plugin/issues/61 |
| 所属团队 | 软件实现&持续集成工具链团队 |
| 所属微服务 | openlibing-ide-plugin（IDE 插件，多端：vscode / trae / Work Buddy / lingma） |
| 所属模块 | 插件整合 + 账户体系整改（对接 hidevlab，不再使用 openlibing） |
| 负责人 | [待填写] |
| 创建日期 | 2026-10-26 |

### 1.2 需求摘要

> 从需求串讲（2026-10-23）+ 用户表述需求信息提炼，**禁止超出范围**。

**业务目标**：将 resource-manager 与 devstation 两个 IDE 插件**合为一个插件**，并将账户体系整改为**对接 hidevlab 平台**（不再使用 openlibing 账户体系）。插件适用于 vscode / trae / Work Buddy / lingma 多端。

**核心功能点**（本 issue 范围 = 插件整合 + 账户体系整改）：

1. **插件合一**：resource-manager + devstation 合并为单一插件，两端能力整合到统一入口；
2. **账户体系整改**：插件账户体系由 openlibing 切换为 **hidevlab 平台**，登录/鉴权/凭证管理走 hidevlab；
3. **resource-manager 既有能力保留**：从 hidevlab 平台申请资源并挂载、远程连接、代码同步（整合后功能不回退）；
4. **devstation 既有能力保留**：任务临时执行环境（资源申请/资源配置/任务执行/资源释放，详见 issue 60 补齐内容）。

**业务规则 / 边界**：

- 资源申请（resource-manager）走 **hidevlab 提供的接口**；
- devstation 走**灵枢提供的接口**（详见 issue 60 能力补齐）；
- **三分接口尚未提供**（串讲确认）：hidevlab / 灵枢依赖接口未就绪，评审基于开发提供的 ide 插件 demo；
- 本次仅支持自定义任务并提供调测功能（与 issue 60 共口径）。

**不涉及（禁止发散）**：devstation 能力补齐（可视化配置/一键执行/日志产物/重试调测）归 issue 60 覆盖，本 issue 聚焦插件合一与账户体系切换；不新增第三方平台接入（仅 hidevlab 对接）。

### 1.3 测试目标

| 测试点 | 对应用例 |
|------|------|
| 插件合一：两插件合并后统一入口、能力整合无缺失、resource-manager/devstation 功能均可用 | TC-ISSUE61-001、TC-ISSUE61-002 |
| 账户体系整改：登录/鉴权切换 hidevlab，不再依赖 openlibing；未登录/失效凭证处理 | TC-ISSUE61-003、TC-ISSUE61-005 |
| resource-manager 保留能力回归：资源申请/挂载/远程连接/代码同步（复用既有回归用例库，仅登记回归验证） | TC-ISSUE61-006、TC-ISSUE61-007 |
| 多端兼容：vscode / trae / Work Buddy / lingma 安装与基础可用 | TC-ISSUE61-002 |
| （回归）整合后 devstation 任务执行链路可用（详细能力补齐见 issue 60） | TC-ISSUE61-008 |

### 1.4 测试范围

| 测试类型 | 是否覆盖 | 说明 |
|----------|----------|------|
| UI功能测试 | 是 | IDE 插件界面：统一入口、账户登录/鉴权入口、资源申请/挂载/远程连接/代码同步操作、插件安装启用（多端） |
| API接口测试 | 部分 | hidevlab 接口链路（资源申请/账户鉴权）——**三分接口未提供**，接口未就绪前用例标记 block；就绪后按真实链路验证 |
| DFX测试 | 否 | 验收标准无性能/可靠性指标；资源申请与任务执行并发由平台侧保障，本 issue 不设 DFX 断言 |
| 安全测试 | 是（部分维度） | 账户体系整改涉及认证与凭证管理：认证校验（hidevlab 登录/鉴权切换，openlibing 旧体系废弃）、敏感信息防护（凭证/token 存储与日志）。其余维度豁免（见下声明） |

**安全 6 维度覆盖声明**（AGENTS.md 规则 04 强制）：

| 维度 | 覆盖状态 | 说明 |
|------|----------|------|
| 认证校验 auth_check | ✓ | 账户体系整改核心：hidevlab 登录/鉴权切换，openlibing 旧体系不可用/废弃校验 |
| 横向越权 horizontal_check | 豁免 | 不改跨用户资源访问控制；hidevlab 资源归属由平台侧管控 |
| 纵向越权 vertical_check | 豁免 | 不改角色/权限模型 |
| 传输安全 transport_check | 豁免 | 不改传输配置；接口链路沿用既有 HTTPS/凭证体系 |
| CSRF csrf_check | 豁免 | 非浏览器会话接口（IDE 插件/服务端接口） |
| 敏感信息防护 sensitive_data_check | ✓ | 账户切换后凭证/token 的存储、日志脱敏（不出现明文凭证） |

### 1.5 测试策略

- 手工测试（主链路，IDE 插件操作 + 两端观测）：
  - 插件合一：安装合并后插件，验证统一入口、resource-manager 与 devstation 能力入口整合；
  - 账户体系整改：hidevlab 登录/鉴权正常，openlibing 旧登录失效，凭证管理与刷新；
  - resource-manager 保留能力：执行**既有回归用例库**做功能回归验证（资源申请/挂载/远程连接/代码同步，不重复生成用例，仅登记回归验证 TC-ISSUE61-006/007）；
  - 多端兼容：vscode / trae / Work Buddy / lingma 安装启用与基础操作；
  - 依赖接口未就绪用例标记 block，就绪后补执行。
- 自动化测试：插件 UI 自动化依赖 IDE 环境与 hidevlab 接口，接口未就绪前以手工为主；hidevlab 接口就绪后可补 `auto_api`（账户鉴权/资源申请链路），脚本位置 `src/automation/software-cicd/api/...`（待接口就绪后登记）。

### 1.6 复用检查（强制）

> 设计用例前必须检索：特性树 `assets/testcase_pro/软件实现&持续集成工具链团队/{01~04 类型目录}/` 与
> `01_系统测试/通用功能/易用性/` 易用性通用库；可覆盖的测试点**直接复用**，标注 reuse。

| 检索范围 | 可复用用例 | 复用结论 |
|----------|-----------|----------|
| 特性树（本团队 01~04） | 无 IDE 插件/资源申请类存量用例 | 需新建（全部 new） |
| 易用性通用库 | 无直接命中（插件为 IDE 内嵌 UI，非 Web 平台页面） | 需新建 |

### 1.7 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 三分接口尚未提供（hidevlab / 灵枢） | 资源申请/账户鉴权链路用例无法完整执行 | 接口未就绪前用例设计先行，相关用例标记 block；向开发确认接口就绪计划后补执行 |
| 插件多端（vscode / trae / Work Buddy / lingma）环境差异 | 多端兼容用例覆盖受限 | 优先主用端（vscode/trae）实测，其余端安装启用验证；执行时确认测试可用端 |
| 插件合一回归面大（两插件既有能力） | 整合后能力缺失/回退风险 | 覆盖 resource-manager 与 devstation 关键保留能力用例（TC-ISSUE61-005/006/008） |
| 账户体系切换（openlibing → hidevlab）影响既有凭证 | 旧凭证失效/迁移问题 | 覆盖旧体系废弃校验（TC-ISSUE61-004）+ 新体系登录鉴权（TC-ISSUE61-003） |

### 1.8 依赖与前置条件

- 测试环境：合并后插件安装包（开发提供）、ide 插件 demo（评审已提供）
- hidevlab 平台测试账号（账户体系整改后登录鉴权用）
- 可用 IDE 端（vscode / trae 为主）
- 三分接口：hidevlab 接口就绪状态确认（未就绪用例 block）
- 开发侧：插件合一构建产物 + hidevlab 对接实现
