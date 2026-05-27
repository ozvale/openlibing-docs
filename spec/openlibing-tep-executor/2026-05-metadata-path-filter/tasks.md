# Tasks: metadata-path-filter

## Implementation Tasks

### Task 1: 新增实例属性 test_paths [x]

**文件**: `tepexecor_frame/executor.py`

**位置**: `__init__()` 方法（约第 25 行）

**改动**:
```python
self.test_paths = []
```

---

### Task 2: 解析 testPaths 配置字段 [x]

**文件**: `tepexecor_frame/executor.py`

**位置**: `accept_para()` 方法（约第 296 行，处理 `config_json_data` 区域）

**改动**:
```python
test_paths_raw = config_json_data.get("testPaths", [])
self.test_paths = [p if p.endswith("/") else p + "/" for p in test_paths_raw]
```

---

### Task 3: 新增路径过滤静态方法 [x]

**文件**: `tepexecor_frame/executor.py`

**位置**: 类的静态方法区域（实例方法之前）

**改动**:
```python
@staticmethod
def _is_file_path_in_test_paths(file_path: str, test_paths: list) -> bool:
    if not test_paths:
        return True
    for path in test_paths:
        if file_path.startswith(path):
            return True
    return False
```

---

### Task 4: 添加 metadata 收集过滤逻辑 [x]

**文件**: `tepexecor_frame/executor.py`

**位置**: `get_testcase_metadata()` 方法（第 511-519 行）

**改动**:
在 `for name, class_name, file_path, case_level, case_type in info_list:` 循环内，添加过滤判断：

```python
for name, class_name, file_path, case_level, case_type in info_list:
    if not self._is_file_path_in_test_paths(file_path, self.test_paths):
        continue
    testcase = ET.SubElement(testcases, "testCase")
    ET.SubElement(testcase, "name").text = name
    ET.SubElement(testcase, "className").text = class_name
    ET.SubElement(testcase, "filePath").text = file_path
    ET.SubElement(testcase, "level").text = case_level
    ET.SubElement(testcase, "type").text = case_type
```

---

## Verification

实现完成后，可通过以下方式验证：

1. **空 testPaths 测试**: 不配置 testPaths，确认全量收集行为不变
2. **单路径测试**: 配置单个 testPaths，确认过滤正确
3. **多路径测试**: 配置多个 testPaths，确认所有匹配路径的用例都被收集
4. **末尾无 `/` 测试**: 配置 `scripts/module_a`（无 `/`），确认自动补全后匹配正确