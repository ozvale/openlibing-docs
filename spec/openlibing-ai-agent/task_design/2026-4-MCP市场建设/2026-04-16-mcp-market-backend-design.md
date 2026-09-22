# MCP Server 插件市场后端设计方案

## 1. 项目概述

基于初版 openlibing skillhub 打造一个面向 AI 编码工具用户的一站式 AI Agent 插件聚合与分发平台，专注于为 Trae IDE、OpenCode 等 AI 编码工具提供 MCP Servers 插件资源的浏览、搜索和一键安装服务。

## 2. 数据模型设计

### 2.1 MCP Server 主表

```python
class MCPServer(Base):
    __tablename__ = "ai_agent_mcp_servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    icon: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="其他")
    team: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1: github, 2: gitcode, 3: others
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # MCP Server 特有字段
    readme_md: Mapped[str | None] = mapped_column(Text)
    remote_server_config: Mapped[str | None] = mapped_column(Text)  # 远程服务器配置
    local_server_config: Mapped[str | None] = mapped_column(Text)   # 本地服务器配置
    env_schema: Mapped[str] = mapped_column(Text, default='{"properties": {}, "required": [], "type": "object"}')  # 环境变量schema
    parameter_schema: Mapped[str] = mapped_column(Text, default='{"properties": {}, "required": [], "type": "object"}')  # 参数schema

    tags: Mapped[list["MCPServerTag"]] = relationship(back_populates="mcp_server", cascade="all, delete-orphan")
```

### 2.2 MCP Server 标签表

```python
class MCPServerTag(Base):
    __tablename__ = "ai_agent_mcp_server_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mcp_server_name: Mapped[str] = mapped_column(
        String(128), ForeignKey("ai_agent_mcp_servers.name", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    mcp_server: Mapped["MCPServer"] = relationship(back_populates="tags")

    __table_args__ = (
        UniqueConstraint("mcp_server_name", "tag", name="uk_mcp_server_tag"),
        Index("idx_mcp_tag_server_name", "mcp_server_name"),
        Index("idx_mcp_tag", "tag"),
    )
```

### 2.3 用户 MCP Server 参数配置表

```python
class MCPServerUserConfig(Base):
    __tablename__ = "ai_agent_mcp_server_user_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mcp_server_name: Mapped[str] = mapped_column(
        String(128), ForeignKey("ai_agent_mcp_servers.name", ondelete="CASCADE"), nullable=False
    )
    trae_remote_config: Mapped[str | None] = mapped_column(Text)  # TRAE 远程配置
    trae_local_config: Mapped[str | None] = mapped_column(Text)   # TRAE 本地配置
    opencode_remote_config: Mapped[str | None] = mapped_column(Text)  # OpenCode 远程配置
    opencode_local_config: Mapped[str | None] = mapped_column(Text)   # OpenCode 本地配置
    local_config_user_params: Mapped[str] = mapped_column(Text, default="{}")  # JSON格式，存储用户自定义参数（本地）
    remote_config_user_params: Mapped[str] = mapped_column(Text, default="{}")  # JSON格式，存储用户自定义参数（远程）
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    mcp_server: Mapped["MCPServer"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "mcp_server_name", name="uk_user_mcp_server"),
        Index("idx_user_id", "user_id"),
        Index("idx_user_mcp_server", "user_id", "mcp_server_name"),
    )
```

### 2.4 数据模型说明

- **MCPServer**：MCP Server 主表，包含基本信息和 MCP Server 特有配置
  - `source_type`：源码类型（1: github, 2: gitcode, 3: others）
  - `source_url`：源码地址
  - `remote_server_config`：远程服务器配置（JSON 格式），包含 mcpServers 对象，每个服务器包含 url 和可选的 headers 字段
  - `local_server_config`：本地服务器配置（JSON 格式），包含 mcpServers 对象，每个服务器包含 command、args 和可选的 env 字段
  - `env_schema`：环境变量模式（JSON 格式），定义了该 MCP Server 所需的环境变量结构
  - `parameter_schema`：参数模式（JSON 格式），定义了该 MCP Server 所需的参数结构
  - `readme_md`：MCP Server 的 README 文档

- **MCPServerTag**：MCP Server 标签表，用于分类和搜索

- **MCPServerUserConfig**：用户 MCP Server 参数配置表，存储用户为特定 MCP Server 保存的自定义参数值和生成的配置
  - `user_id`：用户唯一标识
  - `mcp_server_name`：关联的 MCP Server 名称
  - `trae_remote_config`：Trae IDE 远程配置
  - `trae_local_config`：Trae IDE 本地配置
  - `opencode_remote_config`：OpenCode 远程配置
  - `opencode_local_config`：OpenCode 本地配置
  - `local_config_user_params`：JSON 格式存储的用户自定义参数（本地配置）
  - `remote_config_user_params`：JSON 格式存储的用户自定义参数（远程配置）
  - `created_at`：创建时间
  - `updated_at`：更新时间

## 3. API 端点设计

### 3.1 前端 API

#### 3.1.1 MCP Server 列表

```
GET /api/mcp-servers
参数：
- q: 搜索关键词（匹配名称、描述、团队、源码地址、标签）
- category: 分类筛选
- tag: 标签筛选
- sort: 排序方式（updatedAt, likeCount）
- page: 页码
- limit: 每页数量
```

#### 3.1.2 MCP Server 详情

```
GET /api/mcp-servers/{name}
```
  
#### 3.1.3 MCP Server 统计

```
GET /api/mcp-servers/stats
```

#### 3.1.4 用户配置获取

```
GET /api/mcp-servers/{name}/user-config
参数：
- user_id: 用户ID
```

#### 3.1.5 用户配置生成

```
POST /api/mcp-servers/{name}/user-config
请求体：
{
  "userId": "string",
  "transportType": "local|remote",
  "userParams": {"key": "value"}
}
```

#### 3.1.6 分类列表

```
GET /api/mcp-servers/categories
```

#### 3.1.7 标签列表

```
GET /api/mcp-servers/tags
```

### 3.2 管理后台 API

#### 3.2.1 MCP Server 管理列表

```
GET /mcp-servers
参数：
- q: 搜索关键词
- category: 分类筛选
- sort: 排序方式（updatedAt, likeCount）
- page: 页码
- limit: 每页数量
```

#### 3.2.2 创建 MCP Server

```
POST /mcp-servers
请求体：
{
  "name": "string",
  "displayName": "string",
  "icon": "string",
  "description": "string",
  "category": "string",
  "team": "string",
  "sourceUrl": "string",
  "readmeMd": "string",
  "remoteServerConfig": "json string",
  "localServerConfig": "json string",
  "envSchema": "json string",
  "parameterSchema": "json string",
  "tags": ["string"]
}
```

#### 3.2.3 更新 MCP Server

```
POST /mcp-servers/{name}
请求体：
{
  "displayName": "string",
  "icon": "string",
  "description": "string",
  "category": "string",
  "team": "string",
  "sourceUrl": "string",
  "readmeMd": "string",
  "remoteServerConfig": "json string",
  "localServerConfig": "json string",
  "envSchema": "json string",
  "parameterSchema": "json string",
  "tags": ["string"]
}
```

#### 3.2.4 删除 MCP Server

```
POST /mcp-servers/{name}/delete
```

#### 3.2.5 导入 MCP Server 预览

```
POST /mcp-servers/readme
请求体：
{
  "repoUrl": "string",
  "branch": "string"
}
```

## 4. 核心功能模块

### 4.1 MCP Server 配置生成器

- 根据 MCP Server 类型（远程/本地）生成不同的配置
- 支持 Trae IDE 和 OpenCode 两种工具的配置格式
- 处理用户自定义参数

### 4.2 搜索和筛选

- 多字段搜索（名称、描述、团队、源码地址）
- 按分类筛选
- 按标签筛选
- 多排序方式（最新发布、最热门）

### 4.3 统计和分析

- 喜欢/收藏统计
- 管理后台数据概览

## 5. 与现有系统集成

### 5.1 数据库集成

- 使用相同的数据库连接配置
- 共享 Base 模型类
- 保持一致的表命名规范

### 5.2 API 集成

- 在现有 FastAPI 应用中添加新的路由
- 保持相同的 API 设计风格
- 共享认证和权限机制

### 5.3 管理后台集成

- 在现有管理后台中添加 MCP Server 管理模块
- 共享管理后台布局和样式
- 统一的操作体验

## 6. 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL/SQLite
- **ORM**：SQLAlchemy 2.0
- **认证**：JWT（与现有系统一致）
- **文档**：Swagger UI（自动生成）

## 7. 实现计划

### 7.1 阶段一：数据模型和基础设施

1. 创建 MCP Server 相关的数据模型
2. 创建数据库迁移脚本
3. 实现基础的 CRUD 操作

### 7.2 阶段二：API 开发

1. 实现前端 API 端点
2. 实现管理后台 API 端点
3. 开发 MCP Server 配置生成器

### 7.3 阶段三：测试和优化

1. 编写单元测试和集成测试
2. 性能优化
3. 文档完善

## 8. 预期效果

- 实现 MCP Server 插件的集中展示和管理
- 提供便捷的配置生成和复制功能
- 支持多维度搜索和筛选
- 提供完善的管理后台
- 与现有系统无缝集成

## 9. 风险和应对措施

- **数据迁移风险**：使用 Alembic 进行数据库迁移，确保数据安全
- **API 兼容性**：遵循 RESTful API 设计规范，确保向后兼容
- **性能问题**：实现分页和缓存机制，优化查询性能
- **安全问题**：使用 HTTPS，实现输入验证和权限控制
