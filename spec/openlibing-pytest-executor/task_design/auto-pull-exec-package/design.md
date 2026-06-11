# pytest 测试环境初始化自动拉取依赖资源 - 技术设计

## 方案概述

本方案通过增强 pytest-executor 的环境初始化流程，实现多数据源共享存储挂载能力，确保测试环境准备的自动化和配置统一管理。

## 架构决策

### 决策 1：多数据源挂载实现方式

**选择**：遍历列表逐一执行挂载命令

**原因**：
- 简单直观，易于维护
- 每个挂载操作独立，便于错误处理和日志记录
- 符合现有挂载命令的执行模式

### 决策 2：挂载脚本路径配置位置

**选择**：配置在 scheduler_config.py 中

**原因**：
- 统一配置管理，便于维护
- 避免在每个用例的环境信息中重复配置
- 便于环境间的配置迁移

### 决策 3：配置格式

**选择**：只支持数组格式，不兼容字符串格式

**原因**：
- 简化代码逻辑，避免类型判断
- 强制使用新格式，确保配置一致性

## 关键设计要点

### 1. 扩展的配置数据结构

```python
# scheduler_config.py 新增配置
class Config:
    # ... 现有配置 ...
    mount_script_path = "/usr/local/bin/mount_share.sh"  # 挂载脚本路径
```

```python
# machine_info 配置格式
{
    # 共享存储挂载（仅支持列表格式）
    "mount_source_data": ["deepseek_v4_pro", "baai_taco"],
    "mount_dest_dir": ["/mnt/ascend/models/deepseek_v4_pro", "/mnt/ascend/dataset/baai_taco"],
    "res_type": "container"  # 可选：容器类型
}
```

### 2. 执行时序（本地执行模式）

```
┌─────────────────────────────────────────────────────────────────┐
│                    测试环境初始化流程（本地执行）                  │
├─────────────────────────────────────────────────────────────────┤
│  1. 获取环境配置（machine_info）                                 │
│         ↓                                                      │
│  2. 建立SSH连接（支持跳板机）                                    │
│         ↓                                                      │
│  3. 创建远程工作目录（/home/<test_dir_name>）                    │
│         ↓                                                      │
│  4. 清除原有目录（rm -rf /home/<test_dir_name>/*）              │
│         ↓                                                      │
│  5. [增强] 挂载共享存储（支持多数据源）                           │
│         ↓                                                      │
│  6. 上传测试代码（pytest-testkit + test_dir）                   │
│         ↓                                                      │
│  7. 执行测试                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3. 执行时序（远程执行模式）

```
┌─────────────────────────────────────────────────────────────────┐
│                    测试环境初始化流程（远程执行）                  │
├─────────────────────────────────────────────────────────────────┤
│  1. 获取环境配置（machine_info）                                 │
│         ↓                                                      │
│  2. 建立SSH连接（支持跳板机）                                    │
│         ↓                                                      │
│  3. 创建工作目录（/home/<test_dir_name>）                        │
│         ↓                                                      │
│  4. 清除原有目录（rm -rf /home/<test_dir_name>/*）              │
│         ↓                                                      │
│  5. [新增] 挂载共享存储（支持多数据源）                           │
│         ↓                                                      │
│  6. [新增] 上传测试代码（test_dir）                             │
│         ↓                                                      │
│  7. 执行测试（在调度机上运行，访问目标设备）                      │
└─────────────────────────────────────────────────────────────────┘
```

### 3. 挂载逻辑说明

| 配置格式 | 处理方式 |
|---------|----------|
| 列表格式 | 遍历列表，逐一执行挂载命令 |
| 列表长度不一致 | 以较短列表为准，多余项忽略并记录警告 |
| 空列表或None | 跳过挂载步骤 |

### 4. 测试工程代码拷贝

当前已实现：
```python
scp.put(str(self.test_dir), recursive=True, remote_path=remote_path)
```

用户将测试用例依赖的资源放在测试工程代码中即可，无需额外处理。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `pytest-executor/src/executor/pytest_executor.py` | 修改 | 增强挂载逻辑，支持多数据源 |
| `pytest-executor/src/scheduler/scheduler_config.py` | 修改 | 新增挂载脚本路径配置 |

## 接口变更

### 修改方法

```python
# PytestExecutor 类修改方法
def _prepare_test_environment(self, server_info, machine_info, upload_testkit=True):
    """
    Prepare test environment on target machine:
    - Clear existing directory
    - Mount shared storage
    - Upload test code to /home directory
    
    Args:
        server_info: Server connection information
        machine_info: Machine information (包含 mount_source_data 和 mount_dest_dir)
        upload_testkit: Whether to upload pytest-testkit (default: True)
    
    Returns:
        bool: Whether preparation succeeded
    """
```

### 删除方法

- `_upload_to_server`: 已重命名为 `_prepare_test_environment`

## 错误处理策略

| 错误场景 | 处理策略 |
|---------|----------|
| 挂载命令失败 | 记录警告，继续执行后续步骤 |
| 多数据源列表长度不一致 | 以较短列表为准，记录警告 |
| 配置格式错误（非列表） | 记录错误，跳过挂载步骤 |

## 风险 & 缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 挂载脚本路径配置错误 | 中 | 提供默认值，配置错误时使用默认脚本 |
| 多数据源挂载时间过长 | 低 | 添加日志记录，便于性能分析 |
| 配置格式不统一 | 中 | 文档明确说明只支持列表格式 |

## 测试策略

1. **单元测试**：
   - 验证多数据源挂载（列表格式）
   - 验证列表长度不一致的处理
   - 验证错误处理逻辑

2. **集成测试**：
   - 完整执行流程验证（本地执行）
   - 多环境执行场景验证

## 性能考虑

- 挂载操作：串行执行，避免资源竞争
- 错误重试：不重试，记录警告继续执行