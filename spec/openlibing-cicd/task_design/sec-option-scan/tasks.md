# sec-option-scan 实现任务

## openlibing-cicd 仓

- [x] 创建 Liquibase 建表脚本（sec_option_scan_record + sec_option_scan_file_detail）
- [x] 创建 Entity 类（SecOptionScanRecordEntity + SecOptionScanFileDetailEntity）
- [x] 创建 DTO 类（SecOptionScanReportDTO + SecOptionFileDetailDTO）
- [x] 创建 VO 类（SecOptionOverviewVO + SecOptionFileDetailVO）
- [x] 创建 Mapper 接口（SecOptionScanRecordMapper + SecOptionScanFileDetailMapper）
- [x] 创建 Service 接口和实现（SecOptionScanService + SecOptionScanServiceImpl）
- [x] 创建 Controller（SecOptionScanController）
  - [x] POST /metrics/sec-option/report
  - [x] GET /metrics/sec-option/overview
  - [x] GET /metrics/sec-option/file-detail

## test-devops 仓

- [x] 创建 action.yml（含 source-dir、run-number、package-name 输入）
- [x] 创建 Python 扫描脚本（bin/sec_option_scan.py，基于 pyelftools）
- [x] 创建 Node.js 入口（dist/index.js）
- [x] 创建扫描器（dist/scanner.js）
- [x] 创建检测器（dist/detectors/SecOptionDetector.js）
- [x] 创建上传器（dist/uploaders/CicdUploader.js）
- [x] 创建配置加载器（dist/config/loader.js）
- [x] 创建日志工具（dist/utils/logger.js）
- [x] 创建默认配置（.sec-option.yml）
- [x] 创建工作流示例（.gitcode/workflows/sec-option-scan.yaml）
