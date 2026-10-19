# Archive: remove-ort-dependency

- 仓库: openlibing-sbom
- 特性分支: `feat-remove-ort-dependency`
- 业务 Issue: https://gitcode.com/openlibing/openlibing-sbom/issues/112
- 业务 PR: https://gitcode.com/openlibing/openlibing-sbom/pull/158（→ `release_20261019_iter1`）
- 交付 commit（业务分支 head `a22ec3d5`）：
  - `934be424` 主交付：ORT 依赖移除（64 文件，+313/−3347）
  - `c9f9d4f4` 追加：SPDX 3.0.1 类型支持移除 + fetchOpenEulerRepoMeta 定时任务下线（5 文件，+12/−70）
  - `a22ec3d5` 追加：PR 检视修复，测试残留与 FileUtil 死代码清理（7 文件，+4/−383）
  - `00399e78` 冲突解决：合入 `release_20261019_iter1`（Spring Boot 4 迁移），保持删除正确
- 归档日期: 2026-10-19（检视修复后更新）

## 交付结果

移除 openlibing-sbom 对 org.ossreviewtoolkit（ORT）的完全依赖：

- 下线 `definition_file` / `sbom_tracer_data` 两类任务支持，analyzer 模块整体删除（26 文件）
- Batch 链路简化：删 2 个 Analyze Step + SkipAnalyzeSbomContentDecider，job XML 直连
- API 下线：`POST /uploadSbomTraceData` 移除；`/publishSbomFile(WithCompress)` 两类 type 返回 400
- FillUpLicenseStep 换用 `org.spdx:java-spdx-library`，新增 `SpdxLicenseExpressionUtil`/`SpdxLicenseParseException`
- raw_sbom 任务查询增加 value_type 白名单（`RawSbomRepository` default 方法），存量已下线类型记录不被调度
- 业务代码 `org.ossreviewtoolkit` import 与 Maven 依赖清零（sbom-tools 子模块源码不在范围）

追加交付（c9f9d4f4，使用者可感知的能力变化）：

- **移除 `SbomContentType.SPDX_3_0_1_JSON_SBOM` 类型支持**：枚举值删除，`findBySpecAndFormat` 收敛为仅 SPDX 2.2 + JSON 分支；上传/导出 SPDX 3.0.1 文档由"value_type 入库后永不调度（垃圾数据）"改为直接抛 `unsupported spec and format` 拒绝；`/publishSbomFile(WithCompress)` 的合法类型列表收敛为仅 `[spdx_2.2_json_sbom]`；`SbomSpecification.SPDX_3_0_1` 枚举保留（存量文档查询引用）
- **下线 fetchOpenEulerRepoMeta 定时任务**：删 `fetchOpenEulerRepoMetaJobDetail`/`Trigger` Bean 与 `FetchOpenEulerRepoMetaJob`（每周六 cron 已过时）；`SbomController#fetchOpenEulerRepoMeta` 手动触发途径保留

追加交付（a22ec3d5，PR 检视修复）：

- 清理 uploadSbomTraceData 相关测试残留：TestConstants 零引用常量、`mindsporeTracerTest_tracer_result.tar.gz` 样例、data.sql 产品种子行
- 删除仅测试可达的生产代码：`FileUtil` 的 `extractTarGzipArchive`×3/`extractTarArchiveInputStream`/`ensureDirExists`×2（`tarBytes` 保留，导出链路在用）、零引用测试辅助类 `TestCommon` 整类
- 文档同步：`doc/import_sbom/importSbom.md` 移除 eBPF 监控数据/包管理器配置导入来源描述，弃用章节加注 SkipAnalyzeSbomContentDecider 下线

## 验证结论

- 主交付（934be424）：全模块 compile/test-compile 通过；相关单测 28/28；`dependency:tree` 全模块无 ORT；业务代码全局 grep 0 命中；pre-commit 13 hook 全通过
- 追加交付（c9f9d4f4/a22ec3d5）：每次均 clean 后全仓编译 + 单测通过（PublishSbomRequestValidatorTest 8/8 含 SPDX 3.0.1 拒绝用例、RepoServiceImplTest 9/9、SbomServiceImplTest 82/82、SbomControllerTest 40/40）；pre-commit 全 hook 通过
- `org.ossreviewtoolkit`/`SPDX_3_0_1_JSON_SBOM` 业务代码 grep 清零（`SbomSpecification.SPDX_3_0_1` 与测试字面量按设计保留）
- beta 环境部署验证通过（sbom-dev `2ffb8465`，含 934be424 + c9f9d4f4）：SPDX SBOM 发布全流程 + license 关联正确；两类 type 拒绝；404；存量数据不影响调度；检视修复 `a22ec3d5` 随 sbom-dev `775b463d` 部署验证中

## 与设计方案的偏差记录

| 偏差                                                                                  | 原因                                                                                                                                           |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| java-spdx-library 由 1.1.12 改为统一 2.0.3（项目既有基线）                            | utils 模块 `LicenseUtil` 依赖 2.x API（`LicenseCompareHelper.listAllListedLicenseIdsMatched`），1.x 不具备；两个大版本不能共存于同一 classpath |
| 查询白名单收敛为 `RawSbomRepository` default 方法                                     | `JobConfiguration`（job 重启）是第二个调用方，白名单逻辑收敛到仓库层                                                                           |
| 附加修复 `.pre-commit-config.yaml`（3 个 Maven hook 移除 `-pl '!analyzer,...'`）      | analyzer 模块删除后 hook 的 reactor 选择器失效                                                                                                 |
| 范围扩展（c9f9d4f4）：移除 SPDX 3.0.1 类型支持 + 下线 fetchOpenEulerRepoMeta 定时任务 | 需求补充：SPDX 3.0.1 实际不支持（原先仅 validator 显式拒绝，枚举残留），定时任务功能已过时；详见「追加交付」                                   |
| 范围扩展（a22ec3d5）：测试残留与 FileUtil 死代码清理                                  | PR 检视发现 uploadSbomTraceData 删除后的零引用残留与仅测试可达生产代码；详见「追加交付」                                                       |

## 过程冲突与解决

- **PR #158 与 release_20261019_iter1 冲突（7 个 modify/delete）**：release 侧 Spring Boot 4 迁移（Spring Batch 包名调整）改动了被删文件，解决为保持删除；merge commit `00399e78`
- **根 pom 重复管理**：dependencyManagement 中 `org.spdx:java-spdx-library` 原有 2.0.3 声明（L76），新增 1.1.12 条目会覆盖生效导致 LicenseUtil 编译失败——统一回 2.0.3 后解决

## 经验沉淀

1. **IDE 文件缓冲回写**：Trae IDE 打开的文件可能用旧缓冲覆盖磁盘（本任务 FillUpLicenseStep 被回滚 3 次、SbomService 等被回写为旧版含已删 API）。对策：编码前确认 IDE 未打开目标文件或已重新加载；出现竞态时请用户关闭标签页再写入；破坏性回写用 `git stash push -- <files>` 隔离而非直接丢弃，便于追溯
2. **删除第三方库依赖前先全局盘点 API 面**：`FillUpLicenseStep` 用法极浅（parse + licenses()），但同仓其他模块（utils/LicenseUtil）可能依赖同一库的不同 API 面——版本决策必须以"全仓最大 API 需求"为准
3. **java-spdx-library 2.x 解析行为**：非法/空白表达式不抛异常而是返回 `InvalidLicenseExpression` 占位对象，需显式检查（含"叶子收集为空"兜底）才能保留调用方的 fallback 语义
4. **删除模块时检查 pre-commit/CI 配置**：模块名可能硬编码在 `.pre-commit-config.yaml`、流水线脚本的 `-pl` 选择器中
5. **Windows 下 maven 私仓件 "present, but unavailable"**：加 `-Daether.enhancedLocalRepository.trackingFilename=_remote.repositories.disabled` 可解（本地仓 tracking 标记缺失）
