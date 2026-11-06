# 实现清单：安全 Issue 集中整改

> 分支 `fix-security-issue` → 已合入 `sbom-dev`；commit 与整改结果均已在对应 Issue 评论区留档。

## #170 导出回执异常收敛

- [x] `SbomExportServiceImpl` catch 链收敛（SbomRuntimeException 保留 / IOException 与未知 RuntimeException 固定文案）
- [x] `SbomExportServiceImplTest` 新增 2 个收敛用例（20/20 通过）
- [x] Issue #170 评论区发布修复方案（commit `42dd897c`）

## #158 解码缓冲统一

- [x] `LicenseClientImpl` 1GB 硬编码 → 复用 `spring.codec.max-in-memory-size`
- [x] Issue #158 评论区发布整改补充

## #92 路径穿越定性

- [x] 核查告警代码已被 `a22ec3d5`（Refs #112）死代码清理删除
- [x] Issue #92 评论区发布验证结论（可关闭）

## #90 漏洞依赖治理

- [x] 删除 sshd-core 三处声明（属性/DM/直依赖）
- [x] common BOM 1.0.21.3 + httpcore5 5.4.3 + joda-time 2.14.3 升级；Log4j 治理移交 Boot BOM
- [x] 删除 spring-boot-starter-parent 全量对比（338 节点，3 处 minor 漂移）
- [x] 修复删 parent 连锁坑：compiler `-parameters` + surefire 3.2.5 pluginManagement + `@Param` 补齐
- [x] kotlin-stdlib-common 1.8.0 链路定性（空壳 artifact，无 CVE 风险；待向 common 仓反馈）
- [x] Issue #90 评论区发布整改结果

## #89 / #100 域名外置 Nacos

- [x] A 类 17 项：vcs/uvp/sonatype/license.properties + `sbom.service.website.domain` 本地清空、Nacos 配值（beta/prod 按 namespace 区分）
- [x] B 类 1 项：`LicenseClientImpl` 域名常量改 `@Value` 注入
- [x] C 类 61 项噪音定性归档
- [x] Nacos 侧配置录入（openlibing-beta / openlibing-prod 两个 namespace 的 `sbom` dataId）
- [x] gamma 部署验证 17/17 `[OK]`（临时 NacosConfigCheckRunner，验证后删除）
- [x] Issue #89、#100 评论区发布整改/定性记录（#100 弱口令定性为环境侧，建议测试资源改密）

## 门禁加固

- [x] root pom 激活 findsecbugs-plugin + sb-contrib
- [x] CRLF 误报：4 类 `@SuppressFBWarnings` + spotbugs-annotations(provided)；白名单检测保持在线
- [x] COMMAND_INJECTION：`spotbugs-exclude.xml` 方法级豁免 SignatureUtil.sign
- [x] bandit：branch-diff.py 去 shell=True；run-mvn.py nosec 独立行
- [x] 清理 root 模块陈旧 `target/classes`（56 处误报的本地根因）
- [x] `pre-commit run --all-files` 14/14 全绿

## 待办（不在本 spec 范围）

- [ ] #105 生产 Swagger UI 收敛（swagger url 环境差异项）
- [ ] #149 H 级：CI 不可信 PR 检出与凭证注入（挂起）
- [ ] #53 LogSanitizer 残留确认关闭
- [ ] CVE 子 issue（#77/#70/#69/#66/#59/#48/#33/#19）随 #90 关闭
- [ ] 向 common 仓反馈 kotlin.version Beta → stable
