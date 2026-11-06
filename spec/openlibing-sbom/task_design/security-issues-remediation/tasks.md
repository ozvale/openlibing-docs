# 实现清单：安全 Issue 集中整改

> 分支 `fix-security-issue` → 已合入 `sbom-dev`；commit 与整改结果均已在对应 Issue 评论区留档。

## #170 导出回执异常收敛

- [x] `SbomExportServiceImpl` catch 链收敛（SbomRuntimeException 保留 / IOException 与未知 RuntimeException 固定文案）
- [x] `SbomExportServiceImplTest` 新增 2 个收敛用例（20/20 通过）
- [x] Issue #170 评论区发布修复方案（commit `42dd897c`）

## #158 解码缓冲统一

- [x] `LicenseClientImpl` 1GB 硬编码 → 复用 `spring.codec.max-in-memory-size`（全局值固定 256MB，见 `application.properties`，属经评估的业务决策：SBOM 数据体量大，10MB 级上限不适用）
- [x] Issue #158 评论区发布整改补充
- [ ] 遗留（登记为待办，本项不勾选）：Spring 解码器 shim 是否移除确认、大文件下载路径流式化、出站下载并发限流（见「待办」清单）

## #92 路径穿越定性

- [x] 核查告警代码已被 `a22ec3d5`（Refs #112）死代码清理删除
- [x] Issue #92 评论区发布验证结论（可关闭）

## #90 漏洞依赖治理

- [x] 删除 sshd-core 三处声明（属性/DM/直依赖）
- [x] common BOM 1.0.21.3 + httpcore5 5.4.3 + joda-time 2.14.3 升级；Log4j 治理移交 Boot BOM
- [x] 删除 spring-boot-starter-parent 全量对比（338 节点，3 处 minor 漂移）
- [x] 修复删 parent 连锁坑：compiler `-parameters` + surefire 3.2.5 pluginManagement + `@Param` 补齐
- [x] kotlin-stdlib-common 1.8.0 链路定性：引入链路为 okio-jvm 3.4.0（dependency:tree 确认）；jar 实测 374 个 entry、0 个 `.class` 文件（仅 `.kotlin_metadata`/`.kotlin_builtins`），无可执行字节码，无 CVE 攻击面。注：#90 扫描所报 kotlin CVE 针对 2.0.20 的完整 stdlib，与本 artifact 无关
- [x] Issue #90 评论区发布整改结果

## #89 / #100 域名外置 Nacos

> 计数口径：SENINFO 扫描命中 78 项 = A 类 16（运行时配置）+ B 类 1（代码常量）+ C 类 61（噪音）。`sbom.service.website.domain` 为清单外增量项（关联 #105），一并外置后外置 key 共 17 个。

- [x] A 类 16 项：vcs/uvp/sonatype/license.properties 域名 key 本地清空、Nacos 配值（beta/prod 按 namespace 区分）
- [x] 增量 1 项：`sbom.service.website.domain` 本地清空、Nacos 按 namespace 配值
- [x] B 类 1 项：`LicenseClientImpl` 域名常量改 `@Value` 注入
- [x] C 类 61 项噪音定性归档
- [x] Nacos 侧配置录入（openlibing-beta / openlibing-prod 两个 namespace 的 `sbom` dataId）
- [x] gamma 部署验证 17/17 `[OK]`（16 A 类 + 1 增量；临时 NacosConfigCheckRunner，验证后删除）
- [x] Issue #89、#100 评论区发布整改/定性记录（#100 弱口令定性为测试用例假口令，非真实凭据、不与任何真实实例重合，无占位化/轮换需求）

## 门禁规则豁免（含依据）与工具链整改

> 说明：规则豁免/检测抑制属门禁弱化操作，以下各项均记录判定依据与缓解位置；豁免仅覆盖列明的方法/文件，新增代码不受豁免。

- [x] root pom 激活 findsecbugs-plugin + sb-contrib（真实门禁增强）
- [x] CRLF 误报：4 类 `@SuppressFBWarnings` + spotbugs-annotations(provided)，justification 注明运行时 log4j2 `%enc{CRLF}`/`%replace` 清洗兜底；include 白名单该 pattern 保持在线，豁免仅限列明 4 类
- [x] COMMAND_INJECTION 豁免：`spotbugs-exclude.xml` 以 Class+Method 级 Match 仅覆盖 `SignatureUtil.sign` 两个重载，注释写明判定依据与缓解位置——数组式 `ProcessBuilder.command()` 不经 shell；`file` 上游 `sign(String,byte[])` 已 normalize+startsWith(tmpDir) 白名单校验；`client/clientConfig/keyName` 为 `@Value` 服务端配置且 `checkFile()` 做存在性校验。残留面（`sign(String)` 重载为 public、可被未来调用方传入任意路径）在此记录；不单独立 Issue，失效前提（命令改字符串拼接或引入用户可控入参须删除豁免重新评估）写入豁免注释。
- [x] bandit：branch-diff.py 去 shell=True；run-mvn.py nosec 独立行
- [x] 清理 root 模块陈旧 `target/classes`（56 处误报的本地根因）
- [x] `pre-commit run --all-files` 14/14 全绿

## 待办（不在本 spec 范围）

- [ ] #105 生产 Swagger UI 收敛（swagger url 环境差异项）
- [ ] #149 H 级：CI 不可信 PR 检出与凭证注入（挂起）
- [ ] #53 LogSanitizer 残留确认关闭
- [ ] CVE 子 issue（#77/#70/#69/#66/#59/#48/#33/#19）随 #90 关闭
- [ ] 向 common 仓反馈 kotlin.version Beta → stable
- [ ] 启动期 fail-fast 校验：对 A 类关键域名 key 做非空断言，覆盖非 Nacos/配置缺失场景（当前仅 UvpClientImpl 有空值守卫）
- [ ] Spring 解码器 shim 移除确认（`BOOT-INF/classes` 下不得存在 `org/springframework` 覆盖路径）
- [ ] 大文件下载路径流式化 + 出站下载并发限流（#158 残余 DoS 面）
- [ ] 非关键出站 client（LicenseClientImpl/SonatypeClientImpl 等）空值兜底对齐 UvpClientImpl 的守卫模式
