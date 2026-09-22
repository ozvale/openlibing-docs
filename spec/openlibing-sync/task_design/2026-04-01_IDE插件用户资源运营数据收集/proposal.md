# 工程能力看板 — 数据接入与测试用例解析插件

## 需求背景

OpenLibing 同步服务需要构建工程能力看板的数据底座，支撑两个核心能力：
1. **通用数据接入能力**：允许第三方应用通过统一 API 接口将运营数据写入 Doris 数据模型，支持动态建表和字段映射，为看板提供数据来源。
2. **测试用例元数据解析插件**：从 OBS 对象存储中解析 XML 格式的测试执行报告，提取测试用例的元数据、执行结果、耗时等结构化信息，支持 Flaky 检测和质量度量。

两个能力分别服务于看板的数据采集层和数据加工层。

## 功能描述

### 数据接入能力
- 提供统一 REST API `/api/data/ingest` 接收第三方数据接入请求
- 支持按 appCode + modelCode 动态路由到对应的数据模型
- 实现 Doris 动态建表和列映射，将 JSON 数据写入结构化存储
- 提供数据模型的注册、查询管理功能

### 测试用例元数据解析插件
- 从 OBS 拉取流水线产生的 XML 测试报告文件
- 解析元数据文件（metadata 前缀）和结果文件，提取结构化字段
- 支持 Flaky 检测（基于多轮执行结果判定）
- 逐步增强字段覆盖：level、type、frameType、文件路径、类名、文件名

## 验收标准
- [ ] 数据接入 API 可正确接收请求并将数据写入 Doris
- [ ] 数据模型支持动态注册和查询
- [ ] 测试用例解析插件可正确解析多格式 XML 报告
- [ ] 测试结果包含完整的字段信息（level、type、frameType、filePath、className、fileName）
- [ ] 未执行用例正确计入 resultsList
- [ ] 包路径命名规范统一（opelibing -> openlibing）

## 影响范围
- `openlibing-sync-service`：新增数据接入 Controller、Service、Mapper 层，新增 Doris 动态数据源操作
- `openlibing-sync-plugins`：新增测试用例元数据解析插件，不断迭代增强字段模型
- 影响 OBS 读取、Doris 写入两条数据链路