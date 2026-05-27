# GitCode数据采集服务 - 部署指南

## 1. 环境要求

### 1.1 系统要求

- **Python**: 3.8 或更高版本
- **内存**: 至少 512MB 可用内存
- **磁盘**: 至少 1GB 可用磁盘空间

### 1.2 依赖服务

- **Doris数据库**: 0.15.0 或更高版本
- **GitCode API**: 需要访问令牌

### 1.3 网络要求

- 能够访问 GitCode API (https://api.gitcode.com)
- 能够访问 Doris 数据库

---

## 2. 本地部署

### 2.1 安装Python环境

```bash
# 检查Python版本
python3 --version
```

### 2.2 克隆项目

```bash
# 克隆代码仓库
git clone <repository-url>
cd gitCodeDataCollect
```

### 2.3 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

### 2.4 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

### 2.5 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件
vim .env  # 或使用其他编辑器
```

填写实际配置:

```bash
# GitCode 仓库访问令牌
# 命名格式: repo_name_TOKEN
model-agent_TOKEN=your_token_here
MindSpeed-Bridge_TOKEN=your_token_here
# ... 更多仓库token

# Doris 数据库配置
DORIS_HOST=your_doris_host
DORIS_DATABASE=your_database
DORIS_USER=your_user
DORIS_PASSWORD=your_password
```

### 2.6 配置采集任务

编辑 `config.yaml` 文件，配置需要采集的仓库:

```yaml
# 配置需要采集的仓库
repositories:
  - owner: Ascend
    repo_name: msinsight
    is_active: true
    auth:
      access_token: ${msinsight_TOKEN}  # 使用环境变量


### 2.7 初始化数据库

连接到Doris数据库,创建数据库和表:

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS gitcode_db;

-- 使用数据库
USE gitcode_db;

-- 创建Issue表
CREATE TABLE IF NOT EXISTS issues (
    issue_id BIGINT,
    repository_name VARCHAR(200),
    created_at DATETIME,
    updated_at DATETIME,
    is_deleted TINYINT,
    raw_data TEXT
) UNIQUE KEY(issue_id)
DISTRIBUTED BY HASH(issue_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "2"
);

-- 创建评论表
CREATE TABLE IF NOT EXISTS issue_comments (
    comment_id BIGINT,
    repository_name VARCHAR(200),
    issue_id BIGINT,
    created_at DATETIME,
    updated_at DATETIME,
    is_deleted TINYINT,
    raw_json TEXT
) UNIQUE KEY(comment_id)
DISTRIBUTED BY HASH(comment_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "2"
);
```

### 2.8 运行测试

```bash
# 运行单元测试
pytest tests/ -v

# 确保所有测试通过
```

### 2.9 运行采集任务

```bash
# 采集Issue数据
python main.py config.yaml --type=issue

# 采集评论数据
python main.py config.yaml --type=issue_comment

# 指定代码仓采集
python main.py config.yaml --type=issue --owner=your_owner --repo=your_repo_name

# 指定采集时间范围
python main.py config.yaml --type=issue --since=2024-01-01 --until=2024-12-31

# 组合使用：指定代码仓和时间范围
python main.py config.yaml --type=issue --owner=your_owner --repo=your_repo_name --since=2024-01-01 --until=2024-12-31
```

---

## 3. DolphinScheduler部署

### 3.1 打包项目

```bash
# 运行打包脚本
python package_for_dolphin.py

# 生成 gitcode-collector.zip
```

### 3.2 上传到DolphinScheduler

1. 登录DolphinScheduler Web界面
2. 进入"资源中心" -> "文件管理"
3. 上传 `gitcode-collector.zip`
4. 解压到指定目录

### 3.3 配置任务

#### 方式1: 使用环境变量

1. 创建任务,选择"Python"类型
2. 配置脚本路径: `main.py`
3. 配置参数: `config.yaml --type=issue`
4. 在"环境变量"中添加:
   ```
   # 仓库访问令牌
   your_repo_name_TOKEN=your_token_here
   another_repo_name_TOKEN=your_token_here

   # Doris数据库配置
   DORIS_HOST=your_doris_host
   DORIS_DATABASE=your_database
   DORIS_USER=your_user
   DORIS_PASSWORD=your_password
   ```

#### 方式2: 使用命令行参数

1. 创建任务,选择"Python"类型
2. 配置脚本路径: `main.py`
3. 配置参数:
   ```
   config.yaml --token=your_token_here --type=issue
   ```

### 3.4 配置调度

1. 创建工作流
2. 添加任务节点
3. 配置调度周期(如每天凌晨2点执行)
4. 配置告警通知

### 3.5 定时任务配置示例

```yaml
# 每天凌晨2点采集Issue
- 任务名称: collect_issues
  调度时间: 0 2 * * ?
  脚本: python main.py config.yaml --type=issue

# 每天凌晨3点采集评论
- 任务名称: collect_comments
  调度时间: 0 3 * * ?
  脚本: python main.py config.yaml --type=issue_comment
```

---

## 4. 故障排查

### 4.1 常见问题

#### 问题1: 连接Doris失败

**症状**:
```
Error: Can't connect to MySQL server at '192.168.1.100'
```

**解决方案**:
1. 检查Doris服务是否运行
2. 检查网络连接
3. 检查防火墙配置
4. 验证用户名和密码

#### 问题2: API请求失败

**症状**:
```
Error: 403 Forbidden
```

**解决方案**:
1. 检查access_token是否正确
2. 检查API速率限制
3. 检查网络连接

#### 问题3: 内存不足

**症状**:
```
MemoryError: Unable to allocate array
```

**解决方案**:
1. 减少批量处理的数据量
2. 增加系统内存
3. 优化代码,使用流式处理

### 4.2 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/task_*.log

# 查看API调用失败
grep "API请求失败" logs/task_*.log

# 查看数据库错误
grep "数据库" logs/task_*.log
```

---

## 5. 附录

### 5.1 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 9030 | Doris FE | Doris前端服务（默认端口） |

**注意**: 实际端口配置请参考Doris数据库的实际配置。

### 5.2 GitCode API速率限制

GitCode API对每个访问令牌有以下速率限制：

| 限制类型 | 限制值 | 说明 |
|---------|--------|------|
| 每小时请求数 | 5000次 | 每个token每小时最多5000次请求 |
| 并发请求 | 1个 | 同一token同时只能有1个请求 |

**多Token并行采集**：
- 系统支持为不同仓库配置独立的访问令牌
- 每个token独立计算速率限制
- 通过配置多个仓库的token，可以实现并行采集，提高整体采集效率
- 建议为每个仓库配置独立的token，避免速率限制冲突

### 5.3 性能基准

| 指标 | 数值 | 说明 |
|------|------|------|
| 单Token采集速度 | 约50条/分钟 | 受API速率限制影响 |
| 多Token并行采集 | N×50条/分钟 | N为token数量，可线性提升 |
| Stream Load导入速度 | 10000条/秒 | 批量导入到Doris的速度 |
| 内存占用 | 100-500MB | 取决于批量处理的数据量 |
| CPU占用 | 10-30% | 正常采集时的CPU使用率 |

**性能优化建议**：
- 为每个仓库配置独立的访问令牌，实现并行采集
- 适当调整批量处理的数据量，平衡内存占用和性能
- 在非高峰期执行采集任务，避免API速率限制
