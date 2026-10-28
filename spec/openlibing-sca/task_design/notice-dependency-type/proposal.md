# NOTICE 扫描明细依赖类型与按依赖范围导出

## 需求背景

NOTICE 扫描明细（`tbl_project_notice_scan_detail`）目前不区分软件是直接依赖还是间接依赖。SBOM 侧（openlibing-sbom `sbom-dev` 分支）已具备依赖类型判定能力（`package_statistics.dependency_type`，基于 SPDX 关系计算：根包自身 + 根包 DEPENDS_ON 目标 + SPDXRef-DOCUMENT 直接 DEPENDS_ON 目标 + 未被任何包依赖的包 = 直接依赖；非根包 DEPENDS_ON 目标 = 间接依赖；交集 = 直接&间接），并已新增内部接口 `POST /internal-api/queryPackageDependencyTypes` 向调用方透传原始数据（name/version/downloadLocation/purl/dependencyType，不去重不归并，取舍逻辑由调用方 sca 处理）。

业务 Issue：https://gitcode.com/openlibing/openlibing-sca/issues/112

## 功能描述

做：

1. `tbl_project_notice_scan_detail` 新增 `dependency_type` 列（INT，NULL），枚举语义与 SBOM `DependencyType` 对齐：0-直接依赖 / 1-间接依赖 / 2-直接&间接依赖 / NULL-未补充。
2. 新扫描（`startScan`）解析 SBOM 明细后，调用 SBOM internal-api 查询依赖类型，按（softwareName, version）匹配归并回填；SBOM 调用失败降级为 NULL，不阻断扫描。
3. 存量补充接口：按制品（productNames 列表）回填其**全部历史扫描**明细的 `dependency_type`，幂等可重复执行。
4. 导出拆分：`/export` 与 `/exportBatch` 增加可选参数 `exportScope`（FULL-全量默认 / DIRECT-仅直接依赖），导出内容按依赖范围过滤重建，缺省行为向后兼容。

不做：

- 不改动 SBOM 仓（其接口已就绪）。
- 不改动 NOTICE 扫描主流程的下载/提取/合并逻辑（仅明细增加一个字段填充）。
- 不提供按依赖类型的明细过滤查询（/info 仅透出新字段）。

## 验收标准

- [ ] 新扫描明细自动填充依赖类型，与 SBOM package_statistics 口径一致（0/1/2 语义）
- [ ] SBOM 依赖类型查询失败时扫描正常完成，明细依赖类型为 NULL
- [ ] 补充接口可对指定制品的全部历史扫描明细回填依赖类型，幂等，并为最新一次扫描重建直接依赖合并文件
- [ ] 扫描完成与补充重建时同时生成全量与直接依赖两份合并 NOTICE 文件（direct 生成失败不影响扫描终态）
- [ ] 导出支持 FULL（全量，含直接+间接依赖）与 DIRECT（仅直接依赖，纯转存 direct 文件）两种范围，缺省 FULL
- [ ] Liquibase 迁移脚本（detail 表 dependency_type 列 + scan 表 direct_merged_oss_url 列）+ 相关单元测试通过

## 影响范围

- 业务仓 `openlibing-sca`（dm 模块为主，涉及 analysis entity/dto/vo、common feign/enums、resources mapper/liquibase、test）。
- docs 仓 `openlibing-docs`（spec 归档）。
