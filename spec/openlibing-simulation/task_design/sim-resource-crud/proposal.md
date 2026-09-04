# 仿真机器/引擎/qcow 资源增删改接口

## 需求背景

- 业务 Issue：[#26](https://gitcode.com/openlibing/openlibing-simulation/issues/26)「提供仿真机器，引擎，qcow文件的增删改接口」
- 现状：6 张资源表的实体已存在，但模块内**没有任何增/改/删 SQL 与管理端点**（Controller 仅任务与健康检查），全部写路径缺失。
- 目标：为以下 6 张表提供 RESTful 增删改接口：
  `t_server_basic_info`、`t_server_extend_info`、`t_engine_basic_info`、`t_qcow_info`、`t_resource_attachment`、`t_server_using`

## 功能描述

做什么：
- 按资源域新增 Controller / Service / Mapper 三层，均放置于 controller / service / mapper 三类目录：
  - **服务器域**（t_server_basic_info + t_server_extend_info + t_server_using，3 张表各自独立增删改端点）
  - **引擎域**（t_engine_basic_info，独立增删改端点）
  - **qcow 域**（t_qcow_info，独立增删改端点）
  - **附件域**（t_resource_attachment，独立增删改端点）
- 删除策略（已确认）：`t_server_basic_info`、`t_server_using` 有 `is_deleted` 列 → **逻辑删除**（UPDATE `is_deleted='1'`）；其余 4 表无该列 → **物理 DELETE**
- 新增：id 由应用层 `CommmonUtils.getUuid()` 生成；审计字段显式赋值（create_time/last_modify_time 由 SQL `now()` 或代码补齐）
- 沿用本库既有编码范式（纯 MyBatis XML、`ResponseEntity(code,msg,data)`、方法级 `@RequestMapping(value,method=POST)`、creator 从 `X-Openlibing-User` 头解析）

不做什么：
- 不新增列表/详情查询接口（仅增删改，已确认）
- 不改动现有环境分配/释放逻辑（`NodeManageServiceImpl.saveNodeManageTask`/`releaseNodeManageTask`、`QemuTaskServiceImpl` 对 t_server_using 的既有写路径）
- 不实现文件上传/下载；`t_resource_attachment` 仅维护元数据行
- 服务器表不额外加密/解密 password（沿用库内 t_server_basic_info 现存写入约定）
- 不引入 MyBatis-Plus / 不新建数据源 / 不加 changelog（无表结构变更）

## 验收标准

- [ ] 6 张表均有可用的 新增/修改/删除 端点（新增/修改 200；参数缺失/记录不存在返回 400）
- [ ] server_basic_info 删除后 `is_deleted='1'`（逻辑删）；server_using 同
- [ ] engine/qcow/attachment/extend 删除为物理 DELETE
- [ ] 新增记录 id 为 32 位 UUID，审计字段有值
- [ ] 接口经 `InternalSimulationAuthFilter` 保护（非 health-check 路径自动生效）
- [ ] `mvn test` 通过（含新增单测）；pre-commit 通过
- [ ] 业务 PR 关联 issue #26，打 ai-assisted 标签

## 影响范围

- 仓：openlibing-simulation（业务代码），openlibing-docs（本 proposal）
- 涉及文件：见 `tasks.md` 清单
- 不影响：现有任务/节点管理 SQL 与端点、Dockerfile、pom 依赖
