# 命令执行安全组件 — 技术设计

## 方案概述

提供 `SecureCmdExecutor` 命令执行安全组件，采用**纵深防御**架构：命令白名单（L1）→ 参数黑名单（L2）→ 执行沙箱（L3），为业务方提供安全的系统命令调用能力。

## 整体架构

```
调用方
  │
  ▼
SecureCmdExecutor (单例入口)
  ├── register() ─────────── 注册命令白名单
  ├── filterInjection() ──── L1 白名单校验 + L2 参数黑名单校验
  ├── build() ────────────── 构造 ProcessBuilder（CommandLine.parse 拆词 + env/dir 校验）
  ├── execute() ──────────── 同步执行 + 超时控制
  ├── pipesExec() ────────── 管道执行（/bin/sh -c）
  ├── asyncExec() ────────── 异步执行（调用方管理生命周期）
  └── writeParams() ──────── stdin 输入写入
        │
        ▼
  ProcessInfo<O, E> (进程生命周期管理)
  ├── Process ────────────── JDK 原生进程对象
  ├── StreamGobbler ×2 ───── 守护线程消费 stdout/stderr（防管道死锁）
  ├── waitFor() ──────────── 等待进程终止 + 等待消费线程完成
  └── ensureDestroyed() ──── 优雅销毁（SIGTERM → 宽限期 → SIGKILL）
        │
        ▼
  ProcessResult (Consumer<String>) ── 收集输出行
```

## 防御层级设计

### L1 — 命令白名单

**机制**：`CopyOnWriteArrayList<String>` 存储已注册命令，`filterInjection()` 中精确匹配。

**注册**：通过 `register()` 方法注册，有大小上限（`MAX_WHITELIST=100`），`synchronized` 保证并发安全 + 去重。

**匹配策略**：白名单匹配的是命令模板字符串（含 `%s` 占位符），代表开发者意图。参数通过 L2 逐个校验，模板在白名单中，`String.format()` 组合后不会引入新的危险字符，无需对最终命令做二次校验。

### L2 — 参数黑名单校验（CmdValidator）

**机制**：对外部参数做 Unicode NFKC 归一化后，用正则匹配危险字符。

**正则**：`"(^-.*)|[\\\\<>|`&$;!(){}\\[\\]#~'\"\\s]"`

| 拦截目标 | 字符 |
|---------|------|
| 路径遍历/转义 | `\` |
| 重定向 | `<` `>` |
| 管道 | `\|` |
| 命令替换 | `` ` `` |
| 后台执行/逻辑与 | `&` |
| 变量展开 | `$` |
| 历史展开/逻辑非 | `!` |
| 子 shell | `(` `)` |
| brace 展开 | `{` `}` |
| 字符类展开 | `[` `]` |
| shell 注释 | `#` |
| home 展开 | `~` |
| 引号 | `'` `"` |
| 所有空白 | `\s` |
| flag 注入 | 以 `-` 开头 |

**扩展**：支持业务通过 `extendBlock` 参数扩展黑名单正则片段。

### ~~L3 — 最终命令二次校验~~（已移除）

**原设计**：`String.format()` 替换参数后，对最终命令字符串再做一次黑名单校验。

**移除原因**：`String.format()` 后的命令必然包含空格（命令与参数之间），而空格在黑名单正则中（`\s`），导致所有带参数的命令都会被误拦截。参数已在 L2 逐个校验，模板在白名单中，组合后不会引入新的危险字符，L2 参数级校验已足够。

### L3 — 执行沙箱

- **超时控制**：所有同步执行方法强制指定超时时间
- **优雅销毁**：SIGTERM → 1 秒宽限 → SIGKILL
- **输出消费**：StreamGobbler 守护线程异步消费 stdout/stderr，防止管道缓冲区满导致死锁
- **环境变量管控**：key 黑名单 + 多值追加/单值覆盖
- **工作目录校验**：存在性、禁根目录、禁系统目录

## 架构决策

### D1: 单例模式

**决策**：`SecureCmdExecutor` 采用单例模式，白名单全局共享。

**理由**：命令白名单是全局安全策略，不应存在多个实例各自维护不同的白名单。

### D2: ProcessBuilder + CommandLine.parse

**决策**：使用 Apache Commons Exec 的 `CommandLine.parse()` 将命令字符串拆为 token 数组，再传给 `ProcessBuilder(String[])`。

**理由**：避免整串传给 shell 解释（`Runtime.exec(String)` 的风险），token 数组直接传给 `execvp`，不经过 shell 解析。管道场景（`pipesExec`）是唯一的例外，显式通过 `/bin/sh -c` 执行。

### D3: StreamGobbler 异步消费

**决策**：子进程启动后立即创建两个非守护线程消费 stdout/stderr。

**理由**：OS 管道缓冲区有限（Linux 默认 64KB），如果子进程输出超过缓冲区大小且无人读取，子进程会阻塞在 `write()` 上导致死锁。非守护线程保证消费完成后 JVM 才退出。

### D4: 环境变量 — key 黑名单 + 多值追加/单值覆盖

**决策**：
- 危险 key 黑名单：`LD_PRELOAD`、`BASH_ENV`、`ENV`、`IFS`、`PS1`、`PROMPT_COMMAND`、`SHELLOPTS`
- 多值变量（`PATH`、`CLASSPATH`、`LD_LIBRARY_PATH` 等）追加而非覆盖
- 单值变量（如 `JAVA_HOME`）覆盖/新增
- key 和 value 都做黑名单字符校验

**理由**：`ProcessBuilder.environment()` 的 `putAll` 是覆盖语义。多值变量覆盖会丢失原有路径（如 `PATH`），单值变量覆盖是合理需求（如 `JAVA_HOME` 从 java17 切到 java8）。

### D5: 工作目录 — 基础安全检查

**决策**：校验目录存在性、禁止根目录、禁止关键系统目录（`/etc`、`/proc`、`/sys`、`/dev`、`/boot`、`/root`）。不设置全局 baseDir。

**理由**：公共库无法预知各业务的目录结构，做基础防护即可。业务方在上层封装中按需加更严格约束。

### D6: pipesExec / asyncExec API 设计

**决策**：
- `pipesExec`：只补充带 `env` + `dir` 的变体，不加 `isVerified`（管道场景风险最高，参数必须校验）
- `asyncExec`：补充带 `env` + `dir` 的变体（无参数 + 有参数各一个），不加超时（异步场景由调用方管理生命周期）

**理由**：避免 API 膨胀，只补充最常用的组合。

### D7: 移除最终命令二次校验（L3）

**决策**：不对 `String.format()` 后的最终命令做黑名单校验。

**理由**：黑名单正则包含 `\s`（所有空白字符），而命令字符串必然包含空格（命令名与参数之间），对最终命令做黑名单校验会误拦截所有带参数的命令。L1（白名单匹配模板）+ L2（参数逐个黑名单校验）已提供充分防护——模板是开发者预定义的安全字符串，参数经过 NFKC 归一化 + 正则匹配，`String.format()` 只是将已校验的参数替换到模板占位符中，不会引入新的危险字符。

### D8: 跨平台支持

**决策**：组件同时支持 Windows 和 Linux 平台。

**实现**：
- **管道执行**：`getShellCommand()` 根据平台返回 `["cmd", "/c"]`（Windows）或 `["/bin/sh", "-c"]`（Linux）
- **禁止目录**：`BLOCKED_DIRS` 同时包含 Linux 系统目录（`/etc`、`/proc` 等）和 Windows 系统目录（`C:\Windows\System32` 等），`validateDir()` 对 Windows 路径做大小写不敏感比较
- **测试**：所有测试命令通过 `IS_WINDOWS` 常量 + 辅助方法实现跨平台兼容（`echo`/`sleep`/`cat`/`ls` 等）

## 进程生命周期设计

```
ProcessInfo 构造
  ├── pb.start() 启动子进程
  ├── 创建 StreamGobbler(stdout) 线程 → start
  └── 创建 StreamGobbler(stderr) 线程 → start
        │
        ▼
  waitFor(timeout, unit)
  ├── process.waitFor(timeout, unit)
  │   ├── 超时 → 返回 false → ensureDestroyed(1s)
  │   │   ├── process.destroy() (SIGTERM)
  │   │   ├── waitFor(1s)
  │   │   │   ├── 退出 → waitForThreads() → 结束
  │   │   │   └── 未退出 → destroyForcibly() (SIGKILL) → waitForThreads()
  │   │   └── 结束
  │   └── 正常退出 → 返回 true → waitForThreads()
  │       ├── outThread.join(10s)
  │       └── errThread.join(10s)
  └── 返回结果
```

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `constants/CmdValidatorConstants.java` | 新增 | 黑名单正则、shell 常量、白名单上限、环境变量黑名单、多值变量集合、禁止目录集合 |
| `exception/CmdValidatorException.java` | 新增 | 校验异常类（命令校验错误、参数校验错误、注册错误、超时错误） |
| `validator/CmdValidator.java` | 新增 | 参数黑名单校验器（NFKC 归一化 + 正则匹配 + 扩展黑名单） |
| `security/SecureCmdExecutor.java` | 新增 | 组件主入口（单例、白名单注册、多种 execute 变体、pipesExec、asyncExec） |
| `process/ProcessInfo.java` | 新增 | 进程生命周期管理器（启动、等待、销毁、输出消费） |
| `process/ProcessResult.java` | 新增 | 执行结果封装（Consumer<String>，收集输出行） |
| `process/StreamGobbler.java` | 新增 | 输出流消费守护线程（BufferedReader + UTF-8） |
| `security/SecureCmdExecutorTest.java` | 新增 | 完整测试类 |
| `validator/CmdValidatorTest.java` | 新增 | 完整测试类 |
| `process/ProcessInfoTest.java` | 新增 | 完整测试类 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 黑名单新增字符可能误杀合法参数 | 不加 `*` `?`（glob 场景常见），通过 `extendBlock` 按需扩展 |
| 管道执行经过 shell 解释，风险最高 | L1 白名单匹配模板 + L2 参数黑名单校验双重防护 |
| 异步执行无超时，进程可能泄漏 | Javadoc 明确标注调用方有责任管理进程生命周期，ProcessInfo 提供 ensureDestroyed |
| 环境变量多值追加可能产生重复路径 | 追加前检查是否已包含该值 |
| Windows `%VAR%` 变量展开未在黑名单中 | 管道场景参数经过 L2 校验，`%` 字符不影响命令结构安全；如需拦截可通过 `extendBlock` 扩展 |
