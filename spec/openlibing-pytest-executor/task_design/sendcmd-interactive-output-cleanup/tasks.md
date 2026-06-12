# sendcmd_interactive 返回值清理 — 实现任务

## 进度: 0/3 complete

- [ ] Task 1: 在 ssh.py 中新增输出清理方法
  - 新增 `_remove_ansi_escapes` 静态方法，移除 ANSI 转义序列
  - 新增 `_remove_command_echo` 静态方法，移除命令回显
  - 新增 `_clean_interactive_output` 方法，组合清理逻辑
  - 更新 `_exec_cmd_interactive_common` 方法，调用清理方法

- [ ] Task 2: 更新测试验证清理效果
  - 在 [test_ssh_success.py](file:///home/tzing/openlibing/openlibing-pytest-executor/pytest-testkit/tests/test_ssh_success.py) 中新增 ANSI 清理测试
  - 新增命令回显清理测试
  - 新增组合清理效果测试

- [ ] Task 3: 更新 README 文档说明
  - 更新 sendcmd_interactive 函数说明，标注返回值已清理多余信息
  - 添加清理内容说明（ANSI、命令回显、banner）

## 关键约束

- 必须保持向后兼容，不影响现有 API 行为
- 清理逻辑必须高效，不影响命令执行性能
- 清理后的输出必须保持原始输出的核心内容
- 必须处理各种边缘情况（空输出、无回显等）

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| pytest_testkit/pytest_testkit/lib/base/ssh.py | 修改 | 新增清理方法 + 调用清理逻辑（约 30 行） |
| pytest-testkit/tests/test_ssh_success.py | 修改 | 新增测试用例（约 15 行） |
| pytest-testkit/README.md | 修改 | 更新函数说明（约 5 行） |

## 验证方式

- ANSI 清理测试：发送带颜色编码的命令，验证返回值中无 `\x1b` 字符
- 命令回显清理测试：发送 `echo` 命令，验证返回值中无命令本身
- 现有测试通过：确保所有现有测试不受影响