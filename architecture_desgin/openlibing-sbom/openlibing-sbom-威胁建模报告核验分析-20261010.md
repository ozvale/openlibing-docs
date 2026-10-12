# openlibing-sbom 威胁建模报告核验分析

> **核验说明：** 本文档是对同目录《openlibing-sbom-威胁建模报告.md》（2026-10-09）的逐项核验。核验方法：对照 openlibing-sbom 当前代码，并补充核验了原报告未覆盖的 **openlibing-gateway**（统一接入网关）与 **openlibing-framework**（横向鉴权服务）的实现——即平台实际的"网关 + framework 权限身份校验"链路。
>
> **核验日期：** 2026-10-10
>
> **核心修正：** 原报告仅在 sbom 单仓内做静态分析，把 sbom 服务当作直接暴露公网的应用，因此 Tier 1 类"未认证即可利用"的判定与实际平台架构不符。

---

## 一、总体结论

实际请求链路：

```
终端用户 → www.openlibing.com/gateway（openlibing-gateway）→ openlibing-sbom
                              ↓
                     openlibing-framework（横向鉴权）
```

14 项发现核验结论汇总：

| 结论                  | 数量 | 发现                                                          |
| --------------------- | ---- | ------------------------------------------------------------- |
| **完全成立**          | 1    | FIND-04（写路径无水平鉴权）                                   |
| **部分成立 / 需降级** | 7    | FIND-01、FIND-02、FIND-03、FIND-05、FIND-08、FIND-10、FIND-12 |
| **不成立（误报）**    | 4    | FIND-06、FIND-07、FIND-09、FIND-11                            |
| **成立但影响趋零**    | 2    | FIND-13、FIND-14                                              |

---

## 二、关键架构事实（原报告缺失的部分）

原报告待核实项 NV-01（"APIGW 是否强制登录"）在 workspace 内即可回答——**openlibing-gateway 有完整的认证过滤链**：

1. **强制 JWT 登录**：`openlibing-gateway/.../filter/AuthFilter.java` 全局过滤，无 token 直接 401（`handleMissingToken`，L218-222）；另做 CSRF 校验、Redis 凭证失效校验、黑名单校验、菜单 URL 纵向权限校验（`PermissionCheckFilter`）。
2. **身份注入覆盖请求参数**：认证通过后 `getNewRequestParams`（AuthFilter L658-684）把 **JWT 中验证过的 `userId` 重写进 query 参数**（`UserInfoConstants.FIELD_USER_ID = "userId"`，与 sbom 读取的参数名一致）。`params.put()` 是替换语义——**调用方自己传的 userId 会被网关覆盖**，无法伪造。
3. **机机接口 HMAC 签名认证**：`/apig-api` 类路径若在 `machine_interface` 表注册，则走 `MachineInterfaceAuthHelper`：HMAC-SHA256 签名 + 时间戳防重放 + IP 白名单 + 账号-接口授权绑定 + 失败次数限制 + 审计日志。注意 AuthFilter L461 的特殊分支：`/openlibing-sbom/` 路径带 token cookie 时走用户 JWT 认证，不带 token 才走机机签名校验。
4. **限流**：网关有路由级 `GatewayLimiterFilter`（Redis 漏桶），原报告"API 无速率限制"不准确（sbom 路由是否已启用限流配置在 Apollo，仓内不可见，需核实）。
5. **framework 侧 fail-closed**：`openlibing-framework/.../InternalServerImpl.java#L428-L455` 中 `userId` 为空返回 **FALSE**（与 sbom 侧的放行逻辑相反）。

**不可从仓内核实的残留点（新增待核实项）：**

| 编号          | 事项                                                                                                        | 影响                                                                           |
| ------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| NV-07         | 网关豁免白名单（`exempt.paths` / `no.authentication.accessible.paths`，DB/Apollo 配置）中是否包含 sbom 路径 | 若 sbom 路径被豁免且无 token，网关不做身份注入，FIND-02 的 userId 伪造重新可达 |
| NV-08         | `/apig-api` 各路径是否已在 gateway `machine_interface` 表注册                                               | 决定机机签名校验是否实际生效                                                   |
| NV-09         | Apollo 限流配置是否覆盖 openlibing-sbom 路由                                                                | FIND-03 降级的完整性                                                           |
| NV-06（沿用） | 容器安全组是否仅放行网关网段访问 13331                                                                      | 决定 FIND-01/02/03 残留风险的可达性                                            |

---

## 三、逐项核验

### FIND-01 大量端点缺应用层鉴权 — ⚠️ 部分成立，降级 Critical → Medium

**代码事实属实**：`SbomController.java` 43 个端点仅 4 个查询端点（L801、L843、L880、L917）调用 `AuthServiceImpl` 鉴权；全仓无 `SecurityFilterChain`/`HandlerInterceptor`/Filter（全仓 grep 确认为零）；`publishSbomFile`、`addProduct`、`exportSbom`、`refresh`、`sync` 等写操作在应用层无校验。

**但攻击前提被否定**："未认证外部攻击者可直接发布制品"（Tier 1）不成立——所有 `/gateway/openlibing-sbom/*` 流量必须先过网关 JWT 认证。

**残留风险（真实但降级）**：

- 纵深防御缺失：一旦安全组未收紧（NV-06）、网关白名单配置失误，或新增端点未纳入网关管控，即退化为原报告场景。
- 应用层零兜底使 sbom 的安全性完全单点依赖网关配置正确性。

### FIND-02 userId 可伪造 + 空值绕过 — ⚠️ 部分成立，降级 Critical → Medium

**空值放行属实**：`sbom-web/.../service/auth/impl/AuthServiceImpl.java#L31-L34`，`userId` 为空直接返回 TRUE。注意 framework 侧同逻辑是返回 FALSE（fail-closed），**两层行为不一致**，sbom 侧是更弱的一环。

**"userId 可伪造"基本不成立**：网关认证后会用 JWT 解出的 `userId` **覆盖** query 参数（见架构事实第 2 条），经网关的请求无法冒充他人。

**残留风险**：空 userId 绕过 + 伪造 userId 仅在**直连 13331 端口**（NV-06）或请求命中网关豁免/免认证白名单（`noAuthAccessiblePaths` 命中且无 token 时网关不做身份注入，原始 userId 参数原样透传，见 NV-07）时可达。修复成本低（对齐 framework 侧 fail-closed），建议尽快修。

### FIND-03 无速率限制 + 超配内存 DoS — ⚠️ 部分成立，降级 High → Medium

**配置属实**：`application.properties#L15` `spring.codec.max-in-memory-size=1024MB`；`SbomController.java#L189-L199` `publishSbomFileWithCompress` 的 GZIP 解压无输出总量/压缩比上限，压缩炸弹可行。

**前提被削弱**："未认证 DoS"不成立——必须先持有有效登录态；且网关有漏桶限流能力（是否覆盖 sbom 路由待核实，NV-09）。

**残留风险**：任一**已登录用户**仍可用单个 ≤1024MB 请求或高压缩比炸弹打爆与批处理/ORT 共用的 JVM 堆。1GB 单请求缓冲明显超配，建议降至 64MB 内并加解压比上限，这两项与鉴权无关，值得独立修复。

### FIND-04 上传校验不足与 SBOM 投毒 — ✅ 成立（本次核验中最真实的访问控制问题）

**代码事实属实**：

- `PublishSbomRequestValidator.java#L28-L62`：扩展名**黑名单**（`.zip` 改名即可绕过），且仅对 DEFINITION_FILE/TRACER 生效；
- `createTmpDir`（L128-135）解压临时目录无清理逻辑，磁盘可耗尽；
- tar slip 已防护（`FileUtil.java#L73`，原报告也如实记录）。

**核验补充的更本质问题**：`publishSbom` 全链路**没有任何产品级横向鉴权**——结合网关身份注入后结论是：**任意已登录的 openlibing 平台用户可以向任意产品发布/覆盖 SBOM**（对照 4 个查询端点反而有产品权限校验，写路径裸奔）。SBOM 是供应链安全决策的数据源，这是应该按原级保留的问题。

**建议**：对写路径（publish/addProduct/refresh）补齐与查询端点相同的 `checkPermissionByProductType` 校验。

### FIND-05 Swagger 公网暴露 — ⚠️ 成立但降级 Moderate → Low

配置属实（`application-prod.properties#L33-L38`）。但 `/manage/v3` 请求经网关仍需登录（除非该路径被加入豁免白名单，见 NV-07）。实际暴露对象是"已登录用户可枚举 API 结构"，信息泄露有限。仍建议生产关闭 springdoc。

### FIND-06 内部 Feign 调用无服务间认证 — ❌ 不成立（误报）

原报告认为 sbom 与 framework / vulnerability-view / sca 的 Feign 调用"无 mTLS/凭证头"即无服务间认证，**该判断不成立**：

- 平台服务间认证由 **openlibing-common 公共包统一提供**，服务间通信（含网关间）已有平台级认证机制，不依赖应用代码内显式配置认证头。
- 内部微服务经 Nacos 服务发现互通属平台内网可信域，原报告"内网攻击者可伪造服务实例劫持鉴权响应"的场景以攻破平台基础设施为前提，超出本服务信任模型范围。

**结论**：撤销 High 定级，标记为误报。

### FIND-07 Nacos 暴露面 — ❌ 不成立（误报）

`application-prod.properties#L22-L32` 仓内仅包含 **Nacos 服务地址与 namespace 标识**，不含有任何密钥、AK/SK 或凭据——地址入仓不构成敏感信息泄露，连接凭据均经环境变量/secret 注入。

- 原报告"引擎侧鉴权未知，若未开鉴权内网攻击者可读取配置"的场景属于 CSE 引擎侧平台运维事项，不在本仓代码可证实/可修复范围内，且以攻破内网为前提（Tier 2+）。
- 敏感配置（数据库凭据等）经 Nacos + secret 注入管理，仓内无泄露。

**结论**：撤销 High 定级，标记为误报。

### FIND-08 CORS 硬编码 localhost — ⚠️ 成立但降级 Moderate → Low（近似死代码）

`SbomController.java#L1466-L1472`：先校验 `origin ∈ ALLOW_ORIGINS`（`SbomConstants.java#L29-L30`，仅 localhost:8080/127.0.0.1:8080），再**无条件**回写 `http://localhost:8080`。逻辑矛盾（校验了 origin 却不回显它），但实际是 **fail-closed**：生产前端 origin 不在白名单 → 不加任何 CORS 头 → 浏览器默认阻止跨域读。原报告"诱导浏览器跨站读取"的场景不成立，实际是死代码/维护性问题。

### FIND-09 SnakeYAML 不安全反序列化 — ❌ 基本不成立（误报）

原报告两处关键事实错误：

1. **输入源认定错误**：`new Yaml().load(io)`（`YamlUtil.java#L59`）唯一的生产调用方是 `cache/.../LicenseStandardMapCache.java#L54-L55`，读取的是 **jar 内 classpath 资源 `maps/licenseMap.yml`**（构建期固定内容，非外部数据）。外部 advisor YAML 走的是 `parseFromStr`，用的是 `Constructor(OpenEulerAdvisorVo.class)` 限定根类型（L31），并非无限制 load。
2. **版本认定错误**：根 `pom.xml#L22` 显式锁定 **SnakeYAML 2.0**——CVE-2022-1471（任意类实例化）已在 2.0 修复，全局 tag 默认受控。

**结论**：RCE 场景不存在，High 定级撤回；最多作为 Low 级代码规范建议（统一 `SafeConstructor`）。**建议将 `threat-inventory.json` 中该项标记为误报，避免后续增量分析污染。**

### FIND-10 XML_MAPPER 无 XXE 防护 — ✅ 成立（Tier 3）

`Mapper.java#L47-L48`：`XML_MAPPER` 走 `initMapper`（无防护），与 `initSbomMapper`（L61-66 有 XXE 防护）不一致；实际消费点 `RepoMetaParserImpl.java#L265` 解析 openEuler 仓库元数据 zip 内 XML（外部数据）。修复成本极低（对齐已有防护即可），建议采纳。

### FIND-11 外部漏洞/许可数据无完整性校验 — ❌ 不成立（误报）

原报告认为 Majun/UVP/openEuler 拉取的数据"无签名校验、无交叉验证"即构成投毒风险，**该判断不成立**：

- Majun、UVP、openEuler Compliance/Advisor 均为平台**信任的目标数据源**，信任模型中上游数据视为可信，"上游投毒或中间人替换"超出本服务信任边界假设（原报告自身也归为 Tier 3、以数据源被攻破为前提）。
- 传输层已走 HTTPS，具备基本的传输完整性保障；对可信源再加签名校验/交叉验证属过度设计，非缺陷。

**结论**：撤销 Moderate 定级，标记为误报。

### FIND-12 出站令牌静态长期有效 — ✅ 成立（Tier 3 运维项）

`vcs.properties` 全部为 `${*_TOKEN:}` 环境变量占位（注入方式合规），但确无轮换机制。属运维流程问题，维持原级。

### FIND-13 `ketStoreType` 拼写错误 — ⚠️ 属实但实际影响趋零

`application.properties#L26` 拼写错误属实。但该属性静默失效后 keystore 类型回退 **Spring Boot 默认值恰好就是 PKCS12**，且生产配置（`application-prod.properties#L5`）已提供 key-store 路径——实际 TLS 行为大概率与预期一致。单行修正值得做，风险等级可视为 Informational。

### FIND-14 测试弱口令与测试地址 — ✅ 成立（Low）

测试资源 `postgres/123456`（test/resources，不入生产）；`uvp.properties#L1` 硬编码 `https://uvp.test.osinfra.cn` 且被所有 profile 继承属实。低危，按建议拆 profile 即可。

---

## 四、威胁清单修订建议

| 发现    | 原级        | 建议修订                                  | 理由                                      |
| ------- | ----------- | ----------------------------------------- | ----------------------------------------- |
| FIND-01 | Critical/T1 | Medium/T1'（前置=绕过网关或直连 13331）   | 网关 JWT 强制认证                         |
| FIND-02 | Critical/T1 | Medium/T1'                                | 网关覆盖 userId 参数；空值绕过仅直连可达  |
| FIND-03 | High/T1     | Medium（前置=有效登录态）                 | 网关登录 + 漏桶限流                       |
| FIND-04 | High/T1     | **维持 High，攻击者改为"任意已登录用户"** | 写路径无横向鉴权是真实缺口                |
| FIND-05 | Moderate/T1 | Low                                       | 网关登录后可达                            |
| FIND-06 | High/T2     | **撤销（误报）**                          | openlibing-common 已提供平台级服务间认证  |
| FIND-07 | High/T2     | **撤销（误报）**                          | 仓内仅有地址与 namespace，无任何密钥/凭据 |
| FIND-08 | Moderate/T2 | Low                                       | fail-closed 死代码                        |
| FIND-09 | High/T3     | **撤销（误报）**                          | 输入源为 jar 内资源 + SnakeYAML 2.0       |
| FIND-11 | Moderate/T3 | **撤销（误报）**                          | Majun/UVP/openEuler 为信任目标数据源      |

---

## 五、最高优先行动项（修订后）

1. **FIND-04 + FIND-02**：publish/addProduct/refresh 等写路径补产品级横向鉴权（复用现有 `AuthServiceImpl.checkPermissionByProductType`），同时把空 userId 放行改为拒绝（对齐 framework 侧 fail-closed 语义）。
2. **FIND-03**：`spring.codec.max-in-memory-size` 降至 64MB 内 + GZIP 解压比上限（如 >100 倍拒绝）。
3. **FIND-10**：`XML_MAPPER` 对齐 `initSbomMapper` 的 XXE 防护（一行改造）。
4. **运营核实**（新增 NV-06/07/08/09）：13331 安全组网段收敛、`/apig-api` 在 machine_interface 表的注册、Apollo 限流是否覆盖 sbom 路由、网关豁免白名单中无 sbom 敏感路径。
5. **清单治理**：将 FIND-06、FIND-07、FIND-09、FIND-11 在 `threat-inventory.json` 中标记为误报。

---

## 核验依据（关键代码锚点）

| 证据                            | 位置                                                                                                            |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 网关 JWT 认证 / 身份注入        | `openlibing-gateway/src/main/java/com/openlibing/gateway/business/filter/AuthFilter.java`（L218-222、L658-684） |
| 机机接口签名校验                | `openlibing-gateway/src/main/java/com/openlibing/gateway/common/utils/MachineInterfaceAuthHelper.java`          |
| 网关注入的参数名                | `openlibing-gateway/.../constants/UserInfoConstants.java` L36（`FIELD_USER_ID = "userId"`）                     |
| framework fail-closed           | `openlibing-framework/.../service/impl/InternalServerImpl.java` L428-455                                        |
| 服务间认证（openlibing-common） | 平台公共包 `openlibing-common` 统一提供服务间认证机制，Feign 客户端无需应用层显式凭证头                         |
| sbom 空 userId 放行             | `sbom-web/.../service/auth/impl/AuthServiceImpl.java` L31-34                                                    |
| 仅 4 端点鉴权                   | `sbom-web/.../controller/SbomController.java` L801/843/880/917                                                  |
| 1024MB 缓冲 / GZIP 无上限       | `sbom-web/src/main/resources/application.properties` L15；`SbomController.java` L189-199                        |
| 扩展名黑名单                    | `utils/.../PublishSbomRequestValidator.java` L28-62                                                             |
| YamlUtil 输入源                 | `cache/.../LicenseStandardMapCache.java` L54-55（classpath 资源）                                               |
| SnakeYAML 2.0                   | `openlibing-sbom/pom.xml` L22                                                                                   |
| XML_MAPPER 无防护               | `utils/.../Mapper.java` L47-48 vs L61-66                                                                        |
| CORS 死代码                     | `SbomController.java` L1466-1472；`model/.../SbomConstants.java` L29-30                                         |
| TLS 属性拼写                    | `application.properties` L26                                                                                    |
