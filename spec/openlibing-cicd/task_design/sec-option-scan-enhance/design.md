# sec-option-scan-enhance 技术方案

## 架构概览

```
code-metrics-scan (sec-option-scan 插件 v1.4.0)
  │  index.js ─→ scanner.js ─→ SecOptionDetector.js (Python + scan-options)
  │                        └→ CicdUploader.js (pipelineName / repoUrl / scanOptions)
  │  POST /openlibing-cicd/build-artifact/sec-option/report
  ▼
openlibing-cicd-fork
  ├── BuildArtifactController
  ├── SecOptionScanService / SecOptionScanServiceImpl
  ├── SecOptionScanRecordMapper
  ├── SecOptionScanFileDetailMapper
  └── MySQL (sec_option_scan_record + sec_option_scan_file_detail)
```

## 数据库变更

### Liquibase changeset: `20260723-add-sec-option-scan-record-fields`

在 `sec_option_scan_record` 表新增 4 列：

| 列名 | 类型 | 说明 |
|------|------|------|
| pipeline_name | VARCHAR(255) | 流水线名称（ATOMGIT_WORKFLOW 环境变量值） |
| package_download_accessible | TINYINT(1) | 下载URL可访问性：NULL=无URL，1=可下载，0=不可下载 |
| repo_url | VARCHAR(512) | 代码仓链接（gitcode.com/owner/repo） |
| scan_options | VARCHAR(512) | 实际扫描项列表（逗号分隔，不传=全部13项） |

新增索引：
- `idx_sec_option_record_repo_url` (repo_url)
- `idx_sec_option_record_pipeline_name` (pipeline_name)

## API 变更

### 上报接口（不变更路径，扩展字段）

POST /openlibing-cicd/build-artifact/sec-option/report

新增请求字段：
- `pipelineName` (String, 可选) - 流水线名称
- `repoUrl` (String, 可选) - 代码仓链接（格式 gitcode.com/owner/repo）
- `scanOptions` (List<String>, 可选) - 实际扫描项列表

### 概览查询接口

POST /openlibing-cicd/build-artifact/sec-option/overview

筛选字段变更为：
- `repoUrl` (模糊匹配) - 代码仓链接
- `pipelineName` (模糊匹配) - 流水线名称
- `packageName` (模糊匹配) - 构建产物包名

返回 VO 新增字段：
- `repoUrl` - 代码仓链接
- `pipelineName` - 流水线名称
- `scanOptions` - 实际扫描项列表
- `downloadUrl` - 构建产物下载URL
- `downloadAccessible` - 下载URL可访问性

### 下拉框接口

POST /openlibing-cicd/build-artifact/sec-option/dropdown

返回三个维度：
- `repoUrls` (List<String>) - 代码仓链接列表
- `pipelineNames` (List<String>) - 流水线名称列表
- `packageNames` (List<String>) - 构建产物包名列表

支持级联筛选：选中 repoUrl 后，pipelineNames 和 packageNames 只返回匹配值。

### 文件详情查询接口

POST /openlibing-cicd/build-artifact/sec-option/file-detail

定位方式变更为：repoUrl + runNumber + packageName（精确匹配）

## 插件变更

### Python 脚本 (sec_option_scan.py)

新增 5 个检测函数：

| 函数 | key | 检测方式 |
|------|-----|----------|
| fortify | fortify | 检测 .dynsym 中 __*_chk 函数（_FORTIFY_SOURCE 宏） |
| fvisibility | fvisibility | 统计 .dynsym 中 STV_HIDDEN vs STV_DEFAULT 符号数 |
| ftrapv | ftrapv | 检测 __addvsi3/__subvsi3/__mulvsi3 等溢出陷阱函数 |
| stack_clash | stackClash | 检测 PT_GNU_STACK 段存在性（简化策略，暂返回 NO） |
| aslr | aslr | 复用 PIE 检测逻辑（ASLR 二进制侧支持等价于 PIE） |

CLI 接口扩展：`python3 sec_option_scan.py <scan-dir> <output-file> [scan-options]`

### action.yml

- 版本升至 1.4.0
- 新增 `scan-options` 输入参数（逗号分隔 key 列表，不传=全部13项）

### Node.js 传递链

- `index.js`：读取 scan-options 输入 + ATOMGIT_WORKFLOW + 拼接 repoUrl
- `scanner.js`：传递 scanOptions / pipelineName / repoUrl 给 detector 和 uploader
- `SecOptionDetector.js`：将 scanOptions 作为第 3 个 CLI 参数传给 Python 脚本
- `CicdUploader.js`：payload 新增 pipelineName / repoUrl / scanOptions 字段

## 筛选逻辑

### 概览查询

直接从 `sec_option_scan_record` 表查询，不依赖 `repo_info` 表：

```sql
SELECT * FROM sec_option_scan_record
WHERE status = 0
  AND repo_url LIKE '%{repoUrl}%'
  AND pipeline_name LIKE '%{pipelineName}%'
  AND package_name LIKE '%{packageName}%'
ORDER BY detection_completed_at DESC
```

### 下拉框级联

查询去重值时，选中的维度作为 WHERE 条件过滤，不按自身过滤：
- queryDistinctRepoUrls：按 pipelineName + packageName 过滤，SELECT DISTINCT repo_url
- queryDistinctPipelineNames：按 repoUrl + packageName 过滤，SELECT DISTINCT pipeline_name
- queryDistinctPackageNames：按 repoUrl + pipelineName 过滤，SELECT DISTINCT package_name

## 关键设计决策

1. **repoUrl 格式**：使用 `gitcode.com/owner/repo`（不含协议前缀），由 ATOMGIT_REPOSITORY 拼接域名得到。避免完整 URL（含 https://）导致的模糊匹配歧义。

2. **pipelineName 来源**：GitCode runner 自动注入 ATOMGIT_WORKFLOW 环境变量，与 GitCode 平台流水线名称一致。

3. **scanOptions 存储格式**：逗号分隔字符串（如 "bindNow,nx,pic"），不传或为空表示全部 13 项。前端按此区分已扫描/未扫描项。

4. **N/A 处理**：rate=-1 表示已扫描但不适用，排序时按数值排序（-1 排在最后），显示时格式化为 "N/A"。平均率排除 rate<0 的项。

5. **HTTP HEAD 可访问性**：5s 连接 + 10s 读取超时，失败返回 false（不可下载），无 URL 返回 null。

## 影响范围

- **openlibing-cicd**：SecOptionScanServiceImpl / 所有 DTO/VO / Entity / Liquibase / Controller
- **code-metrics-scan**：sec-option-scan 插件全部文件（Python / Node.js / action.yml / README）
