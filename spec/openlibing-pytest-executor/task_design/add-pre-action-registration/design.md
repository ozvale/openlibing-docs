# pytest-testkit 前置活动注册能力设计

## 关联 Issue
- https://gitcode.com/openlibing/openlibing-pytest-executor/issues/11

## 需求背景

用例执行前存在一些前置动作（环境变量加载、参数注入等），目前缺乏统一的注册与执行机制。需要在 pytest-testkit 插件中提供通用的注册函数 `register_pre_action`，支持：
- 在 conftest.py 中全局注册前置动作
- 支持前置动作之间的依赖关系
- 前置动作结果可通过 fixture 注入到测试用例
- 执行失败时用例直接报错，报错原因为前置注册函数失败

---

## 方案概述

新增 `PreActionRegistry` 模块，通过 pytest hooks 集成到测试生命周期：

```
pytest_configure (session start)
    └── 用户调用 register_pre_action 注册前置动作

pytest_runtest_setup (before each test)
    └── 环境分配完成
    └── 执行已注册的前置动作（按依赖顺序）
    └── 收集执行结果到 item 对象

pytest_runtest_call (test execution)
    └── pre_action_results fixture 提供结果给测试用例
```

---

## 数据结构设计

### PreAction 数据类

```python
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List, Dict

@dataclass
class PreAction:
    """
    前置动作定义。
    
    Attributes:
        name: 前置动作名称，用于依赖引用和结果获取
        func: 执行函数，签名为 (environments: Dict[str, Device], **kwargs) -> Any
        kwargs: 传递给 func 的固定参数
        depends_on: 依赖的前置动作名称列表，依赖动作先执行
        priority: 执行优先级（数值小优先），用于无依赖时的排序
        skip_on_fail: 当依赖动作失败时是否跳过执行，默认 True
    """
    name: str
    func: Callable
    kwargs: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    priority: int = 100
    skip_on_fail: bool = True
    
    # 执行结果（运行时填充）
    result: Any = None
    executed: bool = False
    success: bool = False
    error: Optional[str] = None
```

### PreActionRegistry 类

```python
class PreActionRegistry:
    """
    前置动作注册中心。
    
    管理 session 级别的前置动作注册、依赖解析、执行调度。
    """
    
    def __init__(self):
        self._actions: Dict[str, PreAction] = {}
        self._execution_order: List[str] = []  # 解析后的执行顺序
    
    def register(
        self,
        name: str,
        func: Callable,
        kwargs: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        priority: int = 100,
        skip_on_fail: bool = True
    ) -> None:
        """
        注册前置动作。
        
        Args:
            name: 前置动作名称（唯一标识）
            func: 执行函数，签名为 (environments, **kwargs) -> Any
            kwargs: 传递给 func 的固定参数
            depends_on: 依赖的前置动作名称列表
            priority: 执行优先级
            skip_on_fail: 依赖失败时是否跳过
        
        Raises:
            ValueError: 名称重复或依赖不存在
        """
        ...
    
    def resolve_dependencies(self) -> List[str]:
        """
        解析依赖关系，返回执行顺序。
        
        使用拓扑排序，按依赖关系和 priority 排序。
        
        Raises:
            CircularDependencyError: 存在循环依赖
        """
        ...
    
    def execute(
        self,
        environments: Dict[str, Device],
        item: pytest.Item
    ) -> Dict[str, PreActionResult]:
        """
        按顺序执行所有已注册的前置动作。
        
        Args:
            environments: 已分配的环境（Device 字典）
            item: pytest 测试项对象
        
        Returns:
            执行结果字典 {name: PreActionResult}
        
        Raises:
            PreActionError: 任一前置动作执行失败时抛出
        
        Note:
            失败的动作会记录错误，跳过后续依赖动作，最终抛出 PreActionError。
        """
        ...
    
    def get_results(self) -> Dict[str, Any]:
        """
        获取所有已执行动作的结果。
        
        Returns:
            {name: result_value} 字典
        """
        ...
```

---

## API 设计

### register_pre_action 函数

用户在 conftest.py 中调用的注册函数：

```python
def register_pre_action(
    name: str,
    func: Callable[[Dict[str, Device], ...], Any],
    kwargs: Optional[Dict[str, Any]] = None,
    depends_on: Optional[List[str]] = None,
    priority: int = 100,
    skip_on_fail: bool = True
) -> None:
    """
    注册测试前置动作。
    
    在 pytest_configure 钩子中调用，注册 session 级别的前置动作。
    
    Example:
        # conftest.py
        
        def pytest_configure(config):
            # 注册环境变量加载
            register_pre_action(
                name="load_env_vars",
                func=load_test_env_vars,
                kwargs={"env_file": "test.env"},
                priority=10
            )
            
            # 注册参数注入（依赖环境变量加载）
            register_pre_action(
                name="inject_params",
                func=inject_test_params,
                depends_on=["load_env_vars"],
                kwargs={"config_file": "params.yaml"}
            )
    """
    ...
```

### pre_action_results fixture

提供前置动作结果给测试用例：

```python
@pytest.fixture
def pre_action_results(request) -> Dict[str, Any]:
    """
    提供已执行前置动作的结果。
    
    Usage:
        def test_example(environments, pre_action_results):
            # 获取 load_env_vars 的结果
            env_vars = pre_action_results.get("load_env_vars")
            
            # 获取 inject_params 的结果
            params = pre_action_results.get("inject_params")
            
            # 使用注入的参数
            timeout = params.get("timeout", 30)
    """
    return getattr(request.item, "_pre_action_results", {})
```

---

## 执行流程设计

### 依赖解析算法（拓扑排序）

```python
def _resolve_execution_order(actions: Dict[str, PreAction]) -> List[str]:
    """
    拓扑排序 + priority 辅助排序。
    
    算法：
    1. 构建依赖图
    2. Kahn 算法拓扑排序
    3. 同层级按 priority 排序
    4. 检测循环依赖
    """
    # 1. 构建图
    graph = {name: set(action.depends_on) for name, action in actions.items()}
    
    # 2. 计算入度
    in_degree = {name: 0 for name in actions}
    for name, deps in graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[name] += 1
    
    # 3. Kahn 算法
    queue = sorted(
        [n for n, d in in_degree.items() if d == 0],
        key=lambda n: actions[n].priority
    )
    result = []
    
    while queue:
        # 取出优先级最高的无依赖节点
        current = queue.pop(0)
        result.append(current)
        
        # 减少依赖该节点的入度
        for name in actions:
            if current in graph[name]:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)
                    queue.sort(key=lambda n: actions[n].priority)
    
    # 4. 检测循环依赖
    if len(result) != len(actions):
        raise CircularDependencyError("存在循环依赖的前置动作")
    
    return result
```

### 执行流程

```python
def _execute_pre_actions(
    registry: PreActionRegistry,
    environments: Dict[str, Device],
    item: pytest.Item
) -> None:
    """
    在 pytest_runtest_setup 中执行前置动作。
    
    流程：
    1. 获取执行顺序
    2. 按顺序逐个执行
    3. 处理依赖失败（skip_on_fail）
    4. 记录结果到 item
    5. 任一必要动作失败则抛出 PreActionError 导致用例报错
    """
    order = registry.resolve_dependencies()
    results = {}
    failed_actions = {}  # {name: error_message}
    
    for name in order:
        action = registry._actions[name]
        
        # 检查依赖是否失败
        deps_failed = any(
            dep in failed_actions 
            for dep in action.depends_on
        )
        
        if deps_failed and action.skip_on_fail:
            action.executed = False
            action.success = False
            action.error = "依赖动作失败，跳过执行"
            failed_actions[name] = action.error
            continue
        
        # 执行动作
        try:
            # 构建参数：environments + kwargs + 依赖结果
            exec_kwargs = action.kwargs.copy()
            for dep in action.depends_on:
                if dep in results:
                    exec_kwargs[f"{dep}_result"] = results[dep]
            
            action.result = action.func(environments, **exec_kwargs)
            action.executed = True
            action.success = True
            results[name] = action.result
            
        except Exception as e:
            action.executed = True
            action.success = False
            action.error = str(e)
            failed_actions[name] = str(e)
            logger.error(f"前置动作 {name} 执行失败: {e}")
    
    # 记录结果到 item
    item._pre_action_results = results
    item._pre_action_failed = len(failed_actions) > 0
    
    # 如果有失败，抛出异常导致用例报错
    if item._pre_action_failed:
        failed_names = list(failed_actions.keys())
        error_details = "; ".join([f"{n}: {e}" for n, e in failed_actions.items()])
        raise PreActionError(
            f"前置动作执行失败: {failed_names}\n详细错误: {error_details}"
        )
```

---

## plugin.py 集成设计

### pytest_configure 修改

```python
def pytest_configure(config):
    # ... existing code ...
    
    # 初始化前置动作注册中心
    config.pre_action_registry = PreActionRegistry()
    
    # 注册自定义 marker
    config.addinivalue_line(
        "markers", "pre_action: mark test to enable pre-action execution"
    )
```

### pytest_runtest_setup 修改

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    # ... existing code (logging, environment allocation) ...
    
    yield
    
    # 环境分配后执行前置动作
    if hasattr(item.config, "pre_action_registry"):
        registry = item.config.pre_action_registry
        if registry.has_actions():
            environments = getattr(item, "infra_environments", {})
            # 执行前置动作，失败时抛出 PreActionError
            _execute_pre_actions(registry, environments, item)
```

### 新增 fixture

```python
@pytest.fixture
def pre_action_results(request):
    """
    提供前置动作执行结果。
    """
    return getattr(request.item, "_pre_action_results", {})
```

---

## 模块文件结构

```
pytest_testkit/
├── __init__.py              # 导出 register_pre_action
├── plugin.py                # 集成 hooks + fixtures
├── lib/
│   └── pre_action/
│       ├── __init__.py      # 导出 PreAction, PreActionRegistry
│       ├── action.py        # PreAction 数据类
│       └── registry.py      # PreActionRegistry + register_pre_action
│       └── exceptions.py    # CircularDependencyError, PreActionError
```

---

## 错误处理设计

| 场景 | 处理策略 |
|------|---------|
| 循环依赖 | pytest_configure 时抛出 CircularDependencyError，终止测试 |
| 依赖不存在 | register 时抛出 ValueError |
| 动作执行异常 | 记录错误，标记失败，跳过后续依赖动作，最终抛出 PreActionError |
| 无环境分配 | 前置动作收到空 environments dict，按设计处理 |

### PreActionError 异常

```python
class PreActionError(Exception):
    """
    前置动作执行失败异常。
    
    当任一前置动作执行失败时抛出，导致测试用例报错。
    异常消息包含失败的动作名称和详细错误信息。
    """
    pass
```

---

## 使用示例

### conftest.py 全局注册

```python
import pytest
from pytest_testkit import register_pre_action

def load_env_vars(environments, env_file):
    """加载环境变量"""
    import os
    from dotenv import load_dotenv
    load_dotenv(env_file)
    return dict(os.environ)

def inject_params(environments, config_file, load_env_vars_result=None):
    """注入参数，可获取依赖动作结果"""
    import yaml
    with open(config_file) as f:
        params = yaml.safe_load(f)
    # 可使用环境变量结果
    if load_env_vars_result:
        params["env_mode"] = load_env_vars_result.get("TEST_MODE", "default")
    return params

def setup_device(environments, **kwargs):
    """初始化设备连接"""
    for name, device in environments.items():
        device.login()
        device.sendcmd("mkdir -p /tmp/test_workspace")
    return {"initialized": True}

def pytest_configure(config):
    # 注册前置动作
    register_pre_action(
        name="load_env_vars",
        func=load_env_vars,
        kwargs={"env_file": "test.env"},
        priority=10  # 最先执行
    )
    
    register_pre_action(
        name="inject_params",
        func=inject_params,
        kwargs={"config_file": "params.yaml"},
        depends_on=["load_env_vars"],
        priority=20
    )
    
    register_pre_action(
        name="setup_device",
        func=setup_device,
        depends_on=["inject_params"],
        skip_on_fail=True
    )
```

### 测试用例使用

```python
import pytest

@pytest.mark.env({"name": "device1", "model": "Atlas 800T A2"})
@pytest.mark.remote_run
def test_with_pre_actions(environments, pre_action_results):
    # 获取注入的参数
    params = pre_action_results.get("inject_params")
    timeout = params.get("timeout", 30)
    
    # 获取设备初始化结果
    device_ready = pre_action_results.get("setup_device")
    
    # 使用已初始化的设备
    device = environments["device1"]
    device.sendcmd(f"ls /tmp/test_workspace")
```

---

## 验收标准

- [ ] 提供 `register_pre_action` 函数，支持在 conftest.py 中全局注册
- [ ] 支持前置动作之间的依赖关系（拓扑排序执行）
- [ ] 提供 `pre_action_results` fixture，将结果注入测试用例
- [ ] 前置动作执行失败时用例直接报错，报错原因为前置注册函数失败
- [ ] 循环依赖时抛出明确异常
- [ ] 依赖动作失败时，后续动作可配置是否跳过（skip_on_fail）

---

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| pytest_testkit/lib/pre_action/__init__.py | 新增 | 导出模块 |
| pytest_testkit/lib/pre_action/action.py | 新增 | PreAction 数据类 |
| pytest_testkit/lib/pre_action/registry.py | 新增 | PreActionRegistry + register_pre_action |
| pytest_testkit/lib/pre_action/exceptions.py | 新增 | 异常定义 |
| pytest_testkit/__init__.py | 修改 | 导出 register_pre_action |
| pytest_testkit/plugin.py | 修改 | 集成 hooks + 新增 fixture |
| tests/test_pre_action.py | 新增 | 单元测试 |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 注册时机过晚导致执行失败 | 明确文档说明：register_pre_action 只能在 pytest_configure 中调用 |
| 依赖结果传递复杂 | 提供清晰的 API 设计，依赖结果通过 `{dep}_result` 参数传递 |
| 执行失败信息不够详细 | 在 logger 中记录详细错误，PreActionError 消息包含失败动作名称和详细错误 |

---

## 设计日期
2026-05-25