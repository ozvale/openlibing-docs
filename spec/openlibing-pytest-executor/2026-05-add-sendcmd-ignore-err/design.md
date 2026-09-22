# Design: Add `ignore_err` Parameter and Dict Return Type to SSH Command Execution

## Overview

This change adds an `ignore_err` parameter to SSH command execution methods, changes the return type to dictionary `{'success': bool, 'stdout': str, 'stderr': str}`, and **never throws exceptions**. All execution status is reflected in the `success` field.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Call Chain (After Change)                          │
│                          ⚠️ Never Throw Exceptions                           │
└─────────────────────────────────────────────────────────────────────────────┘

Device.sendcmd(cmd, timeout, environment, cwd, ignore_err=False)
        │
        ▼
Ssh.ssh_cmd(cmd, timeout, environment, cwd, ignore_err=False)
        │
        ├──────────────────────┬─────────────────────┐
        ▼                      ▼                     │
_direct_exec_cmd()     _jump_exec_command()         │
        │                      │                     │
        ▼                      ▼                     │
┌─────────────────────────────────────────────┐     │
│  stdout_content = stdout.read().decode()    │     │
│  stderr_content = stderr.read().decode()    │     │
│  exit_code = channel.recv_exit_status()     │     │
│                                             │     │
│  if exit_code != 0:                         │     │
│      logger.warning(stderr_content)         │     │
│                                             │     │
│  # Calculate success                        │     │
│  if exit_code == 0:                         │     │
│      success = True                         │     │
│  elif ignore_err:                           │     │
│      success = True  # error ignored        │     │
│  else:                                      │     │
│      success = False                        │     │
│                                             │     │
│  return {                                   │     │
│      'success': success,                    │     │
│      'stdout': stdout_content,              │     │
│      'stderr': stderr_content               │     │
│  }                                          │     │
│                                             │     │
│  ⚠️ NO RuntimeError raised                  │     │
└─────────────────────────────────────────────┘     │
                                                   │
                                                   │
Device.sendcmd_interactive(cmd, expect_prompt,     │
                          timeout, cwd, ignore_err)
        │
        ▼
Ssh.ssh_cmd_interactive(cmd, expect_prompt, timeout,
                        cwd, ignore_err=False)
        │
        ├──────────────────────┬─────────────────────┐
        ▼                      ▼                     │
_direct_exec_cmd_interactive() _jump_exec_cmd_interactive()
        │                      │
        ▼                      ▼
┌─────────────────────────────────────────────┐
│  matched_prompt = False                     │
│  Send command and collect output            │
│                                             │
│  if prompt_regex.search(output):            │
│      matched_prompt = True                  │
│      break                                  │
│                                             │
│  if not matched_prompt:                     │
│      logger.warning("prompt not matched")   │
│                                             │
│  # Calculate success                        │
│  if matched_prompt:                         │
│      success = True                         │
│  elif ignore_err:                           │
│      success = True  # error ignored        │
│  else:                                      │
│      success = False                        │
│                                             │
│  return {                                   │
│      'success': success,                    │
│      'stdout': output,                      │
│      'stderr': ""                           │
│  }                                          │
│                                             │
│  ⚠️ NO RuntimeError raised                  │
└─────────────────────────────────────────────┘
```

## Implementation Details

### 1. Success Field Logic

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     success 计算逻辑                                          │
└─────────────────────────────────────────────────────────────────────────────┘

    非交互式 (exit_code):
    ══════════════════════

    if exit_code == 0:
        success = True              ← 命令成功
    elif ignore_err:
        success = True              ← 命令失败但忽略 → success=True
    else:
        success = False             ← 命令失败，不忽略 → success=False


    交互式 (matched_prompt):
    ═══════════════════════════════

    if matched_prompt:
        success = True              ← prompt 匹配
    elif ignore_err:
        success = True              ← prompt 不匹配但忽略 → success=True
    else:
        success = False             ← prompt 不匹配，不忽略 → success=False
```

### 2. Return Dictionary Structure

```python
{
    'success': bool,    # True if: (1) command succeeded, OR (2) ignore_err=True
    'stdout': str,      # stdout content (stripped)
    'stderr': str       # stderr content (stripped), empty string if no error
}
```

### 3. Unified Error Handling (Non-Interactive) - No Exceptions

```python
def _direct_exec_cmd(self, cmd, timeout=None, environment=None, cwd=None, ignore_err=False):
    if cwd:
        cmd = f"cd {shlex.quote(cwd)} && {cmd}"
    quoted_cmd = shlex.quote(cmd)
    cmd_prefix = f"bash -l -c {quoted_cmd}"
    
    _, stdout, stderr = self.client.exec_command(
        cmd_prefix, timeout=timeout, environment=environment
    )
    
    stdout_content = stdout.read().decode('utf-8').strip()
    stderr_content = stderr.read().decode('utf-8').strip()
    exit_code = stdout.channel.recv_exit_status()
    
    self.logger.info(f"[Ssh._direct_exec_cmd] executed: {cmd}, exit_code={exit_code}")
    
    if exit_code != 0:
        self.logger.warning(f"[Ssh._direct_exec_cmd] error: {stderr_content}")
    
    if exit_code == 0:
        success = True
    elif ignore_err:
        success = True
    else:
        success = False
    
    return {
        'success': success,
        'stdout': stdout_content,
        'stderr': stderr_content
    }


def _jump_exec_command(self, cmd, timeout=None, environment=None, cwd=None, ignore_err=False):
    if cwd:
        cmd = f"cd {shlex.quote(cwd)} && {cmd}"
    quoted_cmd = shlex.quote(cmd)
    cmd_prefix = f"bash -l -c {quoted_cmd}"
    
    stdin, stdout, stderr = self.target_client.exec_command(
        cmd_prefix, timeout=timeout, environment=environment
    )
    
    stdout_content = stdout.read().decode('utf-8').strip()
    stderr_content = stderr.read().decode('utf-8').strip()
    exit_code = stdout.channel.recv_exit_status()
    
    self.logger.info(f"[Ssh._jump_exec_command] executed: {cmd}, exit_code={exit_code}")
    
    if exit_code != 0:
        self.logger.warning(f"[Ssh._jump_exec_command] error: {stderr_content}")
    
    if exit_code == 0:
        success = True
    elif ignore_err:
        success = True
    else:
        success = False
    
    return {
        'success': success,
        'stdout': stdout_content,
        'stderr': stderr_content
    }
```

**Key changes:**

| Aspect | Before | After |
|--------|--------|-------|
| Error detection | Different between methods | Unified: `exit_code != 0` |
| Exception | Thrown on failure | **Never thrown** |
| success calculation | N/A | `exit_code == 0` OR `ignore_err=True` |
| Return type | `str` | `dict` |
| Logging | Inconsistent | Unified: info + warning |

### 4. Interactive Mode with matched_prompt - No Exceptions

```python
def _direct_exec_cmd_interactive(self, cmd, expect_prompt, timeout=30, cwd=None, ignore_err=False):
    try:
        if cwd:
            self.channel.send(f"cd {shlex.quote(cwd)} && {cmd}\n")
        else:
            self.channel.send(cmd + '\n')
        
        output = ''
        matched_prompt = False
        start_time = time.time()
        
        if expect_prompt is None:
            prompt_patterns = [
                r'[$#%>]\s*$',
                r'[\w-]+@[\w-]+[:~][\w/]*[$#%>]\s*$',
                r'\]\s*#\s*$',
            ]
            expect_prompt = '|'.join(prompt_patterns)
        
        prompt_regex = re.compile(expect_prompt, re.MULTILINE)
        
        while time.time() - start_time < timeout:
            if self.channel.recv_ready():
                output += self.channel.recv(1024).decode("utf-8")
                if prompt_regex.search(output):
                    matched_prompt = True
                    break
            else:
                time.sleep(0.1)
        
        self.logger.info(f"[Ssh._direct_exec_cmd_interactive] matched_prompt={matched_prompt}")
        
        if not matched_prompt:
            self.logger.warning(
                f"[Ssh._direct_exec_cmd_interactive] prompt not matched"
            )
        
        if matched_prompt:
            success = True
        elif ignore_err:
            success = True
        else:
            success = False
        
        return {
            'success': success,
            'stdout': output,
            'stderr': ""
        }
    except Exception as e:
        self.logger.error(f"[Ssh._direct_exec_cmd_interactive] Details: {traceback.format_exc()}")
        raise
```

### 5. Edge Cases

| Case | success | stdout | stderr | Exception |
|------|---------|--------|--------|-----------|
| `exit_code == 0` | `True` | stdout_content | stderr_content | **No** |
| `exit_code != 0`, `ignore_err=False` | `False` | stdout_content | stderr_content | **No** |
| `exit_code != 0`, `ignore_err=True` | `True` | stdout_content | stderr_content | **No** |
| Prompt matched | `True` | collected output | `""` | **No** |
| Prompt not matched, `ignore_err=False` | `False` | collected output | `""` | **No** |
| Prompt not matched, `ignore_err=True` | `True` | collected output | `""` | **No** |
| Connection lost | N/A | N/A | N/A | **Yes** (not affected by ignore_err) |

### 6. Usage Examples

```python
result = device.sendcmd("ls /nonexistent", ignore_err=False)
# result = {'success': False, 'stdout': '', 'stderr': '...'}
# Caller checks: if not result['success']: handle failure

result = device.sendcmd("ls /nonexistent", ignore_err=True)
# result = {'success': True, 'stdout': '', 'stderr': '...'}
# Error was ignored, success=True

result = device.sendcmd("ls", ignore_err=False)
# result = {'success': True, 'stdout': 'file1\nfile2', 'stderr': ''}
# Command succeeded
```

## Success Criteria Mapping

**需求 1**: 增加 ignore_err 参数
- ✅ 支持忽略预期内的报错
- ✅ `ignore_err=True` 时，`success=True`（成功忽略错误）
- ✅ stderr 打印日志，同时返回在字典中

**需求 2**: 返回命令是否成功
- ✅ 返回字典包含 `success` 字段
- ✅ **永不抛异常**，调用者检查 `result['success']`
- ✅ `success=True`：命令成功 或 成功忽略错误
- ✅ `success=False`：命令失败且不忽略

**新增特性**: matched_prompt tracking
- ✅ 交互式命令跟踪 prompt 匹配状态
- ✅ `matched_prompt=True` → `success=True`
- ✅ `matched_prompt=False` + `ignore_err=True` → `success=True`
- ✅ `matched_prompt=False` + `ignore_err=False` → `success=False`

## File Changes

### `pytest_testkit/lib/base/ssh.py`
- Add `ignore_err=False` parameter to `ssh_cmd()` and `ssh_cmd_interactive()`
- Change return type from `str` to `dict`
- **Remove all RuntimeError raises** - use `success` field instead
- Unify `_direct_exec_cmd()` and `_jump_exec_command()` error handling
- Add `matched_prompt` tracking in interactive commands

### `pytest_testkit/lib/common/environment/device.py`
- Add `ignore_err=False` parameter to `sendcmd()` and `sendcmd_interactive()`
- Update return type handling (pass through dict from ssh methods)
- Update docstrings