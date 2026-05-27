# pytest-testkit 前置动作注册能力 — 实现任务

## 进度: 7/7 complete

- [x] Task 1: 创建 exceptions.py - PreActionError 和 CircularDependencyError
- [x] Task 2: 创建 action.py - PreAction 数据类
- [x] Task 3: 创建 registry.py - PreActionRegistry 和 register_pre_action
- [x] Task 4: 创建 pre_action/__init__.py - 导出模块
- [x] Task 5: 修改 pytest_testkit/__init__.py - 导出 register_pre_action
- [x] Task 6: 修改 plugin.py - 集成 hooks 和新增 fixture
- [x] Task 7: 更新 README.md - 添加前置动作注册功能文档

## 实现概要

### 新增文件

| 文件 | 说明 |
|------|------|
| lib/pre_action/exceptions.py | 异常定义（PreActionError, CircularDependencyError 等） |
| lib/pre_action/action.py | PreAction 数据类 |
| lib/pre_action/registry.py | PreActionRegistry + register_pre_action + 拓扑排序 |
| lib/pre_action/__init__.py | 模块导出 |

### 修改文件

| 文件 | 说明 |
|------|------|
| pytest_testkit/__init__.py | 导出 register_pre_action |
| pytest_testkit/plugin.py | _init_pre_action, _execute_pre_actions, pre_action_results fixture |
| README.md | 新增前置动作注册功能章节 |

## 验证结果

- Python 语法检查通过
- 模块导入测试通过（pre_action 模块）

## 实现日期

2026-05-25