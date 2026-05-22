# Design: Add `cwd` Parameter to SSH Command Execution

## Overview

This change adds a `cwd` parameter to SSH command execution methods, allowing users to specify the working directory for command execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Call Chain (After Change)                          │
└─────────────────────────────────────────────────────────────────────────────┘

Device.sendcmd(cmd, timeout, environment, cwd)
        │
        ▼
Ssh.ssh_cmd(cmd, timeout, environment, cwd)
        │
        ├──────────────────────┬─────────────────────┐
        ▼                      ▼                     │
_direct_exec_cmd()     _jump_exec_command()         │
        │                      │                     │
        ▼                      ▼                     │
┌─────────────────────────────────────────────┐     │
│  if cwd:                                     │     │
│      cmd = f"cd {shlex.quote(cwd)} && {cmd}"│     │
│  cmd = f"bash -l -c {shlex.quote(cmd)}"     │     │
└─────────────────────────────────────────────┘     │
                                                   │
                                                   │
Device.sendcmd_interactive(cmd, expect_prompt,     │
                          timeout, cwd) ◄──────────┘
        │
        ▼
Ssh.ssh_cmd_interactive(cmd, expect_prompt, timeout,
                        send_input, cwd)
        │
        ├──────────────────────┬─────────────────────┐
        ▼                      ▼                     │
_direct_exec_cmd_interactive() _jump_exec_cmd_interactive()
        │                      │
        ▼                      ▼
┌─────────────────────────────────────────────┐
│  if cwd:                                     │
│      channel.send(f"cd {cwd} && {cmd}\n")   │
└─────────────────────────────────────────────┘
```

## Implementation Details

### 1. Parameter Addition

| Method | Location | New Parameter |
|--------|----------|---------------|
| `Ssh.ssh_cmd()` | `ssh.py:121` | `cwd=None` |
| `Ssh.ssh_cmd_interactive()` | `ssh.py:131` | `cwd=None` |
| `Device.sendcmd()` | `device.py:220` | `cwd=None` |
| `Device.sendcmd_interactive()` | `device.py:252` | `cwd=None` |

### 2. Command Transformation (Non-Interactive)

For non-interactive commands, transform the command before execution:

```python
def _direct_exec_cmd(self, cmd, timeout=None, environment=None, cwd=None):
    if cwd:
        cmd = f"cd {shlex.quote(cwd)} && {cmd}"
    quoted_cmd = shlex.quote(cmd)
    cmd_prefix = f"bash -l -c {quoted_cmd}"
    # ... existing execution logic
```

**Why `shlex.quote()`?** Prevents shell injection when directory path contains spaces or special characters.

### 3. Command Transformation (Interactive)

For interactive commands, send the directory change first:

```python
def _direct_exec_cmd_interactive(self, cmd, expect_prompt, send_input,
                                  timeout=30, cwd=None):
    if cwd:
        self.channel.send(f"cd {shlex.quote(cwd)} && {cmd}\n")
    else:
        self.channel.send(cmd + '\n')
    # ... existing logic
```

### 4. Edge Cases

| Case | Handling |
|------|----------|
| `cwd=None` | No transformation, existing behavior |
| `cwd="/path with spaces"` | Properly quoted via `shlex.quote()` |
| `cwd="/nonexistent"` | Shell returns error, propagated to caller |
| `cwd=""` (empty string) | Treated as `None`, no transformation |

## File Changes

### `pytest_testkit/lib/base/ssh.py`

1. `ssh_cmd()`: Add `cwd=None` parameter, pass to internal methods
2. `ssh_cmd_interactive()`: Add `cwd=None` parameter, pass to internal methods
3. `_direct_exec_cmd()`: Add `cwd` handling, transform command
4. `_jump_exec_command()`: Add `cwd` handling, transform command
5. `_direct_exec_cmd_interactive()`: Add `cwd` handling
6. `_jump_exec_cmd_interactive()`: Add `cwd` handling

### `pytest_testkit/lib/common/environment/device.py`

1. `sendcmd()`: Add `cwd=None` parameter, pass to `ssh_cmd()`
2. `sendcmd_interactive()`: Add `cwd=None` parameter, pass to `ssh_cmd_interactive()`

## Security Considerations

- Use `shlex.quote()` for all directory paths to prevent shell injection
- Do not allow arbitrary shell commands in `cwd` parameter
- Directory paths are treated as literal paths, not shell expressions