# 统一操作日志方案与实现审查（2026-10-12）

审查对象：`D:/code/plans/operation_log_architecture/operation-log-architecture.md`，以及方案列出的 16 个后端仓库。

结论：统一入口、统一表、有界异步写入的方向成立，但当前实现不能据此认定“不会影响业务性能”或“可以完整记录所有操作”。存在启动装配冲突、失败参数未统一脱敏、Handler 重叠匹配等功能缺陷；写入性能保护也没有覆盖网关、请求线程、任务客户端、查询和清理全链路。

本次只新增审查记录，不修改生产代码、业务仓 common 版本、beta 数据或原方案。记录创建于 framework 的 `operation_log_architecture` 分支。`plans/` 本身不是 Git 仓库，为遵守分支约束，没有直接在该目录修改方案。

> 后续整改：参见 [2026-10-12 整改与性能边界记录](operation-log-architecture-hardening-2026-10-12.md)。以下保留首轮发现，不代表这些问题均仍未处理。

## 1. 范围、基线与证据边界

- 后端以本地 `operation_log_architecture` 引用为审查基线；未 fetch，不把本地分支等同于远端最新代码或 beta 已部署版本。
- common 的日志 Java 源码在当前开发分支与目标分支一致，但 POM 不同：目标分支为 `1.0.21.1-SNAPSHOT` / Spring 6，当前开发分支为 `1.0.21.2-SNAPSHOT` / Spring 7。不能把对日志源码的审查当成对新依赖栈的兼容性验证。本次不调整任何版本。
- framework 已切到目标分支；其它非目标分支仓通过 Git 差异确认相关日志代码的一致性，并对有差异的关联代码读取目标分支内容。
- 全仓检索覆盖 Handler、公共 Feign 扫描、旧日志 INSERT、任务直写、查询 Mapper；深读 common/framework/gateway 主链和 CICD/coderepo 任务、项目查询链，检查其它业务仓快照实现。不是对所有业务接口逐一完成的集成验收。
- 方案 16 仓中，按 `INSERT INTO log_` / `insert into log_` 检索生产 XML，命中仅在 framework 的统一表 Mapper；此结果不是所有可能写入方式均已排除的证明。
- 本地两套前端没有 `operation_log_architecture` 引用。主站当前 `master`，CICD 前端当前 `full-check-update`；前端发现只描述这些本地版本，不推定 beta 的实际页面版本。
- 未向 beta 发送模拟请求，未连接数据库，未执行 EXPLAIN 或性能压测，未进行完整应用启动验证。

后端引用：common `9c093aa`；framework `7c630b18`；gateway `b3db7df`；cicd `3067fd3cd`；coderepo `f91a291c`；codecheck `3a6689db`；anti-poison `d350180`；ai `c6a14c4`；sca `75a68a43`；vulnerability `c8aadb12`；platform-release `23996ce5`；sbom `033fed1e`；computing-resource-workspace `11a7b1b`；metric `61896b6`；ops `cdb68d58`；design-api-management `16111ca8`。

## 2. 实际调用链与已经具备的保护

```text
网关放行
  → Marker 同步读 Redis 菜单；缓存缺失时查数据库；解析并构建匹配索引
  → 下游 Servlet 切面读取可信标记
  → 请求线程：选择 Handler → before 查询/序列化
  → 原 Controller / Service
  → 请求线程：返回体 JSON 转 Map → 填公共字段 → after 查询/序列化
  → 每实例日志线程池：默认 core=2、max=8、queue=1000
  → Recorder 有限重试 → framework 写入入口
  → 每 framework 实例 Semaphore.tryAcquire，默认并发 8
  → 菜单 identification 精确 SELECT → 单条 INSERT
  → 调用方输出 MANAGE_LOG，交给既有采集链入湖
```

参数绑定失败：异常观察器返回 null，保留原异常处理响应；带标记时经 `writeDirect` 进入同一线程池。定时任务：本仓 DirectWriter 同步 begin，执行任务，再同步 finish；framework 查询原记录后 UPDATE。framework 自身 Recorder 走本地 `InternalServer`，不绕 Feign 调自己。

已实现：无标记请求跳过主要采集工作；before/after 异常隔离；线程池有界且拒绝不回退到请求线程；Recorder 默认最多两次尝试；公共 Feign 默认连接 1 秒、读取 3 秒、底层不重试；framework 写入前非阻塞限并发；菜单精确查询有索引；主键重复返回成功；原表只读保留；参数异常与环绕切面使用请求级防重复标记。

这些是代码事实，不是吞吐量、P99、数据库容量或入湖成功率的实测结果。

## 3. 需要优先处理的发现

### R01 / P1：三个业务仓存在公共写入客户端装配冲突

证据：common 的 `OperationLogRecorder` 构造器按 `OperationLogWriteClient` 注入；公共 `OperationLogWriteFeignClient` 实现该接口。CICD、coderepo、vulnerability 的本仓 `FrameworkLogClient` 也继承该接口，且启动类同时扫描本仓包和公共 Feign 包。两组 `@FeignClient` 均未关闭默认 `primary=true`，Recorder 没有限定注入目标。

- 公共 Recorder（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogRecorder.java:99）
- CICD 客户端（D:/code/openlibing-cicd/src/main/java/com/openlibing/cicd/business/feign/FrameworkLogClient.java:23）、CICD 扫描入口（D:/code/openlibing-cicd/src/main/java/com/openlibing/cicd/OpenlibingCicdApplication.java:23）
- coderepo 客户端（D:/code/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/feign/FrameworkLogClient.java:23）
- vulnerability 客户端（D:/code/openlibing-vulnerability/src/main/java/com/openlibing/business/fegin/FrameworkLogClient.java:24）

影响：按当前声明装配两个 primary 候选会触发 `NoUniqueBeanDefinitionException`，应作为发布前启动检查的阻断项。单独 new Recorder 或 Mockito 单测不会发现这个问题。本地最小 Spring BeanFactory 复现已确认该候选冲突机制；未宣称已启动三个完整业务应用。

建议：本仓 FrameworkLogClient 收敛为查询职责，写入统一注入公共客户端；framework 保留本地适配器。若暂时保留两个写入接口，必须明确唯一装配选择，并验证超时配置实际落在哪个客户端上。补三个仓的轻量 Spring 装配测试。

### R02 / P1：普通业务失败参数没有统一脱敏

证据：Recorder.serializeParams（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogRecorder.java:395） 只排除基础设施对象和特定参数名，然后直接 `JSON.toJSONString(copy)`。`truncateParams` 只截长度。参数校验异常有独立敏感键处理，不能覆盖正常进入 Controller 后返回业务失败或抛异常的路径。framework 写入端也未提供统一脱敏兜底。

本地合成参数复现：`password=SYNTHETIC_AUDIT_SECRET` 在序列化结果中仍可检出。未使用任何真实凭据。项目查询时再掩码不能撤销已入库、已输出到 MANAGE_LOG 的数据。

建议：在公共采集边界对 params、新旧快照、异常文案制定一致的允许字段/敏感字段规则；递归处理嵌套 DTO、Map、集合及 JSON 字符串，先脱敏再限量。测试成功、业务失败、异常失败、参数校验失败四条路径。

### R03 / P1：通用参数导致 Handler 同时命中，资源维度丢失

证据：FeedBackLogHandler（D:/code/openlibing-framework/src/main/java/com/openlibing/framework/common/aop/FeedBackLogHandler.java:41） 和 InformationBulletinBoardLogHandler（D:/code/openlibing-framework/src/main/java/com/openlibing/framework/common/aop/InformationBulletinBoardLogHandler.java:43） 都接受任意非空 `id`；Wiki/公告等还有通用 `ids` 列表匹配。它们没有结合 Controller 类型收窄。

OperationLogAspect.selectHandler（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogAspect.java:126） 在多命中时返回 null。比如 删除公告接口（D:/code/openlibing-framework/src/main/java/com/openlibing/framework/business/controller/ManageController.java:130） 的 `id` 会同时满足公告与反馈 Handler。结果可能只有公共字段，缺少资源和快照，操作日志页面无法按资源追溯。

本地以同一 `OperationLogContext(params={id:123})` 调用这两个真实 Handler，均返回 true。

建议：DTO 类型与 Controller/方法身份共同决定匹配，不能单靠 id/ids，也不要用“列表中第一个命中”掩盖冲突。上下文已有 Controller 类型；同一个管理 Controller 下仍需方法或更具体参数约束。补全部 Handler 同时装配的互斥性测试。

### R04 / P1 性能风险：所有已放行路由都付出菜单读取和重建成本

证据：Marker.filter（D:/code/openlibing-gateway/src/main/java/com/openlibing/gateway/business/filter/OperationLogMarkerFilter.java:47） 同步调用菜单匹配；matchOperationLogMenu（D:/code/openlibing-gateway/src/main/java/com/openlibing/gateway/common/utils/UserAuthHelper.java:140） 每次创建三个 Map 并遍历全量菜单；缓存读取（D:/code/openlibing-gateway/src/main/java/com/openlibing/gateway/common/utils/UserAuthHelper.java:412） 命中仍执行 Redis EXISTS、GET 和整份 JSON 解析，未命中同步查库。

影响不只限于 write_log=1 的写请求：最终不写日志的查询请求也先经历该路径。GlobalFilter 没有将这部分阻塞工作显式隔离。Redis/数据库变慢时，catch 异常只能避免异常转成业务错误，不能消除等待时间；并发缓存失效还可能同时回源。

建议：先量化每请求 Redis 次数、菜单字节数、解析/索引构建耗时及路由线程阻塞。至少取消多余 EXISTS；索引应在菜单版本变化时构建，而非逐请求构建。若采用实例内不可变快照，需要与方案“不新增缓存”的范围一起明确，并实现版本失效、回源合并和刷新失败策略。不要只把阻塞操作搬到另一个无界队列。

### R05 / P1 性能与完整性风险：请求线程和单条日志体积没有预算

证据：Aspect.toResultMap（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogAspect.java:156） 对整个返回对象序列化再解析；Recorder.writeAssembled（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogRecorder.java:149） 在投递前调用 after。失败参数也是完整序列化后才截断；old_data/new_data/ex_message 没有公共大小上限，最终写 TEXT。

具体快照放大：AI loadApplications（D:/code/openlibing-ai/src/main/java/com/openlibing/ai/common/aop/AiToolManageLogHandler.java:291） 逐 ID 查询，before 和成功后的 after 均可能调用；N 项批量操作可额外产生约 2N 次查询。framework Wiki 会把批量实体整体序列化，发布模板 Handler 会装载关联集合。按主键查询并不等于查询次数和返回数据量有界。

本地合成 100000 字符参数被完整序列化为 100050 字符后，才进入后续截断。这里只证明处理顺序，不将这次运行当成性能基准。

影响：主请求额外耗时、短命大对象与 GC、队列持有大快照、Feign 报文和数据库写放大；超过列容量还会导致整条日志失败。queue=1000 限制任务个数，不限制内存字节数。

建议：定义单条总 UTF-8 字节预算、单字段预算、集合条数/深度/查询次数上限；批量查询避免 N+1；仅采集必要结果字段。超限使用明确的摘要/省略说明，不能截出非法 JSON。不能简单把 before 移到异步，否则旧值已改变。

### R06 / P2 性能风险：默认队列策略容易造成可见性长尾

证据：ExecutorConfig（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogExecutorConfig.java:38）：core=2、max=8、queue=1000，关闭等待 10 秒。

本地使用相同 ThreadPoolExecutor 参数和受闩锁阻塞的任务复现：1002 个未完成任务时 pool=2、queue=1000；第 1003 个才扩容到 3。max=8 不是常态工作线程数。

在未扩容阶段，吞吐估算应先按 `2 / 平均单任务服务时间`；队列等待不包含在当前 write_duration 中。请求已成功但日志几十秒后才可见是可能的机制结果，具体时长待实测。扩容也不能解决 framework 持续超载；当前忙拒绝不重试，队列可能快速消耗成丢失。

建议：依据允许的落库延迟配置 core/max/queue，评估固定并发或更小队列；新增最老任务年龄和排队时长指标。发布退出窗口与最坏排队/重试时间一起设计。当前 10 秒不构成“退出前一定排空”的保证。

### R07 / P1 故障隔离风险：任务直写未绑定公共超时配置

证据：R01 三个本仓 FrameworkLogClient 未声明 `configuration=OperationLogFeignConfig.class`，contextId 也不是 `operationLogWriteClient`。CICD/coderepo 的 DirectWriter（D:/code/openlibing-cicd/src/main/java/com/openlibing/cicd/common/operationlog/OperationLogDirectWriter.java:27） 注入本仓客户端，同步执行 begin/finish/write。

因此公共客户端的 1 秒连接/3 秒读取默认值，以及针对 operationLogWriteClient 的属性，不能直接证明这些调用获得同样的超时保护。外部配置中心可能另有配置，本次未读取，不能断言部署中为无限超时。

建议：统一写客户端，同时保留 begin/finish 的同步有序语义；检查最终 Feign Options。framework 本地适配器还需要 JDBC/连接获取超时，Feign 超时不适用于它。远端客户端超时也不等于服务端 SQL 已取消。

### R08 / P1 性能风险：清理实际没有分批

证据：batchDeleteOperationLogs（D:/code/openlibing-framework/src/main/java/com/openlibing/framework/common/job/BatchPersonalDataJob.java:271） 一次 SELECT 所有过期 id 到内存，一条 DELETE 删除全部过期行，再把全部 id 拼成一个日志字符串。与方案 §7“分批删除”不一致。

统一表聚合多个仓一年数据，过期积压时会同时放大堆内存、删除事务、索引维护和数据库 I/O；新增写入 Semaphore 不限制此路径。即使当前新表没有一年数据，这也是确定存在的生命周期缺陷。

建议：固定批量，按稳定游标/ID 批次查询并删除，批次独立提交、限速、可中断与恢复；核算每批实际删除数，控制隐私清理日志长度。验证失败重启后的继续处理以及与在线 INSERT 的并发影响。

### R09 / P2：菜单写入开关缓存失效依赖无关鉴权请求

证据：framework.deleteAllUserPermission（D:/code/openlibing-framework/src/main/java/com/openlibing/framework/common/utils/OpenlibingRedis.java:99） 删除 menuUrls，却不删除 operationLogMenus。后者只在 gateway.getMenus 回源（D:/code/openlibing-gateway/src/main/java/com/openlibing/gateway/common/utils/UserAuthHelper.java:387） 时被间接删除；getMenus 是普通用户权限判断路径的一部分。

公开/免登录/机机等路径虽然会经过独立 Marker，却不保证执行该权限查询；只运行这些路径时，修改 write_log 后仍可能使用旧的 operationLogMenus，直到其它请求触发失效或 24 小时 TTL 到期。

建议：菜单变更事务提交后，直接使两类缓存同时失效。再测试“只发送公开/机机请求”的开关变更场景，而非依赖一次普通页面访问顺便刷新。

### R10 / P2：异步投递入口在真正投递前失败会漏记

证据：AsyncOperationLogSkipFilter（D:/code/openlibing-coderepo/src/main/java/com/openlibing/coderepo/common/operationlog/AsyncOperationLogSkipFilter.java:41） 在绑定参数前隐藏日志头；公共异常观察器仅在存在日志头时记录。CICD 有同样机制。

因此同步仓库/流水线接口若请求体不可读、缺少参数，或业务校验/线程池投递失败，可能既不走 HTTP 日志，也根本没有任务执行。虽然避免了“请稍后”假完成行，却留下失败记录空档。与方案“启用日志的标准参数失败均写一条”的总体规则存在边界冲突。

建议：保留可信菜单上下文，区分“已受理且由任务负责”与“未受理失败”；任务成功受理后才让 HTTP 路径退出记账。补绑定失败、业务拒绝、投递拒绝、执行成功/失败的完整状态测试。

### R11 / P2 性能风险：查询会反向争用写入数据库资源

- CICD getPipelineLogList（D:/code/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/LoggingServiceImpl.java:77） 没调用默认 30 天的 applyDefaultTimeRange；filter-meta 调用了。列表不传时间时可覆盖全部保留数据。
- 同类 filter-meta 在逐维 buildFilter 时反复 listAllowed；一次选择 5 个维度可触发 5 次 framework 远程白名单查询，framework 每次读取菜单和 URL 集合，再执行各维度 GROUP BY。应在一次请求内复用白名单，不需要新增跨请求缓存。
- 平台列表 SQL（D:/code/openlibing-framework/src/main/resources/mapper/OperationLogMapper.xml:119） 读取所有列，包含 old_data/new_data；最终列表仅需 hasDetail，也把大 TEXT 拉进了 JVM。每页另有 COUNT。
- 六个二级索引会增加 INSERT/UPDATE/DELETE 成本；多 module_id 的 IN、跨模块时间排序、OR 账号条件、列头 GROUP BY 不能仅凭“有索引”保证无排序或低扫描量。当前没有执行计划证据。

建议：列表/列头统一时间边界；白名单每请求查一次；平台列表不取详情正文；对叶子、多模块、项目、资源、账号 OR、列头、深分页分别 EXPLAIN ANALYZE，再决定索引与分页方案。压测必须把查询和清理与持续写入同时运行。

### R12 / P2：列头超 1000 项时已选值仍会被丢弃

证据：CICD toFilterMetaItems（D:/code/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/LoggingServiceImpl.java:411） 与 coderepo 同名方法（D:/code/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/service/impl/LoggingServiceImpl.java:327）：先放入 SQL 返回的前 1000 个值，再追加未出现的已选值，最后 subList(0,1000)。追加项正好被裁掉。

SQL LIMIT 外的已选值还被直接赋 count=0，并不能代表真实计数。与方案“已选值即使计数靠后也保留”的契约不符。

建议：先为已选值保留容量、补查其实际计数，再填充其它候选；定义已选值本身超限时的入参校验。补满 1000 项且已选值在范围外的测试。

### R13 / P1 发布风险：混合版本和旧前端可导致断档或关掉日志

方案 §2.8 已要求成批发布，但没有覆盖当前实际的长期混合版本窗口：旧 DTO 使用 tableFlag 等字段，新 framework 要求 id/moduleId/起止时间；common 的旧切面已空转，新链路又依赖网关标记。任一环节未配套，都可能出现操作成功但两边表均未获得预期记录。

本地前端具体证据：主站 menu.vue（D:/code/openlibing-web/apps/web-openlibing/src/views/authorityManagement/menu.vue:809） 编辑菜单时显式重建 URL 对象，没有保留 writeLog；后端 menuUrl（D:/code/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/MenuServiceImpl.java:573） 将缺失 writeLog 写成 0。若这组版本组合上线，编辑其它菜单字段也会关闭该 URL 的日志。

本地 CICD 日志页面（D:/code/openlibing-cicd-web/src/views/pipeline/PipelineLog/index.vue:506） 仍读取 operationTargetName，而后端已返回 resourceName。当前本地版本不能完成新查询契约验收；未确认线上前端情况。

建议：做实例级发布清单，记录制品版本/摘要、common 版本、网关打标能力、DDL 版本和前端版本。混合期间冻结旧页面菜单编辑或实现明确的更新兼容策略；新增 URL 默认 0 与旧 URL 更新时字段省略应区别设计。不要只用一个 SNAPSHOT 名称代表各实例代码一致。

### R14 / P2：指标不足以证明“没有丢日志”和端到端成功

证据：OperationLogMetrics（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogMetrics.java:13） 在没有 MeterRegistry 时空转；Recorder.saveLog（D:/code/openlibing-common/src/main/java/com/openlibing/common/aspect/operationlog/OperationLogRecorder.java:259） 的耗时从任务开始执行才计时，包含重试/退避/湖侧日志输出，不是独立的 framework SQL P99。

framework 返回成功后先加 succeeded，再执行 lakeWriter；湖侧抛异常会加 failed，导致一条记录同时进入成功和失败计数。MANAGE_LOG 输出成功也不证明下游数据湖已收录。任务 DirectWriter、Handler 补数失败、网关打标失败没有统一纳入这组写入指标。

可靠性边界：队列满、退出、framework 拒绝、重试耗尽均可丢失；begin 失败后任务仍执行，finish 找不到记录；finish 失败可永久停留“进行中”。INSERT 的数据库异常被转换为业务失败，Recorder 的连接/5xx 重试不覆盖这部分失败。当前没有持久化补偿，主键幂等不能替代可靠投递。

建议：拆分采集/排队/发送/MySQL 接受/湖侧输出/湖侧收录的指标；增加在途数量、最老排队年龄、Handler 缺失、多匹配、任务 begin/finish 失败和过期进行中监测。核验真实 metrics 暴露、采集与告警链。定义每一类失败的计数归属及对账口径，避免简单把成功/失败计数相加当成总请求数。

## 4. 写入性能章节应补充的具体内容

当前方案确实已有 §5.3 写入和 §5.4 容量/背压/压测（约第 1700–1778 行），问题在于部分保护的覆盖范围与实现不一致，且没有性能结果。建议在原方案下一次修订中增加以下明确契约。

1. 请求同步成本：网关菜单加载/匹配、Handler before/after 查询数与耗时、返回体转换和快照字节数分别预算；“写库异步”不能替代这些约束。
2. 负载口径：按真实路径分类计数，区分同步 HTTP、参数失败、页面异步完成、定时任务 begin/finish；避免把已经包含在入口 QPS 的失败请求再加一次。网关开销按全部放行路由 QPS 估计。
3. 数据库成本：新日志通常至少菜单 SELECT + INSERT；任务 begin/finish 合计还包括原记录 SELECT + UPDATE。计入六个二级索引维护、TEXT 大小、COUNT/GROUP BY 和清理负载。
4. 并发预算：所有 framework 副本的预算相加；每副本预算应低于池容量并给核心业务留余量。该 Semaphore 不隔离请求反序列化、读查询和清理，也不提供数据库 statement timeout。
5. 调用端容量：持续到达率必须低于持续处理率；短突发所需队列约为 `max(0, 到达率−处理率)×突发持续时间`，但还要同时满足允许排队延迟和 `队列长度×单条驻留字节数` 的内存预算。处理率需实测，默认 maxPoolSize 不能直接代入常态线程数。
6. 故障语义：明确快速拒绝会丢日志；哪些失败重试、哪些不重试、哪些需要人工补偿。若要求可靠审计，应重新设计持久化投递，而非仅加大内存队列或重试次数。
7. 延迟指标：单独统计业务新增耗时、入队等待、发送耗时、framework 接收至 SQL 完成、最终可查询延迟；不要用 operation_start/end（业务时间）或当前 write_duration 冒充全部指标。
8. 上线门槛：写明对照基线、峰值来源、请求/快照大小分布、连接池配置、副本数、持续时间和通过阈值。未测得的数值保持“待验证”，不能把默认线程数和超时写成性能结论。

建议修订的文字：§5.3“不增加独立远程调用”应说明 Redis/回源数据库开销；§5.4“无头只增加一次 header 判断”仅适用于下游采集快路径，不能表示网关端到端成本；§5.1“等值/IN 即可命中并完成排序”须改成按实际 SQL 验证；§7“分批清理”和敏感字段禁止规则目前尚未完整落实。版本说明、旧 FrameworkClient 示例也应与最终采用的公共客户端和制品版本对齐。

## 5. 验证记录与下一步顺序

已执行本地最小复现，使用合成数据，不接数据库或 beta。重新编译了被调用的 Recorder 和两个 Handler，使用本机已有依赖；编译和运行最终退出码为 0。Java 编译曾受沙箱文件访问限制，放宽后同一编译完成；不是业务测试失败。

```text
PROBE primary conflict: NoUniqueBeanDefinitionException, Feign default primary=true
PROBE generic id matches: feedback=true, bulletin=true
PROBE params pre-truncation: chars=100050, synthetic secret retained=true
PROBE 1002 outstanding: pool=2, queued=1000
PROBE 1003 outstanding: pool=3, queued=1000
```

前两项分别验证 Spring 候选选择机制和真实 Handler 的匹配结果；不是完整服务启动或 HTTP 集成测试。后两类验证处理顺序与线程池行为，不是 TPS/P99 基准。没有把仓库中已有 surefire 报告计为本次重新执行的单测。

建议处理顺序：

1. 发布前：消除写客户端歧义、统一脱敏、修复 Handler 互斥性、核实旧菜单编辑页兼容性与制品矩阵。
2. 性能保护：网关匹配热路径、快照预算与 N+1、所有写客户端超时、清理分批、队列与指标设计。
3. 链路完整性：菜单缓存直接失效、异步投递失败兜底、查询时间边界、列头已选值保留。
4. beta 配套版本就绪后：运行正常写入/业务失败/绑定失败/异步任务全链路；再做稳态、5 倍突发、慢 Redis、缓存失效、framework 超载/5xx、数据库连接耗尽、队列满、进程退出和清理并发验证。

压测验收必须同时给出：业务端 P50/P95/P99 变化、日志可见性延迟、入库与丢失/在途数量、队列恢复、DB CPU/I/O/连接/慢 SQL、各路径故障恢复结果。没有这些证据，本次只能给出“设计与代码风险已识别”，不能给出“写入性能通过”。
