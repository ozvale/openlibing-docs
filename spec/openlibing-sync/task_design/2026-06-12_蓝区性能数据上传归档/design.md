# 蓝区性能数据上传归档 — 技术设计

## 方案概述

在 `openlibing-sync-service` 中修改 `TestCaseDataController` 和 `TestCaseDataServiceImpl`，新增 `label` 和 `archivePath` 参数，支持通过 `label` + `archivePath` 自定义 OBS 归档路径。不对 label 的具体值做特殊判断，统一走相同的路由逻辑。

## 架构决策

- **label + archivePath 驱动目录路由**：根据参数组合决定 OBS 存储路径结构，无 label 时保持现有路径不变
- **label 可单独使用**：归档为 `/{label}/{filename}`，不强制要求 archivePath
- **archivePath 必须搭配 label**：归档为 `/{label}/{archivePath}/{filename}`，不允许单独传入
- **archivePath 优先级高于流水线参数**：当 label + archivePath 与流水线参数同时传入时，以 archivePath 为最终归档路径
- **斜杠清理**：label 和 archivePath 两侧的斜杠会被 `StringUtils.strip(value, "/")` 去除，避免路径异常
- **不做 label 值特殊处理**：移除 performance/precision 等特殊路由分支，所有 label 值统一走相同逻辑

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/controller/TestCaseDataController.java` | 修改 | 新增 `label`、`archivePath` 可选参数；调整校验逻辑；错误响应携带具体参数描述 |
| `domain/service/testcase/TestCaseDataService.java` | 修改 | `uploadTestcaseMetadata` 方法签名新增 `label`、`archivePath` 参数 |
| `domain/service/testcase/impl/TestCaseDataServiceImpl.java` | 修改 | 实现 label + archivePath 路由逻辑，去除两侧斜杠，移除 performance/precision 特殊分支 |
| `upload_to_openlibing.py` | 修改 | `auth_secret` → `openlibing_secret`，支持环境变量，新增 `--archive-path` |

## 接口变更

### 请求参数变更

**变更前**：
```
POST testcase/metadata/upload (multipart/form-data)
- files: List<MultipartFile> (必填)
- pipelineId: String (必填)
- pipelineRunId: String (必填)
- jobId: String (必填)
```

**变更后**：
```
POST testcase/metadata/upload (multipart/form-data)
- files: List<MultipartFile> (必填)
- pipelineId: String (可选)
- pipelineRunId: String (可选)
- jobId: String (可选)
- label: String (可选，可单独使用)
- archivePath: String (可选，需与 label 同时传入)
```

### 校验规则

| 条件 | 校验 | 错误信息 |
|------|------|---------|
| files 为空 | 返回 BAD_REQUEST | `files must not be empty` |
| archivePath 非空但 label 为空 | 返回 BAD_REQUEST | `archivePath requires label` |
| label 和流水线参数均为空 | 返回 BAD_REQUEST | `must provide either label or pipelineId/pipelineRunId/jobId` |
| files 数量 > 100 | 返回 FILES_UPLOAD_EXCEED_LIMIT | — |

## OBS 路径路由逻辑

```java
private String buildObjectKey(String label, String archivePath, String pipelineId,
                              String pipelineRunId, String jobId, String filename) {
    String trimmedLabel = StringUtils.strip(label, "/");
    String trimmedArchivePath = StringUtils.strip(archivePath, "/");

    if (StringUtils.isNotBlank(trimmedLabel) && StringUtils.isNotBlank(trimmedArchivePath)) {
        // label + archivePath：/{label}/{archivePath}/{filename}
        return String.join("/", trimmedLabel, trimmedArchivePath, filename);
    }

    if (StringUtils.isNotBlank(trimmedLabel)) {
        // 仅 label：/{label}/{filename}
        return String.join("/", trimmedLabel, filename);
    }

    // 无 label：冒烟测试路径（保持现有行为）
    return String.join("/", "testcase-metadata", pipelineId, pipelineRunId, jobId, filename);
}
```

## 数据流

```
蓝区测试环境
    │
    ▼
upload_to_openlibing.py --label "performance" --archive-path "20260612/143025" --files perf_data.xml
    │
    ▼
POST testcase/metadata/upload (label=performance, archivePath=20260612/143025, files=perf_data.xml)
    │
    ▼
TestCaseDataController
    │  校验：label 非空 → archivePath 可选
    │  校验：label + archivePath 均非空 → 流水线参数可选
    ▼
TestCaseDataServiceImpl
    │  去除两侧斜杠：label.strip("/") → "performance", archivePath.strip("/") → "20260612/143025"
    │  路由：label + archivePath → performance/20260612/143025/perf_data.xml
    ▼
ObsUtilClient.batchUploadFiles
    │
    ▼
OBS: performance/20260612/143025/perf_data.xml
    │
    ▼
perfstudio 平台消费
```

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 无 label 时流水线参数校验遗漏 | Controller 层显式校验：label 为空时流水线参数必须非空 |
| label/archivePath 含前后斜杠导致路径异常 | `StringUtils.strip(value, "/")` 去除两侧斜杠 |
| label 仅为斜杠字符（如 `///`） | strip 后为空字符串，`isNotBlank` 判定为空，走流水线路由 |
| 向后兼容性 | 无 label 时行为完全不变，现有调用方无感知 |

## 跨仓影响

- `openlibing-pytest-executor`：需修改 `upload_to_openlibing.py`，`auth_secret` 重命名为 `openlibing_secret`，支持环境变量读取，新增 `--archive-path` 参数
- `openlibing-sync`：服务端接口变更，需确保向后兼容
