# openlibing-cicd — AI 可复用经验

仅沉淀经过验证且会复用的规则。

## Liquibase

- 已执行（history 表有记录）的 changeset **严禁修改内容**（checksum 校验失败会阻断服务启动）；结构变更必须另起新 changeset + preConditions 幂等守卫。
- 本项目 history 表名是自定义的 `LIQUIBASE_DATABASE_CHANGELOG`（application.yaml `database-change-log-table`），不是默认的 `DATABASECHANGELOG`。
- checksum 冲突 DB 直修法：先把表结构手工迁移到目标版本，再 `UPDATE LIQUIBASE_DATABASE_CHANGELOG SET MD5SUM='<当前部署包算出的新值>' WHERE ID=... AND AUTHOR=...`，重启即通过。
- 2026-09 实例：changeset `20260904-create-sec-option-filing` 被反复改写（V1→record_id→package_path）导致 401 环境启动失败。

## GitCode CLI

- 本机安装形态：pip 包 `gitcode-cli 0.5.5`，可执行文件 `C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\Scripts\gitcode.exe`（不在 PATH，用绝对路径调用；GC_TOKEN 已配置）。

## pre-commit（Windows 本机）

- python 实际路径 `C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\python.exe`；不在 PATH 时 local 钩子（`python scripts/run-mvn.py`）报 cmd 9009。
- Maven 钩子需要用户级环境变量 `openlibing_mvn_repo_username` / `openlibing_mvn_repo_password`（缺失 exit 2）；本地离线验证可用 `mvn -o` 等价复刻钩子 goals。
- gitleaks 钩子做全工作区扫描，`.idea/workspace.xml`、`src/main/resources/openlibing.pfx`、`target/` 为仓库既有命中，与当次改动无关（属遗留治理项）。
- `spotless:apply` 会直接改写文件，产生的格式化差异需确认后随 commit 落库。

## MQS 消息契约（PR 同步/编译）

- PR 同步主动触发走 `req_type=compile`；触发人只用统一 `account` 字段（不建平台账号组）；`br_name`=目标分支、`tgt_branch`=源分支；整体字段与 coderepo `MqsMessageSenderImpl#buildMessage` 契约对齐。

## Common 升级（Boot 3→4 / Jackson 2→3）

- Boot 3 时代 starter 的自动配置类引用 Boot 3 内部类（Boot 4 模块化移包），运行期 NoClassDefFoundError 且构建期不报错：redisson-spring-boot-starter（手动装配场景拆用 redisson core）、springdoc 2.x（拆钉扎走 BOM 3.1.1）、pagehelper 2.x（升 4.x）。
- `@WebMvcTest` 在 Boot 4 拆到独立构件 `spring-boot-starter-webmvc-test`（test scope，无版本号走 Boot BOM），import 迁至 `org.springframework.boot.webmvc.test.autoconfigure`。
- Jackson 2→3：core/databind 包名 `com.fasterxml.jackson` → `tools.jackson`，annotation 包保留原名；`JsonDeserializer` → `ValueDeserializer`；`JsonProcessingException` → `JacksonException`（unchecked）；yaml 配 `spring.jackson.use-jackson2-defaults: true` 保持 Jackson 2 序列化默认行为。
- mybatis-plus 3.5.17 的 `AbstractWrapper.in()` 在构建期即解析 Lambda 列名，纯 Mockito 单测需 `TableInfoHelper.initTableInfo(...)` 初始化实体元数据，否则报 "can not find lambda cache"。
- spring-rabbit 4.1.1 移除 `RetryInterceptorBuilder.maxAttempts(int)`，改用 `maxRetries(int)`，总尝试 = 1 + maxRetries（`maxAttempts(3)` 等价 `maxRetries(2)`）。

## 三段式密钥（keys/*.ks，一次性消费）

- `ReadFileUtils` 读取 `keys/tcpFile|tcsFile|tcwFile.ks` 后**立即删除**（防泄露设计）；仅当 JVM 系统属性 `spring.profiles.active` **精确等于** `local`（`-D` 参数，非 yaml 配置）时读后不删。
- 本地反复启动/跑测试被"密钥消失"卡住的解法：IDEA VM options 加 `-Dspring.profiles.active=local`；或启动前从备份 `config\keys-backup\*.ks` 拷回 `keys\`。
- 跑过单测（真实触发 `SecurityUtil.decrypt` 的用例）也会消费密钥，"测试过了但下次启动报 Decrypt work key error"即此原因。

## CI 与本地 spotless 行为分歧

- CI 环境解析不到 `openlibing-common:1.0.21.2` POM → `expandWildcardImports` 禁用 + google-java-format 行为与本地有差异：**本地 spotless:apply 判定干净的文件，CI mvn-spotless 仍可能改写并判 Failed**。
- 可靠解法：绕过 spotless，直接用同版本格式化器处理（guava 需 33.x，14.0-rc1 会 NoSuchMethodError）：
  `java --add-exports jdk.compiler/com.sun.tools.javac.{util,file,parser,tree,api,code,main,jvm,processing}=ALL-UNNAMED -cp "google-java-format-1.35.0.jar;guava-33.6.0-jre.jar" com.google.googlejavaformat.java.Main -replace <文件...>`
- 推送前用该命令跑一遍改动文件，可消除 CI pre-commit 的反复打回。

## 并行合并的静默回退（PipelineServiceImplTest 案例）

- 长生命周期分支（基于旧基线拉出、隔天才合并）合入主线时，若他人已向同一测试文件提交改动（如 5a32715d 把 exportBuildLog 调用改 7 参），Git 自动合并可能把该区域判为"origin 侧回退"而**静默采用旧版**——无冲突告警、Maven 增量编译不重编译未变文件也不暴露，只有 IDEA Rebuild 全量编译才报"参数长度不同"。
- 防范：合并涉及共享测试文件后，对自己此前新增的测试特征 `git grep` 核对仍在；合并后跑 `mvn test`（含 test-compile）而非只 `compile`。

## GitCode CLI 传参禁忌（gitcode.cmd 垫片）

- `gitcode.cmd` 是 cmd 垫片：`-b/--body` 内容含**换行、管道符 `|`、ASCII 双引号 `"`** 时会被 cmd 拆参（too many arguments / 内容截断）。
- 可靠方案：python `subprocess.run([r'C:\Users\admin\AppData\Roaming\npm\gitcode.cmd', 'issue', 'comment', '490', ..., '-b', body], capture_output=True)`——list 传参由 python 负责转义，长 Markdown/代码片段完整送达。
- CLI 无 `pr edit`/`pr comments` 子命令时的替代：PR 关联 issue 用 `PATCH /pulls/{n}` 的 `issue_nums` 字段（需伴随 title 等允许字段一起提交）；逐线程 resolve 走 `PUT /pulls/{n}/comments/{discussion_id}?access_token=`（Bearer/查询参数均可，token 在 `C:\Users\admin\.gitcode\config.json`）。

## 权限组（framework 实现，issue 挂 cicd）

- 成员数类统计必须与用户可见页面同源同口径（权限组列表 vs 成员管理页 query-project-user）：独立口径必然漂移；正确做法是复用列表页口径（PROJECT 角色行数 + join user_basic_info 排除孤儿行 + 默认组并入 project_user_role_info 外部账号），distinct 去重也无法对齐（漏外部账号且口径不同）。
- 操作级菜单拆分（operation_log v2 操作名区分）配置顺序：先为新菜单配置角色授权，再清理旧菜单下重复 URL 记录；顺序颠倒会直接导致所有相关接口全员 403。
- 操作日志定长列（resource_name/ex_message）拼接列表值时统一模式：200 字符上限 + 超限回退条数摘要（`共N个资源，明细已省略`），避免超列长写入失败。
- 资源展示名随请求由前端传递（id 本就前端传入），后端不做跨库反查资源主表——分库分表规划下不可依赖 framework 直查 pipeline_info。
