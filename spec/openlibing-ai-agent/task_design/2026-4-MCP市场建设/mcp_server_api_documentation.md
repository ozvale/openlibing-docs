# MCP Server API 接口文档

## 1. 概述

MCP Server 插件市场后端 API 提供了 MCP Server 插件的浏览、搜索、详情查看、配置生成等功能，支持 Trae IDE 和 OpenCode 两种工具的配置格式。

## 2. 接口列表

### 2.1 公共接口

| 接口名称 | HTTP 方法 | 路径 | 功能描述 |
|---------|----------|------|---------|
| 获取 MCP Server 列表 | GET | /api/mcp-servers | 获取 MCP Server 列表，支持搜索、筛选和排序 |
| 获取 MCP Server 详情 | GET | /api/mcp-servers/{name} | 获取指定 MCP Server 的详细信息 |
| 点赞 MCP Server | POST | /api/mcp-servers/{name}/like | 为指定 MCP Server 点赞 |
| 取消点赞 MCP Server | POST | /api/mcp-servers/{name}/unlike | 取消对指定 MCP Server 的点赞 |
| 获取分类列表 | GET | /api/mcp-servers/categories | 获取所有分类 |
| 获取标签列表 | GET | /api/mcp-servers/tags | 获取热门标签 |
| 获取统计信息 | GET | /api/mcp-servers/stats | 获取 MCP Server 统计信息 |
| 获取用户配置 | GET | /api/mcp-servers/{name}/user-config | 获取用户的 MCP Server 配置 |
| 生成用户配置 | POST | /api/mcp-servers/{name}/user-config | 生成用户的 MCP Server 配置 |

### 2.2 管理接口

| 接口名称 | HTTP 方法 | 路径 | 功能描述 |
|---------|----------|------|---------|
| 管理端获取 MCP Server 列表 | GET | /api/admin/mcp-servers | 管理端获取 MCP Server 列表，支持搜索、筛选和排序 |
| 管理端创建 MCP Server | POST | /api/admin/mcp-servers | 管理端创建 MCP Server |
| 管理端更新 MCP Server | POST | /api/admin/mcp-servers/{name} | 管理端更新 MCP Server |
| 管理端删除 MCP Server | POST | /api/admin/mcp-servers/{name}/delete | 管理端删除 MCP Server |
| 管理端预览 MCP Server README | POST | /api/admin/mcp-servers/readme | 管理端从仓库预览 MCP Server README |

## 3. 接口详情

### 3.1 获取 MCP Server 列表

**HTTP 方法**: GET
**路径**: `/api/mcp-servers`
**功能描述**: 获取 MCP Server 列表，支持搜索、筛选和排序

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| q | string | 否 | 搜索关键词 | "test server" |
| category | string | 否 | 分类筛选，默认"all" | "ai-assistant" |
| tag | string | 否 | 标签筛选 | "llm" |
| sort | string | 否 | 排序方式，可选值：updatedAt, likeCount，默认 updatedAt | "likeCount" |
| page | integer | 否 | 页码，默认 1 | 2 |
| limit | integer | 否 | 每页数量，范围 1-50，默认 12 | 20 |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| data | array | MCP Server 列表 |
| total | integer | 总数量 |
| page | integer | 当前页码 |
| limit | integer | 每页数量 |

#### 示例请求

```bash
GET /api/mcp-servers?q=test&category=ai-assistant&sort=likeCount&page=1&limit=12
```

#### 示例响应

```json
{
  "data": [
    {
      "name": "test-server",
      "displayName": "Test Server",
      "icon": "https://example.com/icon.png",
      "description": "A test MCP server",
      "category": "ai-assistant",
      "team": "Test Team",
      "tags": ["test", "ai"],
      "likeCount": 10,
      "sourceUrl": "https://github.com/test/server",
      "updatedAt": "2026-04-23T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 12
}
```

### 3.2 获取 MCP Server 详情

**HTTP 方法**: GET
**路径**: `/api/mcp-servers/{name}`
**功能描述**: 获取指定 MCP Server 的详细信息

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| name | string | MCP Server 名称 |
| displayName | string | 显示名称 |
| icon | string | 图标 URL |
| description | string | 描述 |
| category | string | 分类 |
| team | string | 团队 |
| tags | array | 标签列表 |
| likeCount | integer | 点赞数 |
| sourceUrl | string | 源码地址 |
| updatedAt | string | 更新时间 |
| createdAt | string | 创建时间 |
| readmeMd | string | README 文档 |
| remoteServerConfig | object | 远程服务器配置 |
| localServerConfig | object | 本地服务器配置 |
| envSchema | object | 环境变量模式 |
| parameterSchema | object | 参数模式 |

#### 示例请求

```bash
GET /api/mcp-servers/test-server
```

#### 示例响应

```json
{
  "name": "test-server",
  "displayName": "Test Server",
  "icon": "https://example.com/icon.png",
  "description": "A test MCP server",
  "category": "ai-assistant",
  "team": "Test Team",
  "tags": ["test", "ai"],
  "likeCount": 10,
  "sourceUrl": "https://github.com/test/server",
  "updatedAt": "2026-04-23T10:00:00Z",
  "createdAt": "2026-04-22T10:00:00Z",
  "readmeMd": "# Test Server\nThis is a test server.",
  "remoteServerConfig": {
    "mcpServers": {
      "test": {
        "url": "https://api.example.com",
        "headers": {
          "Authorization": "Bearer {token}"
        }
      }
    }
  },
  "localServerConfig": {
    "mcpServers": {
      "test": {
        "command": "python",
        "args": ["server.py"],
        "env": {
          "PORT": "8000"
        }
      }
    }
  },
  "envSchema": {
    "properties": {
      "PORT": {
        "description": "Server port",
        "guidance": "Enter the port number for the server"
      }
    },
    "required": ["PORT"],
    "type": "object"
  },
  "parameterSchema": {
    "properties": {
      "token": {
        "category": "headers",
        "description": "API token",
        "guidance": "Enter your API token"
      }
    },
    "required": ["token"],
    "type": "object"
  }
}
```

### 3.3 点赞 MCP Server

**HTTP 方法**: POST
**路径**: `/api/mcp-servers/{name}/like`
**功能描述**: 为指定 MCP Server 点赞

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| ok | boolean | 操作结果 |

#### 示例请求

```bash
POST /api/mcp-servers/test-server/like
```

#### 示例响应

```json
{
  "ok": true
}
```

### 3.4 取消点赞 MCP Server

**HTTP 方法**: POST
**路径**: `/api/mcp-servers/{name}/unlike`
**功能描述**: 取消对指定 MCP Server 的点赞

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| ok | boolean | 操作结果 |

#### 示例请求

```bash
POST /api/mcp-servers/test-server/unlike
```

#### 示例响应

```json
{
  "ok": true
}
```

### 3.5 获取分类列表

**HTTP 方法**: GET
**路径**: `/api/mcp-servers/categories`
**功能描述**: 获取所有分类

#### 请求参数

无

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| categories | array | 分类列表 |

#### 示例请求

```bash
GET /api/mcp-servers/categories
```

#### 示例响应

```json
{
  "categories": [
    "ai-assistant",
    "code-analysis",
    "dev-tools"
  ]
}
```

### 3.6 获取标签列表

**HTTP 方法**: GET
**路径**: `/api/mcp-servers/tags`
**功能描述**: 获取热门标签

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| limit | integer | 否 | 标签数量，范围 1-50，默认 20 | 10 |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| tags | array | 标签列表 |

#### 示例请求

```bash
GET /api/mcp-servers/tags?limit=10
```

#### 示例响应

```json
{
  "tags": [
    "llm",
    "ai",
    "python",
    "java"
  ]
}
```

### 3.7 获取统计信息

**HTTP 方法**: GET
**路径**: `/api/mcp-servers/stats`
**功能描述**: 获取 MCP Server 统计信息

#### 请求参数

无

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| totalMCPServers | integer | 总 MCP Server 数量 |
| recentMCPServers | array | 最近添加的 MCP Server 列表 |
| topMCPServers | array | 最受欢迎的 MCP Server 列表 |

#### 示例请求

```bash
GET /api/mcp-servers/stats
```

#### 示例响应

```json
{
  "totalMCPServers": 100,
  "recentMCPServers": [
    {
      "name": "new-server",
      "displayName": "New Server",
      "icon": "https://example.com/new-icon.png",
      "description": "A new MCP server",
      "category": "ai-assistant",
      "team": "New Team",
      "tags": ["new", "ai"],
      "likeCount": 5,
      "sourceUrl": "https://github.com/new/server",
      "updatedAt": "2026-04-23T10:00:00Z"
    }
  ],
  "topMCPServers": [
    {
      "name": "popular-server",
      "displayName": "Popular Server",
      "icon": "https://example.com/popular-icon.png",
      "description": "A popular MCP server",
      "category": "ai-assistant",
      "team": "Popular Team",
      "tags": ["popular", "ai"],
      "likeCount": 100,
      "sourceUrl": "https://github.com/popular/server",
      "updatedAt": "2026-04-23T10:00:00Z"
    }
  ]
}
```

### 3.8 获取用户配置

**HTTP 方法**: GET
**路径**: `/api/mcp-servers/{name}/user-config`
**功能描述**: 获取用户的 MCP Server 配置

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |
| userId | string | 是 | 用户 ID | "user123" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| id | integer | 配置 ID |
| userId | string | 用户 ID |
| mcpServerName | string | MCP Server 名称 |
| traeRemoteConfig | string | Trae IDE 远程配置 |
| traeLocalConfig | string | Trae IDE 本地配置 |
| opencodeRemoteConfig | string | OpenCode 远程配置 |
| opencodeLocalConfig | string | OpenCode 本地配置 |
| localConfigUserParams | object | 本地配置用户参数 |
| remoteConfigUserParams | object | 远程配置用户参数 |
| createdAt | string | 创建时间 |
| updatedAt | string | 更新时间 |

#### 示例请求

```bash
GET /api/mcp-servers/test-server/user-config?userId=user123
```

#### 示例响应

```json
{
  "id": 1,
  "userId": "user123",
  "mcpServerName": "test-server",
  "traeRemoteConfig": "{\"mcpServers\": {\"test\": {\"url\": \"https://api.example.com\", \"headers\": {\"Authorization\": \"Bearer abc123\"}}}}",
  "traeLocalConfig": "{\"mcpServers\": {\"test\": {\"command\": \"python\", \"args\": [\"server.py\"], \"env\": {\"PORT\": \"8000\"}}}}",
  "opencodeRemoteConfig": null,
  "opencodeLocalConfig": null,
  "localConfigUserParams": {
    "PORT": "8000"
  },
  "remoteConfigUserParams": {
    "token": "abc123"
  },
  "createdAt": "2026-04-23T10:00:00Z",
  "updatedAt": "2026-04-23T10:00:00Z"
}
```

### 3.9 生成用户配置

**HTTP 方法**: POST
**路径**: `/api/mcp-servers/{name}/user-config`
**功能描述**: 生成用户的 MCP Server 配置

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |
| body.userId | string | 是 | 用户 ID | "user123" |
| body.transportType | string | 否 | 传输类型，可选值：local, remote，默认 local | "remote" |
| body.userParams | object | 否 | 用户参数 | {"token": "abc123"} |

#### 响应参数

同获取用户配置接口

#### 示例请求

```bash
POST /api/mcp-servers/test-server/user-config
Content-Type: application/json

{
  "userId": "user123",
  "transportType": "remote",
  "userParams": {
    "token": "abc123"
  }
}
```

#### 示例响应

同获取用户配置接口


## 4. 数据模型

### 4.1 MCPServerListItem

```json
{
  "name": "string",
  "displayName": "string",
  "icon": "string",
  "description": "string",
  "category": "string",
  "team": "string",
  "tags": ["string"],
  "likeCount": 0,
  "sourceUrl": "string",
  "updatedAt": "string"
}
```

### 4.2 MCPServerDetail

```json
{
  "name": "string",
  "displayName": "string",
  "icon": "string",
  "description": "string",
  "category": "string",
  "team": "string",
  "tags": ["string"],
  "likeCount": 0,
  "sourceUrl": "string",
  "updatedAt": "string",
  "createdAt": "string",
  "readmeMd": "string",
  "remoteServerConfig": {
    "mcpServers": {
      "string": {
        "url": "string",
        "headers": {"string": "string"}
      }
    }
  },
  "localServerConfig": {
    "mcpServers": {
      "string": {
        "command": "string",
        "args": ["string"],
        "env": {"string": "string"}
      }
    }
  },
  "envSchema": {
    "properties": {
      "string": {
        "description": "string",
        "guidance": "string"
      }
    },
    "required": ["string"],
    "type": "string"
  },
  "parameterSchema": {
    "properties": {
      "string": {
        "category": "string",
        "description": "string",
        "guidance": "string"
      }
    },
    "required": ["string"],
    "type": "string"
  }
}
```

### 4.3 UserConfigDetail

```json
{
  "id": 0,
  "userId": "string",
  "mcpServerName": "string",
  "traeRemoteConfig": "string",
  "traeLocalConfig": "string",
  "opencodeRemoteConfig": "string",
  "opencodeLocalConfig": "string",
  "localConfigUserParams": {"string": "string"},
  "remoteConfigUserParams": {"string": "string"},
  "createdAt": "string",
  "updatedAt": "string"
}
```

### 4.4 GenerateUserConfigRequest

```json
{
  "userId": "string",
  "transportType": "string",
  "userParams": {"string": "string"}
}
```

## 5. 完整调用示例

以下是一个完整的调用示例，展示了如何获取 MCP Server 列表、查看详情并生成用户配置。

### 5.1 获取 MCP Server 列表

```bash
curl -X GET "http://localhost:8000/api/mcp-servers?category=ai-assistant&sort=likeCount"
```

### 5.2 获取 MCP Server 详情

```bash
curl -X GET "http://localhost:8000/api/mcp-servers/chatgpt-server"
```

### 5.3 生成用户配置

```bash
curl -X POST "http://localhost:8000/api/mcp-servers/chatgpt-server/user-config" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user123", "transportType": "remote", "userParams": {"api_key": "sk-1234567890abcdef"}}'
```

### 5.4 获取用户配置

```bash
curl -X GET "http://localhost:8000/api/mcp-servers/chatgpt-server/user-config?userId=user123"
```

## 6. 错误处理

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| 400 | 请求参数错误 | 检查请求参数是否符合要求 |
| 404 | MCP Server 不存在 | 检查 MCP Server 名称是否正确 |
| 500 | 服务器内部错误 | 联系系统管理员 |

## 7. 管理接口详情

### 7.1 管理端获取 MCP Server 列表

**HTTP 方法**: GET
**路径**: `/api/admin/mcp-servers`
**功能描述**: 管理端获取 MCP Server 列表，支持搜索、筛选和排序
**权限要求**: 管理员

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| q | string | 否 | 搜索关键词 | "test server" |
| category | string | 否 | 分类筛选，默认"all" | "ai-assistant" |
| sort | string | 否 | 排序方式，可选值：updatedAt, likeCount，默认 updatedAt | "likeCount" |
| page | integer | 否 | 页码，默认 1 | 2 |
| limit | integer | 否 | 每页数量，范围 1-50，默认 12 | 20 |

#### 响应参数

同公共接口中的获取 MCP Server 列表接口

#### 示例请求

```bash
GET /api/admin/mcp-servers?q=test&category=ai-assistant&sort=likeCount&page=1&limit=12
```

#### 示例响应

同公共接口中的获取 MCP Server 列表接口

### 7.2 管理端创建 MCP Server

**HTTP 方法**: POST
**路径**: `/api/admin/mcp-servers`
**功能描述**: 管理端创建 MCP Server
**权限要求**: 管理员

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |
| displayName | string | 否 | 显示名称 | "Test Server" |
| icon | string | 否 | 图标 URL | "https://example.com/icon.png" |
| description | string | 否 | 描述 | "A test MCP server" |
| category | string | 否 | 分类，默认"其他" | "ai-assistant" |
| team | string | 否 | 团队，默认"未知团队" | "Test Team" |
| sourceUrl | string | 否 | 源码地址 | "https://github.com/test/server" |
| readmeMd | string | 否 | README 文档 | "# Test Server" |
| remoteServerConfig | string | 否 | 远程服务器配置 JSON 字符串 | '{"mcpServers": {"test": {"url": "https://api.example.com"}}}' |
| localServerConfig | string | 否 | 本地服务器配置 JSON 字符串 | '{"mcpServers": {"test": {"command": "python", "args": ["server.py"]}}}' |
| envSchema | string | 否 | 环境变量模式 JSON 字符串 | '{"properties": {}, "required": [], "type": "object"}' |
| parameterSchema | string | 否 | 参数模式 JSON 字符串 | '{"properties": {}, "required": [], "type": "object"}' |
| tags | array | 否 | 标签列表 | ["test", "ai"] |

#### 响应参数

同公共接口中的获取 MCP Server 详情接口

#### 示例请求

```bash
POST /api/admin/mcp-servers
Content-Type: application/json

{
  "name": "test-server",
  "displayName": "Test Server",
  "icon": "https://example.com/icon.png",
  "description": "A test MCP server",
  "category": "开发者工具",
  "team": "Test Team",
  "sourceUrl": "https://github.com/test/server",
  "readmeMd": "# Test Server\nThis is a test server.",
  "remoteServerConfig": "{\"mcpServers\": {\"test\": {\"url\": \"https://api.example.com\"}}}",
  "localServerConfig": "{\"mcpServers\": {\"test\": {\"command\": \"python\", \"args\": [\"server.py\"]}}}",
  "envSchema": "{\"properties\": {}, \"required\": [], \"type\": \"object\"}",
  "parameterSchema": "{\"properties\": {}, \"required\": [], \"type\": \"object\"}",
  "tags": ["test", "ai"]
}
```

#### 示例响应

同公共接口中的获取 MCP Server 详情接口

### 7.3 管理端更新 MCP Server

**HTTP 方法**: POST
**路径**: `/api/admin/mcp-servers/{name}`
**功能描述**: 管理端更新 MCP Server
**权限要求**: 管理员

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |
| displayName | string | 否 | 显示名称 | "Updated Test Server" |
| icon | string | 否 | 图标 URL | "https://example.com/new-icon.png" |
| description | string | 否 | 描述 | "An updated test MCP server" |
| category | string | 否 | 分类 | "updated-category" |
| team | string | 否 | 团队 | "Updated Team" |
| sourceUrl | string | 否 | 源码地址 | "https://github.com/updated/server" |
| readmeMd | string | 否 | README 文档 | "# Updated Test Server" |
| remoteServerConfig | string | 否 | 远程服务器配置 JSON 字符串 | '{"mcpServers": {"test": {"url": "https://updated-api.example.com"}}}' |
| localServerConfig | string | 否 | 本地服务器配置 JSON 字符串 | '{"mcpServers": {"test": {"command": "python3", "args": ["server.py"]}}}' |
| envSchema | string | 否 | 环境变量模式 JSON 字符串 | '{"properties": {"PORT": {"description": "Server port"}}, "required": ["PORT"], "type": "object"}' |
| parameterSchema | string | 否 | 参数模式 JSON 字符串 | '{"properties": {"token": {"description": "API token"}}, "required": ["token"], "type": "object"}' |
| tags | array | 否 | 标签列表 | ["updated", "test"] |

#### 响应参数

同公共接口中的获取 MCP Server 详情接口

#### 示例请求

```bash
POST /api/admin/mcp-servers/test-server
Content-Type: application/json

{
  "displayName": "Updated Test Server",
  "description": "An updated test MCP server",
  "tags": ["updated", "test"]
}
```

#### 示例响应

同公共接口中的获取 MCP Server 详情接口

### 7.4 管理端删除 MCP Server

**HTTP 方法**: POST
**路径**: `/api/admin/mcp-servers/{name}/delete`
**功能描述**: 管理端删除 MCP Server
**权限要求**: 管理员

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| name | string | 是 | MCP Server 名称 | "test-server" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| ok | boolean | 操作结果 |

#### 示例请求

```bash
POST /api/admin/mcp-servers/test-server/delete
```

#### 示例响应

```json
{
  "ok": true
}
```

### 7.5 管理端预览 MCP Server README

**HTTP 方法**: POST
**路径**: `/api/admin/mcp-servers/readme`
**功能描述**: 管理端从仓库预览 MCP Server README
**权限要求**: 管理员

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| repoUrl | string | 是 | 仓库 URL | "https://github.com/test/server" |
| branch | string | 否 | 分支名称 | "main" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| readme_content | string | README 内容 |
| preview_result | object | 预览结果 |

#### 示例请求

```bash
POST /api/admin/mcp-servers/readme
Content-Type: application/json

{
  "repoUrl": "https://github.com/test/server",
  "branch": "main"
}
```

#### 示例响应

```json
{
  "readme_content": "# Test Server\nThis is a test server.",
  "preview_result": {
    "success": true,
    "message": "Preview successful"
  }
}
```

## 8. 注意事项

1. 所有接口都需要进行身份认证（根据实际部署环境配置）
2. 管理接口需要管理员权限和有效的管理员令牌
3. 请求参数中的日期时间格式为 ISO 8601 格式（例如：2026-04-23T10:00:00Z）
4. 响应中的配置字段（如 traeRemoteConfig）返回的是 JSON 字符串，需要客户端解析
5. 分页接口默认每页返回 12 条记录，最多支持 50 条
6. 创建和更新接口中的配置字段需要提供 JSON 字符串格式的数据