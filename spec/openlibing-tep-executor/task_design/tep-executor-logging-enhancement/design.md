# TEP Executor 日志增强方案

## 1. 需求背景

当前 `openlibing-tep-executor` 测试执行器的日志系统存在以下问题：
1. 环境日志收集仅按 IP 判断，无法直接收集本地 localhost 日志
2. 缺少独立的 tep-executor.log 日志文件
3. 部分关键日志散落在其他日志中，不便于问题追踪
4. 日志文件 URL 未统一打印

## 2. 功能描述

### 2.1 新增 tep-executor.log 日志文件

- 创建独立的 `tep-executor.log` 日志文件
- 与现有的 `hutafagent.log` 独立
- 便于问题定位和日志分析

### 2.2 增强环境日志收集逻辑

**当前逻辑：**
```python
if host in current_ips:
    # 处理本地文件
else:
    # 通过 SFTP 处理远程文件
```

**增强后逻辑：**
```python
if host in current_ips:
    # 处理本地文件
else:
    # 通过 SFTP 处理远程文件

# 新增：不判断 IP，直接收集 localhost 日志
collect_localhost_logs()
```

### 2.3 日志场景增强

需要收集并打印到 `tep-executor.log` 的日志场景：

| 场景 | 打印内容 | 打印位置 |
|-----|---------|---------|
| `get_metadata_info_from_testset` | `process testset file {testset_file}` | utils.py |
| `TestSet.gen` | `Valid testset files: {file_list}` | test_set.py |
| `_get_all_testset_files` | `_tmp_testset_files` 文件列表 | executor.py |
| `zip_files_in_conf_log` | 压缩文件列表/跳过文件列表 | executor.py |

### 2.4 日志文件 URL 打印

在 `generate_logs` 函数中打印所有日志文件的 URL，参考 `collect_result_metadata` 中 `log_metadata_url` 的方式。

## 3. 技术方案

### 3.1 新增 tep-executor.log 日志处理器

**文件：** `tepexecor_frame/cte/log.py`

```python
# 新增 tep_executor 日志器
tep_executor_logger = logging.getLogger('tep_executor')
tep_executor_logger.setLevel(logging.DEBUG)
tep_executor_logger.propagate = False  # 不传播到 root logger

# 新增文件处理器
tep_executor_handler = ExtRotatingFileHandler(
    "tep-executor.log",
    max_bytes=20 * 1024 * 1024,  # 20MB
    backup_count=25
)
tep_executor_handler.setFormatter(formatter)
tep_executor_handler.setLevel(logging.INFO)
tep_executor_logger.addHandler(tep_executor_handler)
```

### 3.2 增强 zip_files_in_conf_log 函数

**文件：** `tepexecor_frame/executor.py`

```python
def zip_files_in_conf_log(self):
    """收集配置文件日志并压缩"""
    # ... 保留原有逻辑 ...

    # 新增：直接收集 localhost 日志（不判断 IP）
    self._collect_localhost_logs(zipf)

    # ... 原有逻辑继续 ...
```

```python
def _collect_localhost_logs(self, zipf):
    """直接收集 localhost 日志"""
    hostname = "localhost"

    for model, all_paths in self.log_conf.items():
        for path_pattern in all_paths:
            expanded_path = os.path.expanduser(path_pattern)

            if os.path.isdir(expanded_path):
                for root, dirs, files in os.walk(expanded_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._should_add_file(file_path):
                            zip_path = os.path.join(hostname, model, file_path.lstrip("/"))
                            self._add_file_to_zip(zipf, file_path, zip_path, model, hostname)
            else:
                for file_path in glob.glob(expanded_path):
                    if self._should_add_file(file_path):
                        zip_path = os.path.join(hostname, model, file_path.lstrip("/"))
                        self._add_file_to_zip(zipf, file_path, zip_path, model, hostname)
```

### 3.3 增强文件压缩日志

**文件：** `tepexecor_frame/executor.py`

```python
def _add_file_to_zip(self, zipf, file_path, zip_path, model, hostname):
    """添加文件到 ZIP，记录日志"""
    file_size = os.path.getsize(file_path)

    if file_size > self.max_size_bytes:
        logger.info(f"skip {file_path}, file size {file_size/1024/1024:.2f}MB over limit")
        tep_executor_logger.info(f"[SKIP] {file_path} (size: {file_size/1024/1024:.2f}MB > {self.max_size_bytes/1024/1024}MB)")
        return

    try:
        zipf.write(file_path, zip_path)
        tep_executor_logger.info(f"[ADD] {file_path} -> {zip_path}")
        logger.info(f"will add filetype[local walk], {file_path} to {zip_path}")
    except Exception as e:
        logger.error(f"add file {file_path} to zip fail: {e}")
        tep_executor_logger.error(f"[FAIL] {file_path}: {e}")
        raise
```

### 3.4 增强 TestSet.gen 日志

**文件：** `tepexecor_frame/test_set.py`

```python
def gen(self, test_set_gen_params: TestSetGenParams):
    # ... 原有代码 ...

    # 增强：打印所有找到的 testset 文件
    tep_executor_logger.info(f"[TEST_SET] Valid testset files: {_tmp_testset_files}")

    # ... 原有代码 ...
```

### 3.5 增强 get_metadata_info_from_testset 日志

**文件：** `tepexecor_frame/cte/utils.py`

```python
def get_metadata_info_from_testset(testset_file):
    # 已有日志：logger.info(f"process testset file {testset_file}")
    # 增强：添加到 tep_executor_logger
    tep_executor_logger.info(f"[METADATA] process testset file: {testset_file}")

    # ... 原有代码 ...
```

### 3.6 增强 _get_all_testset_files 日志

**文件：** `tepexecor_frame/executor.py`

```python
def _get_all_testset_files(self):
    """获取所有测试集文件"""
    test_set_dir = self.data.get('task_param', {}).get('test_set_dir')
    scripts_dir = self.executor.scripts_dir
    _tmp_testset_files = utils.get_files(scripts_dir,
                                         r'testSet.*\.xml',
                                         ['.git'],
                                         root_dir=test_set_dir)

    # 新增：打印文件列表到 tep-executor.log
    tep_executor_logger.info(f"[TEST_SET] _tmp_testset_files: {_tmp_testset_files}")

    return _tmp_testset_files
```

### 3.7 增强 generate_logs 日志 URL 打印

**文件：** `tepexecor_frame/executor.py`

```python
def generate_logs(self):
    """生成日志并打印 URL"""
    # ... 原有代码 ...

    # 收集日志文件 URL
    log_urls = {
        "test_cases_result_json": log_json_url,
        "metadata_xml": log_metadata_url,
        "result_xml": log_result_xml_url,
        "conf_log_zip": conf_log_url if conf_log_url else "",
    }

    # 打印所有日志文件 URL
    tep_executor_logger.info("[LOG_URLS] Generated log files:")
    for name, url in log_urls.items():
        if url:
            tep_executor_logger.info(f"  - {name}: {url}")

    # ... 原有代码 ...
```

## 4. 影响范围

### 4.1 修改的文件

| 文件 | 操作 | 说明 |
|-----|------|------|
| `tepexecor_frame/cte/log.py` | 修改 | 新增 tep_executor_logger 和文件处理器 |
| `tepexecor_frame/executor.py` | 修改 | 增强日志收集、_get_all_testset_files、generate_logs |
| `tepexecor_frame/test_set.py` | 修改 | TestSet.gen 增加文件列表打印 |
| `tepexecor_frame/cte/utils.py` | 修改 | get_metadata_info_from_testset 增加 tep_executor_logger |

### 4.2 日志文件清单

| 日志文件 | 路径 | 说明 |
|---------|------|------|
| `tep-executor.log` | `tepexecor_frame/logs/` | 新增，独立日志 |
| `hutafagent.log` | `tepexecor_frame/logs/` | 原有日志，保持不变 |
| `all_conf_log.zip` | `cases_log/` | 压缩的配置文件日志 |

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 日志文件过大 | 磁盘空间消耗 | 使用 RotatingFileHandler，20MB 轮转，保留 25 份 |
| 日志重复打印 | 日志膨胀 | tep_executor_logger.propagate = False |
| 权限问题 | 无法创建日志目录 | 使用 try-except 捕获，优雅降级 |

## 6. 验收标准

- [ ] `tep-executor.log` 日志文件独立生成
- [ ] localhost 环境日志被正确收集
- [ ] `get_metadata_info_from_testset` 打印日志到 tep-executor.log
- [ ] `TestSet.gen` 打印 `Valid testset files` 到 tep-executor.log
- [ ] `_get_all_testset_files` 打印 `_tmp_testset_files` 文件列表
- [ ] 压缩文件时打印 `[ADD]` 和 `[SKIP]` 日志
- [ ] `generate_logs` 打印所有日志文件 URL

## 7. 测试计划

| 测试场景 | 预期结果 |
|---------|---------|
| 正常执行流程 | tep-executor.log 生成，包含所有增强日志 |
| 仅 localhost 环境 | localhost 日志正确收集 |
| 文件超限 | 跳过文件并打印 [SKIP] 日志 |
| URL 打印 | generate_logs 后所有 URL 打印到 tep-executor.log |
