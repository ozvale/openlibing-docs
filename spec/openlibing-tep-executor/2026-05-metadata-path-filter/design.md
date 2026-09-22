# Design: metadata-path-filter

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Metadata 路径过滤流程                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    --config test.json
                           │
                           ▼
              ┌─────────────────────────────┐
              │  {                          │
              │    "testcase": [...],       │
              │    "testPaths": [           │  ← 新增配置字段
              │      "scripts/module_a/",   │
              │      "tests/feature_x/"     │
              │    ]                        │
              │  }                          │
              └─────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────┐
              │      accept_para()          │
              │                             │
              │  self.test_paths =          │
              │    config_json_data         │
              │      .get("testPaths", [])  │
              │                             │
              │  自动补全末尾 "/"            │
              └─────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────┐
              │  get_testcase_metadata()    │
              │                             │
              │  遍历所有 testSet 文件       │
              │  提取每个用例的 file_path    │
              │                             │
              │  if test_paths:             │
              │    过滤 file_path            │
              │    仅匹配路径写入 metadata   │
              │  else:                      │
              │    全量收集                  │
              └─────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────────┐
              │      metadata.xml           │
              │                             │
              │  仅包含匹配路径的用例信息     │
              └─────────────────────────────┘
```

## Implementation Details

### 1. 配置字段解析

在 `accept_para()` 方法中解析 `testPaths` 字段：

```python
test_paths_raw = config_json_data.get("testPaths", [])
self.test_paths = [p if p.endswith("/") else p + "/" for p in test_paths_raw]
```

路径末尾自动补 `/`，避免误匹配：
- `tests/a` → 补全为 `tests/a/`
- `tests/a/` → 保持不变

### 2. 路径过滤方法

新增静态方法 `_is_file_path_in_test_paths()`：

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

### 3. metadata 收集过滤

修改 `get_testcase_metadata()` 方法中的用例遍历逻辑：

```python
for name, class_name, file_path, case_level, case_type in info_list:
    if not self._is_file_path_in_test_paths(file_path, self.test_paths):
        continue
    testcase = ET.SubElement(testcases, "testCase")
    ET.SubElement(testcase, "name").text = name
    ...
```

## Configuration Example

```json
{
    "testcase": [
        {"number": "TC_001", "name": "test_case_1"}
    ],
    "testPaths": [
        "scripts/module_a",
        "tests/feature_x/",
        "src/tests/component"
    ]
}
```

代码会自动将路径补全为：
- `scripts/module_a/`
- `tests/feature_x/`
- `src/tests/component/`

## Behavior

| testPaths 状态 | 行为 |
|---------------|------|
| 空列表 `[]` 或不存在 | 全量收集（向后兼容） |
| 有值 `["path1", "path2"]` | 仅收集 file_path 匹配的用例 |

## File Changes

| 文件 | 修改位置 | 改动说明 |
|-----|---------|---------|
| executor.py | `__init__()` | 新增 `self.test_paths = []` |
| executor.py | `accept_para()` | 新增 `testPaths` 解析，自动补 `/` |
| executor.py | 新增静态方法 | `_is_file_path_in_test_paths()` |
| executor.py | `get_testcase_metadata()` | 新增过滤逻辑 |

## Edge Cases Handling

1. **testPaths 为空**: 返回 True，全量收集
2. **file_path 为空字符串**: 不匹配任何路径，跳过
3. **testPaths 包含无效路径**: 静默处理，不影响其他有效路径
4. **路径格式统一**: 自动补 `/` 确保一致性