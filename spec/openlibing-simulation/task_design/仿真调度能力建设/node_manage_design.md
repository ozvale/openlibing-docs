# NodeManageController 设计文档

## 1. 模块概述

NodeManageController 是 openlibing-simulation 项目中的核心控制器模块，负责节点资源的调度和管理。该模块提供资源调度任务管理、服务器节点管理和仿真场景配置管理三大核心功能，为仿真服务平台提供稳定可靠的节点资源调度能力。

## 2. 设计目标

- 提供完整的节点资源生命周期管理
- 支持资源调度任务的创建、查询和释放
- 支持服务器节点的批量注册和管理
- 支持仿真场景的配置和管理
- 保证并发场景下的数据一致性
- 提供统一的 RESTful API 接口

## 3. 架构设计

### 3.1 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                    Controller 层                                │
│               NodeManageController                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service 层                                  │
│               NodeManageService                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Mapper 层                                   │
│               NodeManageMapper                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    数据库层                                     │
│   t_server_basic_info / t_server_task / t_simulation_scene     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心类设计

#### 3.2.1 NodeManageController

| 方法名 | 功能描述 | 参数 | 返回值 |
|-------|---------|------|-------|
| saveNodeManageTask | 创建资源调度任务 | NodeManageParamEntity | ResponseEntity |
| getNodeManageTask | 查询调度任务详情 | simulationTaskId, simulationSceneId | ResponseEntity |
| getNodeList | 查询任务节点信息 | simulationTaskId, simulationSceneId | ResponseEntity |
| releaseNodeManageTask | 释放调度任务 | simulationTaskId, executor, simulationSceneId | ResponseEntity |
| saveNodes | 添加机器 | List\<ServerBasicInfoEntity\> | ResponseEntity |
| saveScene | 添加场景配置 | SimulationSceneEntity | ResponseEntity |
| getScene | 获取场景配置 | sceneId | ResponseEntity |
| deleteScene | 删除场景配置 | sceneId | ResponseEntity |

#### 3.2.2 依赖服务

| 服务名 | 接口 | 用途 |
|-------|------|------|
| NodeManageService | NodeManageService | 节点管理核心业务逻辑 |

## 4. 数据模型设计

### 4.1 NodeManageParamEntity

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| simulationTaskId | String | 仿真任务ID | 必填 |
| productId | String | 产品ID | 可选 |
| simulationSceneId | String | 仿真场景ID | 可选 |
| createBy | String | 创建人 | 可选 |
| pageNo | int | 页码 | 默认1 |
| pageSize | int | 每页数量 | 默认10 |

### 4.2 ServerBasicInfoEntity

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| id | String | 主键ID | 自动生成 |
| groupId | String | 分组ID | 可选 |
| ip | String | 服务器IP | 必填 |
| port | Integer | SSH端口 | 默认22 |
| user | String | 用户名 | 必填 |
| password | String | 密码 | 必填 |
| labId | String | 实验室ID | 可选 |
| labName | String | 实验室名称 | 可选 |
| labRegion | String | 实验室区域 | 可选 |
| bmcIp | String | BMC IP | 可选 |
| bmcPort | Integer | BMC端口 | 可选 |
| bmcUser | String | BMC用户名 | 可选 |
| bmcPassword | String | BMC密码 | 可选 |
| architecture | String | 架构类型 | 可选 |
| creator | String | 创建人 | 可选 |
| tag | String | 标签 | 可选 |
| cpu | Integer | CPU核数 | 可选 |
| memory | Integer | 内存大小(GB) | 可选 |
| createTime | Timestamp | 创建时间 | 自动生成 |
| lastModifyTime | Timestamp | 最后修改时间 | 自动更新 |
| usingCount | String | 使用次数 | 可选 |
| overcommitRatio | double | 超售比例 | 默认1.0 |
| overcommitCpu | Integer | 超售CPU | 可选 |
| overcommitMemory | Integer | 超售内存 | 可选 |
| disk | String | 磁盘大小 | 可选 |
| usableDisk | String | 可用磁盘 | 可选 |
| hidevlabTaskId | String | 关联任务ID | 可选 |
| computingLabServerId | String | 计算实验室服务器ID | 可选 |
| jumperServer | String | 跳板机 | 可选 |

### 4.3 SimulationSceneEntity

| 字段名 | 类型 | 含义 | 约束 |
|-------|------|------|------|
| id | String | 主键ID | 自动生成 |
| name | String | 场景名称 | 必填 |
| description | String | 场景描述 | 可选 |
| serverTags | String | 服务器标签 | 可选 |
| deployTags | String | 部署标签 | 可选 |
| creator | String | 创建人 | 可选 |
| createTime | String | 创建时间 | 自动生成 |
| lastModifyTime | String | 最后修改时间 | 自动更新 |

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
| /simulation/v2/node/manage/task | POST | 创建资源调度任务 |
| /simulation/v2/node/manage/task | GET | 查询调度任务详情 |
| /simulation/v2/node/manage/task | DELETE | 释放调度任务 |
| /simulation/v2/node/manage/task/node | GET | 查询任务节点信息 |
| /simulation/v2/node/manage/node | POST | 添加机器 |
| /simulation/v2/node/manage/scene | POST | 添加场景配置 |
| /simulation/v2/node/manage/scene | GET | 获取场景配置 |
| /simulation/v2/node/manage/scene | DELETE | 删除场景配置 |

### 5.2 接口详细设计

#### 5.2.1 创建资源调度任务

- **路径**: `POST /simulation/v2/node/manage/task`
- **功能**: 创建资源调度任务，分配服务器节点
- **请求体**:
  ```json
  {
    "simulationTaskId": "string (必填)",
    "productId": "string (可选)",
    "simulationSceneId": "string (可选)",
    "createBy": "string (可选)"
  }
  ```
- **成功响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "taskId": "string",
      "sceneId": "string",
      "status": "string",
      "allocatedNodes": []
    }
  }
  ```

#### 5.2.2 查询调度任务详情

- **路径**: `GET /simulation/v2/node/manage/task`
- **功能**: 查询调度任务详情
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | simulationTaskId | String | 是 |
  | simulationSceneId | String | 是 |

#### 5.2.3 查询任务节点信息

- **路径**: `GET /simulation/v2/node/manage/task/node`
- **功能**: 查询任务节点列表
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | simulationTaskId | String | 是 |
  | simulationSceneId | String | 否 |

#### 5.2.4 释放调度任务

- **路径**: `DELETE /simulation/v2/node/manage/task`
- **功能**: 释放资源调度任务
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | simulationTaskId | String | 是 |
  | simulationSceneId | String | 否 |
  | executor | String | 是 |

#### 5.2.5 添加机器

- **路径**: `POST /simulation/v2/node/manage/node`
- **功能**: 批量添加服务器节点
- **请求体**: `List<ServerBasicInfoEntity>`

#### 5.2.6 添加场景配置

- **路径**: `POST /simulation/v2/node/manage/scene`
- **功能**: 创建仿真场景配置
- **请求体**:
  ```json
  {
    "name": "string (必填)",
    "description": "string (可选)",
    "serverTags": "string (可选)",
    "deployTags": "string (可选)",
    "creator": "string (可选)"
  }
  ```

#### 5.2.7 获取场景配置

- **路径**: `GET /simulation/v2/node/manage/scene`
- **功能**: 获取场景配置详情
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | sceneId | String | 是 |

#### 5.2.8 删除场景配置

- **路径**: `DELETE /simulation/v2/node/manage/scene`
- **功能**: 删除场景配置
- **请求参数**:
  | 参数名 | 类型 | 必填 |
  |-------|------|------|
  | sceneId | String | 是 |

## 6. 业务流程设计

### 6.1 资源调度任务创建流程

```
用户请求 → 参数校验 → 资源分配 → 任务保存 → 返回结果
    │              │          │          │
    ▼              ▼          ▼          ▼
  Controller   DTO校验    Service     DB持久化
                                 │
                                 ▼
                          节点状态更新
```

### 6.2 资源释放流程

```
用户请求 → 参数校验 → 任务状态检查 → 资源释放 → 任务更新 → 返回结果
    │              │              │          │          │
    ▼              ▼              ▼          ▼          ▼
  Controller   DTO校验        Service    节点释放    DB更新
                                 │
                                 ▼
                          节点状态重置
```

## 7. 数据库表设计

### 7.1 t_server_basic_info

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | VARCHAR(64) | PRIMARY KEY | 主键ID |
| group_id | VARCHAR(64) | NULL | 分组ID |
| ip | VARCHAR(64) | NOT NULL | 服务器IP |
| port | INT | DEFAULT 22 | SSH端口 |
| user | VARCHAR(64) | NOT NULL | 用户名 |
| password | VARCHAR(255) | NOT NULL | 密码 |
| lab_id | VARCHAR(64) | NULL | 实验室ID |
| lab_name | VARCHAR(128) | NULL | 实验室名称 |
| architecture | VARCHAR(32) | NULL | 架构类型 |
| creator | VARCHAR(64) | NULL | 创建人 |
| cpu | INT | NULL | CPU核数 |
| memory | INT | NULL | 内存大小 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| last_modify_time | DATETIME | NOT NULL | 最后修改时间 |

### 7.2 t_server_task

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | VARCHAR(64) | PRIMARY KEY | 主键ID |
| simulation_task_id | VARCHAR(64) | NOT NULL | 仿真任务ID |
| simulation_scene_id | VARCHAR(64) | NULL | 仿真场景ID |
| server_id | VARCHAR(64) | FOREIGN KEY | 服务器ID |
| status | VARCHAR(32) | NOT NULL | 任务状态 |
| task_type | VARCHAR(32) | NULL | 任务类型 |
| task_param | TEXT | NULL | 任务参数 |
| executor | VARCHAR(64) | NULL | 执行者 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| start_time | DATETIME | NULL | 开始时间 |
| end_time | DATETIME | NULL | 结束时间 |

### 7.3 t_simulation_scene

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | VARCHAR(64) | PRIMARY KEY | 主键ID |
| name | VARCHAR(128) | NOT NULL | 场景名称 |
| description | VARCHAR(512) | NULL | 场景描述 |
| server_tags | VARCHAR(255) | NULL | 服务器标签 |
| deploy_tags | VARCHAR(255) | NULL | 部署标签 |
| creator | VARCHAR(64) | NULL | 创建人 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| last_modify_time | DATETIME | NOT NULL | 最后修改时间 |

## 8. 错误处理设计

| 错误码 | 错误信息 | 触发场景 |
|-------|---------|---------|
| 400 | 参数校验失败 | 请求参数缺失或格式错误 |
| 404 | 任务/场景/节点不存在 | 传入的ID不存在于数据库 |
| 409 | 资源冲突 | 节点已被占用或任务状态不允许操作 |
| 500 | 服务器内部错误 | 数据库操作失败或业务逻辑异常 |

## 9. 安全设计

- **跨域支持**: 使用 `@CrossOrigin` 注解允许跨域访问
- **参数校验**: 使用 `@Valid` 注解进行请求参数校验
- **日志记录**: 使用 `@Slf4j` 记录操作日志
- **敏感信息保护**: 密码字段在日志和响应中进行脱敏处理

## 10. 性能考虑

- **批量操作**: 添加机器接口支持批量添加，减少数据库交互次数
- **分页查询**: 查询接口支持分页，避免大量数据一次性返回
- **索引优化**: 在常用查询字段上建立索引，提升查询效率
- **异步处理**: 资源分配等耗时操作考虑异步处理