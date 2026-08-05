# sec-option-scan-enhance 实现任务

## openlibing-cicd 仓

- [x] Liquibase changeset 20260723 新增 pipeline_name / package_download_accessible / repo_url / scan_options 列
- [x] Liquibase changeset 新增 idx_sec_option_record_repo_url / idx_sec_option_record_pipeline_name 索引
- [x] SecOptionScanRecordEntity 新增 pipelineName / packageDownloadAccessible / repoUrl / scanOptions 字段
- [x] SecOptionScanReportDTO 新增 pipelineName / repoUrl / scanOptions 字段
- [x] SecOptionOverviewQueryDTO 筛选字段改为 repoUrl / pipelineName / packageName 模糊匹配
- [x] SecOptionDropdownQueryDTO 新增 repoUrl / pipelineName / packageName 级联筛选
- [x] SecOptionFileDetailQueryDTO 定位方式改为 repoUrl + runNumber + packageName
- [x] SecOptionOverviewVO.SecOptionRecordItem 新增 repoUrl / pipelineName / scanOptions / downloadUrl / downloadAccessible
- [x] SecOptionDropdownVO 新增 repoUrls / pipelineNames / packageNames
- [x] SecOptionFileDetailVO 新增 repoUrl / pipelineName
- [x] SecOptionScanServiceImpl 实现 HTTP HEAD 可访问性检测
- [x] SecOptionScanServiceImpl.saveScanRecord 写入新字段
- [x] SecOptionScanServiceImpl.queryRecords 按 repoUrl/pipelineName/packageName 模糊匹配
- [x] SecOptionScanServiceImpl 下拉框三维度去重查询 + 级联筛选
- [x] SecOptionScanServiceImpl.findRecord 按 repoUrl + runNumber + packageName 精确定位
- [x] BuildArtifactController 接口路径和日志更新

## code-metrics-scan 仓

- [x] sec_option_scan.py 新增 ALL_OPTION_KEYS 常量（13 项）
- [x] sec_option_scan.py 新增 fortify() 检测函数
- [x] sec_option_scan.py 新增 fvisibility() 检测函数
- [x] sec_option_scan.py 新增 ftrapv() 检测函数
- [x] sec_option_scan.py 新增 stack_clash() 检测函数
- [x] sec_option_scan.py 新增 aslr() 检测函数
- [x] sec_option_scan.py main() 接受第 3 个 CLI 参数 scan-options
- [x] sec_option_scan.py analyze_single() 按 scan_options 过滤检测项
- [x] sec_option_scan.py compute_summary() N/A 项 rate=-1，未扫描项 key 缺失
- [x] action.yml 新增 scan-options 输入参数，版本升至 1.4.0
- [x] index.js 读取 scan-options / ATOMGIT_WORKFLOW / 拼接 repoUrl
- [x] index.js 传递 scanOptions / pipelineName / repoUrl 给 scanner.scan()
- [x] scanner.js 传递 scanOptions 给 detector.detect()
- [x] scanner.js 传递 scanOptions / pipelineName / repoUrl 给 uploader.upload()
- [x] SecOptionDetector.js detect() 接受 scanOptions 参数，传给 Python CLI
- [x] CicdUploader.js upload() payload 新增 pipelineName / repoUrl / scanOptions
- [x] README.md 更新为 13 项表格 + 工作流示例
