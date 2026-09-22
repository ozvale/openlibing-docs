# 蓝区性能数据上传归档

## 需求背景

训练、推理的性能测试用例外溢到蓝区演进，性能数据相对敏感，且需要和黄区数据一同对比消费。当前 openlibing 上传接口仅支持冒烟测试场景（必须传入 pipelineId/pipelineRunId/jobId），不支持按标签归档到不同 OBS 目录，无法满足蓝区性能数据回传黄区 perfstudio 平台的需求。

## 需求价值

1. **打通蓝区性能数据回传链路**：蓝区性能测试数据可通过 openlibing 上传脚本直接回传至黄区 OBS，实现跨区数据流转。
2. **按标签归档，支持多场景扩展**：不同类型测试数据通过 `label` + `archivePath` 自定义归档路径，方便消费方按类型检索和处理。
3. **助力性能竞争力提升**：对蓝区性能数据进行监控、分析、调优，为产品性能优化提供数据支撑。

## 功能描述

### 功能点 1：上传接口支持 label + archivePath 参数

**目标**：openlibing 上传接口 `testcase/metadata/upload` 新增可选 `label` 和 `archivePath` 参数，支持自定义归档路径。

**参数与目录映射规则**：

| 参数组合 | OBS 目录结构 | 说明 |
|---------|-------------|------|
| 无 label、无 archivePath | `testcase-metadata/{pipelineId}/{pipelineRunId}/{jobId}/{filename}` | 现有冒烟测试，保持不变 |
| 仅 label | `/{label}/{filename}` | 按标签直接归档 |
| label + archivePath | `/{label}/{archivePath}/{filename}` | 自定义归档路径 |

**关键行为**：
- `label` 可单独使用，归档为 `/{label}/{filename}`
- `archivePath` 必须与 `label` 同时传入，归档为 `/{label}/{archivePath}/{filename}`
- 当 `label` + `archivePath` 与流水线参数同时传入时，以 `archivePath` 为最终归档路径
- `label` 和 `archivePath` 两侧的斜杠会被自动去除，避免路径异常
- 不对 `label` 的具体值做特殊判断和处理，所有 label 值统一走相同的路由逻辑

**校验规则**：
- `files` 不能为空
- `archivePath` 不能脱离 `label` 单独传入
- 至少需要 `label` 或流水线参数（pipelineId/pipelineRunId/jobId）之一
- 错误响应会在 `data` 字段中返回具体参数错误描述

### 功能点 2：蓝区上传脚本适配

**目标**：改造 `upload_to_openlibing.py` 脚本，支持 `--label` 和 `--archive-path` 参数，`--openlibing-secret` 改为非必传（支持环境变量）。

**使用示例**：
```bash
# 冒烟测试（流水线参数）
python upload_to_openlibing.py \
    --files /path/to/metadata.xml \
    --pipeline-id "pipeline-123" --pipeline-run-id "run-456" --job-id "job-789" \
    --openlibing-secret '{"apig_code": "xxx"}'

# 仅 label
python upload_to_openlibing.py \
    --files /path/to/perf_data.xml \
    --label "performance" \
    --openlibing-secret '{"apig_code": "xxx"}'

# label + archive-path
python upload_to_openlibing.py \
    --files /path/to/perf_data.xml \
    --label "performance" \
    --archive-path "20260612/143025" \
    --openlibing-secret '{"apig_code": "xxx"}'

# 通过环境变量传递 secret
export OPENLIBING_SECRET='{"apig_code": "xxx"}'
python upload_to_openlibing.py \
    --files /path/to/report.log \
    --label "simulation" \
    --archive-path "project-a/run-001"
```

## 验收标准

- [ ] 上传接口支持可选 `label` 和 `archivePath` 参数
- [ ] 无 label 时，接口行为与现有完全一致（流水线参数必填，目录结构不变）
- [ ] 仅 label 时，文件归档到 `/{label}/{filename}`
- [ ] label + archivePath 时，文件归档到 `/{label}/{archivePath}/{filename}`
- [ ] archivePath 不能脱离 label 单独传入
- [ ] label + archivePath 与流水线参数同时传入时，以 archivePath 为最终归档路径
- [ ] label 和 archivePath 两侧斜杠被自动去除
- [ ] 错误响应在 data 字段返回具体参数错误描述
- [ ] 蓝区用户可通过 `upload_to_openlibing.py` 脚本上传性能数据
- [ ] 脚本支持从环境变量 `OPENLIBING_SECRET` 读取凭证
- [ ] 脚本参数校验与后端接口一致

## 影响范围

| 仓库 | 模块 | 变更类型 |
|------|------|----------|
| openlibing-sync | `TestCaseDataController.java` | 修改：新增 label、archivePath 参数，调整校验逻辑 |
| openlibing-sync | `TestCaseDataService.java` | 修改：接口方法签名新增 label、archivePath 参数 |
| openlibing-sync | `TestCaseDataServiceImpl.java` | 修改：实现 label + archivePath 路由逻辑，去除两侧斜杠 |
| openlibing-pytest-executor | `upload_to_openlibing.py` | 修改：auth_secret→openlibing_secret，新增 --archive-path，支持环境变量 |
