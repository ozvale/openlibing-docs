# sec-option-scan-enhance: 安全编译选项扫描增强

## 需求背景

sec-option-scan 插件已完成基础功能（8 项扫描、上报、概览查询），现需进行以下增强：

1. **数据模型改造**：新增 `pipeline_name`、`repo_url`、`scan_options`、`package_download_accessible` 字段，支撑新筛选维度和扫描项可选化
2. **筛选逻辑优化**：由"代码仓名 + 包名"改为"代码仓链接 + 流水线名称 + 包名"三维度模糊匹配，数据来源从 `sec_option_scan_record` 表直接查询，不再依赖 `repo_info` 表
3. **扫描项扩展**：从 8 项扩展为 13 项（新增 fortify/fvisibility/ftrapv/stackClash/aslr，参考 Ascend 安全编译指南）
4. **扫描项可选化**：新增 `scan-options` 参数，用户可指定只扫描部分项，未扫描项 key 缺失于结果中
5. **构建产物可访问性检测**：上报时通过 HTTP HEAD 检测下载 URL 是否可访问，区分公开桶/私有桶

**鉴权改造暂不实施**，本次不涉及。

## 验收标准

- [x] Liquibase changeset 成功新增 4 列 + 2 索引到 `sec_option_scan_record` 表
- [x] 下拉框接口返回 repoUrls / pipelineNames / packageNames 三个维度，支持级联模糊筛选
- [x] 概览查询支持按 repoUrl / pipelineName / packageName 模糊匹配
- [x] 文件详情通过 repoUrl + runNumber + packageName 精确定位
- [x] 概览 VO 返回 repoUrl / pipelineName / scanOptions / downloadUrl / downloadAccessible 字段
- [x] Python 脚本支持 13 项检测，新增 5 个检测函数
- [x] Python 脚本 main() 接受第 3 个 CLI 参数 scan-options（逗号分隔 key 列表）
- [x] 未扫描项 key 缺失于 overviewData/fileDetails，N/A 项 rate=-1
- [x] action.yml 新增 scan-options 输入参数，版本升至 1.4.0
- [x] Node.js 全链路传递 scanOptions / pipelineName / repoUrl 至 CicdUploader payload
- [x] pipelineName 从 ATOMGIT_WORKFLOW 环境变量获取
- [x] repoUrl 由 ATOMGIT_REPOSITORY 拼接 GitCode 域名得到（格式 gitcode.com/owner/repo）
- [x] Maven 编译通过，Python / Node.js 语法检查通过

## 关联 Issue

- openlibing/openlibing-cicd#184
