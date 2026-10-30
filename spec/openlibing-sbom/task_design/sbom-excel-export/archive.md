# SBOM 导出异步化改造 — 最终归档

> change-name: `sbom-excel-export`
> 业务 Issue：[openlibing/openlibing-sbom#163](https://gitcode.com/openlibing/openlibing-sbom/issues/163)
> 交付 PR：[openlibing-sbom#166](https://gitcode.com/openlibing/openlibing-sbom/pull/166)（→ release_20261029_iter2）、[openlibing-web#845](https://gitcode.com/openlibing/openlibing-web/pull/845)（→ release_20261029）
> 归档时间：2026-10-30

## 1. 需求与方案（详见 [proposal.md](./proposal.md) / [design.md](./design.md)）

SBOM 组件分析页「全量导出」异步化双改造：新增软件成分数据（xlsx）导出能力，SBOM 规范文档导出从同步接口切换到平台统一《我的导出》异步导出框架（framework `obs_file` 任务记录 + 本地线程池异步生成 + OBS 上传 + 签名 URL 下载）；前端导出弹窗新增「类型」单选，标题改为「导出软件物料数据」。附带改动：制品列表与 SCA 制品名接口过滤无解析状态数据（LEFT JOIN → INNER JOIN + `task_status IS NOT NULL`）。

方案演进说明：异步调度最初设计为 RabbitMQ，实现阶段改为**双线程池隔离**（Excel 池 core=2/max=2/queue=100、文档池 core=1/max=1/queue=100，AbortPolicy + 队列打满回写失败原因），无 MQ 依赖；OBS 配置改由 framework Nacos data-id（`optional:nacos:framework`）统一下发。

## 2. 交付清单

### openlibing-sbom（后端）

分支 `feat-sbom-excel-export`（干净重建：基于 prod/master cherry-pick 本任务 8 个提交，排除测试分支合并带入的同事提交）：

| commit     | 内容                                                                              |
| ---------- | --------------------------------------------------------------------------------- |
| `386cd8d3` | 主改动：统一异步导出（编排服务/双线程池/OBS 上传/2 接口/DTO/单测）                |
| `c16b4ad0` | 附带改动：制品列表与 SCA 名单过滤无解析状态数据                                   |
| `f2f35f42` | ObjectMapper 注入改用 Mapper.objectMapper（Jackson 3 栈适配）                     |
| `61e0072a` | 导出分批查询+VO 物化包 TransactionTemplate 短事务（修复懒加载异常）               |
| `7d36ace5` | 文档导出对齐同步链路打包 .tar.gz（sbom + sha256 + 签名）                          |
| `073f7085` | Excel「无风险」列宽修正表头单行                                                   |
| `042b5f78` | 导出字段空值口径与页面一致（`--`/Others）                                         |
| `55ca4baa` | 顺带：GitCode VCS 无条件重试层退避 1s→60s                                         |
| `31d60110` | guava 33.3.1/33.4.8 → 33.7.2-jre（清 CVE-2026-102554，过 oss-pr-scan 门禁）       |
| `b0d83ada` | 第一轮检视修复（10 项采纳，详见 PR #166 检视回复）                                |
| `49acd726` | 第二轮检视修复（@Async 执行器绑定/双重编码/孤儿对象清理）                         |
| `44f920ad` | 合入 release_20261029_iter2（PR 目标分支变更后的冲突消解，组合已跑全量 797 用例） |

### openlibing-web（前端）

分支 `feat-sbom-excel-export`（同样干净重建后迭代）：

| commit      | 内容                                                                              |
| ----------- | --------------------------------------------------------------------------------- |
| `03d0b2bea` | 主改动：导出弹窗重构（类型单选/统一异步提交/接口定义/类型映射/tooltip）           |
| `c4995f717` | 弹窗标题改「导出软件物料数据」                                                    |
| `4bb76d16`  | 第一轮检视修复（不可达分支删除/exportSbom 死代码清理/《我的导出》新增类型列）     |
| `dddaf065`  | extractExportIdFromResponse 兼容 number 形态（修复跨仓 Integer 契约回归，5 单测） |
| `6bf7ed6d`  | 合入 release_20261029（PR 目标分支变更后的冲突消解，类型列与文件大小列共存）      |

## 3. 质量验证

- 后端：全模块 `mvn test` 797 用例 0 失败（含导出编排 15+ 用例：任务分发/队列拒绝/真实线程池饱和/CAS 流转/tar 打包/行级页面口径/临时文件清理/OBS 回写失败清理）；改动文件 pre-commit 全过
- 前端：Prettier/ESLint pre-commit 全过；extractExportId 5 单测
- beta 实测：xlsx 与文档导出全链路（提交→浮窗进度→下载）、产物 .tar.gz 三件套、字段口径与页面一致、无解析状态过滤生效

### 3.1 顺带行为变更回归说明

两个顺带 commit 属于行为变更（非纯内部重构），说明影响与回归口径：

| commit     | 行为变更                                                                                                                                                            | 影响评估                                                                                                                                             | 回归场景                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `55ca4baa` | GitCode VCS 客户端无条件兜底重试层退避 1s→60s；其中 `fetchLicenseFromApi`/`fetchLicenseFromRawFile` 与外层重复的兜底层经第一轮检视后移除（仅保留 429 限流条件重试） | 持续性失败不再以 1s 间隔高频请求 GitCode API，降低限流/雪崩风险；代价是瞬态故障恢复等待变长，license 拉取对非 429 失败不再自动重试                   | 制品解析时 VCS license/tag/language 补全的成功率与耗时；GitCode API 限流相关告警趋势 |
| `31d60110` | guava 33.3.1/33.4.8 → 33.7.2-jre（补丁版本升级，清 CVE-2026-102554）                                                                                                | 补丁版本间无已知破坏性 API 变更；仓内直接使用面为 `SbomServiceImpl`/`RepoMetaParserImpl`/`RpmSpecParser`，全仓 797 用例 0 失败 + beta 全链路实测覆盖 | 仓库元数据解析、RPM spec 解析、SBOM 服务内 guava 集合工具路径；oss-pr-scan 门禁通过  |

## 4. 检视处理记录

- **第一轮（atomgit-bot）**：sbom 12 条建议（10 采纳 / 1 误报反驳 / 1 设计决策不采纳）、web 3 条全部采纳；逐条已在对应讨论串回复
- **第二轮（真人：ozvale/yanzhaohong/z_awei/Yubing0_0）**：sbom 3 条行内全部采纳；web 1 条行内为已修复问题的复核（指向 dddaf065）；另有多人 /lgtm

## 5. 过程事件与教训

1. **特性分支污染**：测试分支（sbom-dev/beta_gamma）合并进特性分支导致 PR diff 混入大量同事未合 master 提交 → 以「master 重建 + cherry-pick 本任务提交」方式干净交付；测试分支保持原状供 beta 部署。
2. **存量漏洞暴露**：oss-pr-scan 高危门禁（限值 0）卡在 master 存量的 guava CVE-2026-102554，非本 PR 引入；升级到修复版 33.7.2-jre 解决（两模块版本统一）。
3. **跨仓契约回归**（最重要）：后端返回 ID 从 String 改 Integer 后，前端共享工具 `extractExportIdFromResponse` 的 typeof 判定不识别 number，任务创建成功但页面误报失败。教训：**跨仓修改接口契约时，必须排查消费方（含共享工具函数）的类型判定，不能假设"不透明透传无感"**。
4. **@Async 执行器退化**：容器内 Executor bean 从 1 个变 3 个后，裸 `@Async` 无法唯一定位 TaskExecutor，退化为无界 SimpleAsyncTaskExecutor；新增线程池 bean 时必须排查存量裸 `@Async` 并显式指定执行器。
5. **PR 目标分支变更**：两个 PR 后续被改到 release 分支（release_20261029 / release_20261029_iter2）产生冲突；解决方式为在特性分支 merge 目标 release 分支（而非 rebase），冲突仅 1 处 import 共存类。
6. **成功回写失败的孤儿资源**：上传 OBS 成功但状态回写失败会留下孤儿对象与卡死任务，回写失败路径需同步清理已上传对象。

## 6. 验收对照

| 验收标准（proposal.md）               | 结果                                    |
| ------------------------------------- | --------------------------------------- |
| SBOM 类型异步导出，产物与同步导出一致 | ✅ beta 实测通过（tar.gz 三件套）       |
| xlsx 导出全量 15 列、口径与页面一致   | ✅ beta 实测通过                        |
| 失败原因在《我的导出》可见            | ✅（失败文案截断 255）                  |
| 大制品导出不占请求线程、无超时        | ✅（双线程池隔离）                      |
| 同步导出接口行为不变                  | ✅（`/exportSbom` 保留未动）            |
| 制品列表过滤无解析状态数据            | ✅（含 DISTINCT ON id DESC 确定性加固） |

## 7. 后续事项

- PR #166 / #845 待随 release_20261029 / release_20261029_iter2 发版合并；业务 Issue #163 随 PR 合入关闭
- beta 环境部署 sbom-dev（含第二轮检视修复 `49acd726`；sbom-dev 上的合并提交为 `90bd77a2`）后建议回归：@Async 依赖预计算、中文制品名导出的下载名显示
