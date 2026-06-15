# sec-option-scan: 安全编译选项扫描

## 需求背景

配合 test-devops 仓的 sec-option-scan 插件，需要在 openlibing-cicd 项目中新增安全编译选项扫描结果的上报接口、数据入库和查询接口。

扫描的 8 项安全编译选项：
- BIND_NOW
- NX
- PIC
- PIE
- RELRO
- Run-time Search Path
- SP (Stack Protector)
- Strip

## 验收标准

- [x] POST /metrics/sec-option/report 接口可接收并存储扫描结果
- [x] GET /metrics/sec-option/overview 接口支持按代码仓和流水线ID筛选概览数据
- [x] GET /metrics/sec-option/file-detail 接口支持按构建产物包名查询文件级详情
- [x] 两张表使用 JSON 列存储，支持 8 项安全编译选项，便于后期扩展
- [x] 概览数据中每个选项包含 rate/validFiles/yesCount/noCount/naCount
- [x] Liquibase changelog 建表脚本完整
- [x] 接口参数校验和异常处理完善
- [x] 自动拼接流水线链接

## 关联 Issue

- openlibing/openlibing-cicd#114
