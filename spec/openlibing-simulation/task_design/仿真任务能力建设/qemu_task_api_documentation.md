# QemuTaskController API 接口文档

## 1. 概述

QemuTaskController 提供 Qemu 任务管理相关的 API 接口，包括自动化任务管理、运行脚本管理和分布式锁管理等功能，为仿真服务平台提供虚拟化任务的调度和执行能力。

## 2. 接口列表

| 接口名称 | HTTP 方法 | 路径 | 功能描述 |
|---------|----------|------|---------|
| 创建自动化任务 | POST | /simulation/qemu/auto/task | 创建 Qemu 自动化任务 |
| 查询自动化任务 | GET | /simulation/qemu/auto/task | 根据任务ID查询任务详情 |
| 关闭自动化任务 | PUT | /simulation/qemu/auto/task | 关闭指定自动化任务 |
| 查询仿真环境 | GET | /simulation/qemu/auto/task/env | 查询仿真环境状态 |
| 保存运行脚本 | POST | /simulation/qemu/runScript | 保存运行脚本信息 |
| 删除运行脚本 | DELETE | /simulation/qemu/runScript | 删除指定运行脚本 |
| 修改锁时间 | PUT | /simulation/qemu/uploadLock | 更新分布式锁过期时间 |
| 测试接口 | GET | /simulation/qemu/test | 服务健康检查测试 |

## 3. 接口详情

### 3.1 创建自动化任务

**HTTP 方法**: POST  
**路径**: `/simulation/qemu/auto/task`  
**功能描述**: 创建 Qemu 自动化任务

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| taskName | string | 否 | 任务名称 | "qemu-task-001" |
| taskType | string | 否 | 任务类型 | "SIMULATION" |
| config | object | 否 | 任务配置 | {...} |
| hardwareModel | string | 否 | 硬件型号 | "x86_64" |
| eimulationScene | string | 否 | 仿真场景 | "scene-001" |
| groupName | string | 否 | 分组名称 | "group-001" |
| environmentName | string | 否 | 环境名称 | "env-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 任务信息 |
| data.id | string | 任务ID |
| data.status | string | 任务状态 |
| data.createTime | string | 创建时间 |

#### 示例请求

```bash
POST /simulation/qemu/auto/task
Content-Type: application/json

{
  "taskName": "qemu-task-001",
  "taskType": "SIMULATION",
  "hardwareModel": "x86_64",
  "eimulationScene": "scene-001",
  "groupName": "group-001",
  "environmentName": "env-001"
}
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "task-001",
    "status": "RUNNING",
    "createTime": "2026-05-21 10:00:00"
  }
}
```

### 3.2 查询自动化任务

**HTTP 方法**: GET  
**路径**: `/simulation/qemu/auto/task`  
**功能描述**: 根据任务ID查询任务详情

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| id | string | 是 | 任务ID | "task-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 任务详情 |
| data.id | string | 任务ID |
| data.taskName | string | 任务名称 |
| data.taskType | string | 任务类型 |
| data.status | string | 任务状态 |
| data.config | object | 任务配置 |
| data.hardwareModel | string | 硬件型号 |
| data.eimulationScene | string | 仿真场景 |
| data.logInfo | string | 日志信息 |
| data.createTime | string | 创建时间 |
| data.startTime | string | 开始时间 |
| data.endTime | string | 结束时间 |

#### 示例请求

```bash
GET /simulation/qemu/auto/task?id=task-001
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "task-001",
    "taskName": "qemu-task-001",
    "taskType": "SIMULATION",
    "status": "RUNNING",
    "hardwareModel": "x86_64",
    "eimulationScene": "scene-001",
    "logInfo": "Task is running...",
    "createTime": "2026-05-21 10:00:00",
    "startTime": "2026-05-21 10:01:00",
    "endTime": null
  }
}
```

### 3.3 关闭自动化任务

**HTTP 方法**: PUT  
**路径**: `/simulation/qemu/auto/task`  
**功能描述**: 关闭指定自动化任务

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| id | string | 是 | 任务ID | "task-001" |
| status | string | 是 | 目标状态 | "STOPPED" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 操作结果 |
| data.closed | boolean | 是否成功关闭 |

#### 示例请求

```bash
PUT /simulation/qemu/auto/task
Content-Type: application/json

{
  "id": "task-001",
  "status": "STOPPED"
}
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "closed": true
  }
}
```

### 3.4 查询仿真环境

**HTTP 方法**: GET  
**路径**: `/simulation/qemu/auto/task/env`  
**功能描述**: 查询仿真环境状态

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| taskId | string | 是 | 任务ID | "task-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | array | 环境节点列表 |
| data[].nodeId | string | 节点ID |
| data[].ip | string | 节点IP |
| data[].status | string | 节点状态 |
| data[].cpu | integer | CPU核数 |
| data[].memory | integer | 内存大小(GB) |

#### 示例请求

```bash
GET /simulation/qemu/auto/task/env?taskId=task-001
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "nodeId": "node-001",
      "ip": "192.168.1.101",
      "status": "RUNNING",
      "cpu": 8,
      "memory": 16
    },
    {
      "nodeId": "node-002",
      "ip": "192.168.1.102",
      "status": "RUNNING",
      "cpu": 16,
      "memory": 32
    }
  ]
}
```

### 3.5 保存运行脚本

**HTTP 方法**: POST  
**路径**: `/simulation/qemu/runScript`  
**功能描述**: 保存运行脚本信息

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| id | string | 否 | 脚本ID（自动生成） | "script-001" |
| runNum | string | 否 | 运行编号 | "run-001" |
| checkFileName | string | 否 | 检查文件名 | "check.sh" |
| checkFilePath | string | 否 | 检查文件路径 | "/scripts/check.sh" |
| zipFileName | string | 否 | 压缩文件名 | "script.zip" |
| zipFilePath | string | 否 | 压缩文件路径 | "/scripts/script.zip" |
| fileName | string | 否 | 文件名 | "run.sh" |
| filePath | string | 否 | 文件路径 | "/scripts/run.sh" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 脚本信息 |
| data.id | string | 脚本ID |
| data.createTime | string | 创建时间 |

#### 示例请求

```bash
POST /simulation/qemu/runScript
Content-Type: application/json

{
  "runNum": "run-001",
  "fileName": "run.sh",
  "filePath": "/scripts/run.sh"
}
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "script-001",
    "createTime": "2026-05-21 10:00:00"
  }
}
```

### 3.6 删除运行脚本

**HTTP 方法**: DELETE  
**路径**: `/simulation/qemu/runScript`  
**功能描述**: 删除指定运行脚本

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| id | string | 是 | 脚本ID | "script-001" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 删除结果 |
| data.deleted | boolean | 是否成功删除 |

#### 示例请求

```bash
DELETE /simulation/qemu/runScript?id=script-001
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

### 3.7 修改锁时间

**HTTP 方法**: PUT  
**路径**: `/simulation/qemu/uploadLock`  
**功能描述**: 更新分布式锁过期时间

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
|-------|------|------|------|-------|
| lockName | string | 是 | 锁名称 | "task-lock-001" |
| createdAt | string | 是 | 创建时间 | "2026-05-21 10:00:00" |
| expiredAt | string | 是 | 过期时间 | "2026-05-21 11:00:00" |

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 更新结果 |
| data.updated | boolean | 是否成功更新 |

#### 示例请求

```bash
PUT /simulation/qemu/uploadLock
Content-Type: application/json

{
  "lockName": "task-lock-001",
  "createdAt": "2026-05-21 10:00:00",
  "expiredAt": "2026-05-21 11:00:00"
}
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "updated": true
  }
}
```

### 3.8 测试接口

**HTTP 方法**: GET  
**路径**: `/simulation/qemu/test`  
**功能描述**: 服务健康检查测试

#### 请求参数

无

#### 响应参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| code | integer | 响应码 |
| message | string | 响应消息 |
| data | object | 测试结果 |

#### 示例请求

```bash
GET /simulation/qemu/test
```

#### 示例响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "OK",
    "timestamp": "2026-05-21 10:00:00"
  }
}
```

## 4. 数据模型

### 4.1 QemuTaskEntity

```json
{
  "id": "string",
  "taskName": "string",
  "taskType": "string",
  "status": "string",
  "config": {},
  "runStatusList": [],
  "hardwareModel": "string",
  "eimulationScene": "string",
  "failReason": "string",
  "nodeInfoList": [],
  "logInfo": "string",
  "envCondition": "string",
  "groupName": "string",
  "environmentName": "string",
  "ownerList": [],
  "createTime": "string",
  "startTime": "string",
  "endTime": "string"
}
```

### 4.2 QemuRunScriptEntity

```json
{
  "id": "string",
  "runNum": "string",
  "checkFileName": "string",
  "checkFilePath": "string",
  "zipFileName": "string",
  "zipFilePath": "string",
  "fileName": "string",
  "filePath": "string",
  "createTime": "string"
}
```

### 4.3 LockEntityDto

```json
{
  "lockName": "string",
  "createdAt": "string",
  "expiredAt": "string"
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

### 5.1 创建自动化任务

```bash
curl -X POST "http://localhost:8108/simulation/qemu/auto/task" \
  -H "Content-Type: application/json" \
  -d '{
    "taskName": "qemu-task-001",
    "taskType": "SIMULATION",
    "hardwareModel": "x86_64"
  }'
```

### 5.2 查询自动化任务

```bash
curl -X GET "http://localhost:8108/simulation/qemu/auto/task?id=task-001"
```

### 5.3 关闭自动化任务

```bash
curl -X PUT "http://localhost:8108/simulation/qemu/auto/task" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-001",
    "status": "STOPPED"
  }'
```

### 5.4 查询仿真环境

```bash
curl -X GET "http://localhost:8108/simulation/qemu/auto/task/env?taskId=task-001"
```

### 5.5 保存运行脚本

```bash
curl -X POST "http://localhost:8108/simulation/qemu/runScript" \
  -H "Content-Type: application/json" \
  -d '{
    "runNum": "run-001",
    "fileName": "run.sh",
    "filePath": "/scripts/run.sh"
  }'
```

### 5.6 删除运行脚本

```bash
curl -X DELETE "http://localhost:8108/simulation/qemu/runScript?id=script-001"
```

### 5.7 修改锁时间

```bash
curl -X PUT "http://localhost:8108/simulation/qemu/uploadLock" \
  -H "Content-Type: application/json" \
  -d '{
    "lockName": "task-lock-001",
    "createdAt": "2026-05-21 10:00:00",
    "expiredAt": "2026-05-21 11:00:00"
  }'
```

### 5.8 测试接口

```bash
curl -X GET "http://localhost:8108/simulation/qemu/test"
```

## 6. 错误处理

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| 400 | 请求参数错误 | 检查请求参数是否符合要求，必填字段是否完整 |
| 404 | 任务/脚本不存在 | 检查传入的ID是否正确 |
| 409 | 任务状态不允许操作 | 检查任务当前状态是否允许执行该操作 |
| 500 | 服务器内部错误 | 联系系统管理员 |

## 7. 注意事项

1. 所有接口都支持跨域访问（Cross-Origin）
2. 请求参数中的日期时间格式为 `yyyy-MM-dd HH:mm:ss`
3. 响应格式统一为 JSON，包含 code、message、data 三个字段
4. 创建任务时，任务ID由系统自动生成
5. 分布式锁用于保证任务执行的并发安全性