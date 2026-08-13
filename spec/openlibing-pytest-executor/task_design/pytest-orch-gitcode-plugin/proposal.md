# Proposal: pytest-orch GitCode Actions Plugin Development

## 背景

pytest-executor 是 OpenLibing 平台的核心测试环境调度器,用于为测试任务分配、管理和释放运行环境。原有实现通过 `start.sh` Shell 脚本启动调度流程,存在以下问题:

1. **集成复杂度高**: Shell 脚本在 CI/CD 流水线中集成需要额外配置和维护
2. **可维护性不足**: Shell 脚本难以进行单元测试和类型检查
3. **安全性风险**: Shell 脚本中的参数注入和命令执行存在安全隐患
4. **可扩展性受限**: Shell 脚本难以与 GitCode Actions 生态集成

## 目标

将 `start.sh` Shell 脚本转换为标准的 GitCode Actions JavaScript 插件,实现:

1. **标准化 CI/CD 集成**: 通过 GitCode Actions 插件机制提供标准化集成能力
2. **提升安全性**: 使用 Node.js 实现参数校验、路径安全检查、输入白名单等安全机制
3. **增强可维护性**: 代码可进行单元测试,支持静态分析
4. **提高可扩展性**: 可与 GitCode Actions 生态无缝集成,支持复用和共享

## 需求范围

### 功能需求

| 需求项   | 描述                                                | 优先级 |
| -------- | --------------------------------------------------- | ------ |
| 插件定义 | 定义 GitCode Actions 插件元数据、输入参数和输出参数 | P0     |
| 参数校验 | 对所有 9 个必选参数和 15 个可选参数进行安全校验     | P0     |
| Git 认证 | 安全实现 Git 仓库克隆和认证流程                     | P0     |
| 虚拟环境 | 创建 Python 虚拟环境并安装依赖                      | P0     |
| 环境调度 | 调用 Python 调度器执行环境申请、测试执行和释放流程  | P0     |
| 日志收集 | 收集执行日志并上传到 OBS                            | P0     |
| 错误处理 | 提供清晰的错误消息和失败定位                        | P0     |
| 文档支持 | 提供插件使用指南和迁移说明                          | P1     |

### 非功能需求

| 需求项       | 描述                                         |
| ------------ | -------------------------------------------- |
| 性能要求     | 插件初始化时间 < 5 秒                        |
| 安全要求     | 所有参数必须经过校验,禁止命令注入和路径穿越  |
| 兼容性要求   | 支持 Node.js 16+,兼容 GitCode Actions 运行时 |
| 可测试性要求 | 核心逻辑支持单元测试覆盖                     |

## 验收标准

### 功能验收

- [ ] 插件能够在 GitCode Actions 中成功运行
- [ ] 所有 13 个必选参数和 11 个可选参数均正确传递给 Python 调度器
- [ ] Git 仓库能够成功克隆 executor 和 testcase 两个仓库
- [ ] 虚拟环境能够成功创建并安装依赖
- [ ] Python 调度器能够成功执行环境调度流程
- [ ] 测试日志能够正确收集并上传到 OBS
- [ ] 插件输出参数能够正确返回给调用方

### 安全验收

- [ ] 所有输入参数经过类型、长度和格式校验
- [ ] JSON 参数校验包含字段白名单限制(如 scheduler-secret)
- [ ] 路径操作包含安全断言检查
- [ ] Git 凭证通过 GIT_ASKPASS 机制安全传递
- [ ] 敏感信息不会在日志中泄露

### 文档验收

- [ ] README 包含插件使用指南
- [ ] README 包含从 start.sh 迁移的说明
- [ ] action.yml 包含所有参数的详细描述

## 关联 Issue

- GitCode Issue: openlibing/openlibing-pytest-executor#23

## 提交信息

```
commit 65884d7c7100c9338d99bbc5df4c935c5bc7ecff
Author: z30004965 <zhengting13@huawei.com>
Date:   Mon Jul 13 10:20:52 2026 +0800

feat(pytest-executor): convert start.sh to GitCode Actions JavaScript plugin
```
