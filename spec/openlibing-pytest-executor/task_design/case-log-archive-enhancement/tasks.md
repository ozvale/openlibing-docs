# 用例日志归档增强 - 实现任务

## 进度: 0/6 complete

---

### Task 1: pytest-testkit 修改日志目录结构
**状态**: ⬜ pending  
**预估**: 2h  
**涉及文件**: `pytest-testkit/pytest_testkit/lib/common/log/log_factory.py`

**详细步骤**:
1. 修改 `generate_html_report` 方法，生成新的目录结构：
   - 在 `base_dir/TestCases/` 下创建日期目录（格式：`YYYY-MM-DD`）
   - 在日期目录下创建用例子目录（格式：`{case_name}_{HH-MM-SS}`）
   - 将 HTML 文件生成在用例子目录中
2. 确保目录创建使用 `exist_ok=True` 避免重复创建报错

**验证方式**:
- 运行单个用例，检查目录结构是否符合预期
- 检查 HTML 文件是否正确生成在子目录中

---

### Task 2: pytest-testkit 添加 logger.path 属性
**状态**: ⬜ pending  
**预估**: 1h  
**涉及文件**: `pytest-testkit/pytest_testkit/lib/common/log/log_factory.py`

**详细步骤**:
1. 在 `LogManager` 类中添加 `get_case_log_path()` 方法
2. 在 `switch_to_case_log` 方法中设置 `_local.case_log_path`
3. 在 `InfraLogger` 类中添加 `path` 属性，返回当前用例的归档目录路径

**验证方式**:
- 在用例中通过 `logger.path` 获取路径
- 验证返回的路径与实际生成目录一致

---

### Task 3: pytest-executor 适配新目录结构扫描
**状态**: ⬜ pending  
**预估**: 1.5h  
**涉及文件**: `pytest-executor/pytest_executor/src/report/xml_processor.py`

**详细步骤**:
1. 修改 `_replace_log_case_name` 方法：
   - 从直接扫描 `TestCases/*.html` 改为递归扫描 `TestCases/*/*/*.html`
   - 适配新的目录层级（日期/用例子目录/HTML文件）
2. 确保 HTML 文件重命名后仍在原目录中

**验证方式**:
- 多环境执行场景下，检查 HTML 文件是否正确重命名
- 验证目录结构未被破坏

---

### Task 4: pytest-executor 实现文件打包功能
**状态**: ⬜ pending  
**预估**: 1.5h  
**涉及文件**: `pytest-executor/pytest_executor/src/report/xml_processor.py`

**详细步骤**:
1. 新增 `_package_case_logs` 方法：
   - 扫描用例子目录下除 pytest-testkit 插件生成的 HTML 文件（`{case_name}.html`）之外的所有文件（包括用例自身生成的其他 HTML 文件）
   - 如果存在需要打包的文件，将其打包为 zip（文件名：`{case_name}_log.zip` 或 `{case_name}@{env_name}_log.zip`）
   - zip 文件生成在日期目录下（与用例子目录同级）
   - 如果没有需要打包的文件，则不生成 zip 文件
2. 在 `_replace_log_case_name` 中调用打包方法

**验证方式**:
- 在用例目录下放置测试文件（csv、xlsx、用例自身生成的 HTML 等）
- 验证打包后的 zip 文件包含这些文件
- 验证多环境场景下 zip 文件名包含环境后缀
- 验证没有多余文件时不生成 zip

---

### Task 5: pytest-executor 添加 envDownloadUrl 属性
**状态**: ⬜ pending  
**预估**: 1h  
**涉及文件**: `pytest-executor/pytest_executor/src/report/report_uploader.py`

**详细步骤**:
1. 在 `upload_log_to_obs` 方法中：
   - 扫描日期目录下的 zip 文件
   - 为每个用例匹配对应的 zip 文件
   - 生成 `envDownloadUrl` URL（格式与 HTML 下载 URL 一致）
2. 仅当用例存在对应的 zip 文件时，将 `envDownloadUrl` 添加到 `result_json_list` 的该用例中；无 zip 文件时不设置该属性

**验证方式**:
- 检查生成的 `result_json_list` 中存在打包文件的用例包含 `envDownloadUrl`
- 验证没有打包文件的用例不包含 `envDownloadUrl` 属性
- 验证 URL 格式正确，可下载

---

### Task 6: 集成测试与验证
**状态**: ⬜ pending  
**预估**: 2h  
**涉及范围**: 完整流程验证

**测试场景**:
1. 单环境单用例执行
2. 单环境多用例执行
3. 多环境单用例执行（验证环境后缀处理）
4. 多环境多用例执行

**验证点**:
- [ ] 目录结构正确
- [ ] logger.path 可正常获取
- [ ] HTML 文件正确生成和重命名
- [ ] 非 HTML 文件正确打包
- [ ] envDownloadUrl 正确生成
- [ ] OBS 上传成功

---

## 依赖关系

```
Task 1 ──┬──> Task 3 ──┬──> Task 4 ──┬──> Task 5 ──> Task 6
         │             │             │
Task 2 ──┘             └─────────────┘
```

- Task 1 和 Task 2 可并行
- Task 3 依赖 Task 1
- Task 4 依赖 Task 3
- Task 5 依赖 Task 4
- Task 6 依赖全部前置任务
