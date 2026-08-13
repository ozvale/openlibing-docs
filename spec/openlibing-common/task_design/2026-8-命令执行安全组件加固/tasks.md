# 命令执行安全组件加固 — 实现任务

## 进度: 0/9 complete

### Task 1: 修复 CmdValidatorConstants 常量

- [ ] 修复 `BIN_SH` 路径：`"/bin/;sh"` → `"/bin/sh"`
- [ ] 更新 `REGEX`：去冗余 `\t\r\n`，新增 `#~[]'"`
- [ ] 新增 `BLOCKED_ENV_KEYS` 常量（环境变量 key 黑名单）
- [ ] 新增 `MULTI_VALUE_ENV_KEYS` 常量（多值环境变量集合）
- [ ] 新增 `BLOCKED_DIRS` 常量（禁止的系统目录集合）

### Task 2: 修复 CmdValidator

- [ ] `Pattern.compile()` 移到循环外
- [ ] 基础正则提取为 `static final Pattern` 常量，有 extendBlock 时动态编译

### Task 3: SecureCmdExecutor 安全加固

- [ ] `setWhiteList` 改 `private`
- [ ] `register()` 加 `synchronized` + 去重逻辑
- [ ] 所有带 `params` 的 execute 变体：`String.format()` 后对最终命令做二次黑名单校验
- [ ] `build()` 中新增工作目录校验（存在性、禁根目录、禁系统目录）
- [ ] `build()` 中新增环境变量 key 黑名单校验 + 多值追加/单值覆盖逻辑 + key 字符校验
- [ ] `ensureDestroyed` 调用处宽限期从 `0` 改为 `1` 秒

### Task 4: SecureCmdExecutor API 补全

- [ ] `execute(String[])` 新增带 `timeout` + `timeUnit` 参数的重载
- [ ] `pipesExec` 补充带 `env` + `dir` 的变体
- [ ] `asyncExec` 补充带 `env` + `dir` 的变体（无参数 + 有参数）

### Task 5: ProcessInfo 生命周期加固

- [ ] `waitForThreads()` 的 `join()` 加超时（10 秒）
- [ ] `ensureDestroyed()` 中 `destroyForcibly()` 后补 `waitForThreads()`

### Task 6: StreamGobbler 资源关闭

- [ ] `run()` 中 `BufferedReader` 改为 try-with-resources

### Task 7: ProcessResult 集合替换

- [ ] `CopyOnWriteArrayList` → `ArrayList`

### Task 8: 补充测试类

- [ ] `CmdValidatorTest`：黑名单正则匹配（各危险字符逐一验证）、NFKC 归一化、扩展黑名单拼接、合法参数通过
- [ ] `SecureCmdExecutorTest`：白名单注册（去重/并发/大小限制）、各 execute 变体正常执行、白名单拒绝、参数黑名单拦截、最终命令二次校验、环境变量校验（key 黑名单/多值追加/单值覆盖）、工作目录校验（不存在/根目录/系统目录）、超时销毁、`pipesExec` 正常执行与参数校验、`asyncExec` 正常执行
- [ ] `ProcessInfoTest`：正常退出、超时强杀、`ensureDestroyed` 宽限期行为、`waitForThreads` 超时、`exitValue` 各变体、`isAlive`

### Task 9: 构建验证

- [ ] `mvn compile` 编译通过
- [ ] `mvn test` 全部测试通过
- [ ] 覆盖率 > 60%
