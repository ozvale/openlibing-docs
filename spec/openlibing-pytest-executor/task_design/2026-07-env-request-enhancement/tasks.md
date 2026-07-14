# pytest 测试套件环境请求与连接增强 — 实现任务

## 进度: 5/8 complete

- [x] Task 1: 环境状态判断优化（env_manager.py）
- [x] Task 2: 软件部署状态检查（env_manager.py）
- [ ] Task 3: SSH 连接自动重试（ssh.py + device.py）
- [ ] Task 4: SCP 连接自动重试（sftp.py）
- [x] Task 5: 共享存储挂载检查（env_manager.py）
- [x] Task 6: TTL 参数优化（env_manager.py）
- [x] Task 7: 环境名称统一（env_manager.py）
- [x] Task 8: HTML 日志展示优化与日志模块重构

## 任务详情

### Task 1: 环境状态判断优化 ✅

**文件**: `pytest-executor/src/scheduler/env_manager.py`

**实现内容**:
- 在 `_query_k8s_env_status()` 方法中添加 `rejected` 状态检查
- `status=rejected` 时立即停止重试，返回失败

**提交记录**: `dd94b44 feat(env_manager): enhance k8s environment allocation`

---

### Task 2: 软件部署状态检查 ✅

**文件**: `pytest-executor/src/scheduler/env_manager.py`

**实现内容**:
- 检查 device 中是否有 `softwares` 参数
- 若存在 `softwares` 且不为空，检查部署状态
- 支持状态：
  - `deploying`：继续轮询
  - `deploy_failed`：分配失败
  - `available`：分配成功
- 新增辅助方法 `_check_software_deployment_status()`

**提交记录**: `dd94b44 feat(env_manager): enhance k8s environment allocation`

---

### Task 3: SSH 连接自动重试 ⏳

**文件**: 
- `pytest-testkit/pytest_testkit/lib/base/ssh.py`
- `pytest-testkit/pytest_testkit/lib/common/environment/device.py`

**待实现内容**:
- 连接失败时自动重试
- 支持配置重试次数

---

### Task 4: SCP 连接自动重试 ⏳

**文件**: `pytest-testkit/pytest_testkit/lib/base/sftp.py`

**待实现内容**:
- SCP 操作失败时自动重试
- 支持配置重试次数

---

### Task 5: 共享存储挂载检查 ✅

**文件**: `pytest-executor/src/scheduler/env_manager.py`

**实现内容**:
- 新增辅助方法 `_check_mount_data_source()`
- 检查 device 中是否有 `mount_data_source` 参数
- 若有 `mount_data_source` 但无 `use_nfs=True`，自动补全 `use_nfs=True`
- 在 `pytest_executor.py` 中检查 `/mnt/weight`、`/mnt/share` 目录存在性

**提交记录**: 
- 相关实现在 `pytest-executor/src/scheduler/env_manager.py` 和 `pytest-executor/src/executor/pytest_executor.py`

---

### Task 6: TTL 参数优化 ✅

**文件**: `pytest-executor/src/scheduler/env_manager.py`

**实现内容**:
- 新增辅助方法 `_extract_max_ttl()`
- 从 device 列表中提取所有 `ttl` 值
- 取最大值并提升到外层（与 `env_definition` 同级）
- 将 `ttl` 添加到 API 请求 payload 中

**提交记录**: 
- 相关实现在 `pytest-executor/src/scheduler/env_manager.py`

---

### Task 7: 环境名称统一 ✅

**文件**: `pytest-executor/src/scheduler/env_manager.py`

**实现内容**:
- 使用统一的环境名称格式：`{Config.platform}-{Config.job_unique_id}`
- 移除了 API 请求中的 `env_name` 参数

**提交记录**: 
- `dd94b44 feat(env_manager): enhance k8s environment allocation`
- `383e469 fix(env_manager): remove env_name from API payload`

---

### Task 8: HTML 日志展示优化与日志模块重构 ✅

**文件**: `pytest-testkit/pytest_testkit/lib/common/log/`

**实现内容**:
1. **HTML 日志展示优化**:
   - 修复换行、断行、乱码问题
   - 基于 `logger.tc_step` 记录，支持 step 折叠展开
   - pytest 执行添加 `-s -v --tb=short`

2. **日志模块重构**:
   - 将原有的 `log_factory.py` 拆分为 3 个模块：
     - `filters.py`：敏感数据脱敏过滤器 `SensitiveDataFilter`
     - `infra_logger.py`：核心日志类 `InfraLogger`、日志级别定义、处理器
     - `manager.py`：日志管理器 `LogManager`、文件管理器 `LogFileManager`、HTML 报告生成
   - 更新 `__init__.py` 保持向后兼容，原有 API 不变

**提交记录**: `a5890a8 refactor(log): Split monolithic log_factory.py into 3 files`

---

## 实现位置说明

| 任务 | 实际实现位置 | 原设计位置 | 说明 |
|------|-------------|-----------|------|
| Task 1 | `pytest-executor/src/scheduler/env_manager.py` | 正确 | - |
| Task 2 | `pytest-executor/src/scheduler/env_manager.py` | 正确 | - |
| Task 3 | 待实现 | `pytest-testkit/.../ssh.py` | 待实现 |
| Task 4 | 待实现 | `pytest-testkit/.../sftp.py` | 待实现 |
| Task 5 | `pytest-executor/src/scheduler/env_manager.py` | `pytest-testkit/.../allocator.py` | 实现位置调整 |
| Task 6 | `pytest-executor/src/scheduler/env_manager.py` | `pytest-testkit/.../allocator.py` | 实现位置调整 |
| Task 7 | `pytest-executor/src/scheduler/env_manager.py` | 正确 | - |
| Task 8 | `pytest-testkit/pytest_testkit/lib/common/log/` | 正确 | - |
