# 命令执行安全组件

## 需求背景

openlibing-common 需要提供一个**统一的命令执行安全组件**，为各业务服务提供安全的系统命令调用能力，防止命令注入攻击。

当前业务场景中存在大量命令执行需求（构建/打包/脚本执行/系统工具调用），如果各业务自行使用 `Runtime.exec()` 或 `ProcessBuilder`，容易出现命令注入、进程泄漏、资源耗尽等问题。需要一个公共组件统一收敛风险。

关联业务 Issue：https://gitcode.com/openlibing/openlibing-framework/issues/84

## 功能描述

### 做什么

提供 `SecureCmdExecutor` 命令执行安全组件，核心能力包括：

1. **命令白名单机制**：只允许预注册的命令执行，拒绝一切不在白名单中的命令
2. **参数黑名单校验**：对外部输入参数做 Unicode NFKC 归一化 + 正则匹配，拦截 shell 元字符和危险字符
3. **多种执行模式**：
   - 同步执行（带超时）：固定命令、带参数命令、带环境变量/工作目录命令
   - 管道执行（pipesExec）：支持 shell 管道语法
   - 异步执行（asyncExec）：不阻塞调用方，由调用方管理生命周期
   - stdin 输入执行：通过标准输入流向子进程传递数据
   - 数组形式执行：直接传入命令数组
4. **进程生命周期管理**（ProcessInfo）：
   - 异步消费 stdout/stderr（StreamGobbler 守护线程），防止管道缓冲区死锁
   - 超时等待 + 优雅销毁（SIGTERM → 宽限期 → SIGKILL）
   - 进程状态查询（exitValue、isAlive）
5. **执行结果封装**（ProcessResult）：收集命令输出，支持 toString 还原
6. **环境变量安全管控**：key 黑名单 + 多值追加/单值覆盖策略
7. **工作目录安全校验**：存在性检查、禁止根目录和关键系统目录
8. **完整测试覆盖**：关键方法全覆盖，覆盖率 > 60%

### 不做什么

- 不涉及 Issue #84 中的接口鉴权、Apollo/Eureka 切换 CSE 等其他子需求
- 不提供命令编排/工作流引擎能力（只做单条命令的安全执行）
- 不提供远程命令执行能力（仅本地子进程）

## 验收标准

- [ ] 组件提供完整的命令安全执行能力（白名单 + 黑名单 + 进程管理）
- [ ] 支持同步/异步/管道/stdin/数组多种执行模式
- [ ] 环境变量和工作目录有安全校验
- [ ] 进程生命周期管理完善（超时销毁、优雅退出、输出消费）
- [ ] 测试覆盖所有关键方法
- [ ] 测试覆盖率 > 60%
- [ ] 构建通过，无编译错误

## 影响范围

| 文件                                   | 操作 | 说明                   |
| -------------------------------------- | ---- | ---------------------- |
| `constants/CmdValidatorConstants.java` | 新增 | 黑名单正则、常量定义   |
| `exception/CmdValidatorException.java` | 新增 | 校验异常类             |
| `validator/CmdValidator.java`          | 新增 | 参数黑名单校验器       |
| `security/SecureCmdExecutor.java`      | 新增 | 命令执行安全组件主入口 |
| `process/ProcessInfo.java`             | 新增 | 进程生命周期管理器     |
| `process/ProcessResult.java`           | 新增 | 执行结果封装           |
| `process/StreamGobbler.java`           | 新增 | 输出流消费守护线程     |
| `security/SecureCmdExecutorTest.java`  | 新增 | 完整测试类             |
| `validator/CmdValidatorTest.java`      | 新增 | 完整测试类             |
| `process/ProcessInfoTest.java`         | 新增 | 完整测试类             |
