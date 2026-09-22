# QemuTaskController 设计文档

## 1. 模块概述

QemuTaskController 是 openlibing-simulation 项目中负责 Qemu 任务管理的核心控制器模块。该模块提供 Qemu 自动化任务管理、运行脚本管理和分布式锁管理等功能，为仿真服务平台提供虚拟化任务的调度和执行能力。

## 2. 设计目标

- 提供 Qemu 自动化任务的完整生命周期管理
- 支持运行脚本的保存和删除
- 支持分布式锁机制，保证并发安全
- 提供仿真环境状态查询能力
- 提供统一的 RESTful API 接口

## 3. 架构设计

### 3.1 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                    Controller 层                                │
│               QemuTaskController                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service 层                                  │
│               QemuTaskService                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Mapper 层                                   │
│               QemuTaskMapper                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    数据库层                                     │
│   t_qemu_task / t_qemu_run_script / distributed_lock           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心类设计

#### 3.2.1 QemuTaskController

| 方法名 | 功能描述 | 参数 | 返回值 |
|-------|---------|------|-------|
| saveAutoQemuTask | 创建自动化任务 | QemuTaskEntity | ResponseEntity |
| getAutoQemuTask | 查询自动化任务 | id | ResponseEntity |
| closeAutoQemuTask | 关闭自动化任务 | Map<String, String> | ResponseEntity |
| getEnvironmentViewAuto | 查询仿真环境 | taskId | ResponseEntity |
| saveRunScript | 保存运行脚本 | QemuRunScriptEntity | ResponseEntity |
| deleteRunScript | 删除运行脚本 | id | ResponseEntity |
| uploadLock | 修改锁时间 | LockEntityDto | ResponseEntity |
| test | 测试接口 | 无 | ResponseEntity |

#### 3.2.2 依赖服务

| 服务名 | 接口 | 用途 |
|-------|------|------|
| QemuTaskService | QemuTaskService | Qemu任务核心业务逻辑 |

## 4. 数据模型设计

### 4.1 QemuTaskEntity

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| config | QemuTaskConfigEntity | 任务配置 | 可选 |
| runStatusList | List | 运行状态列表 | 默认空列表 |
| hardwareModel | String | 硬件型号 | 可选 |
| eimulationScene | String | 仿真场景 | 可选 |
| failReason | String | 失败原因 | 可选 |
| nodeInfoList | List | 节点信息列表 | 可选 |
| logInfo | String | 日志信息 | 可选 |
| envCondition | String | 环境条件 | 可选 |
| groupName | String | 分组名称 | 可选 |
| environmentName | String | 环境名称 | 可选 |
| ownerList | List\<String\> | 所有者列表 | 可选 |

### 4.2 QemuRunScriptEntity

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| id | String | 主键ID | 自动生成 |
| runNum | String | 运行编号 | 可选 |
| checkFileName | String | 检查文件名 | 可选 |
| checkFilePath | String | 检查文件路径 | 可选 |
| zipFileName | String | 压缩文件名 | 可选 |
| zipFilePath | String | 压缩文件路径 | 可选 |
| fileName | String | 文件名 | 可选 |
| filePath | String | 文件路径 | 可选 |
| createTime | Timestamp | 创建时间 | 自动生成 |

### 4.3 LockEntityDto

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| lockName | String | 锁名称 | 必填 |
| createdAt | String | 创建时间 | 必填 |
| expiredAt | String | 过期时间 | 必填 |

### 4.4 ResponseEntity

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| code | Integer | 响应码 | 必填 |
| message | String | 响应消息 | 必填 |
| data | Object | 响应数据 | 可选 |

## 5. API 接口设计

### 5.1 接口总览

| API路径 | HTTP方法 | 功能描述 |
|--------|---------|---------|
| /simulation/qemu/auto/task | POST | 创建自动化任务 |
| /simulation/qemu/auto/task | GET | 查询自动化任务 |
| /simulation/qemu/auto/task | PUT | 关闭自动化任务 |
| /simulation/qemu/auto/task/env | GET | 查询仿真环境 |
| /simulation/qemu/runScript | POST | 保存运行脚本 |
| /simulation/qemu/runScript | DELETE | 删除运行脚本 |
| /simulation/qemu/uploadLock | PUT | 修改锁时间 |
| /simulation/qemu/test | GET | 测试接口 |

### 5.2 接口详细设计

#### 5.2.1 创建自动化任务

- **路径**: `POST /simulation/qemu/auto/task`
- **功能**: 创建 Qemu 自动化任务
- **请求体**: QemuTaskEntity
- **成功响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "id": "string",
      "status": "string",
      "createTime": "string"
    }
  }
  ```

#### 5.2.2 查询自动化任务

- **路径**: `GET /simulation/qemu/auto/task`
- **功能**: 查询自动化任务详情
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | id | String | 是 |

#### 5.2.3 关闭自动化任务

- **路径**: `PUT /simulation/qemu/auto/task`
- **功能**: 关闭自动化任务
- **请求体**:
  ```json
  {
    "id": "string",
    "status": "string"
  }
  ```

#### 5.2.4 查询仿真环境

- **路径**: `GET /simulation/qemu/auto/task/env`
- **功能**: 查询仿真环境状态
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | taskId | String | 是 |

#### 5.2.5 保存运行脚本

- **路径**: `POST /simulation/qemu/runScript`
- **功能**: 保存运行脚本信息
- **请求体**: QemuRunScriptEntity

#### 5.2.6 删除运行脚本

- **路径**: `DELETE /simulation/qemu/runScript`
- **功能**: 删除运行脚本
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | id | String | 是 |

#### 5.2.7 修改锁时间

- **路径**: `PUT /simulation/qemu/uploadLock`
- **功能**: 更新分布式锁的过期时间
- **请求体**:
  ```json
  {
    "lockName": "string (必填)",
    "createdAt": "string (必填)",
    "expiredAt": "string (必填)"
  }
  ```

#### 5.2.8 测试接口

- **路径**: `GET /simulation/qemu/test`
- **功能**: 服务健康检查测试

## 6. 业务流程设计

### 6.1 Qemu 任务创建流程

```
用户请求 → 参数校验 → 任务配置解析 → 资源检查 → 任务保存 → 返回结果
    │              │              │          │          │
    ▼              ▼              ▼          ▼          ▼
  Controller   DTO校验        Service    资源检查   DB持久化
                                           │
                                           ▼
                                    分布式锁获取
```

### 6.2 任务关闭流程

```
用户请求 → 参数校验 → 任务状态检查 → 任务停止 → 资源释放 → 返回结果
    │              │              │          │          │
    ▼              ▼              ▼          ▼          ▼
  Controller   DTO校验        Service    任务停止   DB更新
                                           │
                                           ▼
                                    分布式锁释放
```

## 7. 数据库表设计

### 7.1 t_qemu_task

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | VARCHAR(64) | PRIMARY KEY | 主键ID |
| task_name | VARCHAR(128) | NULL | 任务名称 |
| task_type | VARCHAR(32) | NULL | 任务类型 |
| status | VARCHAR(32) | NOT NULL | 任务状态 |
| config_json | TEXT | NULL | 配置JSON |
| log_path | VARCHAR(255) | NULL | 日志路径 |
| creator | VARCHAR(64) | NULL | 创建人 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| start_time | DATETIME | NULL | 开始时间 |
| end_time | DATETIME | NULL | 结束时间 |

### 7.2 t_qemu_run_script

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | VARCHAR(64) | PRIMARY KEY | 主键ID |
| run_num | VARCHAR(64) | NULL | 运行编号 |
| check_file_name | VARCHAR(128) | NULL | 检查文件名 |
| check_file_path | VARCHAR(255) | NULL | 检查文件路径 |
| zip_file_name | VARCHAR(128) | NULL | 压缩文件名 |
| zip_file_path | VARCHAR(255) | NULL | 压缩文件路径 |
| file_name | VARCHAR(128) | NULL | 文件名 |
| file_path | VARCHAR(255) | NULL | 文件路径 |
| create_time | DATETIME | NOT NULL | 创建时间 |

### 7.3 distributed_lock

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| lock_name | VARCHAR(128) | PRIMARY KEY | 锁名称 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| expired_at | DATETIME | NOT NULL | 过期时间 |

## 8. 错误处理设计

| 错误码 | 错误信息 | 触发场景 |
|-------|---------|---------|
| 400 | 参数校验失败 | 请求参数缺失或格式错误 |
| 404 | 任务/脚本不存在 | 传入的ID不存在于数据库 |
| 409 | 任务状态不允许操作 | 任务状态不允许当前操作 |
| 500 | 服务器内部错误 | 数据库操作失败或业务逻辑异常 |

## 9. 安全设计

- **跨域支持**: 使用 `@CrossOrigin` 注解允许跨域访问
- **日志记录**: 使用 `@Slf4j` 记录操作日志
- **分布式锁**: 使用数据库锁保证并发安全

## 10. 性能考虑

- **异步处理**: 任务执行操作考虑异步处理，避免阻塞
- **分页查询**: 环境查询支持分页，避免大量数据一次性返回
- **索引优化**: 在常用查询字段上建立索引