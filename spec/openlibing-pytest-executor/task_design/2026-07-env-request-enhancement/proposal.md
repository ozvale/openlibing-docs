# pytest 测试套件环境请求与连接增强

## 需求背景

为保障编译器业务生产测试基础运行，提升 UniAutos 和 pytest 测试套件的使用体验，需要增强环境管理能力，确保业务开站建证项目目标顺利达成。

## 功能描述

### 1. 环境状态判断优化
- 18s 场景下判断环境状态
- `status=rejected` 时不再重试
- **实现位置**: `pytest-executor/src/scheduler/env_manager.py`

### 2. 软件部署状态检查
- 若 device 中有 `softwares` 参数（数组）且不为空，需判断部署状态
- 状态类型：
  - `deploying`：继续轮询等待
  - `deploy_failed`：分配失败
  - `available`：分配成功
- **实现位置**: `pytest-executor/src/scheduler/env_manager.py`
- **新增辅助方法**: `_check_software_deployment_status()`

### 3. SSH/SCP 连接自动重试
- 连接失败时自动重试
- 可控制重试次数
- **实现位置**: 
  - `pytest-testkit/pytest_testkit/lib/base/ssh.py`
  - `pytest-testkit/pytest_testkit/lib/base/sftp.py`

### 4. 共享存储挂载检查
- 若有 `mount_data_source` 但无 `use_nfs:true`，自动补全
- 检查 `/mnt/weight`、`/mnt/share` 目录存在性及节点使用情况
- **实现位置**: `pytest-testkit/pytest_testkit/lib/common/environment/allocator.py`

### 5. TTL 参数优化
- 将 `ttl` 参数从 device 提升到外层，与 `env_definition` 同级
- 取 device 列表中 `ttl` 的最大值
- **实现位置**: `pytest-testkit/pytest_testkit/lib/common/environment/allocator.py`

### 6. 环境名称统一
- 调用 k8s 时传入统一 name 格式：`{Config.platform}-{Config.job_unique_id}`
- **实现位置**: `pytest-executor/src/scheduler/env_manager.py`

### 7. HTML 日志展示优化
- 修复换行、断行、乱码问题
- 基于 `logger.tc_step` 记录，支持 step 折叠展开
- pytest 执行添加 `-s -v --tb=short`
- **实现位置**: `pytest-testkit/pytest_testkit/lib/common/log/manager.py`

### 8. 日志模块重构
- 将原有的 `log_factory.py` 单一大文件拆分为 3 个模块：
  - `filters.py`：敏感数据脱敏过滤器 `SensitiveDataFilter`
  - `infra_logger.py`：核心日志类 `InfraLogger`、日志级别定义、处理器
  - `manager.py`：日志管理器 `LogManager`、文件管理器 `LogFileManager`、HTML 报告生成
- 更新 `__init__.py` 保持向后兼容，原有 API 不变
- **实现位置**: `pytest-testkit/pytest_testkit/lib/common/log/`

## 验收标准
- [ ] 环境状态判断正确，rejected 状态不重试
- [ ] 软件部署状态检查完整，各状态处理正确
- [ ] SSH/SCP 连接失败自动重试，可配置重试次数
- [ ] 共享存储挂载检查自动补全 use_nfs 参数
- [ ] TTL 参数正确提取到外层
- [ ] 环境名称按统一格式 `{platform}-{job_unique_id}` 生成
- [ ] HTML 日志展示正常，支持 step 折叠展开
- [ ] 日志模块拆分完成，向后兼容

## 影响范围
- `pytest-testkit/pytest_testkit/lib/common/environment/allocator.py`
- `pytest-testkit/pytest_testkit/lib/common/environment/device.py`
- `pytest-testkit/pytest_testkit/lib/base/ssh.py`
- `pytest-testkit/pytest_testkit/lib/base/sftp.py`
- `pytest-testkit/pytest_testkit/lib/common/log/filters.py`（新增）
- `pytest-testkit/pytest_testkit/lib/common/log/infra_logger.py`（新增）
- `pytest-testkit/pytest_testkit/lib/common/log/manager.py`（新增）
- `pytest-testkit/pytest_testkit/lib/common/log/__init__.py`
- `pytest-executor/src/scheduler/env_manager.py`
