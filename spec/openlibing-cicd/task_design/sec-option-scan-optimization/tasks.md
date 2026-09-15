# 安全编译选项扫描能力优化 任务清单

> 跨仓 Standard 模式。进度以 checkbox 反映各仓实现情况。

## 插件 security-compilation-options-action

- [x] 插件 filePath 源头相对化（相对扫描根，`/` 分隔，去随机解压临时目录前缀）
- [x] summary 增加 `totalScannedFiles`（修复日志"Total files 恒为 0"）
- [x] 纯 Go 二进制 fortify/ftrapv 返回 N/A（与 sp 一致）
- [x] scanner 按 `summary.failedCount`/`totalScannedFiles` 计算部分成功状态(status 0/1/2)
- [x] 统一 rpath 语义（YES 合规 / NO 不合规）
- [x] 重建 `dist/index.js` 打包产物，与源码保持一致
- [x] 提 PR → openlibing 主仓 master

## 后端 openlibing-cicd

- [x] `/overview` 出参补全未扫描项 `{"scanned":false}` + 每项透出 totalFiles/applicableFiles/yesCount/rate
- [x] overview 行级新增 totalScannedFiles / filingCoverage / applicableFiles
- [x] file-detail 出参拆 options（仅已备案= FILED）与 rawOptions（全量原始值，未扫描= UNSCANNED）
- [x] file-detail optionFilters 支持 YES/NO/N/A（按 rawOptions 原始值）与 FILED（按备案存在性），可同时选中取并集
- [x] filing/list 扁平行列表 SQL 分页（filePath 模糊 / optionKeys / scanValues / filedStatus / filerName / 时间区间筛选）
- [x] 新增 sec_option_filing 表（Liquibase changeSet）+ unique 复合索引 idx_filing_join
- [x] 新增备案接口：save（批量 upsert，自然键）/ cancel（按 id 删除），角色鉴权
- [x] 新增 record-list 跨包备案记录查询（repoUrl / packageName / optionKey / filerName / filingStartTime / filingEndTime 筛选 + filingTime 排序）
- [x] 新增 filer-list 备案人名单（含每人备案数据项数）
- [x] `/overview` 分页与排序下推 SQL（去掉内存分页）
- [x] 提 PR → openlibing-cicd 主仓 release_20260915

## 前端 openlibing-cicd-web

- [ ] 一级概览页 `/sec-option`（只展示基础信息，不展示扫描项覆盖率数字）
- [ ] 二级详情页 `/sec-option-detail`（逐扫描项检测覆盖率 vs 确认覆盖率，附公式；检测结果数字可点开文件×扫描项矩阵弹窗）
- [ ] 文件详情弹窗（文件×扫描项矩阵，表头逐列筛选、有备案以备案值为准、分页）
- [ ] 三级待备案项列表 `/sec-option-filing-list`（默认只看 NO 项，筛选+全选当前筛选结果+批量备案，跨页保留勾选；已备案行可取消）
- [ ] 独立备案记录页 `/sec-option-filing-records`（跨包，产物包/扫描项/备案时间/备案人筛选 + 排序分页）
- [ ] UNSCANNED 项隐藏；备案写操作按角色控制（仅审批人可见/可用）

## code-metrics-scan（镜像插件）

- [x] 同步 sec_option_scan.py（failedCount/totalScannedFiles/rpath 语义/纯 Go N/A/调试日志）
- [x] 同步 scanner.js（部分成功状态计算）
- [x] 同步 SecOptionDetector.js（空结果返回去多余 averageRate）
- [x] 检查 CicdUploader.js / utils/logger.js 一致
- [ ] 待确认 index.js 分叉处理（code-metrics 缺失 downloadSubdir 逻辑，含自有 ATOMGIT_OUTPUT overview 特性）
- [ ] 提交 3 个已同步文件到分支 sync-sec-option-relativize

## docs 归档 openlibing-docs

- [x] proposal.md / design.md / tasks.md 生成
- [ ] 提 docs PR → openlibing-docs 主仓 master
