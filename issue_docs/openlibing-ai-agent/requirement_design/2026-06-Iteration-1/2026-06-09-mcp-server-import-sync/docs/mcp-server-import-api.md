# MCP Server 导入 & 同步 — 接口变更文档

## 一、新增接口

### 1. 预览 MCP Server 导入

| 项目 | 值 |
|------|-----|
| **Method** | `POST` |
| **Path** | `/api/admin/import-mcp-servers/preview` |
| **说明** | 克隆远程仓库，扫描指定目录下的 MCP Server 配置，返回可导入的服务器列表及冲突信息 |

#### 请求体 (`MCPServerPreviewRequest`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `repoUrl` | string | ✅ | — | 仓库地址，如 `https://gitcode.com/openeuler/mcp-servers` |
| `branch` | string | ❌ | `"main"` | 分支名 |
| `rootDir` | string | ✅ | — | 扫描根目录，如 `servers` |
| `isSingleServer` | boolean | ❌ | `false` | 是否为单服务器仓库。`true` 时直接解析根目录为单个 MCP Server；`false` 时遍历 rootDir 下的子目录 |

#### 请求示例

```json
{
  "repoUrl": "https://gitcode.com/openeuler/mcp-servers",
  "branch": "main",
  "rootDir": "servers",
  "isSingleServer": false
}
```

#### 响应体 (`MCPServerPreviewResponse`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `mcpServers` | `MCPServerPreviewItem[]` | 扫描到的 MCP Server 列表 |
| `conflicts` | `string[]` | 已存在的同名服务器 name 列表 |
| `parseErrors` | `ParseError[]` | 解析失败的文件及错误信息 |
| `repoInfo` | `RepoInfo` | 仓库元信息 |

#### `MCPServerPreviewItem`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 服务器唯一标识（目录名） |
| `displayName` | string \| null | 显示名称（来自 mcp-rpm.yaml） |
| `description` | string | 描述（来自 mcp-rpm.yaml） |
| `configType` | string | 配置类型：`"local"` / `"remote"` / `"none"` |
| `sourceUrl` | string | 源目录 URL（tree 链接） |
| `relativePath` | string | 相对于 rootDir 的路径 |

#### `RepoInfo`

| 字段 | 类型 | 说明 |
|------|------|------|
| `platform` | string | `"github"` / `"gitcode"` |
| `owner` | string | 仓库所有者 |
| `repo` | string | 仓库名 |
| `branch` | string | 分支名 |

#### `ParseError`

| 字段 | 类型 | 说明 |
|------|------|------|
| `filePath` | string | 解析失败的文件路径 |
| `error` | string | 错误信息 |

#### 响应示例

```json
{
  "mcpServers": [
    {
      "name": "lto_dump_mcp",
      "displayName": "LTO Dump MCP",
      "description": "分析 ELF 二进制文件的 LTO 信息",
      "configType": "local",
      "sourceUrl": "https://gitcode.com/openeuler/mcp-servers/tree/main/servers/lto_dump_mcp",
      "relativePath": "lto_dump_mcp"
    }
  ],
  "conflicts": [],
  "parseErrors": [],
  "repoInfo": {
    "platform": "gitcode",
    "owner": "openeuler",
    "repo": "mcp-servers",
    "branch": "main"
  }
}
```

#### 错误响应

| 状态码 | 说明 |
|--------|------|
| `400` | 仓库地址无效或参数错误 |
| `500` | 克隆/解析失败 |

---

### 2. 确认导入 MCP Server

| 项目 | 值 |
|------|-----|
| **Method** | `POST` |
| **Path** | `/api/admin/import-mcp-servers` |
| **说明** | 将预览选中的 MCP Server 写入数据库 |

#### 请求体 (`MCPServerImportRequest`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `repoUrl` | string | ✅ | — | 仓库地址（与预览一致） |
| `branch` | string | ❌ | `"main"` | 分支名 |
| `rootDir` | string | ✅ | — | 扫描根目录（与预览一致） |
| `isSingleServer` | boolean | ❌ | `false` | 是否为单服务器仓库（与预览一致） |
| `mcpServers` | `string[]` | ❌ | `[]` | 要导入的服务器 name 列表 |
| `category` | string | ❌ | `"其他"` | 分类标签 |
| `team` | string | ❌ | `"未知团队"` | 团队标签 |

#### 请求示例

```json
{
  "repoUrl": "https://gitcode.com/openeuler/mcp-servers",
  "branch": "main",
  "rootDir": "servers",
  "isSingleServer": false,
  "mcpServers": ["lto_dump_mcp", "kernel_mcp"],
  "category": "系统工具",
  "team": "openEuler"
}
```

#### 响应体 (`ImportResponse`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `imported` | `string[]` | 成功导入的服务器 name 列表 |
| `failed` | `ImportFailure[]` | 导入失败列表 |
| `count` | int | 成功导入数量 |

#### `ImportFailure`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 服务器 name |
| `error` | string | 失败原因 |

#### 响应示例

```json
{
  "imported": ["lto_dump_mcp", "kernel_mcp"],
  "failed": [],
  "count": 2
}
```

#### 错误响应

| 状态码 | 说明 |
|--------|------|
| `400` | 参数无效或仓库地址错误 |
| `500` | 导入过程异常 |

---

## 二、前端联调要点

1. **接口前缀**：两个接口均挂载在 `/api/admin/import-mcp-servers` 下，与已有的 Skill 导入接口 `/api/admin/import` 平行，互不影响。

2. **字段命名**：请求/响应均使用 **camelCase**（通过 Pydantic `alias`），JSON 传输时使用别名（如 `repoUrl` 而非 `repo_url`）。

3. **预览→确认 两步流程**：
   - 第一步调用 `/preview`，展示 `mcpServers` 列表和 `conflicts` 冲突
   - 用户勾选后，将选中的 name 列表传入第二步 `mcpServers` 字段
   - `repoUrl` / `branch` / `rootDir` / `isSingleServer` 须与预览时一致

4. **isSingleServer 参数**：
    - `false`（默认）：仓库包含多个 MCP Server，后端遍历 `rootDir` 下的子目录
    - `true`：整个仓库（或 `rootDir` 指定目录）就是一个 MCP Server，后端直接解析该目录
    - 前端可根据用户选择（"单服务器仓库" / "多服务器仓库"）传入此参数

5. **configType 含义**：
   - `"local"` — 有 `mcp_config.json` 且包含本地启动配置（command/args）
   - `"remote"` — 有 `mcp_config.json` 且包含远程配置（url）
   - `"none"` — 未找到配置文件

6. **conflicts 字段**：返回数据库中已存在的同名服务器 name，前端可据此提示用户"将覆盖已有服务器"。

7. **定时同步为后端行为**：MCP Server 定时同步（默认每天 18:30）由后端调度器自动执行，无需前端调用。
