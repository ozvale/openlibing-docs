# environment-docker-proxy — 实现任务

## 进度: 6/6 complete

- [x] Task 1: 在 device.py 中新增 `DockerProxy` 类
  - 实现 `__init__(device, docker_name)`
  - 实现 `sendcmd` 方法（包装为 `docker exec {name} {cmd}`）
  - 实现 `sendcmd_interactive` 方法（持久 session 模式）
  - 实现 `exit_docker` 方法（退出 docker session）
  - 实现 `_is_interactive_shell` 静态方法（判断交互式 shell 命令）
  - 定义 `_INTERACTIVE_SHELL_COMMANDS` 集合

- [x] Task 2: 在 Device 类中新增 `_registered_dockers` 属性和 `set_docker` 方法
  - `__init__` 中初始化 `_registered_dockers: dict`
  - 实现 `set_docker(docker_name: str)` 方法

- [x] Task 3: 修改 Device 类的 `__getitem__` 方法
  - 优先查找 `_registered_dockers` 中已注册的容器名
  - 返回对应的 `DockerProxy` 实例

- [x] Task 4: 编写单元测试
  - 测试 `set_docker` 注册容器
  - 测试 `__getitem__` 返回 DockerProxy
  - 测试 DockerProxy 的 `sendcmd` 命令包装正确
  - 测试 DockerProxy 的 `sendcmd_interactive` session 行为
  - 测试 `exit_docker` 方法
  - 测试 `_is_interactive_shell` 方法
  - 测试非 shell 命令不会创建 session 状态

- [x] Task 5: 增强 SSH 层 OSC 序列清理
  - 修改 `_remove_ansi_escapes` 方法，增加 OSC 序列清理
  - 清理 `\x1b]0;title\x07` 等窗口标题设置序列
  - 使用非贪婪匹配避免删除过多内容

- [x] Task 6: 运行测试验证并提交 commit
  - 运行新增测试（28 个测试通过）
  - 确认无破坏现有功能
  - 提交代码变更