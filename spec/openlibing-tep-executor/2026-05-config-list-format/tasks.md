# Tasks: config-list-format

## Task Breakdown

### Task 1: executor.py 新增 config_list 字段和 JSON 格式判断
- **优先级**: High
- **预估改动**: ~30 行
- **文件**: executor.py
- **位置**: `__init__()` 和 `accept_para()`
- **描述**:
  1. 在 `__init__()` 中新增 `self.config_list = None`
  2. 在 `accept_para()` 第 275 行新增 JSON 格式判断
  3. 列表格式时：使用第一个元素走原有流程，同时保存整个列表
  4. 新增 `npu_parallel_num` 参数设置

### Task 2: executor.py prepare() 方法传递 config_list
- **优先级**: High
- **预估改动**: ~5 行
- **文件**: executor.py
- **位置**: `prepare()` 第 581 行
- **描述**:
  1. 修改 `prepare()` 方法调用，新增 `config_list` 参数传递
  2. 传递 `self.config_list` 到 `uniautos.prepare()`

### Task 3: uniautos.py prepare() 接收和传递 config_list
- **优先级**: High
- **预估改动**: ~10 行
- **文件**: uniautos.py
- **位置**: `prepare()` 第 92 行和第 132 行
- **描述**:
  1. 修改 `prepare()` 方法签名，新增 `config_list=None` 参数
  2. 在调用 `TestSet().gen()` 时，传递 `config_list` 到 `TestSetGenParams`

### Task 4: TestSetGenParams 新增 config_list 字段
- **优先级**: High
- **预估改动**: ~1 行
- **文件**: test_set.py
- **位置**: `TestSetGenParams` 第 10-32 行
- **描述**:
  1. 在 `@dataclass` 中新增 `config_list: list = None` 字段

### Task 5: TestSet.__init__() 接收 config_list
- **优先级**: High
- **预估改动**: ~3 行
- **文件**: test_set.py
- **位置**: `TestSet.__init__()` 第 37 行
- **描述**:
  1. 修改 `__init__()` 方法签名，新增 `config_list=None` 参数
  2. 新增 `self.config_list = config_list` 属性

### Task 6: TestSet.__find_testset_files_include_cases() 核心逻辑修改
- **优先级**: High
- **预估改动**: ~60 行
- **文件**: test_set.py
- **位置**: `__find_testset_files_include_cases()` 第 40-97 行
- **描述**:
  1. 在方法开头新增 `self.config_list` 判断
  2. 当 `config_list` 存在时，调用新增的 `__find_testset_by_config_list()` 方法
  3. 当 `config_list` 不存在时，保持原有逻辑（调用原有的查找方法）

### Task 7: TestSet 新增 __find_testset_by_config_list() 方法
- **优先级**: High
- **预估改动**: ~50 行
- **文件**: test_set.py
- **位置**: 新增方法（在 `__find_testset_files_include_cases()` 之后）
- **描述**:
  1. 新增私有方法 `__find_testset_by_config_list()`
  2. 遍历 `config_list` 的每个元素
  3. 根据每个元素的 testcase 搜索对应 testSet 文件
  4. 组装独立的 testSet 文件，重命名以标识配置索引（如 `config0_*.uts`）
  5. 返回多个独立的 testSet 文件路径

### Task 8: 编写单元测试验证功能
- **优先级**: Medium
- **预估改动**: ~100 行
- **文件**: 新增测试文件
- **描述**:
  1. 测试字典格式配置（向后兼容）
  2. 测试列表格式配置（单个元素）
  3. 测试列表格式配置（多个元素）
  4. 测试列表格式配置（空列表异常）
  5. 测试列表格式配置（元素格式异常）

### Task 9: 编写集成测试验证端到端流程
- **优先级**: Medium
- **预估改动**: ~50 行
- **文件**: 新增集成测试文件
- **描述**:
  1. 测试完整的执行流程（字典格式）
  2. 测试完整的执行流程（列表格式）
  3. 测试多个配置的并行执行
  4. 测试 testSet 文件生成和命名

### Task 10: 更新文档和示例
- **优先级**: Low
- **预估改动**: ~20 行
- **文件**: README.md 或新增文档
- **描述**:
  1. 更新 README.md，说明列表格式配置的使用方法
  2. 提供列表格式配置的示例 JSON
  3. 说明字典格式和列表格式的区别和适用场景

## Execution Order

建议按以下顺序执行任务：

```
Phase 1: 核心功能实现
├─ Task 1: executor.py config_list 字段和格式判断
├─ Task 2: executor.py prepare() 参数传递
├─ Task 3: uniautos.py 参数接收和传递
├─ Task 4: TestSetGenParams 新增字段
├─ Task 5: TestSet.__init__() 接收参数
├─ Task 6: __find_testset_files_include_cases() 逻辑修改
└─ Task 7: __find_testset_by_config_list() 新增方法

Phase 2: 测试验证
├─ Task 8: 单元测试
└─ Task 9: 集成测试

Phase 3: 文档更新
└─ Task 10: 文档和示例
```

## Dependencies

```
Task 1 ──┐
         │
Task 2 ──┼── Task 3 ──┐
         │            │
Task 4 ──┤            ├── Task 5 ──┐
         │            │            │
Task 6 ──┘            │            ├── Task 7 ── Task 8 ── Task 9
                      │            │
                      └────────────┘
```

## Testing Strategy

### 单元测试覆盖

1. **executor.py**:
   - JSON 格式判断逻辑
   - 列表格式处理逻辑
   - config_list 字段保存
   - npu_parallel_num 设置

2. **test_set.py**:
   - config_list 判断逻辑
   - __find_testset_by_config_list() 方法
   - testSet 文件命名和分组

### 集成测试覆盖

1. **字典格式**:
   - 完全保持原有行为
   - 生成单个 testSet_Standard.uts

2. **列表格式**:
   - 多个配置并行执行
   - 每个配置生成独立的 testSet 文件
   - testSet 文件命名正确（config0_*.uts, config1_*.uts）

## Risk Assessment

| 风险 | 级别 | 缓解措施 |
|-----|------|---------|
| 向后兼容性破坏 | High | Task 1, 6 保持字典格式原有逻辑 |
| testSet 文件命名冲突 | Medium | Task 7 使用配置索引命名 |
| 参数传递链路错误 | Medium | Task 2, 3, 4, 5 确保传递完整 |
| testcase 分组错误 | High | Task 7 仔细处理每个元素的 testcase |
| 并行执行调度错误 | Low | 依赖现有 uniautos.py 的并行机制 |

## Success Criteria

1. 字典格式配置完全保持原有行为
2. 列表格式配置生成多个独立的 testSet 文件
3. testSet 文件命名正确（config0_*.uts, config1_*.uts）
4. npu_parallel_num 正确设置（= len(config_list))
5. 所有单元测试和集成测试通过
6. 向后兼容性验证通过（字典格式测试）