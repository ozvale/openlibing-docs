# pytest-testkit 前置动作注册能力

## 需求背景

用例执行前存在一些前置动作（环境变量加载、参数注入等），目前缺乏统一的注册与执行机制。需要在 pytest-testkit 插件中提供通用的注册函数，支持：
- 在 conftest.py 中全局注册前置动作
- 支持前置动作之间的依赖关系
- 前置动作结果可通过 fixture 注入到测试用例
- 执行失败时用例直接报错，报错原因为前置注册函数失败

## 关联 Issue

- https://gitcode.com/openlibing/openlibing-pytest-executor/issues/11

## 功能描述

### 核心功能

1. **register_pre_action 函数**：在 conftest.py 中注册前置动作
2. **pre_action_results fixture**：提供前置动作执行结果给测试用例
3. **依赖解析**：拓扑排序算法解析执行顺序
4. **执行调度**：在 pytest_runtest_setup 钩子中执行

### 不做什么

- 不支持延迟参数（运行时从环境获取）
- 不支持 pytest marker 方式注册
- 不支持 function 级别的注册

## 验收标准

- [ ] 提供 `register_pre_action` 函数，支持在 conftest.py 中全局注册
- [ ] 支持前置动作之间的依赖关系（拓扑排序执行）
- [ ] 提供 `pre_action_results` fixture，将结果注入测试用例
- [ ] 前置动作执行失败时用例直接报错，报错原因为前置注册函数失败
- [ ] 循环依赖时抛出明确异常
- [ ] 依赖动作失败时，后续动作可配置是否跳过（skip_on_fail）

## 影响范围

| 仓库名 | 影响范围 |
|--------|---------|
| openlibing-pytest-executor/pytest-testkit | 新增 pre_action 模块，修改 plugin.py |

## 设计日期

2026-05-25