# 用例日志归档增强 - 支持算子结果结构化数据归档

## 需求背景

在昇腾 CANN 测试场景中，单个测试用例通常会批量验证多个算子。目前框架仅支持上传和展示基础的日志文件（如 HTML 格式），缺乏对算子执行结果等结构化数据（如 xlsx 表格）的归档与查看能力，导致测试结果的数据维度不够完整，用户无法直观地查阅详细的算子指标。

## 需求价值

1. **完善测试报告体系**：实现算子级测试结果的结构化归档，补全当前测试报告的缺失环节，提升功能完整性。
2. **提升结果分析效率**：支持用户在 Web 端直接下载并查看算子结果的 Excel 文件，无需登录后台服务器拉取原始数据，大幅优化测试人员的复盘体验。

## 功能描述

### 功能点 1：pytest-testkit 日志目录结构改造

**目标**：为用例提供独立的归档目录，支持业务自行收集算子执行日志等文件。

**当前目录结构**：
```
logs/                          -- 根目录，可自定义指定
└── TestCases/                 -- 固定目录
    └── testcase_id1.html      -- 用例 html 日志文件
```

**新目录结构**：
```
logs/                                          -- 根目录，可自定义指定
└── TestCases/                                 -- 固定 TestCases 目录
    └── 2026-06-02/                            -- 日期（年-月-日）
        └── test_npu_info_11-38-05/            -- 用例名称_时间（时-分-秒）
            ├── testcase_id1.html              -- 用例的 html 日志
            ├── xsaxa.csv                      -- 用例收集的环境日志，业务自己收集归档
            └── 123.html                       -- 用例收集的环境日志，业务自己收集归档
```

**新增能力**：
- 每个用例可根据 `logger.path` 获取当前用例的归档目录（如 `logs/TestCases/2026-06-02/test_npu_info_11-38-05`）
- 用例可自行收集算子执行日志等，归档到 `logger.path` 中

### 功能点 2：pytest-executor 日志收集与打包上传

**目标**：测试结束后自动打包并上传用例归档目录中除插件生成的 HTML 之外的其他文件。

**实现要求**：
1. **适配新的日志目录结构**：如果用例在多环境执行，用例需要环境信息转换时，将 `testcase_id1.html` 转换为 `testcase_id1_env_name.html`（此功能 `xmlprocessor.convert_case_name_for_results_and_log` 已实现），此时需要适配新的目录结构
2. **自动打包非插件生成的文件**：将 `test_npu_info_11-38-05` 目录下除 pytest-testkit 插件生成的 `testcase_id1.html` 之外的所有文件（包括用例自行生成的其他 HTML 文件）打包到 `testcase_id1_log.zip` 或 `testcase_id1_env_name_log.zip` 中；如果没有多余文件则不打包
3. **上传并生成下载链接**：仅当存在打包文件时，在最后的 `result_json_list` 中，将打包的 zip 文件路径按照 `testcase_id1.html` 同样的路径拼接方式，放到 `json_item` 的 `envDownloadUrl` 属性中

## 验收标准

- [ ] pytest-testkit 生成的日志目录结构符合新规范（日期/用例名_时间/文件）
- [ ] 用例可通过 `logger.path` 获取当前用例的归档目录路径
- [ ] pytest-executor 能够正确扫描新的目录结构并执行环境信息转换
- [ ] 用例目录下除 pytest-testkit 插件生成的 HTML 之外的文件被正确打包为 zip 文件（用例自身生成的 HTML 文件也需打包）
- [ ] 仅当存在打包文件时，result_json_list 中的用例包含正确的 envDownloadUrl 属性；无打包文件时不设置该属性
- [ ] 多环境执行场景下，HTML 文件和 zip 文件的环境后缀处理一致

## 影响范围

| 模块 | 文件 | 变更类型 |
|------|------|----------|
| pytest-testkit | `pytest_testkit/lib/common/log/log_factory.py` | 修改 |
| pytest-executor | `pytest_executor/src/report/xml_processor.py` | 修改 |
| pytest-executor | `pytest_executor/src/report/report_uploader.py` | 修改 |

## 关联 Issue

- 业务 Issue: openlibing/openlibing-pytest-executor#15
