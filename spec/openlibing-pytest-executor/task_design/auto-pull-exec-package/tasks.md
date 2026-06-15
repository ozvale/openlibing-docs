# pytest 测试环境初始化自动拉取依赖资源 - 实现任务

## 进度: 0/5 complete

---

### Task 1: 在 scheduler_config.py 中添加挂载脚本路径配置
**状态**: ⬜ pending  
**预估**: 0.25h  
**涉及文件**: `pytest-executor/src/scheduler/scheduler_config.py`

**详细步骤**:
1. 在 Config 类中添加 `mount_script_path` 配置项
2. 设置默认值为 `/usr/local/bin/mount_share.sh`

**验证方式**:
- 验证配置项存在且默认值正确

---

### Task 2: 重构挂载逻辑为独立方法
**状态**: ⬜ pending  
**预估**: 0.5h  
**涉及文件**: `pytest-executor/src/executor/pytest_executor.py`

**详细步骤**:
1. 新增 `_mount_shared_storage` 方法
2. 支持列表格式的 `mount_source_data` 和 `mount_dest_dir`
3. 从 Config 读取 `mount_script_path` 配置
4. 遍历列表逐一执行挂载命令
5. 处理列表长度不一致的情况（以较短列表为准）

**验证方式**:
- 测试多数据源挂载（列表格式）
- 测试列表长度不一致的处理

---

### Task 3: 修改本地执行模式的代码拷贝逻辑
**状态**: ⬜ pending  
**预估**: 0.5h  
**涉及文件**: `pytest-executor/src/executor/pytest_executor.py`

**详细步骤**:
1. 修改 `_upload_to_server` 方法
2. 拷贝目录改为 `/home/<test_dir_name>`
3. 拷贝前添加清除原有目录逻辑
4. 调用 `_mount_shared_storage` 方法

**验证方式**:
- 测试代码拷贝到 `/home` 目录
- 测试清除原有目录逻辑

---

### Task 4: 增强远程执行模式支持
**状态**: ⬜ pending  
**预估**: 1h  
**涉及文件**: `pytest-executor/src/executor/pytest_executor.py`

**详细步骤**:
1. 修改 `_execute_remote_cases` 方法
2. 添加共享存储挂载逻辑（调用 `_mount_shared_storage`）
3. 添加测试工程代码拷贝逻辑（拷贝到 `/home` 目录）
4. 拷贝前添加清除原有目录逻辑

**验证方式**:
- 测试远程执行模式下挂载共享存储
- 测试远程执行模式下代码拷贝到 `/home` 目录

---

### Task 5: 集成测试与验证
**状态**: ⬜ pending  
**预估**: 0.5h  
**涉及范围**: 完整流程验证

**测试场景**:
1. 单环境单用例执行（本地模式）
2. 单环境多用例执行（本地模式）
3. 远程执行模式
4. 多数据源挂载场景

**验证点**:
- [ ] 多数据源挂载正常（列表格式）
- [ ] 挂载脚本路径从 Config 读取正确
- [ ] 测试工程代码正确拷贝到 `/home` 目录
- [ ] 拷贝前正确清除原有目录
- [ ] 列表长度不一致时以较短列表为准
- [ ] 挂载失败时记录警告但不中断流程
- [ ] 空列表或 None 时跳过挂载步骤
- [ ] 远程执行模式也执行挂载和拷贝

---

## 依赖关系

```
Task 1 ──> Task 2 ──> Task 3 ──> Task 5
         │
         └──> Task 4 ──┘
```

- Task 1 必须先完成（提供配置项）
- Task 2 依赖 Task 1（使用配置项）
- Task 3 依赖 Task 2（使用挂载方法）
- Task 4 依赖 Task 2（使用挂载方法）
- Task 5 依赖 Task 3 和 Task 4（验证功能）