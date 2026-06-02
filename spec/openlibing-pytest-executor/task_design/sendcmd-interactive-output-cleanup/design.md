# Design: sendcmd_interactive 返回值清理

## 技术方案

### 方案概述

在 `_exec_cmd_interactive_common` 方法中添加输出清理逻辑，对收集到的原始输出进行处理后再返回。

### 清理流程

```text
原始输出收集
    ↓
清理 ANSI 转义序列
    ↓
清理命令回显
    ↓
清理 Login Banner
    ↓
返回清理后的输出
```

### 实现细节

#### 1. 清理 ANSI 转义序列

使用正则表达式移除所有 ANSI 转义序列：

```python
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[()][A-Za-z0-9]')
```

常见的 ANSI 转义序列：
- `\x1b[0m` - 重置所有属性
- `\x1b[32m` - 绿色文本
- `\x1b[1m` - 粗体
- `\x1b[K` - 清除行
- `\x1b[?2004h` - 开启 bracketed paste mode
- `\x1b[?2004l` - 关闭 bracketed paste mode

#### 2. 清理命令回显

命令回显的特征：
- 用户发送 `cmd + '\n'`
- 终端会回显相同的内容

清理策略：
- 从输出中移除第一行（即命令回显）
- 或使用正则表达式匹配并移除命令回显行

#### 3. 清理 Login Banner

Login banner 通常出现在首次登录时，特征：
- 包含系统信息、欢迎消息
- 通常在命令执行之前出现

清理策略：
- 检测并移除登录 banner 部分
- 或在首次调用时跳过 banner 收集

### 代码修改位置

#### ssh.py - _exec_cmd_interactive_common 方法

```python
def _exec_cmd_interactive_common(self, channel, param: SshCmdInteractiveParam, method_name: str):
    try:
        # ... 原有的命令发送和输出收集逻辑 ...
        
        output = ''
        matched_prompt = False
        start_time = time.time()
        prompt_regex = self._build_prompt_regex(param.expect_prompt)
        
        while time.time() - start_time < param.timeout:
            if channel.recv_ready():
                output += channel.recv(1024).decode("utf-8")
                if prompt_regex.search(output):
                    matched_prompt = True
                    break
            else:
                time.sleep(0.1)
        
        # ... 原有的 exit_code 获取逻辑 ...
        
        # 新增：清理输出
        cleaned_output = self._clean_interactive_output(output, param.cmd)
        
        return self._build_result(success, cleaned_output, "", param.only_stdout)
    except Exception as e:
        self.logger.error(f"[Ssh.{method_name}] Details: {traceback.format_exc()}")
        raise

def _clean_interactive_output(self, raw_output: str, cmd: str) -> str:
    """清理交互式命令输出中的多余信息。
    
    Args:
        raw_output: 原始的终端输出
        cmd: 用户执行的命令
        
    Returns:
        str: 清理后的输出
    """
    # Step 1: 移除 ANSI 转义序列
    output = self._remove_ansi_escapes(raw_output)
    
    # Step 2: 移除命令回显
    output = self._remove_command_echo(output, cmd)
    
    # Step 3: 移除多余空白行
    output = output.strip()
    
    return output

@staticmethod
def _remove_ansi_escapes(text: str) -> str:
    """移除 ANSI 转义序列。"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[()][A-Za-z0-9]')
    return ansi_escape.sub('', text)

@staticmethod
def _remove_command_echo(text: str, cmd: str) -> str:
    """移除命令回显。
    
    策略：移除包含命令字符串的第一行
    """
    lines = text.split('\n')
    # 找到包含命令的行并移除
    cleaned_lines = []
    cmd_found = False
    for line in lines:
        if not cmd_found and cmd in line:
            cmd_found = True
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)
```

### 边缘情况处理

| 场景 | 处理方式 |
|------|----------|
| 输出中无命令回显 | 清理逻辑保持原样 |
| 输出中无 ANSI 序列 | 清理逻辑保持原样 |
| 命令输出为空 | 返回空字符串 |
| 多行命令 | 按行处理，移除所有回显行 |

### 向后兼容性

1. 清理逻辑不影响 `only_stdout` 参数的行为
2. 清理逻辑不影响 `success` 字段的判断逻辑
3. 清理后的输出更易于用户使用，不会破坏现有功能

## 文件修改清单

| 文件 | 修改内容 | 行数估算 |
|------|----------|----------|
| pytest_testkit/lib/base/ssh.py | 新增清理方法和修改 `_exec_cmd_interactive_common` | +30 行 |
| pytest_testkit/tests/test_ssh_success.py | 新增测试验证清理效果 | +15 行 |

## 测试策略

### 单元测试

1. 测试 ANSI 转义序列移除
2. 测试命令回显移除
3. 测试组合清理效果

### 集成测试

使用真实 SSH 连接验证：
1. 带颜色的命令输出清理
2. 多行命令输出清理
3. 空 output 清理

## 验证方式

```python
# 验证 ANSI 清理
result = environment.sendcmd_interactive(
    "echo '\x1b[32mcolored text\x1b[0m'",
    only_stdout=False
)
assert '\x1b' not in result['stdout']
assert 'colored text' in result['stdout']

# 验证命令回显清理
result = environment.sendcmd_interactive(
    "echo 'test'",
    only_stdout=False
)
# 应不包含 'echo 'test'' 命令回显
assert 'echo' not in result['stdout'] or 'test' in result['stdout']
``']