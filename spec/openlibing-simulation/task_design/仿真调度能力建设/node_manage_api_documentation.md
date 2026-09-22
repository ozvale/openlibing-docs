# NodeManageController API 接口文档

## 1. 概述

NodeManageController 提供节点管理相关的 API 接口，包括资源调度任务管理、服务器节点管理和仿真场景配置管理等功能，为仿真服务平台提供节点资源的调度和管理能力。

## 2. 接口列表

| 接口名称 | HTTP 方法 | 路径 | 功能描述 |
|---------|----------|------|---------|
| 创建资源调度任务 | POST | /simulation/v2/node/manage/task | 创建资源调度任务，分配服务器节点 |
| 查询调度任务详情 | GET | /simulation/v2/node/manage/task | 根据任务ID和场景ID查询调度任务详情 |
| 查询任务节点信息 | GET | /simulation/v2/node/manage/task/node | 查询指定任务的节点列表 |
| 释放调度任务 | DELETE | /simulation/v2/node/manage/task | 释放资源调度任务，归还服务器节点 |
| 添加机器 | POST | /simulation/v2/node/manage/node | 批量添加服务器节点 |
| 添加场景配置 | POST | /simulation/v2/node/manage/scene | 创建仿真场景配置 |
| 获取场景配置 | GET | /simulation/v2/node/manage/scene | 根据场景ID获取场景配置详情 |
| 删除场景配置 | DELETE | /simulation/v2/node/manage/scene | 删除指定场景配置 |

## 3. 接口详情

### 3.1 创建资源调度任务

**HTTP 方法**: POST  
**路径**: `/simulation/v2/node/manage/task`  
**功能描述**: 创建资源调度任务，分配服务器节点用于仿真任务

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| simulationTaskId | string | 是 | 仿真任务ID | "task-001" |
| productId | string | 否 | 产品ID | "product-001" |
| simulationSceneId | string | 否 | 仿真场景ID | "scene-001" |
| createBy | string | 否 | 创建人 | "admin" |
| pageNo | integer | 否 | 页码 | 1 |
| pageSize | integer | 否 | 每页数量 | 10 |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 任务信息 |
| data.taskId | string | 任务ID |
| data.sceneId | string | 场景ID |
| data.status | string | 任务状态 |
| data.allocatedNodes | array | 已分配节点列表 |

#### 示例请求

```bash
POST /simulation/v2/node/manage/task
Content-Type: application/json

{
  "simulationTaskId": "task-001",
  "productId": "product-001",
  "simulationSceneId": "scene-001",
  "createBy": "admin"
}
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "taskId": "task-001",
    "sceneId": "scene-001",
    "status": "RUNNING",
    "allocatedNodes": [
      {
        "id": "node-001",
        "ip": "192.168.1.101",
        "port": 22,
        "status": "ALLOCATED"
      }
    ]
  }
}
```

### 3.2 查询调度任务详情

**HTTP 方法**: GET  
**路径**: `/simulation/v2/node/manage/task`  
**功能描述**: 根据任务ID和场景ID查询调度任务详情

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| simulationTaskId | string | 是 | 仿真任务ID | "task-001" |
| simulationSceneId | string | 是 | 仿真场景ID | "scene-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 任务详情 |
| data.simulationTaskId | string | 仿真任务ID |
| data.simulationSceneId | string | 仿真场景ID |
| data.taskType | string | 任务类型 |
| data.status | string | 任务状态 |
| data.taskParam | string | 任务参数(JSON) |
| data.executor | string | 执行者 |
| data.createTime | string | 创建时间 |
| data.startTime | string | 开始时间 |
| data.endTime | string | 结束时间 |

#### 示例请求

```bash
GET /simulation/v2/node/manage/task?simulationTaskId=task-001&simulationSceneId=scene-001
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "simulationTaskId": "task-001",
    "simulationSceneId": "scene-001",
    "taskType": "SIMULATION",
    "status": "RUNNING",
    "taskParam": "{\"cpu\": 4, \"memory\": 8192}",
    "executor": "system",
    "createTime": "2026-05-21 10:00:00",
    "startTime": "2026-05-21 10:01:00",
    "endTime": null
  }
}
```

### 3.3 查询任务节点信息

**HTTP 方法**: GET  
**路径**: `/simulation/v2/node/manage/task/node`  
**功能描述**: 查询指定任务的节点列表

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| simulationTaskId | string | 是 | 仿真任务ID | "task-001" |
| simulationSceneId | string | 否 | 仿真场景ID | "scene-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | array | 节点列表 |
| data[].id | string | 节点ID |
| data[].ip | string | 节点IP地址 |
| data[].port | integer | SSH端口 |
| data[].user | string | 用户名 |
| data[].architecture | string | 架构类型 |
| data[].cpu | integer | CPU核数 |
| data[].memory | integer | 内存大小(GB) |
| data[].status | string | 节点状态 |

#### 示例请求

```bash
GET /simulation/v2/node/manage/task/node?simulationTaskId=task-001
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "node-001",
      "ip": "192.168.1.101",
      "port": 22,
      "user": "root",
      "architecture": "x86_64",
      "cpu": 8,
      "memory": 16,
      "status": "ALLOCATED"
    },
    {
      "id": "node-002",
      "ip": "192.168.1.102",
      "port": 22,
      "user": "root",
      "architecture": "x86_64",
      "cpu": 16,
      "memory": 32,
      "status": "ALLOCATED"
    }
  ]
}
```

### 3.4 释放调度任务

**HTTP 方法**: DELETE  
**路径**: `/simulation/v2/node/manage/task`  
**功能描述**: 释放资源调度任务，归还服务器节点

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| simulationTaskId | string | 是 | 仿真任务ID | "task-001" |
| simulationSceneId | string | 否 | 仿真场景ID | "scene-001" |
| executor | string | 是 | 执行者 | "admin" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 释放结果 |
| data.released | boolean | 是否成功释放 |
| data.releasedNodes | array | 已释放节点列表 |

#### 示例请求

```bash
DELETE /simulation/v2/node/manage/task?simulationTaskId=task-001&executor=admin
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "released": true,
    "releasedNodes": ["node-001", "node-002"]
  }
}
```

### 3.5 添加机器

**HTTP 方法**: POST  
**路径**: `/simulation/v2/node/manage/node`  
**功能描述**: 批量添加服务器节点

#### 请求参数

请求体为服务器节点数组：

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| id | string | 否 | 节点ID（自动生成） | "node-001" |
| groupId | string | 否 | 分组ID | "group-001" |
| ip | string | 是 | 服务器IP地址 | "192.168.1.101" |
| port | integer | 否 | SSH端口，默认22 | 22 |
| user | string | 是 | 用户名 | "root" |
| password | string | 是 | 密码 | "password" |
| labId | string | 否 | 实验室ID | "lab-001" |
| labName | string | 否 | 实验室名称 | "Test Lab" |
| architecture | string | 否 | 架构类型 | "x86_64" |
| creator | string | 否 | 创建人 | "admin" |
| cpu | integer | 否 | CPU核数 | 8 |
| memory | integer | 否 | 内存大小(GB) | 16 |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 添加结果 |
| data.addedCount | integer | 成功添加数量 |
| data.addedNodes | array | 已添加节点ID列表 |

#### 示例请求

```bash
POST /simulation/v2/node/manage/node
Content-Type: application/json

[
  {
    "ip": "192.168.1.101",
    "port": 22,
    "user": "root",
    "password": "password",
    "architecture": "x86_64",
    "cpu": 8,
    "memory": 16,
    "creator": "admin"
  },
  {
    "ip": "192.168.1.102",
    "port": 22,
    "user": "root",
    "password": "password",
    "architecture": "x86_64",
    "cpu": 16,
    "memory": 32,
    "creator": "admin"
  }
]
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "addedCount": 2,
    "addedNodes": ["node-001", "node-002"]
  }
}
```

### 3.6 添加场景配置

**HTTP 方法**: POST  
**路径**: `/simulation/v2/node/manage/scene`  
**功能描述**: 创建仿真场景配置

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| id | string | 否 | 场景ID（自动生成） | "scene-001" |
| name | string | 是 | 场景名称 | "Test Scene" |
| description | string | 否 | 场景描述 | "用于测试的仿真场景" |
| serverTags | string | 否 | 服务器标签 | "cpu-high,mem-high" |
| deployTags | string | 否 | 部署标签 | "production" |
| creator | string | 否 | 创建人 | "admin" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 场景信息 |
| data.id | string | 场景ID |
| data.name | string | 场景名称 |
| data.description | string | 场景描述 |
| data.createTime | string | 创建时间 |

#### 示例请求

```bash
POST /simulation/v2/node/manage/scene
Content-Type: application/json

{
  "name": "Test Scene",
  "description": "用于测试的仿真场景",
  "serverTags": "cpu-high,mem-high",
  "deployTags": "production",
  "creator": "admin"
}
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "scene-001",
    "name": "Test Scene",
    "description": "用于测试的仿真场景",
    "serverTags": "cpu-high,mem-high",
    "deployTags": "production",
    "creator": "admin",
    "createTime": "2026-05-21 10:00:00"
  }
}
```

### 3.7 获取场景配置

**HTTP 方法**: GET  
**路径**: `/simulation/v2/node/manage/scene`  
**功能描述**: 根据场景ID获取场景配置详情

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| sceneId | string | 是 | 场景ID | "scene-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 场景详情 |
| data.id | string | 场景ID |
| data.name | string | 场景名称 |
| data.description | string | 场景描述 |
| data.serverTags | string | 服务器标签 |
| data.deployTags | string | 部署标签 |
| data.creator | string | 创建人 |
| data.createTime | string | 创建时间 |
| data.lastModifyTime | string | 最后修改时间 |

#### 示例请求

```bash
GET /simulation/v2/node/manage/scene?sceneId=scene-001
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "scene-001",
    "name": "Test Scene",
    "description": "用于测试的仿真场景",
    "serverTags": "cpu-high,mem-high",
    "deployTags": "production",
    "creator": "admin",
    "createTime": "2026-05-21 10:00:00",
    "lastModifyTime": "2026-05-21 10:00:00"
  }
}
```

### 3.8 删除场景配置

**HTTP 方法**: DELETE  
**路径**: `/simulation/v2/node/manage/scene`  
**功能描述**: 删除指定场景配置

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| sceneId | string | 是 | 场景ID | "scene-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 删除结果 |
| data.deleted | boolean | 是否成功删除 |

#### 示例请求

```bash
DELETE /simulation/v2/node/manage/scene?sceneId=scene-001
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted": true
  }
}
```

## 4. 数据模型

### 4.1 NodeManageParamEntity

```json
{
  "simulationTaskId": "string",
  "productId": "string",
  "simulationSceneId": "string",
  "createBy": "string",
  "pageNo": 0,
  "pageSize": 0
}
```

### 4.2 ServerBasicInfoEntity

```json
{
  "id": "string",
  "groupId": "string",
  "ip": "string",
  "port": 0,
  "user": "string",
  "password": "string",
  "labId": "string",
  "labName": "string",
  "labRegion": "string",
  "bmcIp": "string",
  "bmcPort": 0,
  "bmcUser": "string",
  "bmcPassword": "string",
  "architecture": "string",
  "creator": "string",
  "tag": "string",
  "cpu": 0,
  "memory": 0,
  "createTime": "string",
  "lastModifyTime": "string",
  "usingCount": "string",
  "overcommitRatio": 0.0,
  "overcommitCpu": 0,
  "overcommitMemory": 0,
  "disk": "string",
  "usableDisk": "string",
  "hidevlabTaskId": "string",
  "computingLabServerId": "string",
  "jumperServer": "string",
  "serverExtendInfos": []
}
```

### 4.3 SimulationSceneEntity

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "serverTags": "string",
  "deployTags": "string",
  "creator": "string",
  "createTime": "string",
  "lastModifyTime": "string"
}
```

### 4.4 ResponseEntity

```json
{
  "code": 0,
  "message": "string",
  "data": {}
}
```

## 5. 完整调用示例

### 5.1 创建资源调度任务

```bash
curl -X POST "http://localhost:8108/simulation/v2/node/manage/task" \
  -H "Content-Type: application/json" \
  -d '{
    "simulationTaskId": "task-001",
    "productId": "product-001",
    "simulationSceneId": "scene-001",
    "createBy": "admin"
  }'
```

### 5.2 查询调度任务详情

```bash
curl -X GET "http://localhost:8108/simulation/v2/node/manage/task?simulationTaskId=task-001&simulationSceneId=scene-001"
```

### 5.3 查询任务节点信息

```bash
curl -X GET "http://localhost:8108/simulation/v2/node/manage/task/node?simulationTaskId=task-001"
```

### 5.4 释放调度任务

```bash
curl -X DELETE "http://localhost:8108/simulation/v2/node/manage/task?simulationTaskId=task-001&executor=admin"
```

### 5.5 添加机器

```bash
curl -X POST "http://localhost:8108/simulation/v2/node/manage/node" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "ip": "192.168.1.101",
      "port": 22,
      "user": "root",
      "password": "password",
      "architecture": "x86_64",
      "cpu": 8,
      "memory": 16,
      "creator": "admin"
    }
  ]'
```

### 5.6 添加场景配置

```bash
curl -X POST "http://localhost:8108/simulation/v2/node/manage/scene" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Scene",
    "description": "用于测试的仿真场景",
    "serverTags": "cpu-high,mem-high",
    "creator": "admin"
  }'
```

### 5.7 获取场景配置

```bash
curl -X GET "http://localhost:8108/simulation/v2/node/manage/scene?sceneId=scene-001"
```

### 5.8 删除场景配置

```bash
curl -X DELETE "http://localhost:8108/simulation/v2/node/manage/scene?sceneId=scene-001"
```

## 6. 错误处理

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| 400 | 请求参数错误 | 检查请求参数是否符合要求，必填字段是否完整 |
| 404 | 任务/场景/节点不存在 | 检查传入的ID是否正确 |
| 409 | 资源冲突（如节点已被占用） | 检查资源状态，选择其他可用资源 |
| 500 | 服务器内部错误 | 联系系统管理员 |

## 7. 注意事项

1. 所有接口都支持跨域访问（Cross-Origin）
2. 请求参数中的日期时间格式为 `yyyy-MM-dd HH:mm:ss`
3. 响应格式统一为 JSON，包含 code、message、data 三个字段
4. 添加机器接口支持批量添加，单次最多建议不超过100台
5. 释放任务时需要提供执行者信息用于审计
6. 场景配置中的标签字段使用逗号分隔多个标签