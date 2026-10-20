# 操作日志审查整改记录（2026-10-12）

对应 [首轮审查记录](operation-log-architecture-review-2026-10-12.md)。本次按用户要求修复必须处理的实现缺陷，优先修改 framework、gateway 和业务仓；版本发布按 beta 验证后发正式版的安排处理，不调整任何 POM、依赖版本或发布配置。

所有源码与本记录均位于各仓 `operation_log_architecture` 工作区；未提交、推送、发布或向 beta 发请求。原方案所在 `plans/` 不是 Git 仓，因此把本次设计补充保存在 framework 分支内，未直接改动原方案。

## 1. 首轮修复

### 装配和调用超时（R01、R07）

CICD、coderepo、vulnerability 本仓 `FrameworkLogClient` 保留查询和已有直接写入职责，声明 `primary=false`，并显式绑定已有 `OperationLogFeignConfig`。公共写入客户端仍是 `OperationLogWriteClient` 的唯一 primary 候选。

没有迁移调用 API，也没有复制写入实现。默认连接 1 秒、读取 3 秒以及底层不重试的既有配置同样应用到任务直接调用。测试使用真实 Feign 注解属性建立 Spring BeanFactory 候选，验证公共接口与本仓具体接口分别得到正确客户端；这不等同于三个完整应用启动验收。

### 采集安全与队列体积（R02、R05 的必须兜底部分）

首轮 common 新增包内 `OperationLogPayloadSanitizer` 并接入 `OperationLogRecorder`，没有改公开 API、线程池策略、版本或依赖。业务失败参数在序列化时脱敏；`writeDirect` 和普通写入在排队前统一处理 params、oldData、newData、exMessage，同一份处理结果同时用于 framework 请求和调用端入湖。续查中对返回体转换的补充见第 4 节。

必须修改 common 的原因：只在 framework 端脱敏，无法清除调用端随后输出到 MANAGE_LOG 的原始值；在每个业务 Handler 单独修补也覆盖不到公共失败路径。

具体边界：

- 递归处理 DTO、Map、集合、数组及字符串中的 JSON；password/passwd/pwd、token、secret、authorization、cookie、credential、access/private key 等字段值替换为 `***`，异常文本中的对应键值和 Bearer 凭据做相同处理。
- 新旧快照、异常字段各限制 32 KiB UTF-8；失败参数保留既有 500 字符列约束，结构化参数序列化另限 500 字节。
- 集合/Map 每层最多 100 项、深度最多 8 层、每次遍历有 1000 个节点的预算；循环引用、不可序列化值、格式错误或超限值使用明确的 `_omitted` 说明，不能把截坏的 JSON 写入数据库。
- 不修改原入参；测试覆盖嵌套字段、集合中的 JSON 字符串、中文 UTF-8 超限、循环引用、格式错误，以及 framework / 湖侧都收不到合成敏感值。

这些限制控制排队后的大字段体积和网络/数据库写放大，**不是整个请求线程的 CPU、SQL 或内存硬上限**。Handler 的 before/after 查询、其已有快照序列化、公共返回体转 Map，以及 DTO 转换成本仍发生在提交前。字段名识别也不能替代业务对任意自由文本的敏感内容审查。

### Handler 互斥（R03）

framework 中接受 id/ids/resourceId 等通用散参的 Handler 先按 Controller 类型收窄。机机接口与机机账号共用 Controller 的批量删除再按 MVC `HandlerMethod` 区分；工具下载排除工具项目 Handler；ManageController 的普通 id 不再误入用户管理 Handler。

未按菜单 identification 或 URL 建业务映射，未改变 common 的“多命中不猜选”规则。新增全组 Handler 同时参与匹配的用例，覆盖反馈、公告单个/批量删除、Wiki、角色、工具下载和无关 Controller。

### 网关菜单匹配（R04）

保留 Redis `operationLogMenus` 作为权威来源，新增的只是同一实例内一份编译后的匹配索引：

- 稳态请求只 GET 一次，不再 EXISTS + GET。
- Redis 内容未变时复用解析结果和三个索引，不逐请求解析和重建。
- 内容变化或缓存失效时重新读取并构建；实例内同步合并缓存未命中的回源；空菜单也回写 `[]`，避免永久空结果回源。
- Redis 故障不额外放大为查数据库；标记入口按既有尽力记录语义降级。
- 路由标记的 Redis/JDBC 阻塞操作移到专用 boundedElastic 调度器，最多 4 个线程、每线程 128 个排队任务；关闭时释放调度器。拒绝时放行业务并移除非可信标记，异常恢复范围不覆盖下游业务链。

索引没有独立 TTL 或新的 Redis key，每次 GET 仍负责观察变更。这是对原方案“不新增缓存”的明确补充：允许复用 Redis 同一内容的本机派生索引，不增加菜单事实来源。

仍需测量 Redis GET 全量内容的字节/耗时、线程队列等待，以及网关本机非路由日志入口的同步匹配成本；本轮没有把它们宣称为零。索引仅合并单实例回源，跨实例失效仍可能各自回源一次。

### 批量快照（R05）

AI 分发记录 before/after 改为各一次批量主键查询，去掉逐 ID 查询。超过 100 条时完全省略该批快照并写 `_omitted`，不静默保留前 100 条；不改变真实业务处理数量。批量资源不再把所有 ID 拼接进 VARCHAR(255) 的单资源字段。

### 清理隔离与保留期（R08）

统一日志清理单独调度，默认每 15 分钟运行一次，可用 `operation-log.cleanup.cron` 调整；保留期仍是一年，依据 `operation_end_time`。

- 每批按 `(operation_end_time, id)` 顺序最多锁定 500 个过期 ID，只删除本批 ID。
- 独立 Spring Bean 的 `REQUIRES_NEW` 保证每批真实提交，避开同类调用导致事务注解不生效的问题。
- 删除数量不一致时抛异常回滚，不报告成功。
- 每轮最多 100 批（50,000 条），剩余记录下一轮继续；每批隐私清理日志的 ID 列表也最多 500 条。
- 不再全量加载一年以前所有 ID，不再单个巨型 DELETE；从其它个人数据清理的调用链中移出，避免日志积压直接阻断后续清理步骤。

每轮数量上限控制单次影响，**不能代替清理能力验证**。上线必须监控过期积压及最老过期记录，保证长期清理速率大于过期产生速率。多实例会按数据库行锁协调，锁等待及 `idx_operation_time` 的实际执行计划仍待 MySQL 环境验证。

### 菜单一致性（R09）

framework 修改菜单后，在事务提交后再失效权限缓存，同时直接删除 `operationLogMenus`，不再依赖后续某个普通鉴权请求间接删除它。回滚时不会执行 afterCommit。缓存服务故障记录错误，不把已提交的菜单更新伪装成业务失败；Redis 故障后的跨实例恢复仍需环境验证。

### 异步投递失败（R10）

CICD / coderepo 的跳过过滤器仅通过请求属性保存可信原请求；下游仍看不到操作日志头。各仓新增失败观察器：

- 成功投递仍只由任务 begin/finish 写日志。
- Controller 返回失败或抛出投递异常时补记一条失败 HTTP 操作，保留原响应或异常。
- 参数绑定/校验失败交给现有 Recorder 处理原请求，观察器返回 null，不消费异常。
- 请求级 WriteGuard 防止重复，未带可信标记、通用菜单不写。

该实现复用 common 已有 API，不为这项改动扩展 common。

### 查询成本与筛选正确性（R11 部分、R12）

CICD 列表未指定起止时间时默认近 30 天，与 filter-meta 对齐。CICD / coderepo 同一次 filter-meta 请求只读取一次可写模块集合。

SQL 在聚合后把已选值排在 top-1000 内，返回其真实计数；Java 合并无匹配项的零计数后优先保留已选值，再执行数量上限。单维度超过 1000 个已选值直接参数报错，避免声称支持却继续丢弃选择。排序表达式中的值全部使用 MyBatis 参数绑定。

## 2. 本轮保留的边界

- R05 尚不能作为整体性能验收关闭：首轮只优化了 AI 批量查询，续查已覆盖 16 仓、63 个 Handler，扩展修复了多仓批量采集、关联查询及 common 内部返回体转换，详见第 4 节。仍有同步单条查询、实体字段序列化和真实负载容量需要验证；不是“其它仓没有检查或修改”。
- R06：不凭估算调整 common 默认 2/8/1000 线程池、重试或关闭等待时间。容量参数需结合日志到达率、实际服务时间和允许的可见性延迟确定。
- R11 未关闭部分：平台列表仍使用现有查询模型；大字段投影和各查询索引需要结合真实执行计划再处理。本轮未增加未经验证的索引。
- R13：版本发布问题按用户安排排除；未改前端或业务仓依赖版本。
- R14：不把当前成功计数解释为端到端入湖确认；不引入 outbox/MQ，不承诺进程崩溃、拒绝和下游故障时零丢失。队列年龄、落库可见时间及端到端指标尚待补充。

## 3. 首轮验证记录

已在本地执行各仓源码编译及相关回归集：common 63、framework 281、gateway 35、AI 9、CICD 32、coderepo 24、vulnerability 1，共 445 项通过，无失败或跳过。用例输出位于各仓 `target/operation-log-fix-test.log`；common 和 framework 最终增量复验记录为 `target/operation-log-final-check.log`。汇总按不重复的测试用例计数，不重复累加复跑。`target/` 是本地构建产物，不提交。

格式化仅针对本轮文件。七个仓的 Checkstyle、SpotBugs、PMD 门禁均通过；common 的 PMD 条件表达式告警修正后完成复验。另使用真实 MyBatis XMLMapperBuilder 验证 CICD / coderepo 已选值及空选择的动态 SQL、framework 限量加锁和删除的绑定参数，结果见 framework 的 `target/operation-log-sql-probe.log`；这不替代 MySQL 执行计划或事务联调。部分仓已有 JaCoCo 历史执行数据与当前字节码不一致的警告，本次不使用这些累计覆盖率作为结论。

本轮未做 beta 请求、完整应用启动、真实 MySQL 删除/锁测试、Redis 故障注入或负载测试。部署完成后至少验证：

1. 日志开/关对照的业务 P50/P95/P99、网关菜单匹配时延和 Redis 流量。
2. 单条日志字节分布、写入并发、队列深度/最老年龄、拒绝数、重试数、从业务完成到查到日志的延迟。
3. 大批量业务操作的快照 SQL 数、Handler 耗时、堆内存/GC，以及超限后 `_omitted` 的页面表现。
4. framework 写入忙拒绝和网络超时下业务延迟、日志失败可观测性；任务 begin/finish 的超时隔离。
5. 菜单 writeLog 开关提交后各网关实例是否即时观察变化；异步投递失败仅一条日志，成功投递仍只一条任务生命周期日志。
6. 历史清理执行计划、单批事务耗时/锁等待、并发写入影响和积压消化速率。

## 4. R05 续查与跨仓修复

### 检查范围和结论

检查 common、framework、gateway、AI、CICD、coderepo、codecheck、anti-poison、SCA、vulnerability、platform-release、SBOM、computing-resource-workspace、metric、ops、design-api-management，共 16 个仓。沿 Controller、Handler 的 before/after、SQL/MongoDB 查询、序列化、公共 Recorder 到异步写入检查；共定位 63 个继承 `AbstractLogHandler` 的实现。

其中 framework 22 个、platform-release 13 个、CICD 5 个、coderepo 4 个、codecheck 和 design-api-management 各 3 个、gateway/AI/anti-poison/SBOM 各 2 个、其余含 Handler 的仓各 1 个。common 提供公共链路，不含业务 Handler。

确认的主要问题是：异步写入之前仍有逐 ID 查询、无上限关联集合、大正文回查和完整返回体转换。因此“写入用了线程池”不能证明业务请求不会被日志采集拖慢。本次在 9 个仓落地补充修复；未发现需修改的实现保留现状，不以改动仓数替代检查覆盖率。

### 已修复的采集开销

- **common**：新增包内 `OperationLogResultSnapshot`，日志切面先构造有界副本，再做 JSON 规范化；脱敏器的 Bean 转换复用该实现。每个集合/对象最多 100 项，深度最多 8 层、总计 1000 个节点、文本总预算 32K Java 字符。大集合在遍历元素前拒绝采集；循环引用、大文本和超限载荷用 `_omitted` 说明。优先保留成功判断字段，并保留任务 ID 等其它顶层字段；标量返回沿用原有成功/HTTP 状态兜底，原业务响应不变。这里的字符预算与排队前的 32 KiB UTF-8 字节上限是两道不同限制。
- **framework**：Wiki 使用日志专用投影，正文超过 4096 字节时由 SQL 返回省略说明；批量采集超过 100 项或空集合时不发快照查询。机器接口/账号、工具项目、公告及成员批量采集增加数量保护。角色权限、角色成员、工具配置、机器授权的日志专用 SQL 最多读取 101 行，用第 101 行识别超限并省略整个关联集合。修正机器账号权限快照误按接口 ID 查询的问题，改按 `account_id` 查询；原业务查询保持原语义。
- **SCA**：屏蔽规则和评审的逐 ID 查询改为一次批量查询，before/after 均检查 100 项上限，空集合不查询。日志专用 SQL 使用绑定参数并再次防御空集合/超限集合。批量资源 ID 不再拼接进单资源列。
- **platform-release**：LTS 基础配置、责任人、多架构评审、发布配置、评审项等批量采集改用 MongoDB 批量查询。发布评审快照改为固定 3 次查询（主记录、领域项、评论），不再调用带逐项关联加载的完整详情方法；版本快照使用 2 次查询（版本、里程碑）。关联集合最多取 101 条，超限明确省略；轮次关联和模板关联同样限量。模板 after 去掉一次重复主记录查询。发布分组树在复制根集合前检查数量，遍历采用最多 100 节点的迭代方式并检测循环引用。批量资源不再把逗号分隔 ID 填入单资源列。另修正多架构发布评审错用普通评审集合的问题，主记录、领域项及评论均按 Controller 选择对应集合；共用的字段模板仍使用原公共集合。
- **design-api-management**：扫描路径批量快照改为一次 `findAllById`，超过 100 条不查询。
- **CICD、coderepo、computing-resource-workspace**：为镜像批量删除、代码仓批量快照、成员批量回查补充 100 项采集上限。
- **ops**：只需要最近备注的日志查询改为数据库 `limit 1`，不再加载全部历史备注后取第一条。

这些限制只作用于日志采集，不缩减实际业务操作的数据范围。集合超限时明确省略，不把前 100 条伪装为完整快照。发布评审、版本和轮次的日志 JSON 改为主记录加关联集合的结构；业务接口返回不变，但需要在 beta 核验日志详情展示和省略提示。

common 的这次修改属于必要修复：只在入队前截断已经序列化好的字符串，无法控制切面先完整转换返回体的开销。补充仅涉及内部采集实现，没有调整公开 API、线程池、重试、依赖或版本号。

### 本次验证和剩余边界

本次相关回归集为 common 67、framework 128、platform-release 46、CICD 32、coderepo 38、computing-resource-workspace 7、ops 6、design-api-management 7，共 331 项；另外 SCA 隔离编译测试 16 项，共 347 项通过。该数字包含复跑首轮的部分用例，不能与首轮 445 项相加作为不重复覆盖量。八个标准构建仓的格式、Checkstyle、SpotBugs、PMD 检查通过，日志为各仓 `target/operation-log-r05-check.log`。

SCA 原有 POM 含未定义的版本属性，标准 Maven 构建受阻。本次未修改 POM：使用本机已有依赖、重新编译相关源码及其源码依赖后执行 16 项 JUnit 测试，结果见 `target/operation-log-r05-isolated-test.log`；格式和 Checkstyle 使用命令行临时属性完成模型解析并通过，见 `target/operation-log-r05-format.log`。这不等同于完整 SCA Maven 构建或全部质量门禁通过。

另外使用真实 MyBatis `XMLMapperBuilder` 解析 7 份相关 Mapper，检查批量参数绑定、空集合、超限集合、Wiki 正文投影以及机器账号关联条件，全部通过，结果见 framework 的 `target/operation-log-r05-sql.log`。新增回归覆盖超限不查询、大集合不读取元素、循环引用、原返回值不变、普通/多架构评审集合隔离和 MongoDB 查询次数/数量上限。

仍需明确保留以下边界：

1. before 必须在业务修改前读取旧值，不能简单移到异步线程。已限制查询次数和行数，但单条慢 SQL、锁等待、远程存储延迟仍可能增加请求耗时，行数上限也不能替代执行计划检查。
2. 部分 Handler 仍直接序列化完整实体或 DTO；单条记录中的大文本、嵌套字段，以及自定义 getter/序列化器的耗时，尚无覆盖全部业务类型的硬上限。Wiki 正文已定点修复，不能据此宣称所有字段的内存成本都受控。
3. 线程池吞吐、积压、拒绝和落库/入湖延迟未实测；保持既有尽力记录语义，不承诺故障零丢失。线程池容量不能凭单元测试决定。
4. 本次未向 beta 发业务请求，未做真实数据库执行计划、完整应用启动或压力测试。第 3 节列出的环境验证仍须执行，不能把本次测试结果当成生产性能结论。

因此 R05 中已确认的多处批量放大与返回体转换问题已有代码修复；整体性能验收仍保持待验证。所有改动继续位于 `operation_log_architecture`，未提交、推送或发布。
